#!/bin/bash

# This script extracts the daemon version from a binary passed as an argument.
# Usage: ./deamons.sh <binary_path>

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <binary_path>" >&2
    exit 1
fi

BINARY_PATH=$1

if [ ! -f "$BINARY_PATH" ]; then
    echo "Error: $BINARY_PATH does not exist." >&2
    exit 1
fi

# Make executable if not already
if [ ! -x "$BINARY_PATH" ]; then
    chmod +x "$BINARY_PATH" 2>/dev/null || true
fi

# Run the binary with --version and extract the daemon version using regex
# Try different methods to get version
VERSION_OUTPUT=$($BINARY_PATH --version 2>&1 || echo "")

# Extract version pattern like 0.4.8.13 or similar
DAEMON_VERSION=$(echo "$VERSION_OUTPUT" | grep -oP 'Tor version \K\d+\.\d+\.\d+\.\d+' | head -n 1)

# If 4-part version not found, try 3-part version
if [ -z "$DAEMON_VERSION" ]; then
    DAEMON_VERSION=$(echo "$VERSION_OUTPUT" | grep -oP '\d+\.\d+\.\d+\.\d+' | head -n 1)
fi

# If still not found, try 3-part version
if [ -z "$DAEMON_VERSION" ]; then
    DAEMON_VERSION=$(echo "$VERSION_OUTPUT" | grep -oP '\d+\.\d+\.\d+' | head -n 1)
fi

if [ -z "$DAEMON_VERSION" ]; then
    echo "Error: Could not extract daemon version from output: $VERSION_OUTPUT" >&2
    exit 1
fi

# Output the daemon version
echo "$DAEMON_VERSION"