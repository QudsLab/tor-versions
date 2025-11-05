import re
import os
import json
import requests
import time
from typing import List, Dict, Any
# Removed custom zfill import as Python strings have a built-in zfill method


BASE_DIR             = os.path.dirname(os.path.abspath(__file__))
DATA_DIR             = BASE_DIR + "/data"
JSON_DIR             = BASE_DIR + "/data/json"
CACHE_DIR            = BASE_DIR + "/data/cache"
CACHE_ALL_DIR        = BASE_DIR + "/data/cache/all"
CACHE_EXPORT_DIR     = BASE_DIR + "/data/cache/export"
CACHE_BROWSER_DIR    = BASE_DIR + "/data/cache/browser"
BLANKS               = BASE_DIR + "/data/json/blanks.json"
VERSIONS_LIST        = BASE_DIR + "/data/json/versions_list.json"
E_VERSIONS           = BASE_DIR + "/data/json/export_versions.json"
B_VERSIONS           = BASE_DIR + "/data/json/browser_versions.json"
E_VERSIONS_GROUPED   = BASE_DIR + "/data/json/export_versions_grouped.json"
B_VERSIONS_GROUPED   = BASE_DIR + "/data/json/browser_versions_grouped.json"
LB_VERSIONS          = BASE_DIR + "/data/json/latest_browser_versions.json"
LE_VERSIONS          = BASE_DIR + "/data/json/latest_export_versions.json"
BASE_URL             = "https://archive.torproject.org/tor-package-archive/torbrowser/"

COMMON_REMOVER_WORDS   = [                           # Common Remover Words
    "debug", "Debug", "DEBUG",                       # debug files
    "?C=N;O=D", "?C=M;O=A", "?C=S;O=A", "?C=D;O=A",  # by mistake added sorting query params
    "sha256", "SHA256", "Sha256",                    # hash files
    ".asc", ".ASC", ".Asc",                          # signature files
    ".txt", ".TXT", ".Txt",                          # text files
    "mar-tools", "geckodriver", "src-",              # other unrelated files --- type a
    "/~sysrqb/builds/","tmp.mar","index.html%3fC",   # other unrelated files --- type b
    "index.html","results","sandbox-",               # other unrelated files --- type c
    "/tor-package-archive/torbrowser/"               # self referencing links
]

EBV_REMOVER_WORDS = [                                # Export Builder Version Remover Words
    "browser", "Browser", "BROWSER",                 # files which are browser related
] + COMMON_REMOVER_WORDS                             # combine with common words

BRV_REMOVER_PREFIXES = [                             # Browser Version Remover Prefixes
    "tor-win32-", "tor-expert-bundle"               # export builder version files
]

PATTERNS           = [
    r"https://archive\.torproject\.org/tor-package-archive/torbrowser/(\d+\.\d+\.\d+)/",
    r'<a href="([\d\.]+[a-zA-Z0-9\-\_]*)/">',
    r'<a href="([^"]+)">'
]

