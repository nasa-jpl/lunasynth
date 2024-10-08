#!/bin/bash

LICENSE_FILE="LICENSE_HEADER.txt"
LICENSE_TEXT=$(cat "$LICENSE_FILE")
LICENSE_IDENTIFIER=$(head -n 1 "$LICENSE_FILE")  # Assuming first line is unique

# Recursively find all .py files
find . -type f -name "*.py" | while read -r file; do
    # Check if the license header is already in the file
    if grep -F -q "$LICENSE_IDENTIFIER" "$file"; then
        echo "License already present in $file. Skipping."
        continue
    fi

    # Check if the first line is a shebang
    if head -n 1 "$file" | grep -q "^#!"; then
        # Insert license after the shebang
        {
            head -n 1 "$file"
            echo "$LICENSE_TEXT"
            tail -n +2 "$file"
        } > "${file}.tmp"
    else
        # Insert license at the top
        {
            echo "$LICENSE_TEXT"
            cat "$file"
        } > "${file}.tmp"
    fi
    # Replace the original file with the new file
    mv "${file}.tmp" "$file"
    echo "Added license to $file."
done
