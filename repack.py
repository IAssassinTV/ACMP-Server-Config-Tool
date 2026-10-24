import os
import re
import struct
import ctypes
import sys
from zlib import adler32, crc32
from hashlib import md5

# Windows consoles may not encode every path or name; replace what they cannot encode instead of crashing.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

# State messages are colored when the console supports ANSI escapes (Windows 10+ needs them enabled).
def _supports_color():
    if not sys.stdout.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        mode = ctypes.c_uint32()
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        return False

USE_COLOR = _supports_color()

def _color(message, code):
    return f"\033[{code}m{message}\033[0m" if USE_COLOR else message

def success(message):
    print(_color(message, "32"))  # green

def warning(message):
    print(_color(message, "33"))  # yellow

def error(message):
    print(_color(message, "31"))  # red

# Try to load LZO2 library with different possible names/paths
lzo2 = None
lzo_paths = [
    'lzo2.dll',  # Common Windows name
    'liblzo2-2.dll',  # Alternative Windows name
    'liblzo2.so',  # Linux name
    'liblzo2.dylib'  # macOS name
]

if sys.platform == 'win32':
    # On Windows, try to find the DLL in the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lzo_paths = [os.path.join(script_dir, path) for path in lzo_paths] + lzo_paths

for path in lzo_paths:
    try:
        lzo2 = ctypes.CDLL(path)
        print(f"Successfully loaded LZO2 library from: {path}")
        break
    except (OSError, FileNotFoundError):
        continue

if lzo2 is None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dll_path = os.path.join(script_dir, 'lzo2.dll')
    
    print("="*80)
    print("LZO2 library not found. To fix this:")
    print(f"1. Download 'lzo2.dll' from a trusted source")
    print(f"2. Save it to: {dll_path}")
    print("3. Run the script again")
    print("="*80)
    
    # Create a placeholder file with instructions
    with open(os.path.join(script_dir, 'GET_LZO2_DLL.txt'), 'w') as f:
        f.write("INSTRUCTIONS TO GET LZO2.DLL\n")
        f.write("="*40 + "\n")
        f.write("1. Download 'lzo2.dll' from one of these sources:\n")
        f.write("   - https://www.dll-files.com/lzo2.dll.html\n")
        f.write("   - Or search for 'lzo2.dll download for Windows'\n")
        f.write(f"2. Place the downloaded 'lzo2.dll' in this directory:\n   {script_dir}\\n")
        f.write("3. Run the script again\n")
    
    raise ImportError("LZO2 library not found. Please follow the instructions above.")

def compress_LZO2A_999(data: bytes) -> bytes:
    src_len = len(data)
    dst_len_estimate = src_len + src_len // 16 + 64 + 3
    wrkmem_size = 8 * 16384 * ctypes.sizeof(ctypes.c_short)

    # Allocate buffers
    src = (ctypes.c_ubyte * src_len).from_buffer_copy(data)
    dst = (ctypes.c_ubyte * dst_len_estimate)()
    dst_len = ctypes.c_int(dst_len_estimate)
    wrkmem = (ctypes.c_ubyte * wrkmem_size)()

    # Call compression
    result = lzo2.lzo2a_999_compress(
        src,
        src_len,
        dst,
        ctypes.byref(dst_len),
        wrkmem
    )

    if result != 0:
        raise ValueError(f"LZO2A-999 compression failed with code {result}")

    return bytes(dst[:dst_len.value])

# A tag (attribute values may contain '>') or the text between two tags
XML_TOKEN = re.compile(rb'<(?:"[^"]*"|\'[^\']*\'|[^\'">])*>|[^<]+')

def minify_xml(xml_data: bytes) -> bytes:
    """
    Undo the indentation extract.py adds on extraction: drop the whitespace between tags so the
    XML is packed raw, on a single line.
    """
    return b"".join(t for t in XML_TOKEN.findall(xml_data) if t.strip())

