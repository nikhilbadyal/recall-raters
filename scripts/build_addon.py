#!/usr/bin/env python3
# Import standard argparse module to parse command-line arguments gracefully
import argparse

# Import os, sys, shutil, subprocess, and zipfile for OS process control and file operations
import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

def kill_anki_process():
    """
    Terminates any running Anki application process cross-platform (macOS, Windows, Linux).
    Prevents file lock conflicts and ensures updated add-on files take effect on next launch.
    """
    print("🔪 Checking for running Anki processes to terminate...")
    try:
        if sys.platform == "darwin":
            # On macOS, attempt to terminate processes named 'Anki' or matching case-insensitively
            result = subprocess.run(["pkill", "-x", "Anki"], capture_output=True)
            if result.returncode == 0:
                print("   Stopped running Anki instance on macOS.")
            else:
                # Case-insensitive search fallback for anki binary name
                subprocess.run(["pkill", "-i", "anki"], capture_output=True)
        elif sys.platform == "win32":
            # On Windows, force kill task using taskkill for anki.exe executable
            subprocess.run(["taskkill", "/F", "/IM", "anki.exe"], capture_output=True)
        else:
            # On Linux, terminate process matching anki
            subprocess.run(["pkill", "-f", "anki"], capture_output=True)
    except Exception as err:
        # Log warning if process termination command fails non-fatally
        print(f"   Warning: Unable to terminate Anki process automatically: {err}")

def get_default_anki_addons_dir() -> Path:
    """
    Detects the standard default Anki 21 add-ons directory based on host Operating System.
    
    Returns:
        Path object pointing to the OS-specific addons21 directory.
    """
    # Expand user home directory path
    home = Path.home()
    
    if sys.platform == "darwin":
        # macOS standard Anki add-ons path
        return home / "Library" / "Application Support" / "Anki2" / "addons21"
    elif sys.platform == "win32":
        # Windows standard Anki add-ons path (%APPDATA%/Anki2/addons21)
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "Anki2" / "addons21"
        return home / "AppData" / "Roaming" / "Anki2" / "addons21"
    else:
        # Linux standard Anki add-ons path (~/.local/share/Anki2/addons21)
        return home / ".local" / "share" / "Anki2" / "addons21"

def main():
    """
    Build script to package the Recall Raters add-on into a .ankiaddon archive,
    optionally kill running Anki instances, and install into target Anki addons directory.
    """
    # Configure command-line argument parser
    parser = argparse.ArgumentParser(
        description="Build and optionally install the Recall Raters Anki add-on."
    )
    
    # Optional flag to trigger auto-installation to default system Anki addons directory
    parser.add_argument(
        "-i", "--install",
        action="store_true",
        help="Automatically copy add-on files to default local system Anki addons21 folder."
    )
    
    # Optional argument to supply a custom target installation directory path
    parser.add_argument(
        "--install-dir",
        type=str,
        default=None,
        help="Custom target directory path to install add-on (e.g. '/path/to/Anki2/addons21')."
    )

    # Optional flag to kill running Anki process during installation (defaults to True on install)
    parser.add_argument(
        "-k", "--kill",
        action="store_true",
        default=True,
        help="Kill any running Anki application instance prior to installation (default: True)."
    )

    # Optional flag to explicitly skip killing Anki process
    parser.add_argument(
        "--no-kill",
        action="store_false",
        dest="kill",
        help="Do not terminate running Anki application instance during installation."
    )

    # Parse supplied CLI arguments
    args = parser.parse_args()

    # Resolve repository root directory relative to this script location
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    # Path to add-on source files directory
    src_dir = repo_root / "src" / "recall_raters"
    
    # Path to output build directory
    dist_dir = repo_root / "dist"
    
    # Ensure source directory exists before attempting build
    if not src_dir.exists():
        print(f"Error: Source directory not found at {src_dir}", file=sys.stderr)
        sys.exit(1)
        
    # Ensure output dist directory exists
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    # Output archive file path (.ankiaddon format)
    output_archive = dist_dir / "recall_raters.ankiaddon"
    
    print(f"📦 Building Anki Add-on package...")
    print(f"  Source: {src_dir}")
    print(f"  Destination: {output_archive}")
    
    # Required files that must be present in the add-on package
    required_files = ["__init__.py", "manifest.json", "config.json"]
    for req_file in required_files:
        if not (src_dir / req_file).exists():
            print(f"Error: Required file '{req_file}' missing from {src_dir}", file=sys.stderr)
            sys.exit(1)
            
    # Create ZIP archive with deflate compression
    with zipfile.ZipFile(output_archive, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files in src_dir and write them into root of zip file
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                # Exclude python cache files or hidden files
                if file.endswith(".pyc") or file.startswith("."):
                    continue
                    
                full_path = Path(root) / file
                # Calculate relative path inside the zip archive (root-level placement)
                arc_name = full_path.relative_to(src_dir)
                
                print(f"  Adding to zip: {arc_name}")
                zipf.write(full_path, arc_name)
                
    print(f"✅ Successfully built Anki Add-on package: {output_archive}")
    print(f"   Size: {output_archive.stat().st_size} bytes\n")

    # Determine whether user requested auto-install or custom install-dir
    target_addons_dir = None
    
    if args.install_dir:
        # User specified explicit custom target installation directory
        target_addons_dir = Path(args.install_dir).expanduser().resolve()
    elif args.install:
        # User requested automatic installation using OS default path
        target_addons_dir = get_default_anki_addons_dir()

    # Perform installation if target directory is resolved
    if target_addons_dir:
        # Terminate running Anki instance if requested
        if args.kill:
            kill_anki_process()

        # Destination sub-folder for this add-on inside addons21
        addon_dest_dir = target_addons_dir / "recall_raters"
        print(f"🚚 Installing add-on to target directory...")
        print(f"   Target path: {addon_dest_dir}")
        
        # Ensure parent addons21 directory exists
        target_addons_dir.mkdir(parents=True, exist_ok=True)
        
        # Remove existing destination directory if present to perform clean overwrite
        if addon_dest_dir.exists():
            shutil.rmtree(addon_dest_dir)
            
        # Copy entire src_dir tree to target add-on destination
        shutil.copytree(src_dir, addon_dest_dir)
        print(f"✨ Successfully installed Recall Raters to: {addon_dest_dir}")
        print("👉 Launch Anki to activate the updated add-on.")

if __name__ == "__main__":
    # Execute main build and install process
    main()
