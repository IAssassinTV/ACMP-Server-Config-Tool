# ACMP-Server-Config-Tool

Extract and repack the game settings archives (`.cxb` and `.smallpox`) used by
Assassin's Creed Brotherhood (ACB), Revelations (ACR), III (AC3) and IV Black Flag (AC4).

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

| Archive                                 | Extracted to                            |
|-----------------------------------------|-----------------------------------------|
| `*.cxb`                                 | `xml_folder/CXB/`                       |
| `*_step_N.smallpox`                     | `xml_folder/STEP_N/`                    |
| `*_param_changes.smallpox`              | `xml_folder/PARAM_CHANGES/`             |
| `*_pc_specific.smallpox`                | `xml_folder/PC_SPECIFIC/`               |
| `*_TestCompatPack.smallpox`             | `xml_folder/TEST_COMPAT_PACK/`          |
| `*_EventRewardAPlusHack.smallpox`       | `xml_folder/EVENT_REWARD_A_PLUS_HACK/`  |

A `.smallpox` goes into the folder named after the part of its name that follows
`gamesettings_c<number>_`, in upper case with its words split by underscores.

An AC4 `.smallpox` saved from an official server reply still starts with the reply's 4-byte
length and ends with a `0x01` byte; `extract.py` reads it either way.

Extracting overwrites XML files with the same name in that folder, so commit or back up any
edits first.

`.cxb` XML is indented with one tag per line so it is easy to read, edit and diff. Only
whitespace between tags is added; the attributes, tags and text themselves are not changed.
Text that sits next to elements (AC4's `playlistconfig.xml` has a few stray `-->` text nodes) is
kept byte for byte on the line of the tag before it, because indenting it would change the text.

### 2. Edit

Edit the XML files in `xml_folder/` with any text editor.

### 3. Repack

```
python repack.py
```

1. Enter the output filename, including the extension (`.cxb` or `.smallpox`). The extension
   and name decide which folder is packed, using the table above.
2. Choose the layout of the game you are packing for:

   | Archive     | Option | Game         | Layout                                 |
   |-------------|--------|--------------|----------------------------------------|
   | `.cxb`      | 1      | ACB          | 32+8 byte file table entries           |
   | `.cxb`      | 2      | ACR/AC3/AC4  | 40+8 byte file table entries           |
   | `.smallpox` | 1      | AC3          | ends with a `0x01` byte                |
   | `.smallpox` | 2      | AC4          | no trailing byte                       |

   The layout must match the game, so pick the one for the game the archive came from. ACB and ACR
   have no `.smallpox` archives, so only AC3 and AC4 are listed for them.

The archive is written next to the scripts.

- **`.cxb`:** every XML file in `xml_folder/CXB/` is packed, in alphabetical order. The
  indentation is removed again so the XML is stored raw on a single line. An unedited ACB or ACR
  archive repacks byte-identical to the original.
- **`.smallpox`:** a single XML file is packed, as-is. The file named after the archive is used
  if it exists; otherwise you are asked to pick one. An unedited AC4 `.smallpox` repacks
  byte-identical to the original, minus the reply's length and trailing byte.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Credits

Special thanks to [@munnich](https://github.com/munnich) for providing the foundation for this tool.
