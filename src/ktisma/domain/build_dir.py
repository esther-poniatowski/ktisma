from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import ResolvedConfig
from .context import SourceContext, VariantSpec


@dataclass(frozen=True)
class BuildDirPlan:
    build_dir: Path
    expected_pdf: Path
    lock_file: Path
    metadata_file: Path
    source_stem: str
    variant: Optional[VariantSpec] = None

    def to_dict(self) -> dict:
        result: dict = {
            "build_dir": str(self.build_dir),
            "expected_pdf": str(self.expected_pdf),
            "lock_file": str(self.lock_file),
            "metadata_file": str(self.metadata_file),
            "source_stem": self.source_stem,
        }
        if self.variant is not None:
            result["variant"] = self.variant.name
        return result


def plan_build_dir(
    ctx: SourceContext,
    config: ResolvedConfig,
    variant: Optional[VariantSpec] = None,
) -> BuildDirPlan:
    """Plan the build directory and expected artifact paths.

    Default pattern per roadmap:
    - <source-dir>/.ktisma_build/<stem>/
    - <source-dir>/.ktisma_build/<stem>-<variant>/ for variants
    """
    stem = ctx.source_file.stem
    out_dir_name = config.build.out_dir_name

    if variant is not None:
        dir_name = f"{stem}-{variant.name}"
    else:
        dir_name = stem

    build_dir = ctx.source_dir / out_dir_name / dir_name
    expected_pdf = build_dir / f"{stem}.pdf"
    lock_file = build_dir / ".ktisma.lock"
    metadata_file = build_dir / ".ktisma.meta.json"

    return BuildDirPlan(
        build_dir=build_dir,
        expected_pdf=expected_pdf,
        lock_file=lock_file,
        metadata_file=metadata_file,
        source_stem=stem,
        variant=variant,
    )
