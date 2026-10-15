# ACMP-Server-Config-Tool

Extract and repack the game settings archives (`.cxb` and `.smallpox`) used by
Assassin's Creed Brotherhood (ACB), Revelations (ACR) and III (AC3).

- `extract.py` extracts an archive into editable, indented XML files.
- `repack.py` packs those XML files back into an archive.

## Requirements

- Python 3.7 or newer. Only the standard library is used.
- The LZO2 compression library:
  - **Windows:** `liblzo2-2.dll` is included. Keep it next to the scripts.
  - **Linux:** install the development package, which provides `liblzo2.so`
    (for example `sudo apt install liblzo2-dev` on Debian/Ubuntu).

## Usage

Put the scripts and the archives you want to work on in the same folder.

### 1. Extract

```
python extract.py
```

Choose an archive from the list. Its XML is saved under `xml_folder/`:

| Archive                         | Extracted to                 |
|---------------------------------|------------------------------|
| `*.cxb`                         | `xml_folder/CXB/`            |
| `*_step_N.smallpox`             | `xml_folder/STEP_N/`         |
| `*_param_changes.smallpox`      | `xml_folder/PARAM_CHANGES/`  |

Extracting overwrites XML files with the same name in that folder, so commit or back up any
edits first.

`.cxb` XML is indented with one tag per line so it is easy to read, edit and diff. Only
whitespace between tags is added; the attributes and tags themselves are not changed.

### 2. Edit

Edit the XML files in `xml_folder/` with any text editor.

### 3. Repack

```
python repack.py
```

1. Enter the output filename, including the extension (`.cxb` or `.smallpox`). The extension
   and name decide which folder is packed, using the table above.
2. For a `.cxb`, choose the layout of the game you are packing for:

   | Option | Game     | File table entry |
   |--------|----------|------------------|
   | 1      | ACB      | 32+8 bytes       |
   | 2      | ACR/AC3  | 40+8 bytes       |

   The layout must match the game, so pick the one for the game the archive came from.

The archive is written next to the scripts.

- **`.cxb`:** every XML file in `xml_folder/CXB/` is packed, in alphabetical order. The
  indentation is removed again so the XML is stored raw on a single line. An unedited ACB or ACR
  archive repacks byte-identical to the original.
- **`.smallpox`:** a single XML file is packed, as-is. The file named after the archive is used
  if it exists; otherwise you are asked to pick one.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Credits

Special thanks to [@munnich](https://github.com/munnich) for providing the foundation for this tool.
