# NBA v0.4.0

Nintendo Badge Arcade EUR Ver. 1.3.1 offline on Luma, with a merged catalog from
the supported 1.3.0 base game and 1.3.1 update.

- Restores 113 badge resources and 14 original catchers absent from the update:
  eight Fire Emblem and six Rhythm Heaven catchers.
- Includes 398 original regular catchers and 8 bonus Arcade Bunny catchers,
  for 406 selectable catchers covering all 2,078 bundled badge resources.
- The bonus catchers use the game's native four-badge layout, collision data and
  badge art. They make the 32 otherwise-unassigned base Bunny badges obtainable.
- Shared asset names use the update's version. Base-only artwork, layouts,
  cabinets, icons, attachments and fixed objects retain their original bytes.
- Existing signed saves stay compatible. Badges remain inside the game; HOME
  badge reads and writes remain disabled. Purchases and gameplay stay offline.

The executable IPS is unchanged: its existing 512-catcher capacity accommodates
the merged catalog. The new content is a LayeredFS asset patch. The public ZIP
includes a portable builder; supply both original pc.sarc files and the update
common Schedule.xml to build your complete personal install.

Release files: `nba-offline-v0.4.0.zip`, `build.json`, `SHA256SUMS`.
