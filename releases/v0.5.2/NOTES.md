# Nintendo Badge Arcade offline v0.5.2

## Changes

You can start the game without a Nintendo Network ID (NNID).
It is not necessary to start the game before you install the patch.

The patch makes local save data before the title screen opens.
The patch does not use SpotPass task registration during startup.
Before this change, a failure during SpotPass task registration caused an SD card error.
The game then showed the HOME button exit screen.

## Requirements

Use the EUR game with update 1.3.1 and Luma3DS.
Select **Enable game patching** in the Luma3DS configuration.

## Files

- **nba-offline-v0.5.2-game-only.zip**: New badges stay in the game. This option keeps your HOME Menu badge data.
- **nba-offline-v0.5.2-home-menu.zip**: The game can send badges to the HOME Menu. This option can replace custom HOME Menu badges.
- **SHA256SUMS**: SHA-256 checksums for the two ZIP files.

## Installation

For Vanilla, select one ZIP file.
Make a backup of your save data before installation.
Put the `luma` folder from the ZIP file in the root of the SD card.
Replace the previous `code.ips` file.
Keep your save data.

For Expanded or Custom Weekly, make a new package with the tools from v0.5.2.
Do the [installation procedure](https://github.com/GrouchoGlasses42/badge-arcade-offline/blob/v0.5.2/README.md#install-the-patch).

## Tests

435 tests gave the correct results.
We did not do 53 tests.
The source checks and release checks found no errors.

Both patch options started the game in an emulator with account and SpotPass errors.
In a console test, the game started without an NNID.
