# Nintendo Badge Arcade offline patch

This patch lets you play Nintendo Badge Arcade without an Internet connection.
It gives you free plays and saves your badge collection on the console.
Use the EUR game with update 1.3.1 and Luma3DS.
The current release is v0.5.0.

## Select a mode

| Mode | Machines for play | Files to install |
| --- | --- | --- |
| **Vanilla** | **1,965 badge resources and 384 regular catchers** from the original default catalog. | The release ZIP contains only `code.ips`. |
| **Expanded** | 406 machines with 2,078 obtainable badge resources. | The desktop script adds the full badge catalog to a private ZIP. |
| **Custom Weekly** | All unique machines from one selected week. | The desktop script makes a private ZIP from your game files and archive packs. |

Expanded includes 398 original regular machines and eight additional bonus layouts.
The practice machine is separate from these 406 machines.
Custom Weekly combines the machines from all seven days.
Each machine appears once in the selection.
The selected week stays active until you install a different patch.

The release ZIPs contain only code patches.
The scripts for Expanded and Custom Weekly make a `pc.sarc` file that contains game resources.
Keep these private ZIPs and all input files outside this repository.
The repository contains no game resources or console keys.

## Select HOME Menu access

Each mode has two options:

| Option | Result |
| --- | --- |
| **Game-only** | New badges stay in the game. The patch preserves HOME Menu badge data, including GYTB badges. |
| **HOME Menu export** | The game can send badges to the HOME Menu. This option can replace custom HOME Menu badges. |

The scripts use game-only unless you add `--home-menu`.
Neither option needs a `badges` folder.
A change to game-only does not restore HOME Menu data that the game replaced.

## Vanilla

1. Select one release ZIP:
   - [Game-only](releases/v0.5.0/nba-offline-v0.5.0-game-only.zip).
   - [HOME Menu export](releases/v0.5.0/nba-offline-v0.5.0-home-menu.zip).
