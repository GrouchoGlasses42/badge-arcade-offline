"""Keep user-owned game material outside the source checkout, even when ignored."""
from pathlib import Path

from patch_format import ROOT


def require_external(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError(f"Game assets and asset-containing output must be outside the repository: {path}")
    return resolved
