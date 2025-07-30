#!/bin/bash
# Recursively upload all files in 2025-06-01 to the wiki-data R2 bucket,
# preserving directory structure (e.g., local 2025-06-01/AA/wiki_00 -> wiki-data/2025-06-01/AA/wiki_00)

SRC_DIR="2025-06-01"
BUCKET="wiki-data"

find "$SRC_DIR" -type f | while read -r file; do
  # Remove leading ./ if present
  rel_path="${file#./}"
  # Upload to R2, preserving path under the bucket
  npx wrangler r2 object put "${BUCKET}/${rel_path}" --file "$file" --remote
done