2. Extract the ZIP.
3. Do the [installation procedure](#install-the-patch).

Each ZIP contains this file:

```text
luma/titles/0004000000153600/code.ips
```

Vanilla needs no extracted game files, desktop script, or console key.
It gives you offline play with **1,965 badge resources and 384 regular catchers** from the original default catalog.

## Prepare the input files

Expanded and Custom Weekly need three files from your extracted EUR RomFS:

| Source | Path in RomFS | Example local filename |
| --- | --- | --- |
| Base game 1.3.0 | `/region_EUR/common/sharc/pc.sarc` | `base-pc.sarc` |
| Update 1.3.1 | `/region_EUR/common/sharc/pc.sarc` | `pc.sarc` |
| Update 1.3.1 | `/region_common/Schedule.xml` | `Schedule.xml` |

1. Extract these files from your own game and update.
2. Put the files in a folder outside this repository.
3. Keep the two `pc.sarc` files under different filenames.

Both modes also need the full EUR badge catalog.
Use `allbadge_v131.dat.boss`, an `allbadge_v131-…-EU.enc` file, or its decrypted SARC file.
Use the same full badge catalog for Expanded and Custom Weekly.
This catalog lets the collection viewer display historical badges after a change between these modes.
Keep your game extdata when you change modes.
The catalog supplies badge resources. It does not give you ownership of those badges.

For an encrypted catalog, supply your local `boot9.bin` dump with `--boot9`.
Install the additional Python package before you use an encrypted pack:

```sh
python3 -m pip install -r requirements-spotpass.txt
```

The scripts keep the original input files, including the full badge catalog.
They remove temporary files after the build.
The output ZIPs contain no console key dump or encryption keys.

The scripts check these SHA-256 values:

```text
base-pc.sarc
2aca8529d7981a9ccad5a448ea06996fc861190b570ee4b25e4c651ce26347a5

pc.sarc
0f379f61166ced829c0f757ade31c00c09ed8e849350edaa8fec2a30974dae48

Schedule.xml
af0f27304a495c3d8fd202631702016bffe0874471962f12cc45a297cb8887ab
```

## Expanded

Use Python 3.11 or later.
This script needs no compiler or game executable.
A decrypted badge catalog needs no additional Python packages or console key.

1. Open a terminal in this repository.
2. Replace the example input paths in this command with your local paths.
3. Run the command:

```sh
python3 tools/build_complete.py \
  --base-archive /path/to/base-pc.sarc \
  --update-archive /path/to/pc.sarc \
  --schedule /path/to/Schedule.xml \
  --allbadge /path/to/allbadge_v131.dat.boss \
  --boot9 /path/to/boot9.bin \
  --output ../nba-private/nba-expanded-luma.zip
```

4. For a decrypted catalog, remove `--boot9` from the command.
5. For HOME Menu export, add `--home-menu` to the command.
6. Extract the output ZIP.
7. Do the [installation procedure](#install-the-patch).

The script combines your base game, update, and full badge catalog resources.
The output ZIP keeps the 406 playable machines and their 2,078 obtainable badge resources.
Other historical layouts appear only in the collection viewer.
The script also increases the archive index size in its private IPS.
Use the complete output ZIP when you install Expanded.
Do not replace its IPS with the Vanilla IPS.

## Custom Weekly

Use Python 3.11 or later, a C++17 compiler, and clang with its ARM assembler.
The script needs the three game files above and two EUR archive packs:

| Input | Content |
| --- | --- |
| Weekly pack | One `data_v131-…-EU.enc` file, or its decrypted SARC file. |
| Full badge catalog | `allbadge_v131.dat.boss`, an `allbadge_v131-…-EU.enc` file, or its decrypted SARC file. |
| `boot9.bin` | Your console key dump. This input is necessary only for encrypted packs. |

The weekly pack supplies machines and badges for the selected week.
The full badge catalog supplies the historical badges for the collection viewer.
The script puts both sets of resources in the private `pc.sarc` file.
Other historical layouts appear only in the collection viewer.
Only the selected week's machines appear in the machine selection.
The practice machine stays separate.

The script uses shared resources from the base game and update.
It does not add their other machines to the machine selection.
All file processing occurs on your computer.
The script keeps your original input files, including the full badge catalog.
It removes its temporary files after the build.
The output ZIP contains no console key dump or encryption keys.

1. Put your archive packs outside this repository.
2. For encrypted packs, install the additional Python package:

```sh
python3 -m pip install -r requirements-spotpass.txt
```

3. Replace the example input paths in this command with your local paths.
4. Run the command:

```sh
python3 tools/build_spotpass.py \
  --base-archive /path/to/base-pc.sarc \
  --update-archive /path/to/pc.sarc \
  --schedule /path/to/Schedule.xml \
  --week /path/to/data_v131-2022-05-27-01-40-EU.enc \
  --allbadge /path/to/allbadge_v131.dat.boss \
  --boot9 /path/to/boot9.bin \
  --output ../nba-private/nba-custom-weekly-luma.zip
```

5. For two decrypted packs, omit `--boot9`.
6. For HOME Menu export, add `--home-menu`.
7. Extract the output ZIP.
8. Do the [installation procedure](#install-the-patch).

To select another week, make a new ZIP with a different `--week` input.
Do not use a Vanilla IPS with an Expanded or Custom Weekly catalog.
The weekly IPS includes two additional changes for the schedule and archive index.

## Install the patch

Use the EUR base game and update 1.3.1 on the console.
The base title ID is `0004000000153600`.
The update title ID is `0004000E00153600`.

1. Close Nintendo Badge Arcade.
2. Make a backup of your game extdata.
3. Make a backup of your HOME Menu badge data.
4. Switch off the console.
5. Connect the SD card to your computer.
6. Open `SD:/luma/titles/0004000000153600/`, if this folder exists.
7. Remove the previous patch's files from this folder:

```text
code.ips
romfs/region_common/Schedule.xml
romfs/region_EUR/common/Schedule.xml
romfs/region_EUR/common/sharc/pc.sarc
catalog.json
```

8. Remove any conflicting `code.bin` or `romfs.bin` from this title's patch folder.
9. Copy the extracted `luma` folder to the root of the SD card.
10. Merge it with the existing `luma` folder, if necessary.
11. Put the SD card in the console.
12. Hold SELECT when you start the console.
13. Select **Enable game patching** in the Luma3DS configuration.
14. Save the configuration.
15. Start Nintendo Badge Arcade.
16. Select a play pack.
17. Confirm the purchase dialog to receive free plays.

The patch gives you plays locally without payment or an Internet request.
The original price and eShop labels stay visible.
Use L/R to select a machine.

Remove only the files for this title's patch.
Keep your extdata, collection saves, other titles, and unrelated modifications.
When you change to Vanilla, removal of the previous RomFS files is necessary.
If these files stay on the SD card, the previous catalog stays active.
Vanilla does not include the full badge catalog.
Historical badges can be absent from its collection viewer, even when your save still contains their ownership records.

To remove the patch, remove the files in step 7.
Keep your extdata backups.

## Build and check the source

The repository keeps the current release, its source code, tests, and this tutorial.
`patches/` contains the ARM source.
`src/` contains the patch and catalog builders.
`src/weekly_native/` contains the desktop C++ code and its parser libraries.
`tools/` contains the desktop commands and release checks.
`releases/v0.5.0/` contains both current ZIPs, build records, and checksums.

1. Install Python 3.11 or later and clang with its ARM assembler.
2. Run this command to make both release ZIPs:

```sh
python3 tools/release.py
```

This command needs no private game files.
The release check compares each IPS with the ARM source and checks the ZIP contents.

3. Run the checks:

```sh
make install
make test
make lint
make verify-release
make check-assets
```

The tests for the C++ code need a C++17 compiler.
Tests that need private game files skip if those files are absent.
For the full local tests, set these paths before `make test`:

```sh
export BADGE_INPUT_DIR=/path/to/executables
export BADGE_BASE_ARCHIVE=/path/to/base-pc.sarc
export BADGE_ARCHIVE=/path/to/pc.sarc
export BADGE_SCHEDULE=/path/to/Schedule.xml
export BADGE_WEEK_SARC=/path/to/week.sarc
export BADGE_ALLBADGE_SARC=/path/to/allbadge.sarc
make test
```

The executable folder uses these filenames and SHA-256 values:

```text
0004000000153600.code.bin
4278e14228eff0672b017d5a532210497ec824d7354fbb0c18ddae97f88323af

0004000e00153600.code.bin
709693735d20649e1f058525d4e6c24109e229dcb8425479b644587c345290fc
```

The public patch is for EUR update 1.3.1.
Luma3DS does not check the executable's SHA-256 value.
Other regions and executable replacements are incompatible with this release.
The desktop checks do not replace a test of a private catalog on your console.

## Acknowledgements

We used [badge-arcade-server-full](https://github.com/AntiFreeze-1/badge-arcade-server-full) as a reference for Badge Arcade file formats.

## Licenses

The project source uses the [MIT license](LICENSE).
TinyXML-2 and picojson retain their licenses in `src/weekly_native/vendor/`.
`LICENSES.txt` in that folder identifies their sources and local changes.
This project has no affiliation with Nintendo.
