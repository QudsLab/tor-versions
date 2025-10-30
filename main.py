import re
import os
import json
import requests
import time
from typing import List, Dict, Any
# Removed custom zfill import as Python strings have a built-in zfill method


BASE_DIR           = os.path.dirname(os.path.abspath(__file__))
JSON_DIR           = BASE_DIR + "/data/json"

BLANKS             = BASE_DIR + "/data/json/blanks.json"
VERSIONS           = BASE_DIR + "/data/json/versions.json"
VERSIONS_LIST      = BASE_DIR + "/data/json/versions_list.json"
VERSIONS_GROUPED   = BASE_DIR + "/data/json/versions_grouped.json"
CACHE_DIR          = BASE_DIR + "/data/cache"

DATA_DIR           = BASE_DIR + "/data"
BASE_FILE          = "torbrowser-versions.txt"
BASE_URL           = "https://archive.torproject.org/tor-package-archive/torbrowser/"

REMOVER_WORDS      = [
        "debug", "Debug", "DEBUG",                       # debug files
        "browser", "Browser", "BROWSER",                 # files which are browser related
        "?C=N;O=D", "?C=M;O=A", "?C=S;O=A", "?C=D;O=A",  # by mistake added sorting query params
        "sha256", "SHA256", "Sha256",                    # hash files
        ".asc", ".ASC", ".Asc",                          # signature files
        ".txt", ".TXT", ".Txt",                          # text files
        "mar-tools", "geckodriver", "src-",              # other unrelated files --- type a
        "/~sysrqb/builds/","tmp.mar","index.html%3fC",   # other unrelated files --- type b
        "index.html","results","sandbox-",               # other unrelated files --- type c
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
    """Check if version is already fetched and cached."""
    json_cache = CACHE_DIR + f"/{version}_files.json"
    return os.path.exists(json_cache)
    """Check if version is already fetched and cached."""
    json_cache = CACHE_DIR + f"/{version}_files.json"
    return os.path.exists(json_cache)

def version_builder() -> List[Dict[str, Any]]:
    """Build main json with file list and urls list under each version."""
    version_json = []
    cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith("_files.json")]
    
    for version_file in cache_files:
        version_number = version_file.replace("_files.json", "")
        try:
            with open(os.path.join(CACHE_DIR, version_file), "r") as file:
                files = json.load(file)
                version_data: Dict[str, Any] = {"version": version_number, "files": []}
                for file_name in files:
                    file_url = BASE_URL + version_number + "/" + file_name
                    version_data["files"].append({"file_name": file_name, "url": file_url})
                version_json.append(version_data)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading cache file {version_file}: {e}")
            continue
    
    # Sort versions naturally
    version_json.sort(key=lambda x: list(map(int, re.findall(r'\d+', x["version"]))))
    return version_json

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

# devlopment time code
# folders
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(JSON_DIR):
    os.makedirs(JSON_DIR, exist_ok=True)
# filrs
if not os.path.exists(BLANKS):
    with open(BLANKS, "w") as file:
        json.dump([], file, indent=4)
        file.close()
if not os.path.exists(VERSIONS):
    with open(VERSIONS, "w") as file:
        json.dump([], file, indent=4)
        file.close()
if not os.path.exists(VERSIONS_LIST):
    with open(VERSIONS_LIST, "w") as file:
        json.dump([], file, indent=4)
        file.close()
if not os.path.exists(VERSIONS_GROUPED):
    with open(VERSIONS_GROUPED, "w") as file:
        json.dump({}, file, indent=4)
        file.close()
# end devlopment time code

# load those 
with open(BLANKS, "r") as file:
    blank_list = json.load(file)


versions = []
for pattern in PATTERNS[:-1]:  # except last pattern
    try:
        text = safe_request(BASE_URL)
        versions += re.findall(pattern, text)
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch version list: {e}")
        continue

with open(VERSIONS_LIST, "w") as file:
    unique_versions = list(set(versions))
    unique_versions.sort(key=lambda s: list(map(int, re.findall(r'\d+', s))))
    json.dump(unique_versions, file, indent=4)
    file.write("\n")

count = 0
with open(VERSIONS_LIST, "r") as file:
    versions = json.load(file)
    total = len(versions)
    for version in versions:
        count += 1
        count_str = str(count).zfill(len(str(total)))
        if version_fatched(version):
            print(f"[{count_str}/{total}] Version {version} already fetched, skipping...")
            continue
        if version in blank_list:
            print(f"[{count_str}/{total}] Version {version} is in blank list, skipping...")
            continue
        url = BASE_URL + version + "/"
        try:
            text = safe_request(url)
            files = re.findall(PATTERNS[-1], text)
        except requests.exceptions.RequestException as e:
            print(f"[{count_str}/{total}] Failed to fetch files for version {version}: {e}")
            continue
        sanitized_files = []
        for file in files:
            if any(rem_word in file for rem_word in REMOVER_WORDS):
                continue
            sanitized_files.append(file)
        if len(sanitized_files) == 0:
            print(f"[{count_str}/{total}] No valid files found for version {version}, skipping...")
            if version not in blank_list:
                blank_list.append(version)
            continue
        else:
            print(f"[{count_str}/{total}] Fetched {len(sanitized_files)} files for version {version}")
        json_cache = CACHE_DIR + f"/{version}_files.json"
        with open(f"{json_cache}", "w") as file:
            json.dump(sanitized_files, file, indent=4)

# open version jsons after all fetching is done
data = version_builder()

# Save main tor versions data
with open(VERSIONS, "w") as file:
    json.dump(data, file, indent=4)
    file.write("\n")

# Save grouped versions data
with open(VERSIONS_GROUPED, "w") as file:
    json.dump(version_grouped(data), file, indent=4)
    file.write("\n")

# write blank versions back
with open(BLANKS, "w") as file:
    json.dump(blank_list, file, indent=4)

print(f"\n[m] Completed! Processed {len(data)} versions with data.")
print(f"[c] Total blank versions: {len(blank_list)}")
print(f"[i] Main data saved to: {VERSIONS}")
print(f"[i] Grouped data saved to: {VERSIONS_GROUPED}")