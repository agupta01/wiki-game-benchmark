import json
import os
import tempfile
from unittest.mock import Mock

import lmdb
import pytest

from src.eval import get_next_article
from src.utils import ArticleNotFound
from src.models import Page
from src.wiki_db import WikiData


class TestGetNextArticle:
    def setup_method(self):
        """Set up test data before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.lmdb")
        self.data_dir = os.path.join(self.temp_dir.name, "data")
        os.makedirs(self.data_dir)

        # Create sample wiki data files
        self.wiki_file_1 = os.path.join(self.data_dir, "wiki_01")
        self.wiki_file_2 = os.path.join(self.data_dir, "wiki_02")

        # Sample page data (JSONL format)
        page_1_data = {
            "title": "Python (programming language)",
            "text": 'Python is a high-level programming language. <a href="Machine Learning">Machine Learning</a> is popular with Python.',
            "url": "/wiki/Python_(programming_language)",
            "links": ["Machine Learning"]
        }
        page_2_data = {
            "title": "Machine Learning",
            "text": 'Machine Learning is a subset of artificial intelligence. <a href="Python (programming language)">Python</a> is commonly used.',
            "url": "/wiki/Machine_Learning",
            "links": ["Python (programming language)"]
        }

        with open(self.wiki_file_1, "w") as f:
            f.write(json.dumps(page_1_data) + "\n")

        with open(self.wiki_file_2, "w") as f:
            f.write(json.dumps(page_2_data) + "\n")

        # Create LMDB index
        env = lmdb.open(self.db_path, map_size=1024 * 1024)
        with env.begin(write=True) as txn:
            txn.put(b"Python (programming language)", self.wiki_file_1.encode())
            txn.put(b"Machine Learning", self.wiki_file_2.encode())
        env.close()

        self.wiki_data = WikiData(self.db_path)

    def teardown_method(self):
        """Clean up after each test method."""
        self.temp_dir.cleanup()

    def test_get_next_article_success(self):
        """Test successful retrieval of next article."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Machine Learning", "Data Science"],
        )

        # Mock invoke function that returns a link
        mock_invoke = Mock(return_value="Machine Learning")

        # Get next article
        next_page = get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

        # Verify the result
        assert next_page.title == "Machine Learning"
        assert "Machine Learning is a subset of artificial intelligence" in next_page.content
        assert (
            "Python (programming language)" in next_page.links
        )  # construct_page extracts links from content

        # Verify invoke was called with current page and goal
        mock_invoke.assert_called_once_with(current_page, "goal")

    def test_get_next_article_not_found_in_index(self):
        """Test when the article returned by invoke is not found in LMDB index."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Machine Learning"],
        )

        # Mock invoke function that returns a non-existent link
        mock_invoke = Mock(return_value="Nonexistent Article")

        # Should raise ArticleNotFound
        with pytest.raises(
            ArticleNotFound, match="Article 'Nonexistent Article' not found in DB."
        ):
            get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

    def test_get_next_article_file_not_found(self):
        """Test when the file path exists in index but file doesn't exist."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Machine Learning"],
        )

        # Add a mapping to non-existent file
        env = lmdb.open(self.db_path, readonly=False)
        with env.begin(write=True) as txn:
            txn.put(b"Nonexistent File Article", b"/nonexistent/path/wiki_99")
        env.close()

        mock_invoke = Mock(return_value="Nonexistent File Article")

        # Should raise FileNotFoundError when file doesn't exist
        with pytest.raises(FileNotFoundError):
            get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

    def test_get_next_article_empty_file(self):
        """Test when the wiki file exists but is empty."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Machine Learning"],
        )

        # Create empty file
        empty_file = os.path.join(self.data_dir, "empty_wiki")
        with open(empty_file, "w"):
            pass  # Create empty file

        # Add mapping to empty file
        env = lmdb.open(self.db_path, readonly=False)
        with env.begin(write=True) as txn:
            txn.put(b"Empty Article", empty_file.encode())
        env.close()

        mock_invoke = Mock(return_value="Empty Article")

        # Should raise ArticleNotFound because no articles in empty file
        with pytest.raises(ArticleNotFound, match="Article 'Empty Article' not found in DB."):
            get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

    def test_get_next_article_malformed_json(self):
        """Test when the wiki file contains malformed JSON."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Machine Learning"],
        )

        # Create file with malformed JSON
        malformed_file = os.path.join(self.data_dir, "malformed_wiki")
        with open(malformed_file, "w") as f:
            f.write("invalid json content")

        # Add mapping to malformed file
        env = lmdb.open(self.db_path, readonly=False)
        with env.begin(write=True) as txn:
            txn.put(b"Malformed Article", malformed_file.encode())
        env.close()

        mock_invoke = Mock(return_value="Malformed Article")

        # Should raise JSONDecodeError because of malformed JSON
        with pytest.raises(json.JSONDecodeError):
            get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

    def test_get_next_article_missing_title_field(self):
        """Test when the JSON is valid but missing required fields."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Machine Learning"],
        )

        # Create file with JSON missing title
        incomplete_file = os.path.join(self.data_dir, "incomplete_wiki")
        with open(incomplete_file, "w") as f:
            f.write(json.dumps({"text": "Some content without title", "url": "/wiki/Incomplete", "links": []}) + "\n")

        # Add mapping to incomplete file
        env = lmdb.open(self.db_path, readonly=False)
        with env.begin(write=True) as txn:
            txn.put(b"Incomplete Article", incomplete_file.encode())
        env.close()

        mock_invoke = Mock(return_value="Incomplete Article")

        # Should raise RuntimeError because KeyError when accessing missing title field
        with pytest.raises(RuntimeError, match="An unknown error occurred."):
            get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

    def test_get_next_article_invoke_returns_empty_string(self):
        """Test when invoke function returns empty string."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Machine Learning"],
        )

        mock_invoke = Mock(return_value="")

        # Should raise ArticleNotFound
        with pytest.raises(ArticleNotFound, match="Invoke function returned empty link"):
            get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

    def test_get_next_article_invoke_returns_none(self):
        """Test when invoke function returns None."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Machine Learning"],
        )

        mock_invoke = Mock(return_value=None)

        # Should raise ArticleNotFound
        with pytest.raises(ArticleNotFound, match="Invoke function returned None"):
            get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

    def test_get_next_article_multiline_jsonl(self):
        """Test reading from a file with multiple JSONL entries (should read first)."""
        current_page = Page(
            url="",
            title="Python (programming language)",
            content="Python is a high-level programming language.",
            links=["Multi Article"],
        )

        # Create file with multiple JSONL lines
        multi_file = os.path.join(self.data_dir, "multi_wiki")
        with open(multi_file, "w") as f:
            f.write(json.dumps({"title": "First Article", "text": "First content", "url": "/wiki/First_Article", "links": []}) + "\n")
            f.write(json.dumps({"title": "Second Article", "text": "Second content", "url": "/wiki/Second_Article", "links": []}) + "\n")

        # Add mapping to multi-line file
        env = lmdb.open(self.db_path, readonly=False)
        with env.begin(write=True) as txn:
            txn.put(b"First Article", multi_file.encode())
        env.close()

        mock_invoke = Mock(return_value="First Article")

        # Get next article - should get the first entry
        next_page = get_next_article(current_page, "goal", mock_invoke, self.wiki_data)

        assert next_page.title == "First Article"
        assert "First content" in next_page.content
