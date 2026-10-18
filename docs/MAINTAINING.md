# Maintaining releases

This folder is an independent Git repository. Choose a GitHub remote and push
its `main` branch. No other project folder is required.

Before a release, update `VERSION`, the builder's release metadata, release notes,
and versioned paths together. Run `make release`, `make test`, `make lint`, and
`make verify-release`. Review the public ZIP allowlist and commit source plus the
versioned `releases/` assets. Private inputs and full-asset personal builds belong
outside tracked files.

Tag the reviewed commit with the matching version (for example, `v0.5.0`) and
push the tag. The release workflow verifies the committed artifact against source
and publishes a GitHub release containing only the two Luma ZIPs, one for each
HOME variant. Manifests, checksums and build tools stay in the source repository.
The checks workflow
also runs on pull requests and branch pushes without requiring game files.

ZIP compression can differ between Python/zlib versions, so CI checks the patch
bytes, file allowlist and recorded artifact hashes rather than
requiring a rebuild to have identical compressed ZIP bytes on every runner.
