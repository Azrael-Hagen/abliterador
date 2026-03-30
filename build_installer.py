#!/usr/bin/env python3
r"""
Build script for Abliterador Studio using PyInstaller.

This script generates standalone executables for Windows, macOS, and Linux.

Usage:
  python build_installer.py                  # Build for current platform
  python build_installer.py --onefile        # Single executable (larger but portable)
  python build_installer.py --windows        # Windows-specific build
  python build_installer.py --linux          # Linux-specific build

Requirements:
  pip install PyInstaller>=6.10.0

Output:
  - dist/AbliteradorStudio/       (Windows: dist\AbliteradorStudio\)
  - dist/abliterador_studio.exe   (Windows, if --onefile)
  - dist/abliterador_studio       (Linux/macOS executable)
"""

import os
import sys
import shutil
import argparse
import subprocess
import importlib.util
from pathlib import Path


def get_pyinstaller_args(
    one_file: bool = False,
    target_os: str = None,
    app_name: str = "AbliteradorStudio",
    entrypoint: str = "abliterador_studio.py",
    console: bool = False,
) -> list:
    """
    Generate PyInstaller command-line arguments.
    
    Args:
        one_file: If True, creates single bundled executable. If False, creates directory.
        target_os: "windows", "linux", "macos", or None for current system.
    
    Returns:
        List of arguments for PyInstaller
    """
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        f"--name={app_name}",
        "--onedir" if not one_file else "--onefile",
        "--windowed" if not console else "--console",
        "--clean",     # Clean build directory before building
        "--noconfirm", # Don't ask for confirmation
        "--icon=abliterador_app/ui/icon.ico" if Path("abliterador_app/ui/icon.ico").exists() else None,
    ]
    
    # Remove None entries
    args = [arg for arg in args if arg]
    
    # Add splash screen if available
    if Path("abliterador_app/ui/splash.png").exists():
        args.append("--splash=abliterador_app/ui/splash.png")
    
    # Add hidden imports for problematic packages
    hidden_imports = [
        "heretic",
        "heretic_llm",
        "transformers",
        "torch",
        "PySide6",
    ]
    for imp in hidden_imports:
        if importlib.util.find_spec(imp) is not None:
            args.append(f"--hidden-import={imp}")

    # Include web assets for packaged FastAPI frontend
    args.append("--collect-data=abliterador_web")
    
    # Entrypoint
    args.append(entrypoint)
    
    return args


def clean_build_artifacts():
    """Remove previous build artifacts."""
    dirs_to_remove = ["build", "dist", "__pycache__", "*.egg-info"]
    
    for pattern in dirs_to_remove:
        if "*" in pattern:
            for item in Path(".").glob(pattern):
                if item.is_dir():
                    print(f"[>>] Removing {item}...")
                    shutil.rmtree(item, ignore_errors=True)
        else:
            if Path(pattern).exists():
                print(f"[>>] Removing {pattern}...")
                shutil.rmtree(pattern, ignore_errors=True)


def build_executable(
    one_file: bool = False,
    target_os: str = None,
    app_name: str = "AbliteradorStudio",
    entrypoint: str = "abliterador_studio.py",
    console: bool = False,
):
    """
    Build standalone executable with PyInstaller.
    
    Args:
        one_file: Single file executable vs. directory bundle
        target_os: Target operating system
    """
    print(f"\n{'='*70}")
    print(f"Abliterador Studio - Build Executable")
    print(f"{'='*70}\n")
    
    # Verify entrypoint exists
    if not Path(entrypoint).exists():
        print(f"ERROR: {entrypoint} not found in current directory.")
        sys.exit(1)
    
    print(f"[OK] Entrypoint found: {entrypoint}")
    
    # Check PyInstaller is installed
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} installed")
    except ImportError:
        print("ERROR: PyInstaller not installed. Run: pip install PyInstaller")
        sys.exit(1)
    
    # Clean previous builds
    print("\n[>>] Cleaning previous build artifacts...")
    clean_build_artifacts()
    
    # Get PyInstaller args
    print("\n[>>] Generating PyInstaller arguments...")
    args = get_pyinstaller_args(
        one_file=one_file,
        target_os=target_os,
        app_name=app_name,
        entrypoint=entrypoint,
        console=console,
    )
    
    # Build
    print("\n[>>] Building executable (this may take 2-5 minutes)...")
    print(f"    Command: {' '.join(args)}\n")
    
    result = subprocess.run(args, check=False)
    
    if result.returncode != 0:
        print("\nERROR: Build failed. Check the output above for details.")
        sys.exit(1)
    
    # Summary
    print(f"\n{'='*70}")
    print("[OK] Build successful!")
    print(f"{'='*70}\n")
    
    if one_file:
        exe_name = f"{app_name}.exe" if sys.platform == "win32" else app_name
        exe_path = Path("dist") / exe_name
        print(f"[+] Executable: {exe_path}")
        print(f"    Size: {exe_path.stat().st_size / (1024**2):.1f} MB")
        print(f"    Run: ./{exe_path}")
    else:
        bundle_path = Path("dist") / app_name
        print(f"[+] Bundle directory: {bundle_path}")
        exe = bundle_path / (f"{app_name}.exe" if sys.platform == "win32" else app_name)
        if exe.exists():
            print(f"  Executable: {exe}")
        print(f"  Run: ./{bundle_path / (f'{app_name}.exe' if sys.platform == 'win32' else app_name)}")
    
    print("\n[>>] You can now distribute this executable or folder to other systems.")
    print("     No Python installation required on target systems.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Build Abliterador Studio standalone executable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_installer.py                    # Default: one directory, current OS
  python build_installer.py --onefile          # Single executable (+ libraries bundled)
  python build_installer.py --windows          # Target Windows
  python build_installer.py --linux --onefile  # Linux single executable
        """,
    )
    
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create single executable (vs. directory bundle). Larger size but fully portable.",
    )
    parser.add_argument(
        "--windows",
        action="store_true",
        help="Build for Windows (cross-OS builds may have limitations)",
    )
    parser.add_argument(
        "--linux",
        action="store_true",
        help="Build for Linux",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts and exit (don't build)",
    )
    parser.add_argument(
        "--all-in-one",
        action="store_true",
        help="Build AbliteradorAllInOne server executable (console + LAN IP visible).",
    )
    
    args = parser.parse_args()
    
    if args.clean:
        print("[>>] Cleaning build artifacts...")
        clean_build_artifacts()
        print("[OK] Clean complete.\n")
        return
    
    target_os = None
    if args.windows:
        target_os = "windows"
    elif args.linux:
        target_os = "linux"
    
    app_name = "AbliteradorStudio"
    entrypoint = "abliterador_studio.py"
    console = False
    if args.all_in_one:
        app_name = "AbliteradorAllInOne"
        entrypoint = "abliterador_all_in_one.py"
        console = True

    build_executable(
        one_file=args.onefile,
        target_os=target_os,
        app_name=app_name,
        entrypoint=entrypoint,
        console=console,
    )


if __name__ == "__main__":
    main()