def safe_request(url: str, max_retries: int = 3, delay: float = 1.0) -> str:
    """Make a safe HTTP request with retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay * (2 ** attempt))  # Exponential backoff
            else:
                raise
    return ""

def version_fatched(version: str) -> bool:
    """Check if version is already fetched and cached in all folder."""
    json_cache = CACHE_ALL_DIR + f"/{version}.json"
    return os.path.exists(json_cache)

def build_export_versions() -> List[Dict[str, Any]]:
    """Build export versions json from export cache files."""
    version_json: List[Dict[str, Any]] = []
    if not os.path.exists(CACHE_EXPORT_DIR):
        return version_json
        
    cache_files = [f for f in os.listdir(CACHE_EXPORT_DIR) if f.endswith(".json")]
    
    for version_file in cache_files:
        version_number = version_file.replace(".json", "")
        try:
            with open(os.path.join(CACHE_EXPORT_DIR, version_file), "r") as file:
                files = json.load(file)
                version_data: Dict[str, Any] = {"version": version_number, "files": []}
                for file_name in files:
                    file_url = BASE_URL + version_number + "/" + file_name
                    version_data["files"].append({"file_name": file_name, "url": file_url})
                version_json.append(version_data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading export cache file {version_file}: {e}")
            continue
    
    # Sort versions naturally
    version_json.sort(key=lambda x: list(map(int, re.findall(r'\d+', x["version"]))))
    return version_json

def build_browser_versions() -> List[Dict[str, Any]]:
    """Build browser versions json from browser cache files."""
    version_json: List[Dict[str, Any]] = []
    if not os.path.exists(CACHE_BROWSER_DIR):
        return version_json
        
    cache_files = [f for f in os.listdir(CACHE_BROWSER_DIR) if f.endswith(".json")]
    
    for version_file in cache_files:
        version_number = version_file.replace(".json", "")
        try:
            with open(os.path.join(CACHE_BROWSER_DIR, version_file), "r") as file:
                files = json.load(file)
                version_data: Dict[str, Any] = {"version": version_number, "files": []}
                for file_name in files:
                    file_url = BASE_URL + version_number + "/" + file_name
                    version_data["files"].append({"file_name": file_name, "url": file_url})
                version_json.append(version_data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading browser cache file {version_file}: {e}")
            continue
    
    # Sort versions naturally
    version_json.sort(key=lambda x: list(map(int, re.findall(r'\d+', x["version"]))))
    return version_json

def process_versions_efficiently(versions: List[str], blank_list: List[str]) -> tuple[List[str], List[str]]:
    """Process all versions efficiently with single fetch per version."""
    export_blank_list = []
    browser_blank_list = []
    total = len(versions)
    total_str_len = len(str(total))
    
    for count, version in enumerate(versions, 1):
        count_display = str(count).zfill(total_str_len)
        
        try:
            all_cache_file = CACHE_ALL_DIR + f"/{version}.json"
            export_cache_file = CACHE_EXPORT_DIR + f"/{version}.json"
            browser_cache_file = CACHE_BROWSER_DIR + f"/{version}.json"
            
            # Check if both export and browser files already exist
            if os.path.exists(export_cache_file) and os.path.exists(browser_cache_file):
                print(f"[{count_display}/{total}] {version} - Already processed (E+B)")
                continue
            
            # Check if we need to fetch from network or use existing cache
            cached_files = []
            if os.path.exists(all_cache_file):
                print(f"[{count_display}/{total}] {version} - Using cached data", end="")
                with open(all_cache_file, "r") as file:
                    cached_files = json.load(file)
            else:
                if version in blank_list:
                    print(f"[{count_display}/{total}] {version} - In blank list, skipping")
                    export_blank_list.append(version)
                    browser_blank_list.append(version)
                    continue
                    
                # Fetch from network
                print(f"[{count_display}/{total}] {version} - Fetching", end="")
                url = BASE_URL + version + "/"
                text = safe_request(url)
                files = re.findall(PATTERNS[-1], text)
                
                # Apply only common filtering for cache
                for filename in files:
                    if any(rem_word in filename for rem_word in COMMON_REMOVER_WORDS):
                        continue
                    cached_files.append(filename)
                    
                if len(cached_files) == 0:
                    print(f" - No valid files")
                    export_blank_list.append(version)
                    browser_blank_list.append(version)
                    continue
                    
                # Save to all cache
                with open(all_cache_file, "w") as file:
                    json.dump(cached_files, file, indent=4)
            
            # Process export files if not exists
            export_files = []
            if not os.path.exists(export_cache_file):
                for filename in cached_files:
                    # Remove files that contain export builder remover words
                    if any(rem_word in filename for rem_word in EBV_REMOVER_WORDS):
                        continue
                    export_files.append(filename)
                    
                if len(export_files) > 0:
                    with open(export_cache_file, "w") as file:
                        json.dump(export_files, file, indent=4)
                else:
                    export_blank_list.append(version)
            
            # Process browser files if not exists
            browser_files = []
            if not os.path.exists(browser_cache_file):
                for filename in cached_files:
                    # Remove files that start with browser remover prefixes
                    if any(filename.startswith(prefix) for prefix in BRV_REMOVER_PREFIXES):
                        continue
                    browser_files.append(filename)
                    
                if len(browser_files) > 0:
                    with open(browser_cache_file, "w") as file:
                        json.dump(browser_files, file, indent=4)
                else:
                    browser_blank_list.append(version)

            # Show results
            export_count = len(export_files) if export_files else (len(json.load(open(export_cache_file))) if os.path.exists(export_cache_file) else 0)
            browser_count = len(browser_files) if browser_files else (len(json.load(open(browser_cache_file))) if os.path.exists(browser_cache_file) else 0)
            print(f" - E:{export_count} B:{browser_count}")
                
        except Exception as e:
            print(f"[{count_display}/{total}] {version} - Error: {e}")
            export_blank_list.append(version)
            browser_blank_list.append(version)
            continue
    
    return export_blank_list, browser_blank_list

def version_grouped(data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """Group files by operating system."""
    grouped: Dict[str, List[Dict[str, str]]] = {
        'windows': [],
        'macos': [],
        'linux': [],
        'android': [],
        'other': []
    }
    for entry in data:
        version = entry["version"]
        files = entry["files"]
        for file in files:
            file_name = file["file_name"].lower()
            # Check OS compatibility
            if any(x in file_name for x in ["win", "windows"]):
                grouped['windows'].append(file)
            elif any(x in file_name for x in ["mac", "osx", "darwin"]):
                grouped['macos'].append(file)
            elif "linux" in file_name:
                grouped['linux'].append(file)
            elif "android" in file_name:
                grouped['android'].append(file)
            else:
                grouped['other'].append(file)
    return grouped

def get_latest_version(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get the latest version with its files (only purely numerical versions)."""
    if not data:
        return {"version": None, "files": []}
    
    # Filter to only include versions that are purely numerical (e.g., "14.0.3", not "14.0.3-alpha")
    numerical_only = [entry for entry in data if re.match(r'^\d+(\.\d+)*$', entry["version"])]
    
    if not numerical_only:
        return {"version": None, "files": []}
    
    # Sort by version number and get the last (latest) one
    sorted_data = sorted(numerical_only, key=lambda x: list(map(int, re.findall(r'\d+', x["version"]))))
    return sorted_data[-1] if sorted_data else {"version": None, "files": []}


