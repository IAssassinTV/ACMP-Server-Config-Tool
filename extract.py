import struct
import string
import re
import os
import sys
import ctypes
from zlib import adler32
from pathlib import Path
import xml.etree.ElementTree as ET

# Windows consoles may not encode the status symbols (✅, ⚠️); replace them instead of crashing.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

# A tag (attribute values may contain '>') or the text between two tags
XML_TOKEN = re.compile(rb'<(?:"[^"]*"|\'[^\']*\'|[^\'">])*>|[^<]+')

def format_xml_minimal(file_path):
    """
    Indent an XML file with one tag per line.
    Only whitespace between tags is added, so attributes and tags stay exactly as stored and
    repack.py can restore the raw XML by removing that whitespace again.
    This function is called automatically after extraction.
    """
    try:
        # Read the file in binary to preserve exact bytes
        with open(file_path, 'rb') as f:
            content = f.read()

        try:
            ET.fromstring(content)
        except ET.ParseError as e:
            print(f"Warning: XML parsing error in {file_path}: {e}. Leaving it unformatted.")
            return False

        tokens = [t for t in XML_TOKEN.findall(content) if t.strip()]
        lines = []
        depth = 0
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith(b'</'):
                depth = max(0, depth - 1)
                lines.append(b'  ' * depth + token)
            elif not token.startswith(b'<'):
                # Text next to child elements: indenting around it would change the text
                print(f"Warning: {file_path} mixes text and elements. Leaving it unformatted.")
                return False
            elif i + 2 < len(tokens) and not tokens[i + 1].startswith(b'<') and tokens[i + 2].startswith(b'</'):
                # Keep <tag>text</tag> on one line
                lines.append(b'  ' * depth + b''.join(tokens[i:i + 3]))
                i += 3
                continue
            else:
                lines.append(b'  ' * depth + token)
                if not token.endswith(b'/>') and not token.startswith((b'<?', b'<!')):
                    depth += 1
            i += 1

        # Write back the file
        with open(file_path, 'wb') as f:
            f.write(b'\n'.join(lines) + b'\n')

        print(f"Formatted: {os.path.basename(file_path)}")
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False

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

def decompress_LZO2A(compressed_data, expected_decompressed_size):
    # allocate buffers
    src = ctypes.create_string_buffer(compressed_data)
    dst = ctypes.create_string_buffer(expected_decompressed_size)

    result = lzo2.lzo2a_decompress_safe(
        ctypes.byref(src),
        len(compressed_data),
        ctypes.byref(dst),
        ctypes.pointer(ctypes.c_int(expected_decompressed_size)),
        None
    )
    if result:
        raise ValueError(f"Decompression failed with code {result}")

    print("Decompressed successfully")
    return dst.raw

# Find all supported archive files in the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
archive_files = [
    f for f in os.listdir(script_dir)
    if f.lower().endswith(('.cxb', '.smallpox'))
]

if not archive_files:
    raise FileNotFoundError(f"No .cxb or .smallpox files found in the script directory: {script_dir}")

# Let user select a file
print("\nAvailable archive files:")
for i, file in enumerate(archive_files, 1):
    print(f"{i}. {file}")

while True:
    try:
        selection = input(f"\nSelect a file (1-{len(archive_files)}, or press Enter for first file): ")
        if not selection:
            binary_file_path = os.path.join(script_dir, archive_files[0])  # Default to first file if no input
            break
        idx = int(selection) - 1
        if 0 <= idx < len(archive_files):
            binary_file_path = os.path.join(script_dir, archive_files[idx])
            break
        print(f"Please enter a number between 1 and {len(archive_files)}")
    except ValueError:
        print("Please enter a valid number")

print(f"\nSelected file: {binary_file_path}")

def get_xml_subfolder(archive_name):
    """
    Folder inside xml_folder that holds the XML of an archive:
    .cxb -> CXB, *_step_N.smallpox -> STEP_N, *_param_changes.smallpox -> PARAM_CHANGES.
    """
    name = archive_name.lower()
    if name.endswith(".cxb"):
        return "CXB"
    match = re.search(r"_(step_\d+|param_changes)\.smallpox$", name)
    return match.group(1).upper() if match else ""

output_dir = os.path.join(script_dir, "xml_folder", get_xml_subfolder(os.path.basename(binary_file_path)))
os.makedirs(output_dir, exist_ok=True)
print(f"Extracting to: {output_dir}")

magic_number = 0x1004FA9957FBAA33
magic_bytes = struct.pack("<Q", magic_number)

with open(binary_file_path, "rb") as f:
    data = f.read()

indices = []
i = data.find(magic_bytes)
while i != -1:
    indices.append(i)
    i = data.find(magic_bytes, i + 1)

def create_dict(strings):
    result = {}
    i = 0
    while i < len(strings) - 1:
        key = strings[i]
        value = strings[i + 1]
        if value and value[0].isdigit():
            result[key] = int(value)
            i += 2
        else:
            break
    return result

def extract_starting_bytes(data, n, to_int = False):
    d = data[:n]
    if to_int:
        d = int.from_bytes(d, byteorder="little")
    return d, data[n:]

archive_ext = os.path.splitext(binary_file_path)[1].lower()

