#!/bin/bash

# This script extracts the daemon version from a binary passed as an argument.
# Usage: ./deamons.sh <binary_path>

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <binary_path>"
    exit 1
fi

BINARY_PATH=$1

if [ ! -x "$BINARY_PATH" ]; then
    echo "Error: $BINARY_PATH is not executable or does not exist."
    exit 1
fi

# Run the binary with --version and extract the daemon version using regex
VERSION_OUTPUT=$($BINARY_PATH --version 2>&1)
DAEMON_VERSION=$(echo "$VERSION_OUTPUT" | grep -oP '\d+\.\d+\.\d+')

if [ -z "$DAEMON_VERSION" ]; then
    echo "Error: Could not extract daemon version."
    exit 1
fi

# Output the daemon version
echo "$DAEMON_VERSION"