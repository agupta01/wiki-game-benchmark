import unittest

from src.api.utils import get_scope


class TestOllamaClientIntegration(unittest.TestCase):
    def test_scope_is_local(self):
        assert get_scope() == "local"


if __name__ == "__main__":
    unittest.main(verbosity=2)