def extract_archive_entry(entry_name, entry_size, entry_index, use_pre_magic_name):
    index = entry_index
    start = index - 4
    end = start + entry_size
    s = data[start:end]
    size, s = extract_starting_bytes(s, 4)
    size = int.from_bytes(size, byteorder='little') # size of the actual XML # type: ignore
    magic, s = extract_starting_bytes(s, 8)
    version, s = extract_starting_bytes(s, 2, True)
    algo, s = extract_starting_bytes(s, 1, True)
    en_bufsize, s = extract_starting_bytes(s, 2, True) # size of buffer to hold compressed data
    de_bufsize, s = extract_starting_bytes(s, 2, True) # size of buffer to hold decompressed data
    print(f"""Segment data:
    Uncompressed XML size: {size}
    Magic: {magic}
    Version: {version}
    Algo: {algo}
    Decompression buffer size: {de_bufsize}
    Compression buffer size: {en_bufsize}""")

    ref = os.path.join(output_dir, f"{entry_name}.xml")
    if os.path.exists(ref):
        print(f"\nReference file size: {os.path.getsize(ref)}\n")
    else:
        print()

    try:
        offset = 0  # Start of binary payload
        chunks = []

        while offset < len(s):
            try:
                # Read compression flag
                is_compressed = s[offset]
                offset += 1

                if is_compressed:
                    # Read compressed block header
                    en_size = int.from_bytes(s[offset:offset+4], "little") # size of compressed data in buffer
                    offset += 4
                    de_size = int.from_bytes(s[offset:offset+4], "little") # size of decompressed data in buffer
                    offset += 4
                    checksum = int.from_bytes(s[offset:offset+4], "little")
                    offset += 4
                    if en_size == 0 and de_size == 0 and checksum == 0:
                        break
                    print(f"""Block data:
                            Compressed: {is_compressed}
                            Decompression size: {de_size}
                            Compression size: {en_size}
                            Checksum: {checksum}
                        """)
                    # Extract compressed data
                    comp_data = s[offset:offset+en_size]
                    offset += en_size

                    # Validate checksum
                    calc_checksum = adler32(comp_data, 0)
                    if calc_checksum != checksum:
                        print(f"⚠️ Checksum mismatch at offset {offset}: expected {hex(checksum)}, got {hex(calc_checksum)}")

                    # Decompress
                    chunk = decompress_LZO2A(comp_data, de_size)
                    chunks.append(chunk)
                else:
                    # Uncompressed block
                    data_size = int.from_bytes(s[offset:offset+4], "little")
                    if data_size == 0:
                        break
                    print(f"""Block data:
                        Compressed: {is_compressed}
                        Data size: {data_size}
                        """)
                    offset += 4
                    chunk = s[offset:offset+data_size]
                    offset += data_size
                    chunks.append(chunk)

            except Exception as e:
                print(f"❌ Error at offset {offset}: {e}")
                break

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {os.path.abspath(output_dir)}")

        # Combine all chunks. The stored XML ends with a NUL terminator; drop it so the extracted file is
        # plain text (git diffs it normally). repack.py adds it back when packing.
        full_data = b"".join(chunks).rstrip(b"\x00")
        if full_data:
            f_out = os.path.join(output_dir, f"{entry_name}.xml")
            with open(f_out, "wb") as f:
                f.write(full_data)
            print(f"Saved decompressed data to {f_out}")

            if archive_ext == ".cxb":
                format_xml_minimal(f_out)
    except Exception as e:
        print(f"Decompression failed: {e}")

def extract_cxb_archive(binary_file_path, data):
    pre_magic_data = data[:indices[0]]

    # convert to string
    decoded = ''.join(chr(b) if chr(b) in string.printable else ' ' for b in pre_magic_data)

    # remove padding
    segments = [s for s in re.split(r'\s+', decoded) if s]

    print("Extracted segments:")
    segments = [(segments[i], int(segments[i + 1])) for i in range(0, len(segments) - 2, 2)]
    print("XML, size:", segments)
    for i in range(len(indices)):
        print(f"Analyzing {segments[i][0]}")
        extract_archive_entry(segments[i][0], segments[i][1], indices[i], True)

def extract_smallpox_archive(binary_file_path, data):
    archive_stem = os.path.splitext(os.path.basename(binary_file_path))[0]

    print("Extracted segments:")
    print("XML, size: []")
    for i in range(len(indices)):
        entry_name = archive_stem if len(indices) == 1 else f"{archive_stem}_{i + 1}"
        print(f"Analyzing {entry_name}")
        extract_archive_entry(entry_name, len(data) - (indices[i] - 4), indices[i], False)

if archive_ext == ".cxb":
    extract_cxb_archive(binary_file_path, data)
elif archive_ext == ".smallpox":
    extract_smallpox_archive(binary_file_path, data)
else:
    raise ValueError(f"Unsupported archive extension: {archive_ext}")

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    script_dir = os.path.dirname(os.path.abspath(__file__))
    xml_folder = os.path.join(script_dir, "xml_folder")
    if not os.path.exists(xml_folder):
        os.makedirs(xml_folder)
        print(f"Created directory: {os.path.abspath(xml_folder)}")
        
    # Run the extraction and formatting
    try:
        # The actual execution happens when the script is imported
        pass
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
