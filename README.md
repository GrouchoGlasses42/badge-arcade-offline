# Nintendo Badge Arcade offline patch

This patch lets you play Nintendo Badge Arcade without an Internet connection.
It gives you free plays and saves your badge collection on the console.
Use the EUR game with update 1.3.1 and Luma3DS.
The current release is v0.5.2.
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

Already using Vanilla? Follow [Upgrade from Vanilla to Expanded](#upgrade-from-vanilla-to-expanded)
for the complete walkthrough, including tools, file extraction, and Windows commands.
For an archived week's lineup, follow [Build and install Custom Weekly](#build-and-install-custom-weekly).

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
   - [Game-only](releases/v0.5.2/nba-offline-v0.5.2-game-only.zip).
   - [HOME Menu export](releases/v0.5.2/nba-offline-v0.5.2-home-menu.zip).
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

You can keep your existing collection when upgrading. Keep the game's extdata;
you do not need to uninstall the game, delete its save, or start the unpatched game.
Expanded requires a private package built on your computer from your game files.
The public Vanilla ZIP alone cannot provide the extra resources.

Follow steps 1–7 in order. If you already have the extracted inputs, skip step 3.
These steps also work for a first Expanded installation.

#### 1. Get the tools and project files

| Tool or download | What you need it for |
| --- | --- |
| [Python 3.11 or later](https://www.python.org/downloads/) | Runs the Expanded builder on Windows, macOS, or Linux. |
| [This repository](https://github.com/GrouchoGlasses42/badge-arcade-offline) | Select **Code → Download ZIP**, then extract it on your computer. The Vanilla release ZIP does not contain the builder. |
| [GodMode9](https://github.com/d0k3/GodMode9/releases) | Extracts files from your installed game and update, and copies your `boot9.bin` dump if needed. See the [setup instructions](https://3ds.hacks.guide/godmode9-usage.html#updating-godmode9). |
| [Luma3DS](https://github.com/LumaTeam/Luma3DS/releases) | Loads the patch on your console. A working Vanilla installation already uses this. See its [game patching documentation](https://github.com/LumaTeam/Luma3DS/wiki/Optional-features). |

Expanded needs no compiler or game executable. You also need an SD-card reader,
the installed **EUR base game 1.3.0** (`0004000000153600`), and
**EUR update 1.3.1** (`0004000E00153600`).

Create this folder layout on your computer. `nba-private` must be **beside** the
extracted repository, not inside it; the builder rejects game files and outputs
inside the repository. The repository folder's name may differ after extraction.

```text
NBA-work/
├── badge-arcade-offline-main/     ← extracted repository; contains tools/ and releases/
└── nba-private/
    └── inputs/                  ← your private input files
```

#### 2. Back up your existing installation

1. Close Nintendo Badge Arcade and power off the console.
2. Put the SD card in your computer and copy its entire contents to a backup folder.
   This preserves the game's extdata, HOME Menu badge data, and current Vanilla patch
   for use with this same console. Do not delete the `Nintendo 3DS` folder.
3. If you also want a separate game extdata backup, use
   [Checkpoint](https://github.com/BernardoGiordano/Checkpoint/releases).
   Back up **extdata**, which contains Badge Arcade's collection, and copy the
   backup from `SD:/3ds/Checkpoint/extdata/` to your computer.

Choose your HOME Menu option before building: the default **game-only** option
preserves existing HOME Menu/GYTB badges. Add `--home-menu` only if you want the
game to export badges to HOME Menu; it can replace custom badges.

#### 3. Extract the three game files with GodMode9

Extract from the installed titles, rather than from the patched `luma` folder.
The base game and update contain different files with the same `pc.sarc` name.

1. Insert the SD card in the console. Hold **START** while powering on to open
   GodMode9; select it in the chainloader if a menu appears.
2. Press **HOME → Title manager → [A:] SD CARD**. Select the base title
   `0004000000153600`, then **Open title folder**. Press **A** on its `.tmd`
   file and choose **TMD file options… → Mount CXI/NDS to drive**.
   Enter the mounted drive when prompted, then open `romfs`.
3. Open `region_EUR/common/sharc/`, press **A** on `pc.sarc`, and select
   **Copy to 0:/gm9/out**. In `[0:] SDCARD/gm9/out/`, highlight that copy and
   press **R + X** to rename it to `base-pc.sarc` before extracting the update.
4. Return to **HOME → Title manager → [A:] SD CARD**. Select the update title
   `0004000E00153600` and mount it the same way. From its `romfs` folder, copy
   `region_EUR/common/sharc/pc.sarc` and `region_common/Schedule.xml` to `0:/gm9/out`.
5. Hold **R + START** to power off. On your computer, copy `base-pc.sarc`,
   `pc.sarc`, and `Schedule.xml` from `SD:/gm9/out/` to `nba-private/inputs/`.

These operations use GodMode9's [title and image browsing features](https://github.com/d0k3/GodMode9#game-file-handling).
If a title is missing, check that both the EUR game and its update are installed.
Use the SHA-256 values in [Prepare the input files](#prepare-the-input-files) to
check your copies if the builder reports an unsupported input.

#### 4. Add the full badge catalog (and boot9 for an encrypted catalog)

1. Put your full **EUR** badge catalog in `nba-private/inputs/`.
   Accepted inputs are `allbadge_v131.dat.boss`, an `allbadge_v131-…-EU.enc`
   archive, or an already decrypted SARC. Use your preserved SpotPass catalog
   or an existing archive you have access to. This is a separate input: extracting
   the game/update or installing Vanilla does not supply the full `allbadge` pack.
   A weekly `data_v131-…-EU.enc` pack cannot replace it.
2. For an encrypted `.boss` or `.enc` catalog, boot GodMode9 again, open
   **[M:] MEMORY VIRTUAL**, press **A** on `boot9.bin`, and select
   **Copy to 0:/gm9/out**. Power off, then copy `SD:/gm9/out/boot9.bin` into
   `nba-private/inputs/`. See [GodMode9's system file handling documentation](https://github.com/d0k3/GodMode9#system-file-handling).
3. For an already decrypted SARC, skip the key dump and omit `--boot9` below.
   Renaming an encrypted file to `.sarc` does not decrypt it.

The catalog and key dump are not distributed in this repository. You need the
catalog before continuing. Keep these inputs and the generated ZIP private.

For the encrypted-catalog example below, the inputs folder should now contain:

```text
nba-private/inputs/
├── base-pc.sarc
├── pc.sarc
├── Schedule.xml
├── allbadge_v131.dat.boss
└── boot9.bin
```

#### 5. Open a terminal and prepare Python

Open the extracted repository folder containing `tools/build_complete.py` and
`requirements-spotpass.txt`. On Windows, right-click in that folder and choose
**Open in Terminal** (PowerShell). On macOS or Linux, open Terminal and use
`cd "/full/path/to/badge-arcade-offline-main"`, replacing the path with yours.
Run the commands for your system, one line at a time:

**Windows (PowerShell):**

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-spotpass.txt
```

**macOS / Linux:**

```sh
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-spotpass.txt
```

The version must be 3.11 or later. These commands create a local
[Python virtual environment](https://docs.python.org/3/library/venv.html);
activation is unnecessary because the next step uses its interpreter directly.
The `pip install` line installs the decryption dependency, PyCryptodome.
Skip that line if your catalog is already decrypted.

#### 6. Build your Expanded ZIP

With the folder layout above, copy the command for your system.
If your catalog has another filename, change the `--allbadge` path to match it.
For a decrypted SARC, also remove the `--boot9` argument and its path.
For HOME Menu export, append `--home-menu`.

**Windows (PowerShell; paste as one line):**

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

Wait for **Expanded personal install:** and a summary reporting
**406 playable machines** and **2,078 obtainable badge resources**.
Your output is `nba-private/nba-expanded-luma.zip`. The script preserves your inputs
and removes its temporary files. No console key dump or encryption keys enter the ZIP.

#### 7. Replace Vanilla with the complete Expanded package

1. Extract `nba-expanded-luma.zip` on your computer.
2. Close the game, power off the console, and connect its SD card to the computer.
3. Open `SD:/luma/titles/0004000000153600/`. Remove the old patch files listed in
   [Install the patch](#install-the-patch), including the Vanilla `code.ips` and
   any previous RomFS overrides. Keep your extdata and collection saves.
4. Copy the generated ZIP's **entire `luma` folder** to the SD card root. Merge
   folders and replace this title's patch files when asked. On systems that offer
   to replace a whole folder, merge its contents instead so other titles stay intact.
5. Confirm that these files exist directly at these paths (not inside an extra
   `nba-expanded-luma` folder):

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

6. Eject the SD card, put it back in the console, and hold **SELECT** while
   powering on. Check **Enable game patching**, then save the Luma3DS configuration.
7. Start Nintendo Badge Arcade. Select a play pack and confirm the purchase
   dialog for free plays. Use **L/R** to browse machines. Your existing earned
   badges should remain in the collection; Expanded adds machines to play,
   rather than automatically awarding every badge.

The script combines your base game, update, and full badge catalog resources.
Other historical layouts appear only in the collection viewer.
The generated IPS increases the archive index size, so **keep the generated
`code.ips` together with its generated RomFS files**. Do not copy the Vanilla IPS
back over it.

#### If you get stuck

| Symptom | What to check |
| --- | --- |
| `py` / `python3` is not found, or the version is below 3.11 | Install Python from the link in step 1, then reopen your terminal. On Windows, try `python` instead of `py -3` if that is your installed Python command. |
| `can't open file ... tools/build_complete.py` | Open the terminal in the extracted source repository, not in the Vanilla release ZIP or the private inputs folder. |
| `No such file or directory` / `FileNotFoundError` | Check the folder layout, spelling, and file extensions. Quote paths containing spaces. |
| `Unsupported input` | Check the hashes above. Common causes are swapped base/update archives, the wrong region or version, or copying from a previous patched RomFS. Renaming the wrong file will not fix its contents. |
| `Game assets and asset-containing output must be outside the repository` | Move `nba-private` beside the repository and use the paths shown above. |
| `Encrypted SpotPass packs require --boot9` / `Encrypted packs need pycryptodome` | Supply the key dump from step 4 and run the step 5 dependency command with the same virtual environment interpreter used to build. |
| `SpotPass pack is not for EUR Badge Arcade` / `Expected the full allbadge resource archive` | Use the full EUR `allbadge` pack, not another region or a weekly `data` pack. |
| `Patch package missing` | Extract the complete repository download, including `releases/`. The builder uses the bundled release; Expanded does not require compiling a new Vanilla patch. |
| The game still shows the old catalog, or crashes after the upgrade | Check **Enable game patching**, the SD paths in step 7, and that both the IPS and RomFS came from the same generated ZIP. Remove conflicting `code.bin` / `romfs.bin` files as described below. Keep the EUR 1.3.1 update installed. |

## Custom Weekly

### Build and install Custom Weekly

Custom Weekly combines all unique machines from the seven days of one archived
week into a fixed selection. Each machine appears once. The practice machine
stays separate. The lineup stays active until you install another package;
it does not rotate automatically or require changing the console's date.

You can switch from Vanilla, Expanded, or another week while keeping your earned
badges. Keep the game's extdata and use the same full badge catalog between builds.
You do not need to install Expanded first.

#### 1. Prepare the shared files and backups

1. Download and extract [this repository](https://github.com/GrouchoGlasses42/badge-arcade-offline)
   using **Code → Download ZIP**. You need `tools/build_spotpass.py` and
   `src/weekly_native/`, which are absent from the Vanilla release ZIP.
2. Use the EUR base game 1.3.0 and EUR update 1.3.1. Follow
   [Back up your existing installation](#2-back-up-your-existing-installation)
   before replacing any patch files.
3. Follow [Extract the three game files with GodMode9](#3-extract-the-three-game-files-with-godmode9)
   to obtain `base-pc.sarc`, update `pc.sarc`, and update `Schedule.xml`.
4. Follow [Add the full badge catalog](#4-add-the-full-badge-catalog-and-boot9-for-an-encrypted-catalog)
   to prepare the EUR `allbadge` archive and, if needed, your `boot9.bin` dump.
   If you already built Expanded, reuse its original inputs.

Keep `nba-private/inputs/` beside the extracted repository, as shown in the
[folder layout above](#1-get-the-tools-and-project-files). Keep your inputs and
generated ZIPs outside the repository. The builder rejects paths inside it.

#### 2. Install the Weekly build tools

Weekly needs **Python 3.11 or later**, a **C++17 compiler**, and **clang with ARM
assembler support**. The script compiles its desktop helper and assembles its
patch automatically. You do not need to compile either manually or extract the
game executable.

**Windows: use Ubuntu in WSL.** The desktop helper uses POSIX APIs, so this guide
uses a Linux build environment on Windows. Follow Microsoft's
[WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install):

1. Open PowerShell **as administrator** and run:

```powershell
wsl --install -d Ubuntu
```

2. Restart Windows if prompted, open **Ubuntu** from the Start menu, and complete
   its first-run username/password setup.
3. Run the Ubuntu commands below **inside Ubuntu**. Continue steps 3–6 in that
   terminal; the Windows `py` command and Windows Python environment are not used.

**Ubuntu / Debian Linux, including Ubuntu in WSL:**

```sh
sudo apt update
sudo apt install python3 python3-venv build-essential clang
```

These packages supply Python, virtual environments, the C++ compiler, and clang.
See Ubuntu's [Python setup](https://ubuntu.com/developers/docs/howto/python-setup/)
and [Clang setup](https://ubuntu.com/developers/docs/howto/clang-setup/) documentation.
Use Ubuntu 24.04 or later for a default Python version above 3.11. On other Linux
distributions, install the equivalent packages using your package manager.

**macOS:** install [Python 3.11 or later](https://www.python.org/downloads/), then
install Apple's [Command Line Tools for Xcode](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/)
from Terminal:

```sh
xcode-select --install
```

Finish the installer before continuing. If the tools are already installed,
you can continue with the existing installation.

In your build terminal, check that all three commands work:

```sh
python3 --version
c++ --version
clang --version
```

Python must report 3.11 or later. The builder runs `c++` by default; if your C++17
compiler uses another name, set `CXX` to that executable, for example
`export CXX=clang++`. It separately calls `clang` for the ARM patch.

#### 3. Choose and add a weekly pack

Put **one complete EUR weekly pack** from your preserved SpotPass data or an
existing archive you have access to in `nba-private/inputs/`.
Use a `data_v131-…-EU.enc` file or its already decrypted SARC. This input is
separate from the full `allbadge` catalog; you need both:

| Input | Content |
| --- | --- |
| `--week` | Weekly pack: provides the week's schedule, machines, and badge resources. |
| `--allbadge` | Full EUR badge catalog: provides historical badges for the collection viewer. |
| `--boot9` | Your local key dump: required if **either** pack is encrypted. Omit it only when **both** packs are decrypted SARCs. |

Keep decrypted packs as complete SARCs. Do not unpack their contents or supply
only an inner machine archive. Renaming an encrypted file does not decrypt it.
The archive packs are not distributed in this repository.

For the encrypted example, your folder should now contain:

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

The weekly filename above is an example, not a bundled download. Use the actual
filename of your pack. Its internal schedule determines the selected week.

#### 4. Open the repository and prepare Weekly's Python environment

In Terminal on macOS/Linux, change to the extracted repository folder:

```sh
cd "/full/path/to/NBA-work/badge-arcade-offline-main"
```

Replace the example path with yours. In Ubuntu on WSL, Windows drives are under
`/mnt/`; for example, a folder in your Windows Downloads directory can be opened
with:

```sh
cd "/mnt/c/Users/YOUR_NAME/Downloads/NBA-work/badge-arcade-offline-main"
```

Replace `YOUR_NAME` and the folder path as needed. Confirm that this folder
contains `tools/build_spotpass.py`, then run:

```sh
python3 -m venv ../nba-private/weekly-venv
../nba-private/weekly-venv/bin/python -m pip install -r requirements-spotpass.txt
```

This creates a Python environment for Weekly beside your private inputs, separate
from any Windows Python environment used for Expanded. No activation is needed.
Skip the `pip install` line only if both packs are already decrypted.

#### 5. Build the Custom Weekly ZIP

Run this command in the same terminal on macOS, Linux, or Ubuntu in WSL.
Change the `--week` and `--allbadge` filenames to match your inputs:

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

For two decrypted SARCs, point `--week` and `--allbadge` to those files and remove
the entire `--boot9` line. With even one encrypted pack, keep `--boot9` and install
the decryption dependency in step 4.

The default **game-only** build preserves existing HOME Menu/GYTB badge data.
Append `--home-menu` if you want HOME Menu export; it can replace custom badges.

Wait for **Custom Weekly personal install:** and a summary such as
`Week 2022-05-27: … unique playable machines`.
The date must match the week you intended to select. Machine counts vary by pack;
the badge-resource count describes the merged collection catalog, not badges
automatically awarded to your save.

The output is `nba-private/nba-custom-weekly-luma.zip`. In the WSL example it is
also available in your Windows `NBA-work/nba-private/` folder for extraction.
All processing happens on your computer. The builder keeps your input files,
removes temporary build files, and excludes the key dump and encryption keys
from the ZIP. Keep the ZIP private because it contains game resources.

#### 6. Install the week and change weeks later

1. Extract `nba-custom-weekly-luma.zip` on your computer. Close the game, power
   off the console, and connect the SD card.
2. Back up your current installation, then remove the previous patch files for
   `0004000000153600` listed in [Install the patch](#install-the-patch).
   Remove conflicting `code.bin` / `romfs.bin` overrides. Keep your extdata,
   collection saves, and other titles' patches.
3. Copy the ZIP's **entire `luma` folder** to the SD root, merging folders and
   replacing this title's files. Keep its generated `code.ips` and RomFS together.
   Weekly's IPS changes the schedule source and archive index; substituting a
   Vanilla or Expanded IPS can produce an incorrect lineup or a crash.
4. Check these paths on the SD card:

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

5. Eject the card and put it back in the console. Hold **SELECT** while powering
   on, check **Enable game patching**, and save the Luma3DS configuration.
6. Start Nintendo Badge Arcade, select a play pack, and confirm the dialog for
   free plays. Use **L/R** to browse the selected week's machines. Historical
   layouts outside this week appear only in the collection viewer. The builder
   uses base/update resources without adding their other machines to the lineup.

To switch weeks, put another complete EUR weekly pack in your inputs folder,
rerun step 5 with its `--week` path, and repeat step 6 with the new ZIP.
Reuse the original base/update files, schedule, and full badge catalog. You can
give `--output` a different filename for each week to keep packages for later.
Always install the entire package when changing weeks, and keep the game's
extdata so ownership survives the change.

To return to Expanded, install the complete Expanded package from its guide.
To return to Vanilla, remove the Weekly RomFS overrides as directed in
[Install the patch](#install-the-patch), then install the Vanilla IPS. Vanilla's
smaller catalog may omit historical badges from its viewer even though their
ownership remains in your save.

#### Weekly troubleshooting

| Symptom | What to check |
| --- | --- |
| `c++` or `clang` is missing | Finish step 2 and reopen the build terminal. On Windows, run the build inside Ubuntu in WSL. The script needs both a C++17 compiler and clang. |
| Compilation fails, or clang cannot assemble for `arm-none-eabi` | Check your compiler installation and ARM target support. `CXX` controls the desktop compiler; the ARM assembler is always invoked as `clang`. Use the tools in step 2. |
| A Python environment fails to run after switching from Windows to WSL | Create the `weekly-venv` environment using Ubuntu's `python3` in step 4. A Windows environment cannot be reused as a Linux environment. |
| `Installed content does not match supported EUR base 1.3.0 / update 1.3.1` | Use the original extracted inputs and compare their hashes in [Prepare the input files](#prepare-the-input-files). Do not use the generated Expanded or Weekly `pc.sarc` as an input. |
| `Pack has no weekly schedule` / `Expected a seven-day archived week` | Supply a complete weekly pack to `--week`, not the `allbadge` catalog or an extracted inner archive. |
| `Archived week is not EUR` / `SpotPass pack is not for EUR Badge Arcade` | Use EUR packs for both `--week` and `--allbadge`. |
| `Expected the full allbadge resource archive` | Point `--allbadge` to the full EUR catalog; a weekly pack is not a substitute. |
| Decryption or input-path errors | Use the checks in [If you get stuck](#if-you-get-stuck). Supply `--boot9` whenever either pack is encrypted, and install PyCryptodome using the Weekly environment's interpreter. |
| The old week remains active, or the game crashes | Replace the whole title patch with the new ZIP's files, check the SD paths above, and enable game patching. Keep the installed EUR 1.3.1 update. Changing the console date does not select another week. |

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
`releases/v0.5.2/` contains both current ZIPs, build records, and checksums.

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
