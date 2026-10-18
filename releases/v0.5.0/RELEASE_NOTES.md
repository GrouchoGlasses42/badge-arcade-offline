# Nintendo Badge Arcade offline v0.5.0

For EUR Nintendo Badge Arcade with the Ver. 1.3.1 update installed and Luma
**Enable game patching** enabled.

Choose one ZIP:

- **nba-offline-v0.5.0-game-only.zip**: the existing HOME-isolated patch. Badges
  stay in the game; custom GYTB badges are preserved.
- **nba-offline-v0.5.0-home-menu.zip**: restores the original HOME badge archive
  access, export worker, placement screens and HOME lesson. This build can
  replace custom GYTB badges. Back up HOME badge data first.

Each ZIP contains only the Luma folder. Copy it to your SD root. Both replace
`luma/titles/0004000000153600/code.ips`; install only one variant at a time.
Both keep offline free plays, network blocks and signed local collection saves.
Existing saves and personal expanded RomFS files remain compatible. Switching
back to game-only does not undo HOME changes already made by the HOME build.

For the combined 2,078-badge / 406-catcher lineup, use the repository's personal
catalog builder with your own supported base/update assets. Add `--home-menu`
for HOME export; the default stays game-only. Public downloads contain no game
assets or build tools.

The game-only IPS is unchanged from v0.4.0. HOME export uses the game's original
capacity and replacement rules. See docs/RESEARCH.md for validation details.

Validation: 352 native/catalog tests passed. The HOME build completed a round
and exported badge files with quantities checked against the signed collection
in Azahar. Placement on a physical 3DS HOME Menu has not yet been tested.
