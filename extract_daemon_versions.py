#!/usr/bin/env python3
"""
Extract daemon versions from Tor Expert Bundle binaries.
This script downloads all binaries, extracts them, and tries to get version info.
For Linux binaries on Linux, it runs them directly.
For other binaries, it extracts version from embedded strings in the binary.
"""

import hashlib
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

# Get OS filter from environment variable (set by GitHub Actions matrix)
OS_FILTER = os.environ.get('OS_FILTER', '').lower()
if OS_FILTER:
    print(f"Running on {SYSTEM}, will process {OS_FILTER} binaries only")
else:
    print(f"Running on {SYSTEM}, OS_FILTER not set, processing all binaries")

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

def calculate_binary_hash(tor_binary: Path) -> str | None:
    """Calculate SHA256 hash of the binary file."""
    try:
        sha256_hash = hashlib.sha256()
        with open(tor_binary, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        hash_value = sha256_hash.hexdigest()
        print(f"  [OK] Binary hash: {hash_value}")
        return hash_value
    except Exception as e:
        print(f"  [FAIL] Error calculating hash: {e}")
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
    binary_path_str = str(tor_binary).lower()
    
    # Android binaries can't be executed on any platform except Android devices
    if "android" in binary_path_str or "arm" in binary_path_str:
        can_execute = False
    elif SYSTEM == "linux" and "linux" in binary_path_str:
        # Try to run Linux binaries on Linux (both x86_64 and i686)
        can_execute = True
    elif SYSTEM == "windows" and "windows" in binary_path_str:
        # Try to run Windows binaries on Windows
        can_execute = True
    elif SYSTEM == "darwin" and "macos" in binary_path_str:
        # Try to run macOS binaries on macOS
        can_execute = True
    
    # Try executing if possible
    if can_execute:
        # Retry with different methods
        attempts = []  # type: ignore
        
        # For Linux, try with LD_LIBRARY_PATH set to bundled libraries
        if SYSTEM == "linux":
            lib_dir = tor_binary.parent  # Libraries are in same dir as binary
            attempts.append({
                'env': {'LD_LIBRARY_PATH': str(lib_dir)},
                'desc': 'with LD_LIBRARY_PATH'
            })
        
        # Default attempt without special env
        attempts.append({'env': {}, 'desc': 'default'})
        
        for attempt in attempts:
            try:
                # Make executable on Unix
                if SYSTEM != "windows":
                    os.chmod(tor_binary, 0o755)
                
                env = os.environ.copy()
                env_vars: dict = attempt['env']  # type: ignore
                if env_vars:
                    env.update(env_vars)
                    print(f"  Running: {tor_binary} --version ({attempt['desc']})")
                else:
                    print(f"  Running: {tor_binary} --version")
                
                result = subprocess.run(
                    [str(tor_binary), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=env
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
                    print(f"  [WARN] Could not extract version from execution")
                    
            except subprocess.TimeoutExpired:
                print(f"  [WARN] Timeout running binary ({attempt['desc']})")
            except Exception as e:
                print(f"  [WARN] Error running binary ({attempt['desc']}): {e}")
        
        print(f"  [INFO] All execution attempts failed, trying binary strings...")
    
    # Fallback: extract from binary strings
    print(f"  Extracting from binary strings (non-native platform)...")
    return extract_version_from_binary_strings(tor_binary)

def process_binary(file_info: dict, temp_dir: Path) -> dict | None:
    """Download, extract, and get version and hash from a binary."""
    file_name = file_info['file_name']
    url = file_info['url']
    
    print(f"\nProcessing: {file_name}")
    
    # Skip if OS_FILTER is set and this file doesn't match
    if OS_FILTER and OS_FILTER not in file_name.lower():
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
    
    # Calculate hash
    binary_hash = calculate_binary_hash(tor_binary)
    
    # Extract version
    version = extract_version(tor_binary)
    
    # Return both version and hash
    return {'version': version, 'hash': binary_hash}

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
    
    if OS_FILTER:
        filtered = [f for f in files if OS_FILTER in f['file_name'].lower()]
        print(f"Will process {len(filtered)} {OS_FILTER} files")
    else:
        print(f"Will process all {len(files)} files")
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Process each file
        updated_count = 0
        for file_info in files:
            file_name = file_info['file_name']
            
            # Skip if OS_FILTER is set and doesn't match
            if OS_FILTER and OS_FILTER not in file_name.lower():
                continue
            
            # Skip if already has daemon_version
            if 'daemon_version' in file_info and file_info['daemon_version'] and not file_info['daemon_version'].startswith('Error'):
                print(f"\n{file_name}: Already has version {file_info['daemon_version']}")
                continue
            
            # Process the binary
            result = process_binary(file_info, temp_path)
            
            if result:
                if result.get('version'):
                    file_info['daemon_version'] = result['version']
                if result.get('hash'):
                    file_info['daemon_hash'] = result['hash']
                updated_count += 1
            else:
                print(f"  Failed to extract version and hash")
    
    # Save updated JSON
    if updated_count > 0:
        print(f"\n{'='*60}")
        print(f"Updated {updated_count} files with daemon versions and hashes")
        print(f"Saving to {JSON_FILE}")
        
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        
        print("[OK] JSON file updated successfully")
    else:
        print("\nNo files were updated")

if __name__ == "__main__":
    main()
