from __future__ import annotations

import shutil
from pathlib import Path


class FileMaterializer:
    """Concrete Materializer: copies build artifacts to final destinations.

    Per roadmap: creates parent directories as needed.
    Uses copy2 to preserve metadata. A successful PDF must never be lost.
    """

    def materialize(self, source: Path, destination: Path) -> None:
        """Copy a build artifact to its final destination."""
        if not source.is_file():
            raise FileNotFoundError(f"Build artifact not found: {source}")

        destination.parent.mkdir(parents=True, exist_ok=True)

        # Use a temporary name to avoid partial overwrites
        tmp_dest = destination.with_suffix(destination.suffix + ".tmp")
        try:
            shutil.copy2(source, tmp_dest)
            tmp_dest.replace(destination)
        except Exception:
            # Clean up partial temp file on failure
            try:
                tmp_dest.unlink(missing_ok=True)
            except OSError:
                pass
            raise
