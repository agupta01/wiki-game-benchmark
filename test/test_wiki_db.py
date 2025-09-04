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
            from src.utils import ArticleNotFound

            with pytest.raises(ArticleNotFound):
                wiki_data.get_article_location("NonexistentArticle")

    def test_get_article_location_case_sensitivity_with_fallback(self):
        """Test that article lookup now supports case-insensitive fallback."""
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

            # Case variations should now work via fallback
            location = wiki_data.get_article_location("python")
            assert location == "2025-06-01/AA/wiki_01"

            location = wiki_data.get_article_location("PYTHON")
            assert location == "2025-06-01/AA/wiki_01"

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

            assert location1 == "2025-06-01/TT/wiki_99"
            assert location2 == "2025-06-01/TT/wiki_99"

            from src.utils import ArticleNotFound

            with pytest.raises(ArticleNotFound):
                wiki_data.get_article_location("Nonexistent")

    def test_empty_article_name(self):
        """Test handling of empty article names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create empty LMDB database
            env = lmdb.open(db_path, map_size=1024 * 1024)
            env.close()

            wiki_data = WikiData(db_path)
            from src.utils import ArticleNotFound

            with pytest.raises(ArticleNotFound):
                wiki_data.get_article_location("")

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
            from src.utils import ArticleNotFound

            with pytest.raises(ArticleNotFound):
                wiki_data.get_article_location("  ")

    def test_case_fallback_capitalized(self):
        """Test fallback to capitalized first letter when exact match fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create database with capitalized article
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"Python", b"2025-06-01/PY/wiki_01")
                txn.put(b"Machine learning", b"2025-06-01/ML/wiki_02")
            env.close()

            wiki_data = WikiData(db_path)

            # Lowercase should find capitalized version
            location = wiki_data.get_article_location("python")
            assert location == "2025-06-01/PY/wiki_01"

            # Mixed case should find capitalized version
            location = wiki_data.get_article_location("machine learning")
            assert location == "2025-06-01/ML/wiki_02"

    def test_case_fallback_lowercase(self):
        """Test fallback to lowercase when exact match and capitalized fail."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create database with lowercase article
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"javascript", b"2025-06-01/JS/wiki_01")
                txn.put(b"html css", b"2025-06-01/WEB/wiki_02")
            env.close()

            wiki_data = WikiData(db_path)

            # Uppercase should find lowercase version
            location = wiki_data.get_article_location("JAVASCRIPT")
            assert location == "2025-06-01/JS/wiki_01"

            # Title case should find lowercase version
            location = wiki_data.get_article_location("Html Css")
            assert location == "2025-06-01/WEB/wiki_02"

    def test_case_fallback_uppercase(self):
        """Test fallback to uppercase when other cases fail."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create database with uppercase article
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"NASA", b"2025-06-01/SPACE/wiki_01")
                txn.put(b"FBI CIA", b"2025-06-01/GOV/wiki_02")
            env.close()

            wiki_data = WikiData(db_path)

            # Lowercase should find uppercase version
            location = wiki_data.get_article_location("nasa")
            assert location == "2025-06-01/SPACE/wiki_01"

            # Mixed case should find uppercase version
            location = wiki_data.get_article_location("fbi cia")
            assert location == "2025-06-01/GOV/wiki_02"

    def test_case_fallback_priority_order(self):
        """Test that fallbacks are tried in the correct priority order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            # Create database with multiple case variations of same concept
            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                # Both capitalized and lowercase exist
                txn.put(b"Python", b"2025-06-01/PY/capitalized")
                txn.put(b"python", b"2025-06-01/PY/lowercase")
                # Both uppercase and lowercase exist
                txn.put(b"JAVA", b"2025-06-01/JAVA/uppercase")
                txn.put(b"java", b"2025-06-01/JAVA/lowercase")
            env.close()

            wiki_data = WikiData(db_path)

            # When searching "python", should prefer "Python" (capitalized) over "python" (lowercase)
            location = wiki_data.get_article_location("python")
            assert location == "2025-06-01/PY/lowercase"  # Exact match wins

            # When searching "PYTHON", should prefer "Python" (capitalized) over "python" (lowercase)
            location = wiki_data.get_article_location("PYTHON")
            assert location == "2025-06-01/PY/capitalized"  # Capitalized fallback wins

            # When searching "Java", should get exact match if it exists
            # But since "Java" doesn't exist, should get capitalized fallback priority
            location = wiki_data.get_article_location("Java")
            # Should fall back to lowercase since no exact "Java" or "java" -> "JAVA" priority
            assert location == "2025-06-01/JAVA/lowercase"

    def test_case_fallback_single_character(self):
        """Test case fallback with single character articles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"A", b"2025-06-01/LETTER/wiki_A")
                txn.put(b"x", b"2025-06-01/LETTER/wiki_x")
            env.close()

            wiki_data = WikiData(db_path)

            # Lowercase should find uppercase
            location = wiki_data.get_article_location("a")
            assert location == "2025-06-01/LETTER/wiki_A"

            # Uppercase should find lowercase
            location = wiki_data.get_article_location("X")
            assert location == "2025-06-01/LETTER/wiki_x"

    def test_case_fallback_no_match_found(self):
        """Test that ArticleNotFound is raised when no case variations exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                txn.put(b"Python", b"2025-06-01/PY/wiki_01")
            env.close()

            wiki_data = WikiData(db_path)

            # Non-existent article should still raise ArticleNotFound after all fallbacks
            from src.utils import ArticleNotFound

            with pytest.raises(ArticleNotFound):
                wiki_data.get_article_location("NonExistentArticle")

    def test_case_fallback_unicode_articles(self):
        """Test case fallback with Unicode characters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.lmdb")

            env = lmdb.open(db_path, map_size=1024 * 1024)
            with env.begin(write=True) as txn:
                # Unicode with different cases
                txn.put("Café".encode("utf-8"), b"2025-06-01/FR/wiki_01")
                txn.put("москва".encode("utf-8"), b"2025-06-01/RU/wiki_01")
            env.close()

            wiki_data = WikiData(db_path)

            # Should find exact Unicode matches through fallbacks
            location = wiki_data.get_article_location("café")
            assert location == "2025-06-01/FR/wiki_01"

            location = wiki_data.get_article_location("МОСКВА")
            assert location == "2025-06-01/RU/wiki_01"