def read_xml_as_bytes(path: str, minify: bool = False) -> bytes:
    # Preserve the XML bytes exactly as stored on disk, apart from the optional minify.
    with open(path, "rb") as f:
        xml_data = f.read()

    if minify:
        xml_data = minify_xml(xml_data)

    # Ensure the XML ends with a null byte
    if not xml_data.endswith(b'\x00'):
        xml_data += b'\x00'

    return xml_data

def build_file_data(xml_data: bytes) -> bytes:
    uncompressed_size = len(xml_data)

    # Split XML into chunks of DECOMP_BUFFER_SIZE
    chunks = [
        xml_data[i:i + DECOMP_BUFFER_SIZE]
        for i in range(0, len(xml_data), DECOMP_BUFFER_SIZE)
    ]

    blocks = []
    for chunk in chunks:
        de_size = len(chunk)
        comp_data = compress_LZO2A_999(chunk)
        en_size = len(comp_data)
        checksum = adler32(comp_data, 0)

        block = struct.pack(
            "<BIII",  # is_compressed = 1, de_size, en_size, checksum
            1,
            en_size,
            de_size,
            checksum,
        ) + comp_data

        blocks.append(block)

    # Build CompressedFileData
    return struct.pack(
        "<I Q H B H H",  # size, magic, version, algo, de_bufsize, en_bufsize
        uncompressed_size,
        MAGIC,
        VERSION,
        ALGO,
        DECOMP_BUFFER_SIZE,
        COMP_BUFFER_SIZE,
    ) + b"".join(blocks)

# Constants
MAGIC = 0x1004FA9957FBAA33
VERSION = 1
ALGO = 2  # LZO2A
DECOMP_BUFFER_SIZE = 32768
COMP_BUFFER_SIZE = 0

# .cxb file table layouts: each entry is a NUL-padded name field followed by an 8-byte size field
CXB_LAYOUTS = [
    ("ACB", 32),          # 32+8
    ("ACR/AC3/AC4", 40),  # 40+8
]
SIZE_FIELD_SIZE = 8

def ask_cxb_layout():
    """
    Ask which game the .cxb is for and return the size of its file table name field.
    """
    print("Available .cxb layouts:")
    for i, (game, name_size) in enumerate(CXB_LAYOUTS, 1):
        print(f"{i}. {game} ({name_size}+{SIZE_FIELD_SIZE} buffer)")

    while True:
        try:
            selection = input(f"Select the .cxb layout (1-{len(CXB_LAYOUTS)}): ").strip()
            idx = int(selection) - 1
            if 0 <= idx < len(CXB_LAYOUTS):
                return CXB_LAYOUTS[idx][1]
            warning(f"Please enter a number between 1 and {len(CXB_LAYOUTS)}")
        except ValueError:
            warning("Please enter a valid number")

# .smallpox layouts: whether the file ends with a 0x01 byte after the compressed data
SMALLPOX_LAYOUTS = [
    ("AC3", True),
    ("AC4", False),
]

def ask_smallpox_layout():
    """
    Ask which game the .smallpox is for and return whether it ends with the 0x01 byte.
    """
    print("Available .smallpox layouts:")
    for i, (game, trailing_byte) in enumerate(SMALLPOX_LAYOUTS, 1):
        print(f"{i}. {game} ({'ends with 0x01' if trailing_byte else 'no trailing byte'})")

    while True:
        try:
            selection = input(f"Select the .smallpox layout (1-{len(SMALLPOX_LAYOUTS)}): ").strip()
            idx = int(selection) - 1
            if 0 <= idx < len(SMALLPOX_LAYOUTS):
                return SMALLPOX_LAYOUTS[idx][1]
            warning(f"Please enter a number between 1 and {len(SMALLPOX_LAYOUTS)}")
        except ValueError:
            warning("Please enter a valid number")

