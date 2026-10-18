# Build, private inputs and reproducibility

## Public release

Use Python 3.11+ and clang with ARM target support on `PATH`:

```sh
python3 tools/release.py
python3 tools/verify_release.py
```

No private inputs or Python packages are needed for these commands. The versioned
release contains only the IPS in its Luma folder, with no original executable or
art. The source repository contains the catalog tool. Source builds also support
base 1.3.0:

```sh
python3 src/badge_patch.py --game-version 1.3.0 --output build/base --package build/base.zip
```

The public executable patch targets the 1.3.1 update. The complete-package tool
merges resources from the supported 1.3.0 base game and 1.3.1 update.

## Prepare inputs

Dump your own matching title/update with a 3DS dumping tool such as GodMode9.
Extract ExeFS/RomFS with your dumping tool; decompress `.code` if necessary.
This project accepts extracted inputs and deliberately does not decrypt games
or include keys. Do not pass a CIA, CXI, NCCH or compressed code to `--code`.
Keep private files in ignored `inputs/`, or reference them outside the repository.

| Input | Size or source | SHA-256 |
| --- | --- | --- |
| `0004000000153600.code.bin` | Base 1.3.0 decompressed `.code`, `0x356000` bytes | `4278e14228eff0672b017d5a532210497ec824d7354fbb0c18ddae97f88323af` |
| `0004000e00153600.code.bin` | Update 1.3.1 decompressed `.code`, `0x357000` bytes | `709693735d20649e1f058525d4e6c24109e229dcb8425479b644587c345290fc` |
| `base-pc.sarc` | Base RomFS `/region_EUR/common/sharc/pc.sarc` | `2aca8529d7981a9ccad5a448ea06996fc861190b570ee4b25e4c651ce26347a5` |
| `pc.sarc` | Update RomFS `/region_EUR/common/sharc/pc.sarc` | `0f379f61166ced829c0f757ade31c00c09ed8e849350edaa8fec2a30974dae48` |
| `Schedule.xml` | Update RomFS `/region_common/Schedule.xml` | `af0f27304a495c3d8fd202631702016bffe0874471962f12cc45a297cb8887ab` |

Use the common schedule, not `/region_EUR/common/Schedule.xml`, as the builder's
input. The output overrides both locations. The portable wrapper checks all three
asset fingerprints before creating output.

## Complete personal install

From a source checkout:

```sh
python3 tools/build_complete.py --archive /path/to/pc.sarc --base-archive /path/to/base-pc.sarc --schedule /path/to/Schedule.xml --output build/nba-all-catchers-luma.zip
```

This needs only Python's standard library: it uses the prebuilt IPS from the
versioned release in the source checkout. Temporary reconstructed game
assets are removed after packaging. The generated ZIP contains your game art;
it is personal build output, not part of the public Git repository.

From a source checkout, an equivalent Make command is:

```sh
make complete ARCHIVE=/path/to/pc.sarc BASE_ARCHIVE=/path/to/base-pc.sarc SCHEDULE=/path/to/Schedule.xml
```

## Native verification

```sh
make install
python3 src/badge_patch.py --code /path/to/0004000e00153600.code.bin --output build/verified
BADGE_INPUT_DIR=/path/to/executables BADGE_ARCHIVE=/path/to/pc.sarc BADGE_BASE_ARCHIVE=/path/to/base-pc.sarc BADGE_SCHEDULE=/path/to/Schedule.xml make test
make lint
```

`BADGE_INPUT_DIR` contains the two exact executable filenames above. Both versions
are tested when both files exist. `BADGE_CODE` can select a single executable;
tests for the other game version then skip. Without environment variables, tests
look in `inputs/`. `BADGE_ARCHIVE`, `BADGE_BASE_ARCHIVE` and `BADGE_SCHEDULE` select archive audit inputs.
Missing inputs produce explicit skips, not fabricated native results.

`make verify BADGE_CODE=/path/to/code.bin` verifies a single executable.
Patched executables stay in ignored build output. On macOS, Unicorn needs the
host cache-information sysctl; a restrictive sandbox can prevent execution.

ZIP timestamps, order and modes are fixed. `tools/verify_release.py` compares the
published IPS against newly assembled records and checks member hashes, public
file allowlists and bundled tool sources. Python/zlib versions may change ZIP
compression bytes; the IPS fingerprint is the cross-toolchain comparison.
