#!/usr/bin/env python3
"""
Script to convert index.json to index.lmdb for fast Wikipedia article lookups.

This script reads the large index.json file and creates an LMDB database
for efficient article location queries.
"""

import json
import os
import sys

import lmdb
from tqdm import tqdm


def convert_json_to_lmdb(json_path: str, lmdb_path: str, map_size: int = 1024 * 1024 * 1024):
    """Convert index.json to an LMDB database.

    Args:
        json_path: Path to the index.json file
        lmdb_path: Path where the LMDB database should be created
        map_size: Maximum size of the LMDB database in bytes (default 1GB)
    """
    if not os.path.exists(json_path):
        print(f"Error: {json_path} does not exist")
        sys.exit(1)

    # Remove existing LMDB database if it exists
    if os.path.exists(lmdb_path):
        print(f"Removing existing database at {lmdb_path}")
        import shutil

        shutil.rmtree(lmdb_path)

    print(f"Converting {json_path} to {lmdb_path}...")
    print(f"LMDB map size: {map_size / (1024*1024*1024):.1f} GB")

    # Open LMDB environment
    env = lmdb.open(lmdb_path, map_size=map_size)

    try:
        # Get file size for progress tracking
        file_size = os.path.getsize(json_path)
        print(f"Index file size: {file_size / (1024*1024):.1f} MB")

        with open(json_path, "r", encoding="utf-8") as f:
            # Load the JSON data
            print("Loading JSON data...")
            data = json.load(f)

            if not isinstance(data, dict):
                print(
                    "Error: JSON file should contain a dictionary mapping article names to locations"
                )
                sys.exit(1)

            print(f"Found {len(data)} articles in index")

            # Write to LMDB in batches for better performance
            batch_size = 10000
            txn = env.begin(write=True)
            try:
                for i, (article, location) in enumerate(tqdm(data.items(), desc="Converting")):
                    # Encode both key and value as UTF-8 bytes
                    key = article.encode("utf-8")
                    value = location.encode("utf-8")

                    txn.put(key, value)

                    # Commit batch periodically
                    if (i + 1) % batch_size == 0:
                        txn.commit()
                        txn = env.begin(write=True)

                # Commit any remaining items
                txn.commit()
            except Exception as e:
                txn.abort()
                raise e

        print(f"Successfully created LMDB database at {lmdb_path}")

        # Verify the database
        print("Verifying database...")
        with env.begin() as txn:
            cursor = txn.cursor()
            count = sum(1 for _ in cursor)
            print(f"Database contains {count} entries")

        # Show some sample entries
        print("\nSample entries:")
        with env.begin() as txn:
            cursor = txn.cursor()
            for i, (key, value) in enumerate(cursor):
                if i >= 5:  # Show first 5 entries
                    break
                article = key.decode("utf-8")
                location = value.decode("utf-8")
                print(f"  {article} -> {location}")

    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

    finally:
        env.close()


def main():
    """Main function to run the conversion."""
    json_path = "index.json"
    lmdb_path = "index.lmdb"

    # Allow command line arguments
    if len(sys.argv) >= 2:
        json_path = sys.argv[1]
    if len(sys.argv) >= 3:
        lmdb_path = sys.argv[2]

    # Check for notebooks/index.json as fallback
    if not os.path.exists(json_path) and os.path.exists("notebooks/index.json"):
        json_path = "notebooks/index.json"
        print(f"Using {json_path}")

    convert_json_to_lmdb(json_path, lmdb_path)


if __name__ == "__main__":
    main()
