"""Ktisma: portable LaTeX build toolkit."""

from importlib.metadata import version, PackageNotFoundError
import platform

try:
    if __package__ is None:
        raise PackageNotFoundError
    __version__ = version(__package__)
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["info", "__version__"]


def info() -> str:
    """Format diagnostic information on package and platform."""
    return f"{__package__} {__version__} | Platform: {platform.system()} Python {platform.python_version()}"
