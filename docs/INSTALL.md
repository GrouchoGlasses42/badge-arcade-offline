# Install Badge Arcade offline

Use the EUR game with **Ver. 1.3.1 update installed**, update title
`0004000E00153600`, TMD 5136. Keep the update installed. The patch's folder
uses base title ID `0004000000153600`.

Choose one release ZIP: **game-only** keeps HOME badge access disabled;
**home-menu** restores native HOME badge access and export. The HOME build can
replace custom GYTB badges. Use game-only if you want to keep those badges.
Both builds use the same title ID, offline collection and network blocks.

1. Keep a backup of your game extdata and HOME badge data.
2. Copy the release's **luma** folder to your SD root, replacing the previous
   `code.ips`. Enable **Enable game patching** in Luma.
3. Start normally, choose a play pack and confirm its purchase dialogue. Plays
   are granted locally; no payment or internet connection takes place.

Code-only installation uses the original lineup. For **406 selectable catchers**,
run the included `tools/build_complete.py` with your own base `base-pc.sarc`, update
`pc.sarc`, and update common `Schedule.xml`, as described in README.md. Then copy
the generated ZIP's **luma** folder to your SD root. Add `--home-menu` to the
builder command for HOME export. A complete installation contains:

```text
SD:/luma/titles/0004000000153600/code.ips
SD:/luma/titles/0004000000153600/romfs/region_common/Schedule.xml
SD:/luma/titles/0004000000153600/romfs/region_EUR/common/Schedule.xml
SD:/luma/titles/0004000000153600/romfs/region_EUR/common/sharc/pc.sarc
```

Use L/R to browse 398 original regular catchers and 8 bonus catchers. Together,
they cover all 2,078 badge resources in the supported base and update archives.
The bonus catchers use an original four-badge layout to make the 32 extra Arcade
Bunny badges obtainable. The separate practice layout stays registered. This is
not a download of every machine/badge ever released online.

The **game-only** patch disables HOME badge reads, writes, archive creation and formatting.
New badges stay inside Badge Arcade. The former placement shortcuts open its
collection viewer. GYTB custom badges are neither imported nor changed. No
`badges` folder is needed. The HOME placement lesson is skipped; the crane
tutorial and other story predicates retain native behavior.

The **home-menu** patch restores the original archive initialization, badge
export worker, collection/category queries, placement screens and HOME lesson.
Earned badges can be exported for use on HOME Menu. The offline collection is
still restored from the game's signed local backups; existing HOME badges are
not imported as the offline collection. The game retains its original HOME
capacity and export rules. Native export can overwrite custom GYTB data.

To switch builds, replace `code.ips` with the other build's file. Keep the same
RomFS files. Switching back to game-only does not restore replaced HOME data.
Existing signed saves remain compatible. Do not delete extdata.
The game's ownership/profile files are `ba_owned_a.dat`, `ba_owned_b.dat`,
`ba_prof_a.dat`, `ba_prof_b.dat`. Native story/statistics files remain separate.
Startup validates signatures and can recover from the second copy. HOME badge
data is no longer a recovery source. HTTP/SOC requests are blocked and BOSS
task starts do not schedule downloads. Price and eShop labels remain visible.

The patch works with Luma game patching. Emulator checks also cover startup,
gameplay, saving and cold starts, including the original 3DS memory configuration.
For game-only, HOME archive files stayed byte-for-byte unchanged through
collecting and restarting. HOME export is checked separately; see RESEARCH.md
for the validation scope.

Remove this title's `code.ips` and the three listed RomFS files to remove the
patch. Keep your extdata backups. Do not combine with another executable patch
or `code.bin` replacement. Other game regions/versions are unsupported by this
release. Confirm `game_version: 1.3.1` in the repository's selected `game-only.json` or `home-menu.json`.