def get_xml_subfolder(archive_name):
    """
    Folder inside xml_folder that holds the XML of an archive: .cxb -> CXB, a .smallpox -> the part
    of its name after gamesettings_c<number>_ in upper case with words split by underscores, e.g.
    *_step_0 -> STEP_0, *_param_changes -> PARAM_CHANGES, *_TestCompatPack -> TEST_COMPAT_PACK.
    """
    if archive_name.lower().endswith(".cxb"):
        return "CXB"
    match = re.search(r"_c\d+_(.+)\.smallpox$", archive_name, re.IGNORECASE)
    if not match:
        return ""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", match.group(1)).upper()

def pack_xml_files():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Ask user for full filename
    while True:
        try:
            filename = input("Enter full filename to save as (including .cxb or .smallpox extension): ").strip()
            if not filename:
                warning("Filename cannot be empty.")
                continue
            if not filename.lower().endswith(('.cxb', '.smallpox')):
                warning("Please save the file with either a .cxb or .smallpox extension.")
                continue
            output_file = os.path.join(script_dir, filename)
            output_ext = os.path.splitext(output_file)[1].lower()
            break
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return

    # Input folder
    input_folder = os.path.join(script_dir, "xml_folder", get_xml_subfolder(os.path.basename(output_file)))
    print(f"Packing from: {input_folder}")

    # Get all XML files from the input folder
    file_names = sorted(f for f in os.listdir(input_folder) if f.lower().endswith('.xml'))

    if output_ext == '.smallpox':
        preferred_name = os.path.splitext(os.path.basename(output_file))[0] + '.xml'
        preferred_path = os.path.join(input_folder, preferred_name)

        if os.path.exists(preferred_path):
            selected_files = [preferred_name]
        elif len(file_names) == 1:
            selected_files = file_names
        else:
            print("Available XML files:")
            for i, file in enumerate(file_names, 1):
                print(f"{i}. {file}")

            while True:
                try:
                    selection = input(f"Select the XML file to pack (1-{len(file_names)}): ").strip()
                    idx = int(selection) - 1
                    if 0 <= idx < len(file_names):
                        selected_files = [file_names[idx]]
                        break
                    warning(f"Please enter a number between 1 and {len(file_names)}")
                except ValueError:
                    warning("Please enter a valid number")

        name = selected_files[0]
        path = os.path.join(input_folder, name)
        print(f"Processing {name}...")

        try:
            xml_data = read_xml_as_bytes(path)
        except Exception as e:
            warning(f"Could not process {name} - {str(e)}.")
            return

        file_data = build_file_data(xml_data)
        if ask_smallpox_layout():
            file_data += b"\x01"

        with open(output_file, "wb") as f:
            f.write(file_data)

        success(f"Successfully created {output_file} with 1 XML file")
        return

    name_size = ask_cxb_layout()

    file_infos = []
    file_datas = []

    for name in file_names:
        path = os.path.join(input_folder, name)
        print(f"Processing {name}...")

        try:
            xml_data = read_xml_as_bytes(path, minify=True)
        except Exception as e:
            warning(f"Could not process {name} - {str(e)}. Skipping...")
            continue

        entry_name = name.split(".")[0].encode("ascii")
        if len(entry_name) >= name_size:
            warning(f"{name} - name is too long for a {name_size}+{SIZE_FIELD_SIZE} entry. Skipping...")
            continue

        file_data = build_file_data(xml_data)
        file_datas.append(file_data)

        # Build FileInfo
        name_buffer = entry_name.ljust(name_size, b"\x00")
        size_str = str(len(file_data)).encode("ascii").ljust(SIZE_FIELD_SIZE, b"\x00")
        file_info = name_buffer + size_str
        file_infos.append(file_info)

    # Write final CXB file
    with open(output_file, "wb") as f:
        # Write file infos
        all_infos = b''.join(file_infos)
        f.write(all_infos)

        # Write end marker
        f.write(b"0".ljust(name_size + SIZE_FIELD_SIZE, b"\x00"))

        # Write file datas
        all_data = b''.join(file_datas)
        f.write(all_data)

    success(f"Successfully created {output_file} with {len(file_names)} XML files")

if __name__ == "__main__":
    pack_xml_files()