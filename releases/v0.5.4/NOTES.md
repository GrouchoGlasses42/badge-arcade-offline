# Nintendo Badge Arcade offline v0.5.4

## Changes

Vanilla now makes all 384 normal machines in the EUR update available for play.
These machines contain 1,965 obtainable badge resources.
The practice machine stays separate.
Use **L/R** to select a machine.

Earlier Vanilla versions kept the original selection of 30 machines.
Their descriptions incorrectly gave 384 as the playable machine count.
This release corrects the selection in the executable.
It uses the layouts already in the installed game update.
Both native schedule paths use the new selection.
The bundled schedule's expiry date does not limit offline play.

Vanilla still needs only `code.ips`.
No extracted game files, full badge catalog, or console key dump is necessary.

Expanded and Custom Weekly keep their generated schedules.
Their builders do not include the Vanilla selection changes.
The full catalog memory correction from v0.5.3 stays active in these packages.

## Requirements

Use the EUR game with update 1.3.1 and Luma3DS.
Select **Enable game patching** in the Luma3DS configuration.

## Files

- **nba-offline-v0.5.4-game-only.zip**: Vanilla. New badges stay in the game. This option keeps your HOME Menu badge data.
- **nba-offline-v0.5.4-home-menu.zip**: Vanilla. The game can send badges to the HOME Menu. This option can replace custom HOME Menu badges.
- **SHA256SUMS**: SHA-256 checksums for the two ZIP files.

## Installation

For Vanilla, install one public ZIP.
Replace this title's `code.ips` file.
Keep your game extdata and collection saves.
If you change from Expanded or Custom Weekly, remove the previous RomFS files.
Do the [installation procedure](../../README.md#install-the-patch).

For Expanded or Custom Weekly, make a complete package with the current scripts.
Keep its IPS and RomFS files together.

## Tests

The native ARM test executes both selection loops with 384 normal layouts.
It also supplies display-only and practice layouts.
The loops select all normal layouts and omit the other layouts.
The fallback schedule test checks the expiry-date correction.
The package tests check that Expanded and Custom Weekly keep their own schedules.

In Azahar 2126.1.1, the game loaded 384 playable machines and the separate practice layout.
This test used the original EUR update archive and the public game-only IPS.
No RomFS replacement was installed.
All 384 normal layouts completed their dependency loading.
The emulator test also checked machine selection past the original limit and free plays.

446 automated tests gave the correct results.
We did not do 58 tests.
The source checks, release checks, and private game material checks found no errors.

The maintainer confirmed a successful Nintendo 3DS test of the new Vanilla selection.
