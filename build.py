import toml
import shutil
import subprocess
import argparse
from pathlib import Path
import configparser

PYPROJECT = Path("pyproject.toml")
VERSION_FILE = Path("src/kapipy/__version__.py")

def bump_version(version_str: str) -> str:
    parts = version_str.strip().split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Unexpected version format: {version_str}")
    major, minor, micro = map(int, parts)
    micro += 1
    return f"{major}.{minor}.{micro}"

def sync_and_bump_version():
    print("🔄 Reading and bumping version...")
    data = toml.load(PYPROJECT)
    old_version = data["project"]["version"]
    new_version = bump_version(old_version)

    # Update pyproject.toml
    data["project"]["version"] = new_version
    with PYPROJECT.open("w", encoding="utf-8") as f:
        toml.dump(data, f)
    print(f"✅ pyproject.toml: {old_version} → {new_version}")

    # Update __version__.py
    VERSION_FILE.write_text(f'__version__ = "{new_version}"\n', encoding="utf-8")
    print(f"✅ __version__.py updated to {new_version}")

def clean_dist():
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("ℹ️ No dist/ directory found, skipping cleanup.")
        return

    print("🧹 Cleaning .whl and .gz files in dist/ (excluding .gitignore)...")
    for file in dist_dir.iterdir():
        if file.suffix in {".whl", ".gz"} and file.is_file():
            print(f"🗑️  Removing {file.name}")
            file.unlink()

def build_package():
    print("📦 Building package using uv...")
    subprocess.run(["uv", "build"], check=True)
    print("✅ Build complete.")

def get_credentials(index: str, path: Path = Path(".pypirc")) -> tuple[str, str]:
    parser = configparser.ConfigParser()
    parser.read(path)
    if index not in parser:
        raise ValueError(f"No credentials found for index '{index}' in {path}")
    username = parser[index]["username"]
    password = parser[index]["password"]
    return username, password

def publish_package(stage: str):
    index = "pypi" if stage == "prod" else "testpypi"
    username, password = get_credentials(index)

    print(f"🚀 Publishing to {index}...")
    subprocess.run([
        "uv", "publish",
        "--index", index,
        "--username", username,
        "--password", password
    ], check=True)
    print(f"✅ Published to {index}.")

def deploy_docs():
    print("🌐 Deploying documentation to GitHub Pages...")
    subprocess.run(["mkdocs", "build"], check=True)
    subprocess.run(["mkdocs", "gh-deploy", "--clean"], check=True)
    print("✅ Documentation deployed.")

def main():
    parser = argparse.ArgumentParser(description="Build and optionally publish the package.")
    parser.add_argument("--stage", choices=["test", "prod"], default="test", help="Target registry: 'test' (default) or 'prod'")
    parser.add_argument("--docs", action="store_true", help="Also deploy documentation to GitHub Pages")
    args = parser.parse_args()

    sync_and_bump_version()
    clean_dist()
    build_package()
    publish_package(args.stage)

    if args.docs:
        deploy_docs()

if __name__ == "__main__":
    main()
