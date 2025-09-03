import unittest

import pytest

from src.clients import OllamaClient, OpenRouterClient
from src.models import OllamaSupportedModel, OpenRouterSupportedModel, Page


class TestOllamaClientIntegration(unittest.TestCase):
    """Integration tests for OllamaClient."""

    def test_ollama_client_initialization(self):
        """Test that OllamaClient can be initialized with a supported model."""
        model = OllamaSupportedModel.QWEN3_0_6B
        client = OllamaClient(model)

        assert client.model_name == model
        assert client.server_url == "http://localhost:11434"
        assert client.lm is not None

    def test_ollama_client_invoke(self):
        """Test that OllamaClient can invoke a model with a Page and goal."""
        model = OllamaSupportedModel.QWEN3_0_6B
        client = OllamaClient(model)

        # Create test page as shown in the example
        page = Page(
            url="",
            title="Abraham Lincoln",
            content="Some text about this president of the United States",
            links=["Apples", "United States of America"],
        )

        # Invoke the client
        result = client.invoke(page, "New York")

        # The result should be one of the available links
        assert isinstance(result, str)
        assert result in page.links

    def test_ollama_client_unsupported_model(self):
        """Test that OllamaClient raises an error for unsupported models."""
        with pytest.raises(ValueError, match="Model .* is not supported by provider"):
            OllamaClient("unsupported-model")


class TestOpenRouterClientIntegration(unittest.TestCase):
    """Integration tests for OpenRouterClient."""

    def test_openrouter_client_initialization(self):
        """Test that OpenRouterClient can be initialized with a supported model."""
        model = OpenRouterSupportedModel.QWEN3_DEEPSEEK_8B
        client = OpenRouterClient(model)

        assert client.model_name == model
        assert client.lm is not None

    def test_openrouter_client_invoke(self):
        """Test that OpenRouterClient can invoke a model with a Page and goal."""
        model = OpenRouterSupportedModel.QWEN3_DEEPSEEK_8B
        client = OpenRouterClient(model)

        # Create test page as shown in the example
        page = Page(
            url="",
            title="Abraham Lincoln",
            content="Some text about this president of the United States",
            links=["Apples", "United States of America"],
        )

        # Invoke the client
        result = client.invoke(page, "New York")

        # The result should be one of the available links
        assert isinstance(result, str)
        assert result in page.links

    def test_openrouter_client_unsupported_model(self):
        """Test that OpenRouterClient raises an error for unsupported models."""
        with pytest.raises(ValueError, match="Model .* is not supported by provider"):
            OpenRouterClient("unsupported-model")


if __name__ == "__main__":
    # Run the integration tests
    unittest.main(verbosity=2)
