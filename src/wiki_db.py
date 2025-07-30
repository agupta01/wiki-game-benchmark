from typing import Optional

import lmdb


class WikiData:
    """A class for querying Wikipedia article locations from an LMDB database."""

    def __init__(self, db_path: str):
        """Initialize the WikiData instance with the path to the LMDB database.

        Args:
            db_path: Path to the LMDB database file

        Raises:
            lmdb.Error: If the database cannot be opened
        """
        self.db_path = db_path
        self.env = lmdb.open(db_path, readonly=True)

    def get_article_location(self, article: str) -> Optional[str]:
        """Get the location of an article in the dataset.

        Args:
            article: The name of the Wikipedia article to look up

        Returns:
            The location path of the article (e.g., "2025-06-01/AA/wiki_01")
            or None if the article is not found
        """
        if not article:
            return None

        try:
            with self.env.begin() as txn:
                location_bytes = txn.get(article.encode("utf-8"))
                if location_bytes is None:
                    return None
                return location_bytes.decode("utf-8")
        except Exception:
            return None

    def __del__(self):
        """Clean up the LMDB environment on object destruction."""
        if hasattr(self, "env"):
            self.env.close()
