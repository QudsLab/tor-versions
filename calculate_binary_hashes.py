#!/usr/bin/env python3
"""
Calculate MD5 and SHA256 hashes for all Tor Expert Bundle binaries.
This script runs after platform-specific version extraction to ensure
every binary has hash information for verification.
"""

import hashlib
import json
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlretrieve

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
        print(f"  [FAIL] Error downloading: {e}")
        return False

def extract_archive(archive_path: Path, extract_dir: Path) -> bool:
    """Extract tar.gz archive."""
    try:
        print(f"  Extracting archive...")
        with tarfile.open(archive_path, 'r:gz') as tar:
            tar.extractall(extract_dir)
        return True
    except Exception as e:
        print(f"  [FAIL] Error extracting: {e}")
        return False

def find_tor_binary(extract_dir: Path) -> Path | None:
    """Find the tor binary in extracted directory."""
    # Common binary names and paths
    binary_names = [
        'tor/tor',           # Linux/macOS
        'tor/tor.exe',       # Windows
        'tor/libtor.so',     # Android shared library
        'tor.real',          # Some variants
        'Tor/tor',           # Case variation
    ]
    
    # First try common paths
    for binary_name in binary_names:
        binary_path = extract_dir / binary_name
        if binary_path.exists():
            print(f"  Found binary: {binary_path}")
            return binary_path
    
    # Fallback: search for any tor-related binary file
    print(f"  Searching for tor binary in {extract_dir}...")
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            file_lower = file.lower()
            # Look for tor executable or library
            if file_lower in ['tor', 'tor.exe', 'libtor.so', 'tor.real']:
                binary_path = Path(root) / file
                print(f"  Found binary: {binary_path}")
                return binary_path
            # Android may have libtor.so or tor.so
            if file_lower.endswith('.so') and 'tor' in file_lower:
                binary_path = Path(root) / file
                print(f"  Found binary: {binary_path}")
                return binary_path
    
    # If still not found, list all files to debug
    print(f"  [DEBUG] Listing all files in extraction:")
    all_files = []
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            rel_path = Path(root).relative_to(extract_dir) / file
            all_files.append(str(rel_path))
            if len(all_files) <= 20:  # Show first 20 files
                print(f"    - {rel_path}")
    
    if len(all_files) > 20:
        print(f"    ... and {len(all_files) - 20} more files")
    
    print(f"  [FAIL] Could not find tor binary")
    return None

def calculate_hashes(binary_path: Path) -> dict:
    """Calculate MD5 and SHA256 hashes of a file."""
    try:
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        
        with open(binary_path, 'rb') as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                md5_hash.update(byte_block)
                sha256_hash.update(byte_block)
        
        hashes = {
            'md5': md5_hash.hexdigest(),
            'sha256': sha256_hash.hexdigest()
        }
        
        print(f"  [OK] MD5: {hashes['md5']}")
        print(f"  [OK] SHA256: {hashes['sha256']}")
        return hashes
    except Exception as e:
        print(f"  [FAIL] Error calculating hashes: {e}")
        return {}

def process_binary(file_info: dict, temp_dir: Path) -> dict:
    """Download, extract, and calculate hashes for a binary."""
    file_name = file_info['file_name']
    url = file_info['url']
    
    print(f"\nProcessing: {file_name}")
    
    # Create temp directory for this file
    file_temp_dir = temp_dir / file_name.replace('.tar.gz', '')
    file_temp_dir.mkdir(exist_ok=True)
    
    # Download
    archive_path = file_temp_dir / file_name
    if not download_file(url, archive_path):
        return {}
    
    # Extract
    extract_dir = file_temp_dir / "extracted"
    extract_dir.mkdir(exist_ok=True)
    if not extract_archive(archive_path, extract_dir):
        return {}
    
    # Find binary
    tor_binary = find_tor_binary(extract_dir)
    if not tor_binary:
        return {}
    
    # Calculate hashes
    hashes = calculate_hashes(tor_binary)
    return hashes

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
    print(f"Will calculate hashes for all binaries")
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Process each file
        updated_count = 0
        for file_info in files:
            file_name = file_info['file_name']
            
            # Check if already has both MD5 and SHA256
            has_md5 = 'binary_md5' in file_info and file_info['binary_md5']
            has_sha256 = 'binary_sha256' in file_info and file_info['binary_sha256']
            
            if has_md5 and has_sha256:
                print(f"\n{file_name}: Already has hashes (MD5 & SHA256)")
                continue
            
            # Process the binary
            hashes = process_binary(file_info, temp_path)
            
            if hashes:
                if hashes.get('md5'):
                    file_info['binary_md5'] = hashes['md5']
                if hashes.get('sha256'):
                    file_info['binary_sha256'] = hashes['sha256']
                updated_count += 1
            else:
                print(f"  Failed to calculate hashes")
    
    # Save updated JSON
    if updated_count > 0:
        print(f"\n{'='*60}")
        print(f"Updated {updated_count} files with binary hashes")
        print(f"Saving to {JSON_FILE}")
        
        with open(JSON_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            f.write('\n')
        
        print("[OK] JSON file updated successfully")
    else:
        print("\nNo files were updated")

if __name__ == "__main__":
    main()
