#!/usr/bin/env python3
"""Build script for nao-core package.

This script:
1. Optionally bumps the version
2. Builds the frontend with Vite
3. Compiles the backend with Bun into a standalone binary
4. Bundles everything into a Python wheel
"""

import os
import re
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

app = App(help="Build and package nao-core CLI.")


class BumpType(Enum):
    patch = "patch"
    minor = "minor"
    major = "major"


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
    """Run a command and exit on failure."""
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        print(f"❌ Command failed: {' '.join(cmd)}")
        sys.exit(1)


def get_env_with_bun() -> dict:
    """Get environment with bun in PATH."""
    env = os.environ.copy()
    bun_path = Path.home() / ".bun" / "bin"
    if bun_path.exists():
        env["PATH"] = f"{bun_path}:{env.get('PATH', '')}"
    return env


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse a semver version string into (major, minor, patch)."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(version: str, bump_type: BumpType) -> str:
    """Bump a semver version string."""
    major, minor, patch = parse_version(version)

    if bump_type == BumpType.major:
        return f"{major + 1}.0.0"
    elif bump_type == BumpType.minor:
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def get_current_version(cli_dir: Path) -> str:
    """Get the current version from pyproject.toml."""
    pyproject = cli_dir / "pyproject.toml"
    content = pyproject.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def update_version(cli_dir: Path, new_version: str) -> None:
    """Update version in pyproject.toml and __init__.py."""
    # Update pyproject.toml
    pyproject = cli_dir / "pyproject.toml"
    content = pyproject.read_text()
    content = re.sub(
        r'^version\s*=\s*"[^"]+"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    pyproject.write_text(content)

    # Update __init__.py
    init_file = cli_dir / "nao_core" / "__init__.py"
    content = init_file.read_text()
    content = re.sub(
        r'^__version__\s*=\s*"[^"]+"',
        f'__version__ = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    init_file.write_text(content)

    print(f"✓ Version bumped to {new_version}")


def build_server(project_root: Path, output_dir: Path) -> None:
    """Build the frontend and backend into a standalone server."""
    backend_dir = project_root / "apps" / "backend"
    frontend_dir = project_root / "apps" / "frontend"

    print("📦 Building nao chat server...")
    print(f"   Project root: {project_root}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Build frontend
    print("\n🎨 Building frontend...")
    run(["npm", "run", "build"], cwd=frontend_dir)

    # Step 2: Copy frontend dist to backend public folder
    print("\n📁 Copying frontend assets to backend...")
    backend_public = backend_dir / "public"
    if backend_public.exists():
        shutil.rmtree(backend_public)
    shutil.copytree(frontend_dir / "dist", backend_public)

    # Step 3: Compile backend with Bun
    print("\n⚡ Compiling backend with Bun...")
    env = get_env_with_bun()
    run(
        ["bun", "build", "src/index.ts", "--compile", "--outfile", str(output_dir / "nao-chat-server")],
        cwd=backend_dir,
        env=env,
    )

    # Step 4: Copy frontend assets next to the binary
    print("\n📦 Bundling assets with binary...")
    output_public = output_dir / "public"
    if output_public.exists():
        shutil.rmtree(output_public)
    shutil.copytree(backend_public, output_public)

    # Cleanup temporary public folder in backend
    shutil.rmtree(backend_public)

    print("\n✓ Server build complete!")
    print(f"   Binary: {output_dir / 'nao-chat-server'}")
    print(f"   Assets: {output_public}")


def build_package(cli_dir: Path) -> None:
    """Build the Python package with uv."""
    # Clean dist folder first
    dist_dir = cli_dir / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print("🧹 Cleaned dist folder")

    print("\n📦 Building Python package...")
    run(["uv", "build"], cwd=cli_dir)

    version = get_current_version(cli_dir)
    print(f"\n✅ Build complete! (v{version})")
    print(f"   Packages are in: {cli_dir / 'dist'}")
    print("\n   To publish to PyPI:")
    print("   uv publish dist/*")


@app.default
def build(
    *,
    force: Annotated[bool, Parameter(["--force", "-f"], help="Force rebuild the server binary")] = False,
    skip_server: Annotated[bool, Parameter(["--skip-server", "-s"], help="Skip server build, only build Python package")] = False,
    bump: Annotated[BumpType | None, Parameter(help="Bump version before building (patch, minor, major)")] = None,
) -> None:
    """Build the nao-core package.

    Builds the frontend, compiles the backend with Bun, and creates a Python wheel.
    """
    cli_dir = Path(__file__).parent
    project_root = cli_dir.parent
    output_dir = cli_dir / "nao_core" / "bin"
    binary_path = output_dir / "nao-chat-server"
    public_dir = output_dir / "public"

    # Bump version if requested
    if bump:
        current = get_current_version(cli_dir)
        new_version = bump_version(current, bump)
        print(f"\n🔖 Bumping version: {current} → {new_version}")
        update_version(cli_dir, new_version)

    # Check if we need to build the server
    needs_build = force or not binary_path.exists() or not public_dir.exists()

    if skip_server:
        if not binary_path.exists() or not public_dir.exists():
            print("❌ Server binary not found. Run without --skip-server first.")
            sys.exit(1)
        print("✓ Skipping server build (--skip-server)")
    elif needs_build:
        build_server(project_root, output_dir)
    else:
        print("✓ Server binary already exists, skipping build (use --force to rebuild)")

    # Verify the binary exists
    if not binary_path.exists():
        print(f"❌ Binary not found: {binary_path}")
        sys.exit(1)

    if not public_dir.exists():
        print(f"❌ Public directory not found: {public_dir}")
        sys.exit(1)

    print(f"\n✓ Server assets ready")
    print(f"   Binary: {binary_path}")
    print(f"   Public: {public_dir}")

    # Build the Python package
    build_package(cli_dir)


if __name__ == "__main__":
    app()
