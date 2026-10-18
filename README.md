# NBA — Nintendo Badge Arcade offline

An offline Luma3DS patch for **Nintendo Badge Arcade EUR Ver. 1.3.1**. Play packs
are granted locally; earned badges stay **inside the game**. HOME badge access
is disabled to protect custom GYTB badges. No `badges` folder is needed.

The expanded catalog combines the bundled **1.3.0 base and 1.3.1 update content**:
**2,078 badge resources**, **398 original regular catchers**, and **8 bonus catchers**.
The bonus catchers make 32 extra Arcade Bunny badges available to win. They reuse
an original four-badge layout. Browse all **406 selectable catchers** with L/R;
the practice layout stays separate. This does not include every online release.

**Works on a modded 3DS with Luma game patching.**
See [release notes](releases/v0.4.0/RELEASE_NOTES.md) for the included features.

## Get the current release

Download [NBA v0.4.0](releases/v0.4.0/nba-offline-v0.4.0.zip). It contains only
the Luma folder and code patch. The public release contains no Nintendo artwork,
executable, CIA, keys or build tools.

For the code-only install, extract the release and copy its **luma** folder to
the SD root. Enable **Enable game patching** in Luma:

```text
SD:/luma/titles/0004000000153600/code.ips
```

Keep the **EUR Ver. 1.3.1 update** installed (`0004000E00153600`, TMD 5136).
The title screen must report Ver. 1.3.1. The patch folder uses the base title ID.
Code-only installation keeps the original catcher lineup. Existing local saves
remain compatible; do not delete extdata.

## Enable all bundled catchers

Extract these three files from **your own supported base game and update RomFS**:

- Base **1.3.0** `/region_EUR/common/sharc/pc.sarc`, saved as `base-pc.sarc`.
- Update **1.3.1** `/region_EUR/common/sharc/pc.sarc`, saved as `pc.sarc`.
- Update **1.3.1** `/region_common/Schedule.xml`.

From this repository, run with Python 3.11+:

```sh
python3 tools/build_complete.py --archive /path/to/pc.sarc --base-archive /path/to/base-pc.sarc --schedule /path/to/Schedule.xml --output build/nba-all-catchers-luma.zip
```

No compiler or Python packages are needed for this step. The tool verifies exact
input fingerprints, keeps update assets when names overlap, restores base-only
assets, expands the catalog, and combines it with the release's code patch.
Copy the generated ZIP's **luma** folder to your SD root, replacing the previous
files. The generated personal ZIP
contains your game assets and stays in ignored `build/`.

Choose a play pack and confirm its original purchase dialogue to receive plays
locally. Existing price/eShop labels remain visible, but no payment or internet
request takes place. Browse catchers with L/R. New badges remain in the game;
placement shortcuts open the collection viewer. The HOME placement lesson is
skipped, while the original crane tutorial remains.
[Full installation details](docs/INSTALL.md).

## Build the patch from source

Use **Python 3.11+** and **clang with the ARM assembler** on `PATH`:

```sh
python3 tools/release.py
```

No game data is required to assemble the public release. This recreates
`releases/v0.4.0/nba-offline-v0.4.0.zip`, `build.json` and `SHA256SUMS`.
`make build` builds just the IPS; `make complete ARCHIVE=... BASE_ARCHIVE=... SCHEDULE=...`
builds the personal expanded ZIP. See [build and input details](docs/BUILD.md).

The supported update's decompressed executable SHA-256 is:

```text
709693735d20649e1f058525d4e6c24109e229dcb8425479b644587c345290fc
```

The builder can also assemble the supplied EUR base Ver. 1.3.0 with
`--game-version 1.3.0`. The current release and expanded catalog target 1.3.1 only.
Other regions/game versions and combined executable replacements are unsupported.
Luma does not check executable fingerprints; the builder verifies `--code` inputs.

## Tests

```sh
make install
make test
make lint
```

Without private inputs, native/archive tests explicitly skip. For the full suite:

```sh
BADGE_INPUT_DIR=/path/to/executables BADGE_ARCHIVE=/path/to/pc.sarc BADGE_BASE_ARCHIVE=/path/to/base-pc.sarc BADGE_SCHEDULE=/path/to/Schedule.xml make test
```

Use the exact filenames and hashes in [BUILD.md](docs/BUILD.md). Native ARM checks
cover both supported game versions, offline requests, signed saves, backup
recovery, HOME access barriers, tutorial flags and capacity limits. Archive audits
verify every catcher dependency and unchanged artwork. Emulator checks cover
catalog loading, catcher gameplay, saved ownership and unchanged HOME files
after restart.

## Repository contents

- `patches/badge_offline.s`: replacement ARM code.
- `src/badge_patch.py`, `badge_versions.py`: versioned code patch builder.
- `src/badge_catalog.py`: SARC audit, catalog expansion and personal ZIP builder.
- `src/patch_format.py`: independent ELF/ARM/IPS/ZIP utilities.
- `tools/`: portable complete-package builder and release tools.
- `tests/`: native, catalog, packaging and reproducibility checks.
- `docs/`: install/build details and reverse-engineering notes.
- `releases/v0.4.0/`: current public release, manifest, checksums and notes.

Source is MIT licensed. This is an independent project, unaffiliated with Nintendo.

GitHub checks and tag-triggered draft releases are configured in `.github/workflows/`.
See [maintaining releases](docs/MAINTAINING.md) before publishing a new version.

## Acknowledgements

The research and compatibility work used the following public resources:

- [Luma3DS loader source](https://github.com/LumaTeam/Luma3DS/tree/master/sysmodules/loader)
  for LayeredFS and IPS patch-loader behaviour.
- [GYTB](https://github.com/MrCheeze/GYTB) for the HOME badge-storage format context.
- [save3ds](https://github.com/wwylele/save3ds) for extdata filename constraints.
- [badge-arcade-server-full](https://github.com/AntiFreeze-1/badge-arcade-server-full)
  for Badge Arcade format research.
