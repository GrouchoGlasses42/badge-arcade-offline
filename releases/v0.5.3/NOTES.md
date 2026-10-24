# Nintendo Badge Arcade offline v0.5.3

## Changes

Expanded and Custom Weekly now reserve 8 MiB for the collection memory heap.
The original limit was 3.5 MiB.
The full catalog contains 7,921 badge resources and needs more memory.
If an allocation failed, the game continued with an invalid memory address.
This caused a failure at **Reading latest data**.
On a console, this failure could cause an ARM11 exception.

Both desktop builders now include the memory correction in their output IPS.
The correction applies to the game-only and HOME Menu export options.
The public Vanilla IPS files have no changes.

This change corrects the failure reported in [issue 1](https://github.com/GrouchoGlasses42/badge-arcade-offline/issues/1).

## Requirements

Use the EUR game with update 1.3.1 and Luma3DS.
Select **Enable game patching** in the Luma3DS configuration.

## Files

- **nba-offline-v0.5.3-game-only.zip**: Vanilla. New badges stay in the game. This option keeps your HOME Menu badge data.
- **nba-offline-v0.5.3-home-menu.zip**: Vanilla. The game can send badges to the HOME Menu. This option can replace custom HOME Menu badges.
- **SHA256SUMS**: SHA-256 checksums for the two ZIP files.

## Installation

For Expanded or Custom Weekly, use the scripts from v0.5.3 to make a new package.
Use your original game files and full EUR badge catalog.
Install the complete output ZIP.
Keep its IPS and RomFS files together.
Keep your game extdata and collection saves.

The public Vanilla ZIPs do not contain the full catalog memory correction.
Do the [installation procedure](../../README.md#install-the-patch) for your mode.

## Tests

The Expanded game-only package loaded the full catalog and entered the arcade in Azahar 2126.1.1.
The same package passed a Nintendo 3DS test.
The emulator gameplay check was not completed.
Custom Weekly did not get an emulator or console test for this correction.

The native ARM test checks the memory sizes requested by the collection manager.
The permanent heap is 8 MiB for full catalog packages.
The temporary heaps keep their original sizes.
The package tests check both builders and both HOME Menu options.

442 automated tests gave the correct results.
We did not do 54 tests.
The source checks, release checks, and private game material checks found no errors.
