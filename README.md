# Tor Versions Tracker

Automated tracker for the latest Tor Expert Bundle and Tor Browser versions with download links.

## Features

- Automatically scrapes Tor Archive for all available versions
- **Separates Export Builder and Browser versions** for clean data organization
- Groups downloads by operating system (Windows, macOS, Linux, Android)
- Filters out debug files, signatures, and other unwanted files
- Runs automatically every 12 hours via GitHub Actions
- Provides structured JSON output for easy integration

## Automation

This repository is fully automated:

### GitHub Actions
- Runs every 12 hours via scheduled workflow
- Updates version data automatically
- Commits and pushes changes to the repository

## Direct JSON Access

Access the latest Tor version data directly via these raw GitHub links:

### Export Builder Versions
- **[Export Versions List](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/versions_list.json)** - Simple array of all discovered Tor version numbers
- **[Export Version Data](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/export_versions.json)** - Export builder files with download links
- **[Export Grouped by OS](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/export_versions_grouped.json)** - Export files organized by operating system

### Browser Versions
- **[Browser Version Data](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/browser_versions.json)** - Browser files with download links
- **[Browser Grouped by OS](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/browser_versions_grouped.json)** - Browser files organized by operating system

### Utility Files
- **[Blank Versions](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/blanks.json)** - List of versions with no valid download files

## Output Files

### Export Builder Files
- `data/json/export_versions.json` - Export builder version data with download links
- `data/json/export_versions_grouped.json` - Export files grouped by operating system

### Browser Files  
- `data/json/browser_versions.json` - Browser version data with download links
- `data/json/browser_versions_grouped.json` - Browser files grouped by operating system

### Utility Files
- `data/json/versions_list.json` - List of all discovered versions
- `data/json/blanks.json` - Versions with no valid downloads

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the scraper:
   ```bash
   python main.py
   ```

## Automated Deployment

The repository is configured to automatically update every 12 hours. No manual intervention required.

## Data Structure

### Export Builder Version Entry:
```json
{
  "version": "13.0.1",
  "files": [
    {
      "file_name": "tor-expert-bundle-13.0.1-windows-x86_64.tar.gz",
      "url": "https://archive.torproject.org/tor-package-archive/torbrowser/13.0.1/tor-expert-bundle-13.0.1-windows-x86_64.tar.gz"
    }
  ]
}
```

### Browser Version Entry:
```json
{
  "version": "13.0.1", 
  "files": [
    {
      "file_name": "torbrowser-install-13.0.1_ALL.exe",
      "url": "https://archive.torproject.org/tor-package-archive/torbrowser/13.0.1/torbrowser-install-13.0.1_ALL.exe"
    }
  ]
}
```

## Cache Structure

The project uses an efficient 3-tier cache system:

- `data/cache/all/` - Raw files with minimal filtering (common unwanted files removed)
- `data/cache/export/` - Export builder specific files  
- `data/cache/browser/` - Browser specific files