# Nintendo Badge Arcade offline patch

This patch lets you play Nintendo Badge Arcade without an Internet connection.
It gives you free plays and saves your badge collection on the console.
Use the EUR game with update 1.3.1 and Luma3DS.
The current release is v0.5.3.
Fresh installations create their local save data without a Nintendo Network ID (NNID).
You do not need to start the unpatched game first.
The offline patch skips startup SpotPass task registration, which can fail on a fresh console
and otherwise appears as an SD-card read error.

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

To change from Vanilla to Expanded, do the [Expanded procedure](#upgrade-from-vanilla-to-expanded).
For machines from an archived week, do the [Custom Weekly procedure](#build-and-install-custom-weekly).

The release ZIPs contain only code patches.
The scripts for Expanded and Custom Weekly make a `pc.sarc` file that contains game resources.
Keep these private ZIPs and all input files outside this repository.
The repository contains no game resources or console keys.

### Update an Expanded or Custom Weekly installation

Version 0.5.3 corrects a memory limit in the full catalog loader.
Before this correction, the game could stop at **Reading latest data**
and show an ARM11 exception.
The Expanded game-only package passed a Nintendo 3DS test.
Custom Weekly uses the same correction, but it did not get a console test.

1. Get the current project files.
2. Use the current scripts to make a new Expanded or Custom Weekly ZIP.
3. Install the complete output ZIP with the procedure for your mode.

Keep your game extdata and collection saves.
The public Vanilla ZIP does not contain this catalog correction.
Refer to the [release notes](releases/v0.5.3/NOTES.md).

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
   - [Game-only](releases/v0.5.3/nba-offline-v0.5.3-game-only.zip).
   - [HOME Menu export](releases/v0.5.3/nba-offline-v0.5.3-home-menu.zip).
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

### Upgrade from Vanilla to Expanded

Expanded keeps your collection when you change modes.
Keep the game's extdata, which contains your collection save.
Do not remove the game or its extdata.
You do not need to start the unpatched game.

The desktop script makes a private Expanded ZIP from your game files.
The public Vanilla ZIP does not contain the additional resources.
Do steps 1 through 7 in sequence.
If you have the three extracted game files, continue with step 4 after you complete step 2.
You can also use this procedure for a new Expanded installation.

#### 1. Prepare the tools and project files

| Tool or download | Function |
| --- | --- |
| [Python 3.11 or later](https://www.python.org/downloads/) | Runs the desktop script on Windows, macOS, or Linux. |
| [This repository](https://github.com/GrouchoGlasses42/badge-arcade-offline) | Contains the desktop script and release files. |
| [GodMode9](https://github.com/d0k3/GodMode9/releases) | Extracts game files and copies your console key dump. Refer to the [installation instructions](https://3ds.hacks.guide/godmode9-usage.html#updating-godmode9). |
| [Luma3DS](https://github.com/LumaTeam/Luma3DS/releases) | Loads the patch on your console. Refer to the [game patching instructions](https://github.com/LumaTeam/Luma3DS/wiki/Optional-features). |

A functional Vanilla installation already uses Luma3DS.
Expanded needs no compiler or game executable.
You also need these items:

- An SD-card reader.
- The installed **EUR base game 1.3.0** (`0004000000153600`).
- The installed **EUR update 1.3.1** (`0004000E00153600`).

1. Open the repository link in the table.
2. Select **Code → Download ZIP**.
3. Extract the ZIP on your computer.
4. Make the `nba-private/inputs/` folder as shown below.

The Vanilla release ZIP does not contain the desktop script.
The extracted repository folder can have a different name.
The `nba-private` folder must be outside the repository.
The script does not accept game files or output paths inside the repository.

```text
NBA-work/
├── badge-arcade-offline-main/     ← extracted repository; contains tools/ and releases/
└── nba-private/
    └── inputs/                  ← your private input files
```

#### 2. Back up your existing installation

1. Close Nintendo Badge Arcade.
2. Switch off the console.
3. Connect the SD card to your computer.
4. Make a backup of all files and folders on the SD card.

This backup contains the game extdata, HOME Menu badge data, and Vanilla patch.
Use this backup with the same console.
Do not delete the `Nintendo 3DS` folder.

For a separate extdata backup, use [Checkpoint](https://github.com/BernardoGiordano/Checkpoint/releases).
Make a backup of the game's **extdata** in Checkpoint.
Copy the backup from `SD:/3ds/Checkpoint/extdata/` to your computer.

Select a HOME Menu option before you make the Expanded ZIP.
The default **game-only** option keeps your existing HOME Menu badges, including GYTB badges.
For HOME Menu export, add `--home-menu` to the command in step 6.
HOME Menu export can replace custom badges.

#### 3. Extract the three game files with GodMode9

Use the files from the installed game and update.
Do not use files from the `luma` patch folder.
The base game and update contain different files with the same `pc.sarc` filename.

1. Put the SD card in the console.
2. Hold **START** while you switch on the console.
3. If the chainloader menu appears, select **GodMode9**.
4. Press **HOME**.
5. Select **Title manager → [A:] SD CARD**.
6. Select the base title `0004000000153600`.
7. Select **Open title folder**.
8. Press **A** on the `.tmd` file.
9. Select **TMD file options… → Mount CXI/NDS to drive**.
10. Open the mounted drive when GodMode9 shows the instruction.
11. Open `romfs/region_EUR/common/sharc/`.
12. Press **A** on `pc.sarc`.
13. Select **Copy to 0:/gm9/out**.
14. Open `[0:] SDCARD/gm9/out/`.
15. Select the copied `pc.sarc` file.
16. Press **R + X**.
17. Change the filename to `base-pc.sarc`.
18. Press **HOME**.
19. Select **Title manager → [A:] SD CARD**.
20. Select the update title `0004000E00153600`.
21. Do steps 7 through 13 for the update title.
22. From the update's `romfs/region_common/` folder, copy `Schedule.xml` to `0:/gm9/out`.
23. Hold **R + START** to switch off the console.
24. Connect the SD card to your computer.
25. Copy `base-pc.sarc`, `pc.sarc`, and `Schedule.xml` from `SD:/gm9/out/` to `nba-private/inputs/`.

For more information, refer to [GodMode9's game file instructions](https://github.com/d0k3/GodMode9#game-file-handling).
If a title is absent, make sure that the EUR base game and update are installed.
If the script reports an unsupported input, compare its SHA-256 value with [Prepare the input files](#prepare-the-input-files).

#### 4. Add the full badge catalog (and boot9 for an encrypted catalog)

Use your saved SpotPass catalog or an archive that you can access.
The full badge catalog is a separate input.
The extracted game files and Vanilla patch do not supply this catalog.
A weekly `data_v131-…-EU.enc` pack cannot replace the full catalog.

1. Put the full **EUR** badge catalog in `nba-private/inputs/`.
2. If the catalog is encrypted, do the key dump procedure below.

The script accepts these catalog formats:

- `allbadge_v131.dat.boss`.
- An `allbadge_v131-…-EU.enc` archive.
- A decrypted SARC file.

For an encrypted catalog, do these steps:

1. Start GodMode9 as given in step 3.
2. Open **[M:] MEMORY VIRTUAL**.
3. Press **A** on `boot9.bin`.
4. Select **Copy to 0:/gm9/out**.
5. Hold **R + START** to switch off the console.
6. Connect the SD card to your computer.
7. Copy `SD:/gm9/out/boot9.bin` to `nba-private/inputs/`.

Refer to [GodMode9's system file instructions](https://github.com/d0k3/GodMode9#system-file-handling).
For a decrypted SARC, do not make a key dump.
Remove the `--boot9` argument from the command in step 6.
A change to the file extension does not decrypt a file.

The repository contains no full badge catalog or console key dump.
Make sure that you have the catalog before you continue.
Keep these inputs and the output ZIP private.

For the encrypted catalog example, make sure that the input folder contains these files:

```text
nba-private/inputs/
├── base-pc.sarc
├── pc.sarc
├── Schedule.xml
├── allbadge_v131.dat.boss
└── boot9.bin
```

#### 5. Open a terminal and prepare Python

1. Open the extracted repository folder on your computer.
2. Make sure that the folder contains `tools/build_complete.py` and `requirements-spotpass.txt`.

**Windows (PowerShell):**

1. Right-click in the repository folder.
2. Select **Open in Terminal**.
3. Run these commands, one line at a time:

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-spotpass.txt
```

**macOS / Linux:**

1. Open Terminal.
2. Run `cd "/full/path/to/badge-arcade-offline-main"` with the path to your repository folder.
3. Run these commands, one line at a time:

```sh
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-spotpass.txt
```

Make sure that the Python version is 3.11 or later.
The `venv` command makes a local [Python virtual environment](https://docs.python.org/3/library/venv.html).
The next step uses the Python interpreter in this environment.
You do not need to activate the environment.
The `pip install` command installs PyCryptodome for decryption.
If your catalog is decrypted, do not run the `pip install` command.

#### 6. Build your Expanded ZIP

1. Select the command for your operating system below.
2. If your catalog has a different filename, change the `--allbadge` path to that filename.
3. For a decrypted catalog, remove the `--boot9` argument and its path.
4. For HOME Menu export, add `--home-menu` to the end of the command.
5. Run the command.

**Windows (PowerShell):**

Enter this command on one line:

```powershell
.\.venv\Scripts\python.exe tools/build_complete.py --base-archive "../nba-private/inputs/base-pc.sarc" --update-archive "../nba-private/inputs/pc.sarc" --schedule "../nba-private/inputs/Schedule.xml" --allbadge "../nba-private/inputs/allbadge_v131.dat.boss" --boot9 "../nba-private/inputs/boot9.bin" --output "../nba-private/nba-expanded-luma.zip"
```

**macOS / Linux:**

```sh
.venv/bin/python tools/build_complete.py \
  --base-archive "../nba-private/inputs/base-pc.sarc" \
  --update-archive "../nba-private/inputs/pc.sarc" \
  --schedule "../nba-private/inputs/Schedule.xml" \
  --allbadge "../nba-private/inputs/allbadge_v131.dat.boss" \
  --boot9 "../nba-private/inputs/boot9.bin" \
  --output "../nba-private/nba-expanded-luma.zip"
```

Wait for the **Expanded personal install:** message.
Make sure that the summary shows **406 playable machines** and **2,078 obtainable badge resources**.
The output file is `nba-private/nba-expanded-luma.zip`.
The script keeps your input files.
It removes temporary files after the build.
The ZIP contains no console key dump or encryption keys.

#### 7. Replace Vanilla with the complete Expanded package

1. Extract `nba-expanded-luma.zip` on your computer.
2. Close Nintendo Badge Arcade.
3. Switch off the console.
4. Connect the SD card to your computer.
5. Open `SD:/luma/titles/0004000000153600/`.
6. Remove the previous patch files given in [Install the patch](#install-the-patch).
7. Remove any conflicting `code.bin` or `romfs.bin` from this title's patch folder.
8. Copy the output ZIP's complete `luma` folder to the SD card root.
9. Merge this folder with the existing `luma` folder.
10. If necessary, replace the patch files for this title.
11. Make sure that the files have the paths shown below.

Keep your extdata, collection saves, and other titles' patches.
If your computer gives an option to replace the complete folder, merge the `luma` folder contents.
Do not put the files inside an additional `nba-expanded-luma` folder on the SD card.

```text
SD:/luma/titles/0004000000153600/
├── code.ips
└── romfs/
    ├── region_common/
    │   └── Schedule.xml
    └── region_EUR/common/
        ├── Schedule.xml
        └── sharc/
            └── pc.sarc
```

12. Eject the SD card from your computer.
13. Put the SD card in the console.
14. Hold **SELECT** while you switch on the console.
15. Select **Enable game patching**.
16. Save the Luma3DS configuration.
17. Start Nintendo Badge Arcade.
18. Select a play pack.
19. Confirm the purchase dialog to receive free plays.
20. Use **L/R** to select a machine.

Your collection keeps the badges that you earned.
Expanded supplies additional machines for play.
It does not give you ownership of all badges.
Other historical layouts appear only in the collection viewer.

The script combines resources from the base game, update, and full badge catalog.
Its IPS increases the archive index size.
Keep the output ZIP's `code.ips` and RomFS files together.
Do not replace this IPS with the Vanilla IPS.

#### Expanded troubleshooting

| Symptom | Corrective action |
| --- | --- |
| The `py` or `python3` command fails. | Install Python from the link in step 1. Open the terminal again. On Windows, use `python` if your installation supplies that command instead of `py -3`. |
| The Python version is less than 3.11. | Install Python 3.11 or later. |
| `can't open file ... tools/build_complete.py` | Open the terminal in the extracted repository folder. The Vanilla release ZIP does not contain this script. |
| `No such file or directory` or `FileNotFoundError` | Check the folder structure, filenames, and file extensions. Put paths that contain spaces inside quotation marks. |
| `Unsupported input` | Compare the input hashes with [Prepare the input files](#prepare-the-input-files). Check the base and update filenames. Use the original EUR files for the specified versions. |
| `Game assets and asset-containing output must be outside the repository` | Move `nba-private` outside the repository. Use the folder structure in step 1. |
| `Encrypted SpotPass packs require --boot9` | Add the key dump path as given in step 4. |
| `Encrypted packs need pycryptodome` | Run the `pip install` command in step 5. Use the same Python environment for installation and the build. |
| `SpotPass pack is not for EUR Badge Arcade` or `Expected the full allbadge resource archive` | Use the full EUR `allbadge` catalog. Do not use a weekly pack as the full catalog. |
| `Patch package missing` | Extract the complete repository download, including `releases/`. The script uses the release files from this folder. |
| The previous catalog stays active, or the game stops. | Check **Enable game patching** and the SD paths in step 7. Install the complete output ZIP. Remove conflicting `code.bin` or `romfs.bin` files. Keep EUR update 1.3.1 installed. |

## Custom Weekly

### Build and install Custom Weekly

Custom Weekly combines the machines from all seven days of one archived week.
Each machine appears once in the selection.
The practice machine stays separate.
The selected week stays active until you install another package.
The selection does not change automatically.
You do not need to change the console date.

You can change from Vanilla, Expanded, or another week without loss of earned badges.
Keep the game's extdata.
Use the same full badge catalog for each build.
You do not need to install Expanded first.

#### 1. Prepare the shared files and backups

1. Open [this repository](https://github.com/GrouchoGlasses42/badge-arcade-offline).
2. Select **Code → Download ZIP**.
3. Extract the ZIP on your computer.
4. Make sure that the repository contains `tools/build_spotpass.py` and `src/weekly_native/`.
5. Make sure that your console has EUR base game 1.3.0 and EUR update 1.3.1.
6. Do the [backup procedure](#2-back-up-your-existing-installation).
7. Do the [game file extraction procedure](#3-extract-the-three-game-files-with-godmode9).
8. Do the [full badge catalog procedure](#4-add-the-full-badge-catalog-and-boot9-for-an-encrypted-catalog).

The Vanilla release ZIP does not contain the Weekly desktop script.
The extraction procedure supplies `base-pc.sarc`, update `pc.sarc`, and update `Schedule.xml`.
The catalog procedure supplies the full EUR `allbadge` catalog and the key dump for encrypted packs.
If you have the original Expanded inputs, use those files.

Keep `nba-private/inputs/` outside the repository as shown in the [folder structure](#1-prepare-the-tools-and-project-files).
Keep the output ZIP outside the repository.
The script does not accept input or output paths inside the repository.

#### 2. Install the Weekly build tools

Weekly needs Python 3.11 or later, a C++17 compiler, and clang with ARM assembler support.
The desktop script compiles a helper program and assembles the patch.
You do not need to compile these programs manually.
You do not need a game executable.

**Windows:**

Use Ubuntu in Windows Subsystem for Linux (WSL).
The helper program uses POSIX interfaces.
Refer to Microsoft's [WSL installation instructions](https://learn.microsoft.com/en-us/windows/wsl/install).

1. Open PowerShell as administrator.
2. Run this command:

```powershell
wsl --install -d Ubuntu
```

3. If Windows gives an instruction to restart, restart Windows.
4. Open **Ubuntu** from the Start menu.
5. Make a username for Ubuntu when the installation program gives the instruction.
6. Make a password for Ubuntu when the installation program gives the instruction.
7. Run the Ubuntu commands below in the Ubuntu terminal.

For the remaining Weekly steps, use the Ubuntu terminal.
Do not use the Windows `py` command or the Expanded Windows Python environment.

**Ubuntu / Debian Linux, including Ubuntu in WSL:**

Run these commands, one line at a time:

```sh
sudo apt update
sudo apt install python3 python3-venv build-essential clang
```

These packages supply Python, virtual environments, the C++ compiler, and clang.
Refer to Ubuntu's [Python instructions](https://ubuntu.com/developers/docs/howto/python-setup/)
and [Clang instructions](https://ubuntu.com/developers/docs/howto/clang-setup/).
Use Ubuntu 24.04 or later for a default Python version greater than 3.11.
For other Linux distributions, install the applicable packages with the distribution's package manager.

**macOS:**

1. Install [Python 3.11 or later](https://www.python.org/downloads/).
2. Open Terminal.
3. Run this command to install Apple's [Command Line Tools for Xcode](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/):

```sh
xcode-select --install
```

4. Complete the installation before you continue.

If the tools are installed, continue with the checks below.

**All operating systems:**

Run these commands in the terminal:

```sh
python3 --version
c++ --version
clang --version
```

Make sure that all three commands operate correctly.
Make sure that Python reports version 3.11 or later.
The script uses `c++` for the helper program.
If your C++17 compiler has another executable name, set `CXX` to that name.
For example, run `export CXX=clang++` to use `clang++`.
The script uses `clang` for the ARM assembler.

#### 3. Select and add a weekly pack

Use one complete **EUR weekly pack** from your saved SpotPass data or an archive that you can access.
Put the pack in `nba-private/inputs/`.
Use a `data_v131-…-EU.enc` file or its decrypted SARC file.
The weekly pack and full badge catalog are separate inputs.
The script needs both inputs.

| Argument | Input |
| --- | --- |
| `--week` | The weekly pack supplies the schedule, machines, and badge resources for one week. |
| `--allbadge` | The full EUR catalog supplies historical badges for the collection viewer. |
| `--boot9` | Your console key dump. This input is necessary if one or both packs are encrypted. |

For decrypted packs, keep the complete SARC files.
Do not extract their contents for use as inputs.
Do not supply only an inner machine archive.
A change to the file extension does not decrypt a file.
The repository contains no archive packs.

For the encrypted example, make sure that the folder structure contains these files:

```text
NBA-work/
├── badge-arcade-offline-main/
└── nba-private/
    └── inputs/
        ├── base-pc.sarc
        ├── pc.sarc
        ├── Schedule.xml
        ├── data_v131-2022-05-27-01-40-EU.enc
        ├── allbadge_v131.dat.boss
        └── boot9.bin
```

The weekly filename is an example.
The repository does not supply this file.
Use the filename of your pack in the build command.
The pack's internal schedule specifies the selected week.

#### 4. Open the repository and prepare Weekly's Python environment

On macOS or Linux, open Terminal.
Run this command with the path to your extracted repository:

```sh
cd "/full/path/to/NBA-work/badge-arcade-offline-main"
```

In Ubuntu on WSL, Windows drives have paths under `/mnt/`.
For a repository in your Windows Downloads folder, use this example:

```sh
cd "/mnt/c/Users/YOUR_NAME/Downloads/NBA-work/badge-arcade-offline-main"
```

Replace `YOUR_NAME` with your Windows username.
Change the remaining folder path if necessary.
Make sure that the repository folder contains `tools/build_spotpass.py`.
Run these commands, one line at a time:

```sh
python3 -m venv ../nba-private/weekly-venv
../nba-private/weekly-venv/bin/python -m pip install -r requirements-spotpass.txt
```

The first command makes a separate Python environment in `nba-private/weekly-venv/`.
You do not need to activate this environment.
The second command installs PyCryptodome for decryption.
If both packs are decrypted, do not run the second command.

#### 5. Build the Custom Weekly ZIP

1. Use the same terminal as in step 4.
2. Change the `--week` path below to the filename of your weekly pack.
3. Change the `--allbadge` path to the filename of your full catalog.
4. If both packs are decrypted, remove the complete `--boot9` line.
5. For HOME Menu export, add `--home-menu` to the end of the command.
6. Run the command:

```sh
../nba-private/weekly-venv/bin/python tools/build_spotpass.py \
  --base-archive "../nba-private/inputs/base-pc.sarc" \
  --update-archive "../nba-private/inputs/pc.sarc" \
  --schedule "../nba-private/inputs/Schedule.xml" \
  --week "../nba-private/inputs/data_v131-2022-05-27-01-40-EU.enc" \
  --allbadge "../nba-private/inputs/allbadge_v131.dat.boss" \
  --boot9 "../nba-private/inputs/boot9.bin" \
  --output "../nba-private/nba-custom-weekly-luma.zip"
```

If one or both packs are encrypted, keep the `--boot9` argument.
Install PyCryptodome as given in step 4.
The default **game-only** option keeps existing HOME Menu badges, including GYTB badges.
HOME Menu export can replace custom badges.

Wait for the **Custom Weekly personal install:** message.
The next line shows the selected week and machine count.
For example, it starts with `Week 2022-05-27:`.
Make sure that this date agrees with your selected week.
The machine count changes with the weekly pack.
The badge resource count includes historical resources in the collection catalog.
The script does not give you ownership of those badges.

The output file is `nba-private/nba-custom-weekly-luma.zip`.
In the WSL example, this file is also in your Windows `NBA-work/nba-private/` folder.
All file processing occurs on your computer.
The script keeps your input files.
It removes temporary files after the build.
The ZIP contains no console key dump or encryption keys.
Keep the ZIP private because it contains game resources.

#### 6. Install the week and change weeks later

1. Extract `nba-custom-weekly-luma.zip` on your computer.
2. Close Nintendo Badge Arcade.
3. Switch off the console.
4. Connect the SD card to your computer.
5. Make a backup of the current installation.
6. Open `SD:/luma/titles/0004000000153600/`.
7. Remove the previous patch files given in [Install the patch](#install-the-patch).
8. Remove any conflicting `code.bin` or `romfs.bin` from this title's patch folder.
9. Copy the output ZIP's complete `luma` folder to the SD card root.
10. Merge this folder with the existing `luma` folder.
11. If necessary, replace the patch files for this title.
12. Make sure that the files have the paths shown below.

Keep your extdata, collection saves, and other titles' patches.
Keep the output ZIP's `code.ips` and RomFS files together.
The Weekly IPS changes the schedule source and archive index size.
Do not replace it with a Vanilla or Expanded IPS.
An incorrect IPS can cause an incorrect machine selection or a game failure.

```text
SD:/luma/titles/0004000000153600/
├── code.ips
├── catalog.json
└── romfs/
    ├── region_common/
    │   └── Schedule.xml
    └── region_EUR/common/
        ├── Schedule.xml
        └── sharc/
            └── pc.sarc
```

13. Eject the SD card from your computer.
14. Put the SD card in the console.
15. Hold **SELECT** while you switch on the console.
16. Select **Enable game patching**.
17. Save the Luma3DS configuration.
18. Start Nintendo Badge Arcade.
19. Select a play pack.
20. Confirm the purchase dialog to receive free plays.
21. Use **L/R** to select a machine.

Only the selected week's machines are available for play.
Other historical layouts appear only in the collection viewer.
The script uses shared resources from the base game and update.
It does not add their other machines to the selection.

To select another week, do these steps:

1. Put another complete EUR weekly pack in `nba-private/inputs/`.
2. Do step 5 with the new `--week` path.
3. Do step 6 with the new ZIP.

Use the original base game files, update files, schedule, and full badge catalog for each build.
To keep a separate ZIP for each week, use a different `--output` filename for each build.
Always install the complete package.
Keep the game's extdata when you change weeks.

To return to Expanded, install the complete Expanded package.
To return to Vanilla, do these steps:

1. Remove the Weekly patch files as given in [Install the patch](#install-the-patch).
2. Install the Vanilla IPS.

Vanilla has a smaller catalog.
Some historical badges can be absent from its collection viewer.
The save keeps ownership records for these badges.

#### Weekly troubleshooting

| Symptom | Corrective action |
| --- | --- |
| The `c++` or `clang` command fails. | Complete step 2. Open the terminal again. On Windows, run the script in Ubuntu on WSL. |
| Compilation fails, or clang cannot assemble for `arm-none-eabi`. | Check the compiler installation and ARM assembler support. Use the tools in step 2. The script uses `CXX` for the helper program and `clang` for the ARM assembler. |
| The Python environment fails after a change from Windows to WSL. | Make `weekly-venv` with Ubuntu's `python3` as given in step 4. Do not use a Windows Python environment in Linux. |
| `Installed content does not match supported EUR base 1.3.0 / update 1.3.1` | Compare the input hashes with [Prepare the input files](#prepare-the-input-files). Use the original extracted files. Do not use an Expanded or Weekly output `pc.sarc` as an input. |
| `Pack has no weekly schedule` or `Expected a seven-day archived week` | Use a complete weekly pack for `--week`. Do not supply the full badge catalog or an inner archive for this argument. |
| `Archived week is not EUR` or `SpotPass pack is not for EUR Badge Arcade` | Use EUR packs for `--week` and `--allbadge`. |
| `Expected the full allbadge resource archive` | Use the full EUR catalog for `--allbadge`. A weekly pack cannot replace the full catalog. |
| Decryption fails, or an input path is incorrect. | Refer to [Expanded troubleshooting](#expanded-troubleshooting). If one or both packs are encrypted, supply `--boot9`. Install PyCryptodome with the Weekly Python environment. |
| The previous week stays active, or the game stops. | Install the complete new ZIP. Check the SD paths and **Enable game patching**. Keep EUR update 1.3.1 installed. A change to the console date does not select another week. |

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

On first boot, the patch creates the game's missing SD extdata before loading the title screen.
New extdata uses the name **Badge Arcade Offline** and a plain cyan icon in Data Management.
Existing game extdata keeps its icon and saves.

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

The repository keeps release ZIPs, source code, tests, and this tutorial.
`patches/` contains the ARM source.
`src/` contains the patch and catalog builders.
`src/weekly_native/` contains the desktop C++ code and its parser libraries.
`tools/` contains the desktop commands and release checks.
`releases/v0.5.3/` contains both current ZIPs, build records, and checksums.

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
