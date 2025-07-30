import os
import tempfile

import lmdb
import pytest

from src.wiki_db import WikiData


class TestWikiData:
    def test_get_article_location_existing_article(self):
        """Test getting location for an existing article."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create a test LMDB database
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"Python", b"2025-06-01/AA/wiki_01")
                txn.put(b"Machine Learning", b"2025-06-01/ML/wiki_42")
            env.close()

            # Test the WikiData class
            wiki_data = WikiData(db_path)
            location = wiki_data.get_article_location("Python")
            assert location == "2025-06-01/AA/wiki_01"

            location = wiki_data.get_article_location("Machine Learning")
            assert location == "2025-06-01/ML/wiki_42"

    def test_get_article_location_nonexistent_article(self):
        """Test getting location for a non-existent article."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create empty LMDB database
            env = lmdb.open(db_path, map_size=1024 * 1024)
            env.close()

            wiki_data = WikiData(db_path)
            location = wiki_data.get_article_location("NonexistentArticle")
            assert location is None

    def test_get_article_location_case_sensitivity(self):
        """Test that article lookup is case-sensitive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create a test LMDB database
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"Python", b"2025-06-01/AA/wiki_01")
            env.close()

            wiki_data = WikiData(db_path)

            # Exact match should work
            location = wiki_data.get_article_location("Python")
            assert location == "2025-06-01/AA/wiki_01"

            # Case variations should not match
            location = wiki_data.get_article_location("python")
            assert location is None

            location = wiki_data.get_article_location("PYTHON")
            assert location is None

    def test_get_article_location_unicode_handling(self):
        """Test handling of Unicode characters in article names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create a test LMDB database with Unicode article names
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put("Café".encode("utf-8"), b"2025-06-01/CC/wiki_15")
                txn.put("北京".encode("utf-8"), b"2025-06-01/ZH/wiki_88")
            env.close()

            wiki_data = WikiData(db_path)

            location = wiki_data.get_article_location("Café")
            assert location == "2025-06-01/CC/wiki_15"

            location = wiki_data.get_article_location("北京")
            assert location == "2025-06-01/ZH/wiki_88"

    def test_init_with_nonexistent_db(self):
        """Test initialization with a non-existent database path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "nonexistent.lmdb")

            with pytest.raises(lmdb.Error):
                WikiData(db_path)

    def test_init_with_invalid_path(self):
        """Test initialization with an invalid path."""
        invalid_path = "/invalid/path/that/does/not/exist/db.lmdb"

        with pytest.raises(lmdb.Error):
            WikiData(invalid_path)

    def test_database_connection_context_management(self):
        """Test that database connections are properly managed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create a test LMDB database
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"Test Article", b"2025-06-01/TT/wiki_99")
            env.close()

            wiki_data = WikiData(db_path)

            # Multiple calls should work without issues
            location1 = wiki_data.get_article_location("Test Article")
            location2 = wiki_data.get_article_location("Test Article")
            location3 = wiki_data.get_article_location("Nonexistent")

            assert location1 == "2025-06-01/TT/wiki_99"
            assert location2 == "2025-06-01/TT/wiki_99"
            assert location3 is None

    def test_empty_article_name(self):
        """Test handling of empty article names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create empty LMDB database
            env = lmdb.open(db_path, map_size=1024 * 1024)
            env.close()

            wiki_data = WikiData(db_path)
            location = wiki_data.get_article_location("")
            assert location is None

    def test_whitespace_article_name(self):
        """Test handling of whitespace-only article names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create LMDB database with whitespace entries
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"   ", b"2025-06-01/WS/wiki_01")
                txn.put(b"\t\n", b"2025-06-01/WS/wiki_02")
            env.close()

            wiki_data = WikiData(db_path)

            # Exact whitespace matches should work
            location = wiki_data.get_article_location("   ")
            assert location == "2025-06-01/WS/wiki_01"

            location = wiki_data.get_article_location("\t\n")
            assert location == "2025-06-01/WS/wiki_02"

            # Different whitespace should not match
            location = wiki_data.get_article_location("  ")
            assert location is None
