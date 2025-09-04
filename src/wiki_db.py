import json
from typing import Callable, Optional, Tuple

import lmdb

from src.models import Page
from src.utils import ArticleNotFound


class WikiData:
    """A class for querying Wikipedia article locations from an LMDB database."""

    def __init__(self, db_path: str, path_transformer: Optional[Callable[[str], str]] = None):
        """Initialize the WikiData instance with the path to the LMDB database.

        Args:
            db_path: Path to the LMDB database file
            path_transformer: A function that takes a path string and returns a transformed path string

        Raises:
            lmdb.Error: If the database cannot be opened
        """
        self.db_path = db_path
        self.path_transformer = path_transformer
        self.env = lmdb.open(db_path, readonly=True)

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

    def __del__(self):
        """Clean up the LMDB environment on object destruction."""
        if hasattr(self, "env"):
            self.env.close()