# development time code - create directories and initialize files
try:
    # Create folders including new cache structure
    directories = [DATA_DIR, JSON_DIR, CACHE_DIR, CACHE_ALL_DIR, CACHE_EXPORT_DIR, CACHE_BROWSER_DIR]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
    
    # Initialize JSON files with empty data
    initial_files: Dict[str, Any] = {
        BLANKS: [],
        VERSIONS_LIST: [],
        E_VERSIONS: [],
        B_VERSIONS: [],
        E_VERSIONS_GROUPED: {},
        B_VERSIONS_GROUPED: {},
        LE_VERSIONS: {},
        LB_VERSIONS: {}
    }
    
    for file_path, initial_data in initial_files.items():
        if not os.path.exists(file_path):
            with open(file_path, "w") as file:
                json.dump(initial_data, file, indent=4)
                print(f"Created file: {file_path}")
                
except Exception as e:
    print(f"Error during initialization: {e}")
    exit(1)
# end development time code

# Load existing blank list
try:
    with open(BLANKS, "r") as file:
        blank_list = json.load(file)
except (json.JSONDecodeError, FileNotFoundError):
    blank_list = []

# Fetch version list from Tor archive
print("Fetching version list from Tor archive...")
versions = []
try:
    for pattern in PATTERNS[:-1]:  # except last pattern
        text = safe_request(BASE_URL)
        versions += re.findall(pattern, text)
    
    unique_versions = list(set(versions))
    unique_versions.sort(key=lambda s: list(map(int, re.findall(r'\d+', s))))
    
    with open(VERSIONS_LIST, "w") as file:
        json.dump(unique_versions, file, indent=4)
        file.write("\n")
    
    print(f"Found {len(unique_versions)} unique versions")
    
except Exception as e:
    print(f"Failed to fetch version list: {e}")
    exit(1)

# Process versions
with open(VERSIONS_LIST, "r") as file:
    versions = json.load(file)

print(f"\nProcessing {len(versions)} versions efficiently...")
print("=" * 50)

# Process all versions with single fetch per version
export_blank_list, browser_blank_list = process_versions_efficiently(versions, blank_list)

# Build final data structures
print("\n[BUILD] Building final data structures...")
try:
    # Build export versions data
    export_data = build_export_versions()
    
    # Build browser versions data  
    browser_data = build_browser_versions()
    
    # Save export versions data
    with open(E_VERSIONS, "w") as file:
        json.dump(export_data, file, indent=4)
        file.write("\n")
    
    with open(E_VERSIONS_GROUPED, "w") as file:
        json.dump(version_grouped(export_data), file, indent=4)
        file.write("\n")
    
    # Save browser versions data
    with open(B_VERSIONS, "w") as file:
        json.dump(browser_data, file, indent=4)
        file.write("\n")
    
    with open(B_VERSIONS_GROUPED, "w") as file:
        json.dump(version_grouped(browser_data), file, indent=4)
        file.write("\n")
    
    # Generate latest versions
    latest_export = get_latest_version(export_data)
    latest_browser = get_latest_version(browser_data)
    
    # Save latest versions data
    with open(LE_VERSIONS, "w") as file:
        json.dump(latest_export, file, indent=4)
        file.write("\n")
    
    with open(LB_VERSIONS, "w") as file:
        json.dump(latest_browser, file, indent=4)
        file.write("\n")
    
    # Update blank list with new blanks
    combined_blanks = list(set(blank_list + export_blank_list + browser_blank_list))
    with open(BLANKS, "w") as file:
        json.dump(combined_blanks, file, indent=4)

    print(f"\n[SUMMARY] Processing complete!")
    print(f"[INFO] Total versions processed: {len(versions)}")
    print(f"[INFO] Export versions with data: {len(export_data)}")
    print(f"[INFO] Browser versions with data: {len(browser_data)}")
    print(f"[INFO] Total blank versions: {len(combined_blanks)}")
    print(f"[INFO] Export data saved to: {E_VERSIONS}")
    print(f"[INFO] Export grouped data saved to: {E_VERSIONS_GROUPED}")
    print(f"[INFO] Browser data saved to: {B_VERSIONS}")
    print(f"[INFO] Browser grouped data saved to: {B_VERSIONS_GROUPED}")
    print(f"[INFO] Latest export version: {latest_export['version']} ({len(latest_export['files'])} files) - {LE_VERSIONS}")
    print(f"[INFO] Latest browser version: {latest_browser['version']} ({len(latest_browser['files'])} files) - {LB_VERSIONS}")
    
except Exception as e:
    print(f"Error building final data: {e}")
    exit(1)