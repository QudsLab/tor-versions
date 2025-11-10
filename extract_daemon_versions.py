#!/usr/bin/env python3
"""
Extract daemon versions from Tor Expert Bundle binaries.
This script downloads all binaries, extracts them, and tries to get version info.
For Linux binaries on Linux, it runs them directly.
For other binaries, it extracts version from embedded strings in the binary.
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
print(f"Running on {SYSTEM}, will process ALL binaries")

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

def extract_version_from_binary_strings(tor_binary: Path) -> str | None:
    """Extract version from strings in the binary file (for non-native binaries)."""
    try:
        # Read binary file and search for version pattern
        with open(tor_binary, 'rb') as f:
            content = f.read()
            # Convert to string, ignoring errors
            text = content.decode('latin-1', errors='ignore')
            
            # Search for Tor version pattern
            # Pattern: "Tor version X.X.X.X" or just "X.X.X.X" near "Tor"
            patterns = [
                r'Tor version ([\d\.]+)',
                r'tor-([\d\.]+)',
                r'VERSION\s*=\s*"([\d\.]+)"',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    version = match.group(1)
                    # Validate it looks like a version (e.g., 0.4.8.19)
                    if re.match(r'^\d+\.\d+\.\d+\.\d+$', version):
                        print(f"  [OK] Extracted version from binary strings: {version}")
                        return version
        
        print(f"  [FAIL] Could not find version in binary strings")
        return None
    except Exception as e:
        print(f"  [FAIL] Error reading binary: {e}")
        return None

def extract_version(tor_binary: Path) -> str | None:
    """Run tor binary with --version and extract version number, or read from strings."""
    file_name = tor_binary.name.lower()
    
    # Check if we can run this binary natively
    can_execute = False
    if SYSTEM == "linux" and "linux" in str(tor_binary).lower():
        # Try to run Linux binaries on Linux
        can_execute = True
    elif SYSTEM == "windows" and "windows" in str(tor_binary).lower():
        # Try to run Windows binaries on Windows
        can_execute = True
    elif SYSTEM == "darwin" and "macos" in str(tor_binary).lower():
        # Try to run macOS binaries on macOS
        can_execute = True
    
    # Try executing if possible
    if can_execute:
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
                print(f"  [WARN] Could not extract version from execution, trying binary strings...")
                
        except subprocess.TimeoutExpired:
            print(f"  [WARN] Timeout running binary, trying binary strings...")
        except Exception as e:
            print(f"  [WARN] Error running binary: {e}, trying binary strings...")
    
    # Fallback: extract from binary strings
    print(f"  Extracting from binary strings (non-native platform)...")
    return extract_version_from_binary_strings(tor_binary)

def process_binary(file_info: dict, temp_dir: Path) -> str | None:
    """Download, extract, and get version from a binary."""
    file_name = file_info['file_name']
    url = file_info['url']
    
    print(f"\nProcessing: {file_name}")
    
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
