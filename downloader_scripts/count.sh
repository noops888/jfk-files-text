#!/bin/bash

# Check if a path is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <directory_path>"
  exit 1
fi

# Get the directory path
DIR="$1"

# Count files by extension (case-insensitive)
find "$DIR" -type f -exec sh -c '
  for file; do
    ext="${file##*.}"               # Extract the file extension
    ext=$(echo "$ext" | tr "[:upper:]" "[:lower:]") # Convert to lowercase
    echo "$ext"
  done
' _ {} + | sort | uniq -c | awk '{print $2 " (" $1 ")"}'

