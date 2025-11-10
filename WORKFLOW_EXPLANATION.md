# Workflow Explanation

## Daily Tor Expert Bundle Version Update

This workflow consists of 3 jobs that run sequentially:

### Job 1: `update-tor-versions`
- Runs the main scraper (`main.py`) to fetch and update Tor version data
- Commits and pushes changes to the repository

### Job 2: `build-matrix`
- Reads `data/json/latest_export_versions.json`
- Creates a matrix of all export bundle files (one entry per file)
- Passes the matrix to the next job

### Job 3: `daemon-version`
- Runs in parallel for each file in the matrix (but with `max-parallel: 1` to avoid conflicts)
- For each export bundle:
  1. Downloads the `.tar.gz` file
  2. Extracts it to find the `tor` binary
  3. Runs the binary with `--version` using `deamons.sh`
  4. Extracts the daemon version (e.g., `0.4.8.13`)
  5. Updates the JSON file with the `daemon_version` field
  6. Commits and pushes the change

### Final Result

The `latest_export_versions.json` file will contain entries like:

```json
{
  "version": "15.0",
  "files": [
    {
      "file_name": "tor-expert-bundle-linux-x86_64-15.0.tar.gz",
      "url": "https://archive.torproject.org/tor-package-archive/torbrowser/15.0/tor-expert-bundle-linux-x86_64-15.0.tar.gz",
      "daemon_version": "0.4.8.13"
    }
  ]
}
```

### Key Features

- **Sequential Processing**: Uses `max-parallel: 1` to process files one at a time, preventing git conflicts
- **Error Handling**: Uses `continue-on-error: true` to skip binaries that can't be processed
- **Cross-Platform**: Handles different OS binaries (Linux, Windows, macOS, Android)
- **Automatic Commits**: Each daemon version is committed separately with a descriptive message
