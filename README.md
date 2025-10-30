# Tor Versions Tracker

Automated tracker for the latest Tor Expert Bundle versions and download links.

## Features

- Automatically scrapes Tor Archive for all available versions
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

### Local Automation (Optional)
- Use `auto_commit.bat` for local Windows automation
- Schedule via Windows Task Scheduler to run every 12 hours

## Direct JSON Access

Access the latest Tor version data directly via these raw GitHub links:

- **[All Versions List](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/versions.json)** - Simple array of all discovered Tor version numbers
- **[Complete Version Data](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/tor-versions.json)** - Full data with download links for each version
- **[Grouped by OS](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/versions_grouped.json)** - Downloads organized by operating system (Windows, macOS, Linux, Android)
- **[Blank Versions](https://raw.githubusercontent.com/QudsLab/tor-versions/refs/heads/main/data/json/blanks.json)** - List of versions with no valid download files

## Output Files

- `data/json/tor-versions.json` - Complete version data with download links
- `data/json/versions_grouped.json` - Downloads grouped by operating system
- `data/json/blanks.json` - Versions with no valid downloads
- `data/json/versions.json` - List of all discovered versions

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

Each version entry contains:
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