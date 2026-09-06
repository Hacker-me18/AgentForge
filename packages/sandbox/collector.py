"""Collection of artifact files produced by sandboxed runs."""

import shutil
from pathlib import Path


class ArtifactCollector:
    """Copies artifact files (*.png/*.json/*.csv) from a staging directory
    into the run's artifacts directory on the host."""

    PATTERNS = ("*.png", "*.json", "*.csv")

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def destination(self, run_id: str) -> Path:
        """Artifacts directory for a given run id."""
        return self.root / run_id

    def collect(self, staging: str | Path, dest: str | Path) -> list[str]:
        """Copy matching artifacts from *staging* into *dest*.

        Returns the sorted list of collected file names.
        """
        staging_path = Path(staging)
        dest_path = Path(dest)
        dest_path.mkdir(parents=True, exist_ok=True)
        names: set[str] = set()
        if not staging_path.is_dir():
            return []
        for pattern in self.PATTERNS:
            for file in staging_path.rglob(pattern):
                if file.is_file():
                    shutil.copy2(file, dest_path / file.name)
                    names.add(file.name)
        return sorted(names)
