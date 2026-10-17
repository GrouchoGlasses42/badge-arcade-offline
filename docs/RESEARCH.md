# Badge Arcade offline work

Targets: supplied EUR base `0004000000153600`, TMD 4096 / Ver. 1.3.0, and
update `0004000E00153600`, TMD 5136 / Ver. 1.3.1. This repository is self-contained.
Custom PNG loading is outside this patch's scope; it uses the game's own assets.

## Offline saves and HOME isolation

The patch works with Luma game patching and keeps Badge Arcade's collection
separate from HOME badge extdata. Native ownership, profile, story and statistics
saves stay in the game's own extdata.

`patches/badge_offline.s` replaces ownership/profile uploads with local signed
backup writes. Startup checks native HMACs and restores the first valid backup.
No HOME quantities are imported or merged. The signed backup files are `ba_owned_a.dat`, `ba_owned_b.dat`, `ba_prof_a.dat`,
`ba_prof_b.dat`. Native encoding, account checks and local story workers remain
active. A stable offline account ID is used only when the cached ID is zero.
Failed writes report failure and preserve the previous second copy.

HOME isolation covers several independent paths:

- `0x2408b8` / `0x2409a8`: complete the former export operation synchronously,
  clear its status/error, close its saving overlay and release its APT guard.
- Native HOME badge-device open, commit, initialization, quantity, category and
  reset operations return locally without filesystem access.
- Dedicated HOME archive mount and create SDK entries return failure before IPC,
  preventing accidental creation or formatting through another caller.
- Pre-title filesystem checks at `0x322608` inspect the virtual filename. Only
  `BADGE:` checks take their success callback directly; shared game-save checks
  replay their original prologue and continue normally.
- The additional pre-title initialization at `0x2e8c44` also returns local
  success, completing the HOME saving stage before TitleTask starts.
- Title resource completion resumes at state `0x36`, beyond HOME reconciliation.
- Story flag getter `0x259680` returns true only for HOME lesson flag 4. It reads
  all other flags normally and changes no persisted flag bits. Crane tutorial
  flag 3 and full setup flag 5 retain native behavior.
- Scene-name references at `0x3034dc`, `0x333830`, `0x335fdc` change from
  `CExporter` to `Book`, the native collection scene. Scene registry names are
  retained so unrelated scene registration is unaffected.

The HTTP client and SOC socket/DNS/send SDK entry points reject real network
operations. Both BOSS task-start interface copies complete without scheduling
network jobs. Normal title login/download states use local resources; optional
unexpected downloads return failure without claiming their buffers were filled.
Play packs run the native purchase-success finalizer locally. Original price and
eShop labels remain visible. Crane physics and badge acquisition remain native.

## Expanded bundled catalog

The catalog merges the supported 1.3.0 base archive and 1.3.1 update archive.
The update contains 1,965 prizes and 384 regular catchers. The base adds 113
prizes absent from the update: 53 Fire Emblem, 28 Rhythm Heaven and 32 Arcade
Bunny badges. It also adds 14 original catchers: `Emblem_000` through
`Emblem_007` and `Rhythm_015` through `Rhythm_020`. Shared filenames retain the
update's bytes. The merged catalog has 2,078 unique prize identities and 398
original regular catchers. This is bundled content, not every online release.

The 32 restored Bunny badges have native textures and collision polygons but
no original catcher assignments. Eight bonus catchers, `BTCenter_004` through
`BTCenter_011`, use four badges each. They copy `Kirby_001`'s four-badge
layout, including its stepped platform, physical placements and collection placements.
Only the machine identity, names, titles, prize references and icon change.
Machine IDs 4600 through 4607 are checked for collisions. Each icon uses the
first assigned badge's existing preview. No original asset is modified.

The final catalog contains 43 categories, 244 cabinets, 408 icons, 2,078 prizes,
28 attachments, 245 fixed objects and 407 layouts. All 406 regular layouts use
machine type 0 and are selectable with L/R. `MroSMB_018` remains practice type 2,
selected through the native practice path. Every prize appears in the regular
lineup; practice does not need to be added to the selector.

`src/badge_catalog.py` audits every machine dependency, category identity, prize
identity and native registry capacity. It rebuilds the SARC name/hash table to
include restored resources and generated bonus layouts/icons, and rebuilds
`pc/PrizeCollection.xml`. Original artwork and physics resources remain
byte-identical. New members use the archive's hash multiplier and 128-byte data
alignment. The schedule has sequential `DefaultStageName000` through `DefaultStageName405`
entries. Both common and EUR schedule locations are overridden. The native
schedule lookup already ignores dates for the bundled primary schedule.

