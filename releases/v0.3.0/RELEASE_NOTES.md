# NBA v0.3.0

An offline patch for Nintendo Badge Arcade EUR Ver. 1.3.1 with its matching
update installed. Works on a modded 3DS with Luma game patching.

- Play packs are granted locally, with online requests blocked.
- Earned badges stay inside the game. HOME badge access is disabled to protect
  custom GYTB badges, while existing signed local saves remain compatible.
- The HOME placement lesson is skipped; the original crane tutorial remains.
- The personal expanded catalog adds 384 regular catchers to L/R, covering all
  1,965 badge resources bundled in the supported update.
- A portable Python catalog builder is included. It creates the complete install
  from the user's own extracted update assets; no game art or executable is
  included in this public release.

Automated checks cover native ARM code, signed saves, backup recovery, HOME
access barriers and catalog dependencies. Emulator checks include startup,
added-catcher navigation and gameplay, end-of-round saving, cold restart,
unchanged HOME archive hashes and the original 3DS memory configuration.

Release files: `nba-offline-v0.3.0.zip`, `build.json`, `SHA256SUMS`.
