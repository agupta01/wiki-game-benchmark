import json
import os
import tempfile
from typing import Callable, Optional, Tuple
from urllib.parse import urlparse

import lmdb

from src.models import Page
from src.utils import ArticleNotFound

import shutil

try:
    import boto3
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


class WikiData:
    """A class for querying Wikipedia article locations from an LMDB database."""

    def __init__(self, db_path: str, path_transformer: Optional[Callable[[str], str]] = None):
        """Initialize the WikiData instance with the path to the LMDB database.

        Args:
            db_path: Path to the LMDB database file. Supports R2 remote mounts, if db_path starts with r2://
            path_transformer: A function that takes a path string and returns a transformed path string

        Raises:
            lmdb.Error: If the database cannot be opened
        """
        self.db_path = db_path
        self.path_transformer = path_transformer
        self.is_cloud = db_path.startswith('r2://')
        self.s3_client = None
        self._temp_db_path = None

        if self.is_cloud:
            if not HAS_BOTO3:
                raise ImportError("boto3 is required for r2:// URLs. Please install it with: pip install boto3")
            self._setup_s3_client()
            self._download_index_file()
        else:
            self.env = lmdb.open(db_path, readonly=True)

    def _setup_s3_client(self):
        """Setup S3-compatible client for R2 access."""
        # R2 is S3-compatible, so we use boto3 with custom endpoint
        # You may need to configure these via environment variables:
        # R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
        account_id = os.getenv('R2_ACCOUNT_ID')
        access_key = os.getenv('R2_ACCESS_KEY_ID') or os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('R2_SECRET_ACCESS_KEY') or os.getenv('AWS_SECRET_ACCESS_KEY')

        if not all([account_id, access_key, secret_key]):
            raise ValueError("R2 credentials not found. Please set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY environment variables")

        endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

        self.s3_client = boto3.client(
            's3',
            region_name="auto",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4')
        )

    def _download_index_file(self):
        """Download the LMDB index directory from R2 to a temporary location."""
        parsed = urlparse(self.db_path)
        bucket = parsed.netloc
        base_key = parsed.path.lstrip('/')

        # Remove the .lmdb extension if present to get the directory path
        # if base_key.endswith('.lmdb'):
        #     base_key = base_key[:-5]  # Remove '.lmdb'

        # Create a temporary directory for the LMDB files
        self._temp_db_path = tempfile.mkdtemp(suffix='_lmdb')

        try:
            # Download both data.mdb and lock.mdb files
            data_key = f"{base_key}/data.mdb"
            lock_key = f"{base_key}/lock.mdb"

            data_path = os.path.join(self._temp_db_path, 'data.mdb')
            lock_path = os.path.join(self._temp_db_path, 'lock.mdb')

            # Download data.mdb (required)
            print(f"Downloading {data_key}, {data_path}")
            self.s3_client.download_file(bucket, data_key, data_path)

            # Download lock.mdb (optional, may not exist in read-only scenarios)
            try:
                print(f"Downloading {lock_key}, {lock_path}")
                self.s3_client.download_file(bucket, lock_key, lock_path)
            except Exception:
                # Create an empty lock file if it doesn't exist
                with open(lock_path, 'wb') as f:
                    pass

            self.env = lmdb.open(self._temp_db_path, readonly=True)
        except Exception as e:
            if os.path.exists(self._temp_db_path):
                import shutil
                shutil.rmtree(self._temp_db_path, ignore_errors=True)
            raise RuntimeError(f"Failed to download LMDB directory from {self.db_path}: {e}")

    def _parse_r2_path(self, location: str) -> Tuple[str, str]:
        """Parse a location path to extract R2 bucket and key.

        Args:
            location: Location path like "2025-06-01/AA/wiki_01"

        Returns:
            Tuple of (bucket, key) for R2 access
        """
        # Extract the base path from the original db_path to construct the data path
        parsed_db = urlparse(self.db_path)
        bucket = parsed_db.netloc

        # The location is relative to the index, so we need to construct the full path
        # e.g., if db_path is r2://wiki-data/2025-06-01/index.lmdb
        # and location is "2025-06-01/AA/wiki_01"
        # then the key should be "2025-06-01/AA/wiki_01"
        key = location

        return bucket, key

    def get_article_location(self, article: str) -> Tuple[str, str]:
        """Get the location of an article in the dataset.

        Args:
            article: The name of the Wikipedia article to look up

        Returns:
            The location path of the article (e.g., "2025-06-01/AA/wiki_01") and the variation that worked
            or ArticleNotFound if the article is not found
        """
        try:
            with self.env.begin() as txn:
                # Try exact match first
                location_bytes = txn.get(article.encode("utf-8"))
                if location_bytes is not None:
                    return location_bytes.decode("utf-8"), article

                # Try fallback variations if exact match fails
                fallback_variations = self._get_case_fallbacks(article)

                for variation in fallback_variations:
                    location_bytes = txn.get(variation.encode("utf-8"))
                    if location_bytes is not None:
                        return location_bytes.decode("utf-8"), variation

                # No match found in any variation
                raise Exception
        except Exception:
            raise ArticleNotFound(f"Article '{article}' not found in DB.")

    def _get_case_fallbacks(self, article: str) -> list[str]:
        """Generate case fallback variations for an article name.

        Args:
            article: The original article name

        Returns:
            List of case variations to try, in priority order
        """
        if not article:
            return []

        fallbacks = []

        # Capitalized first letter (most common Wikipedia format)
        capitalized = (
            article[0].upper() + article[1:].lower() if len(article) > 1 else article.upper()
        )
        if capitalized != article:
            fallbacks.append(capitalized)

        # Title case
        title_cased = article.title()
        if title_cased != article and title_cased != capitalized:
            fallbacks.append(title_cased)

        # Lowercase version
        lowercase = article.lower()
        if lowercase != article and lowercase != title_cased:
            fallbacks.append(lowercase)

        # Uppercase version
        uppercase = article.upper()
        if uppercase != article and uppercase != capitalized and uppercase != lowercase:
            fallbacks.append(uppercase)

        return fallbacks

    def get_page(self, article_title: str) -> Page:
        """Fetches a page object from LMDB. Throws an ArticleNotFoundError if the article isn't in DB."""
        location, article_title = self.get_article_location(article_title)
        # Transform path if needed
        if self.path_transformer:
            location = self.path_transformer(location)

        # Read the JSONL at that location and construct a page object
        if self.is_cloud:
            page_data = self._read_cloud_file(location)
        else:
            with open(location, "r", encoding="utf-8") as file:
                page_data = [json.loads(line) for line in file]

        try:
            article_data = next(filter(lambda x: x["title"] == article_title, page_data))
            return Page(
                url=article_data["url"],
                title=article_data["title"],
                content=article_data["text"],
                links=article_data["links"],
            )
        except StopIteration:
            raise ArticleNotFound(f"Article '{article_title}' not found in DB.")
        except Exception:
            raise RuntimeError("An unknown error occurred.")

    def _read_cloud_file(self, location: str) -> list:
        """Read a JSONL file from R2 cloud storage.

        Args:
            location: The file location path

        Returns:
            List of parsed JSON objects from the file
        """
        bucket, key = self._parse_r2_path(location)

        try:
            # Download file content as string
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')

            # Parse JSONL content
            page_data = []
            for line in content.strip().split('\n'):
                if line.strip():
                    page_data.append(json.loads(line))

            return page_data
        except Exception as e:
            raise RuntimeError(f"Failed to read file from R2: {bucket}/{key} - {e}")

    def __del__(self):
        """Clean up the LMDB environment on object destruction."""
        if hasattr(self, "env"):
            self.env.close()
        # Clean up temporary index directory if it exists
        if hasattr(self, "_temp_db_path") and self._temp_db_path and os.path.exists(self._temp_db_path):
            try:
                if os.path.isdir(self._temp_db_path):
                    shutil.rmtree(self._temp_db_path, ignore_errors=True)
                else:
                    os.unlink(self._temp_db_path)
            except OSError:
                pass  # Ignore cleanup errors

if __name__=='__main__':
    db = WikiData("r2://wiki-data/2025-06-01/index.lmdb", lambda x: x.replace("../", ""))
    page = db.get_page("Anarchy")
    print(page.content)
