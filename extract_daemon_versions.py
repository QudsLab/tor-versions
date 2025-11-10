#!/usr/bin/env python3
"""
Extract daemon versions from Tor Expert Bundle binaries.
This script downloads binaries for the current OS, extracts them, runs --version, and updates the JSON.
"""

import json
import os
import platform
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlretrieve

# Determine current OS
SYSTEM = platform.system().lower()
if SYSTEM == "darwin":
    OS_FILTER = "macos"
elif SYSTEM == "windows":
    OS_FILTER = "windows"
elif SYSTEM == "linux":
    OS_FILTER = "linux"
else:
    print(f"Unsupported OS: {SYSTEM}")
    sys.exit(1)

print(f"Running on {SYSTEM}, will process {OS_FILTER} binaries only")

# Paths
BASE_DIR = Path(__file__).parent
JSON_FILE = BASE_DIR / "data" / "json" / "latest_export_versions.json"

def download_file(url: str, dest: Path) -> bool:
    """Download a file from URL to destination."""
    try:
        print(f"  Downloading: {url}")
        urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"  Error downloading: {e}")
        return False

def extract_archive(archive_path: Path, extract_to: Path) -> bool:
    """Extract tar.gz archive."""
    try:
        print(f"  Extracting archive...")
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(extract_to)
        return True
    except Exception as e:
        print(f"  Error extracting: {e}")
        return False

def find_tor_binary(extract_dir: Path) -> Path | None:
    """Find the tor binary in extracted directory."""
    # Look for 'tor' or 'tor.exe'
    binary_names = ['tor.exe', 'tor'] if SYSTEM == "windows" else ['tor']
    
    for binary_name in binary_names:
        for tor_path in extract_dir.rglob(binary_name):
            # Skip tor-gencert, tor-resolve, etc.
            if tor_path.name in ['tor', 'tor.exe']:
                print(f"  Found binary: {tor_path}")
                return tor_path
    
    print(f"  No tor binary found")
    return None

def extract_version(tor_binary: Path) -> str | None:
    """Run tor binary with --version and extract version number."""
    try:
        # Make executable on Unix
        if SYSTEM != "windows":
            os.chmod(tor_binary, 0o755)
        
        print(f"  Running: {tor_binary} --version")
        result = subprocess.run(
            [str(tor_binary), "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout + result.stderr
        print(f"  Output: {output[:100]}...")
        
        # Extract version using regex: "Tor version 0.4.8.19"
        version_regex = r'Tor version ([\d\.]+)'
        match = re.search(version_regex, output)
        
        if match:
            version = match.group(1)
            print(f"  [OK] Extracted version: {version}")
            return version
        else:
            print(f"  [FAIL] Could not extract version from output")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"  [FAIL] Timeout running binary")
        return None
    except Exception as e:
        print(f"  [FAIL] Error running binary: {e}")
        return None

def process_binary(file_info: dict, temp_dir: Path) -> str | None:
    """Download, extract, and get version from a binary."""
    file_name = file_info['file_name']
    url = file_info['url']
    
    print(f"\nProcessing: {file_name}")
    
    # Skip if not for current OS
    if OS_FILTER not in file_name.lower():
        print(f"  Skipping (not {OS_FILTER})")
        return None
    
    # Create temp directory for this file
    file_temp_dir = temp_dir / file_name.replace('.tar.gz', '')
    file_temp_dir.mkdir(exist_ok=True)
    
    # Download
    archive_path = file_temp_dir / file_name
    if not download_file(url, archive_path):
        return None
    
    # Extract
    extract_dir = file_temp_dir / "extracted"
    extract_dir.mkdir(exist_ok=True)
    if not extract_archive(archive_path, extract_dir):
        return None
    
    # Find binary
    tor_binary = find_tor_binary(extract_dir)
    if not tor_binary:
        return None
    
    # Extract version
    version = extract_version(tor_binary)
    return version

def main():
    """Main function."""
    # Load JSON
    if not JSON_FILE.exists():
        print(f"Error: {JSON_FILE} not found")
        sys.exit(1)
    
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    files = data.get('files', [])
    print(f"Found {len(files)} files in JSON")
    
    # Filter files for current OS
    os_files = [f for f in files if OS_FILTER in f['file_name'].lower()]
    print(f"Will process {len(os_files)} {OS_FILTER} files")
    
    if not os_files:
        print(f"No {OS_FILTER} files to process")
        return
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Process each file
        updated_count = 0
        for file_info in files:
            file_name = file_info['file_name']
            
            # Skip if not for current OS
            if OS_FILTER not in file_name.lower():
                continue
            
            # Skip if already has daemon_version
            if 'daemon_version' in file_info and file_info['daemon_version'] and not file_info['daemon_version'].startswith('Error'):
                print(f"\n{file_name}: Already has version {file_info['daemon_version']}")
                continue
            
            # Process the binary
            version = process_binary(file_info, temp_path)
            
            if version:
                file_info['daemon_version'] = version
                updated_count += 1
            else:
                print(f"  Failed to extract version")
    
    # Save updated JSON
    if updated_count > 0:
        print(f"\n{'='*60}")
        print(f"Updated {updated_count} files with daemon versions")
        print(f"Saving to {JSON_FILE}")
        
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        
        print("[OK] JSON file updated successfully")
    else:
        print("\nNo files were updated")

if __name__ == "__main__":
    main()