The default catcher pointer vector allocated at `0x247e24` grows from 30 to 512.
The schedule parser owns strings in a dedicated heap, separate from its XML
scratch heap. Expanding only the pointer vector exhausted that string heap
before title loading. The patch raises the base allocation at `0x24d438` and
both update branches at `0x24de08` / `0x24de2c` to `0x40000` bytes. Existing
resource pools already cover the expanded catalog: categories 200, cabinets
1,500, icons 2,000, prizes 10,000, fixed objects 500, attachments 200, layouts 2,000.
The native per-lineup telemetry has 30 slots: its trigger path already clamps
indices to 29 and its completion loop stops at 30. These counters are separate
from ownership and the catcher vector; the patch does not enlarge the save schema.

Build the public patch with `python3 tools/release.py`. Build the complete
personal package with `tools/build_complete.py`, both extracted prize archives
and the update's common schedule. Exact inputs, fingerprints and commands are
in [BUILD.md](BUILD.md).
The public `releases/v0.4.0/` ZIP includes the code patch and portable catalog
builder. Personal full-asset packages stay under ignored `build/`.

The complete package records RomFS SHA-256 hashes and accepts a matching EUR
1.3.1 release package with a valid IPS fingerprint. The portable wrapper also
checks exact input asset fingerprints. No user's SARC or executable is shipped
in the public release. The original development logs mentioned below are local
validation history, not dependencies of either builder.

## Validation

Native ARM regression tests execute the exact supplied base and update code.
They cover offline request completion, all four pack choices, native signed
ownership/profile encoding and decoding, recovery from a corrupt primary copy,
failed-write backup preservation, extdata filename limits, game archive creation,
account identity, native story save queuing, HOME operation completion without
I/O, scalar output sizes, SDK mount/create barriers, HOME-only pre-title checks,
HOME lesson isolation, catcher capacity, schedule memory allocations and scene
redirects. Catalog tests audit actual extracted dependencies and unchanged assets.
Package tests check fingerprints, compatibility and the exact allowed file set.

Emulator evidence in the isolated portable Azahar profile:

- `boot-42-home-init`: title and normal crane startup; a five-attempt round
  reached Grab all without a server error. Both signed backups increased from
  14 to 16 resources. All four HOME archive files retained their original hashes.
- `boot-44-expanded-heaps`: expanded startup, L/R traversal into added Animal
  Crossing and button/hammer layouts, playable added catcher and prize drawer.
  Saved ownership reached 61 resources across 28 designs in both signed copies.
- `boot-45-catalog-count`: a temporary diagnostic read the native resource
  manager after loading: regular selector count `0x180` (384), registered layout
  count `0x181` (385). This diagnostic build is not packaged.
- Cold restart retained local ownership; HOME archive hashes remained unchanged
  through startup, navigation, collection and restart.
- `boot-46-release` and `boot-47-old3ds`: the packaged executable reached startup
  and gameplay, including with the original 3DS emulator memory configuration.
- Merged-catalog checks loaded restored Fire Emblem (`Emblem_000`) and Rhythm
  Heaven (`Rhythm_015`) catchers with their original assets. The bonus catcher
  loaded all four assigned Bunny designs on its physical platform, remained
  stable while idle, and completed crane attempts without a server error.
  Native signed save checks retained restored Bunny prize identities across a
  cold restart. All four HOME archive files kept their original hashes.
- The merged catalog suite passed 197 tests with both private archives and both
  supported executables. The unpacked portable builder, run without a compiler
  or extra Python packages, produced the same Luma files as the source build. All
  three packaged RomFS files matched the audited emulator assets. The release
  IPS retained the previous release's exact bytes.

The pre-split combined suite passed 293 tests. This repository retains the NBA
checks and adds independent build/release checks; see its test commands.

## Executable compatibility

The builder selects independent function, literal and field tables by executable
SHA-256 in `src/badge_versions.py`. It never assumes a single address delta.
Luma itself does not verify these hashes. The release targets the installed
EUR Ver. 1.3.1 update.

Base decompressed `.code`: size `0x356000`, SHA-256
`4278e14228eff0672b017d5a532210497ec824d7354fbb0c18ddae97f88323af`.
Update: size `0x357000`, SHA-256
`709693735d20649e1f058525d4e6c24109e229dcb8425479b644587c345290fc`.
The update's story format version is 3 instead of 2; profile/world fields move
by different amounts. IPS payloads replace an unused NEX upload worker and stay
within its verified boundary, preserving the following wrapper.

Backup filenames fit extdata's 16-byte limit; tests enforce that limit in
addition to native signature checks. The game's collection is restored only
from its local signed backups, without reading or writing HOME badge data.

Analysis data, Ghidra projects, private probes and portable emulator files remain
under ignored `work/`. The original game inputs and main emulator profile were
unchanged during development. The update tests use the installed update's NCCH and TMD with the base
and update RomFS mounted separately.

## References

- [save3ds](https://github.com/wwylele/save3ds/blob/master/README.md): extdata name limits.
- [Luma IPS loader](https://github.com/LumaTeam/Luma3DS/blob/master/sysmodules/loader/source/patcher.c).
- [GYTB](https://github.com/MrCheeze/GYTB): HOME badge storage.
- [Badge Arcade format research](https://github.com/AntiFreeze-1/badge-arcade-server-full).
