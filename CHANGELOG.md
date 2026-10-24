# Changelog

All notable changes to ACMP-Server-Config-Tool are listed here, newest first.

## 2026-10-24

### Fixed
- `extract.py` no longer leaves an XML file unformatted when it mixes text and elements (AC4's
  `playlistconfig.xml` has a few stray `-->` text nodes). The text is kept byte for byte on the
  line of the tag before it and only the whitespace between tags is added, so repacking still
  restores the original bytes.

### Changed
- Console output no longer uses emoji. Successes are green, warnings yellow and errors red when
  the console supports ANSI colors; redirected output stays plain.
- `extract.py` prints one line per archive segment and a blank line before each `Analyzing` block,
  so the output of one XML file is easy to tell apart from the next.
- `repack.py` lists the `.smallpox` layouts as **AC3** and **AC4** only, because ACB and ACR have
  no `.smallpox` archives.

## 2026-10-21

### Added
- Assassin's Creed IV Black Flag (AC4) support.
  - `repack.py` asks for the `.smallpox` layout too: **ACB/ACR/AC3** (ends with a `0x01` byte) or
    **AC4** (no trailing byte).
  - The `.cxb` layout with 40+8 byte file table entries is now listed as **ACR/AC3/AC4**.

### Changed
- A `.smallpox` is extracted to and packed from the subfolder named after the part of its name
  that follows `gamesettings_c<number>_`, in upper case with its words split by underscores, so
  every archive gets its own folder: for example `*_pc_specific` → `PC_SPECIFIC/`,
  `*_TestCompatPack` → `TEST_COMPAT_PACK/`, `*_EventRewardAPlusHack` → `EVENT_REWARD_A_PLUS_HACK/`.
  `STEP_N/` and `PARAM_CHANGES/` stay as before.

## 2026-10-15

### Added
- `repack.py` asks which `.cxb` layout to write: **ACB** (32+8 file table entries) or
  **ACR/AC3** (40+8 file table entries). One `main` branch now covers every game; the separate
  `v1` (ACB) and `v2` (ACR/AC3) branches are retired.
- README explains requirements, the extract/edit/pack workflow and the `.cxb` layouts.

### Changed
- Renamed `cxb.py` to `extract.py` and `to_cxb.py` to `repack.py`.
- `extract.py` indents extracted `.cxb` XML by adding line breaks between tags only. Attributes and
  tags stay exactly as stored (for example `<a x="1" />` keeps its space).
- `repack.py` removes that whitespace again when packing a `.cxb`, so the XML is stored raw on a
  single line. An unedited ACB or ACR archive now repacks byte-identical to the original, and
  archives get smaller.
- `repack.py` skips a `.cxb` entry with a warning, instead of writing a corrupt file table,
  if its name is too long for the chosen layout.

## 2026-09-25

### Changed
- `cxb.py` removes the trailing NUL byte from extracted `.smallpox` XML, so the files are plain
  text and git shows real diffs instead of "Binary files differ". `to_cxb.py` adds the NUL back
  when packing, so packed files are unchanged.

### Fixed
- Printing the status symbols (✅, ⚠️) no longer crashes in a Windows console.

## 2026-09-24

### Changed
- `xml_folder/` has one subfolder per archive type: `.cxb` → `CXB/`,
  `*_step_N.smallpox` → `STEP_N/`, `*_param_changes.smallpox` → `PARAM_CHANGES/`. `cxb.py`
  extracts into the matching subfolder and `to_cxb.py` packs from it, so XML from different
  archives no longer overwrites each other.

## 2026-05-24

### Added
- README with credits.

## 2026-05-23

### Added
- Support for `.smallpox` archives: `cxb.py` extracts them, and `to_cxb.py` packs a single XML
  into one when the output filename ends in `.smallpox`.

### Fixed
- Extraction stops at an all-zero block header instead of reading past the last block.

## 2026-05-20

### Changed
- `to_cxb.py` writes the ACB file table layout (32+8 bytes per entry).
- Later the same day, `to_cxb.py` switched to the ACR/AC3 file table layout (40+8 bytes per
  entry).
- `to_cxb.py` asks for the output filename instead of auto-numbering
  `gamesettings_c16233_V<n>.cxb`.
- Extracted XML is pretty-printed with ElementTree/minidom, and XML that fails to parse gets a
  repair attempt.
- Both scripts look for archives and `xml_folder/` next to the script, not in the current
  working directory.

## 2026-01-19

### Added
- `cxb.py`: extracts every LZO2A-compressed XML file from a `.cxb` archive into `xml_folder/`
  and fixes its indentation.
- `to_cxb.py`: packs the XML files in `xml_folder/` back into a `.cxb` archive. Each XML is
  read as UTF-8 (falling back to ISO-8859-1) with whitespace stripped.
- Bundled `liblzo2-2.dll` for Windows.
