import importlib.metadata
from pathlib import Path

def get_version() -> str:
    try:
        return importlib.metadata.version("kapipy")
    except importlib.metadata.PackageNotFoundError:
        # fallback for local dev
        import tomllib
        pyproject = Path(__file__).parents[2] / "pyproject.toml"
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]

__version__ = get_version()
