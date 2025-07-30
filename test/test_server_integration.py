#!/usr/bin/env python3
"""
Integration tests for Ollama's native OpenAI-compatible API.
"""

import json
import os
import signal
import subprocess
import time
import unittest
from typing import Optional

import requests


class OllamaIntegrationTests(unittest.TestCase):
    ollama_process: Optional[subprocess.Popen] = None
    server_url = "http://localhost:11434"
    model_name = "qwen3:0.6b"

    @classmethod
    def setUpClass(cls):
        """Start Ollama server if not running, ensure model is available."""
        print("Setting up Ollama for integration tests...")

        # Check if Ollama is already running
        try:
            response = requests.get(f"{cls.server_url}/api/tags", timeout=2)
            if response.status_code == 200:
                print("Ollama is already running")
                cls.ollama_process = None
            else:
                raise requests.exceptions.RequestException()
        except requests.exceptions.RequestException:
            print("Starting Ollama server...")
            # Start Ollama server
            cls.ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
            )

            # Wait for Ollama to start
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{cls.server_url}/api/tags", timeout=2)
                    if response.status_code == 200:
                        print(f"Ollama started successfully after {i+1} retries")
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            else:
                cls.tearDownClass()
                raise RuntimeError("Ollama failed to start within timeout period")

        # Ensure model is available
        print(f"Checking if model {cls.model_name} is available...")
        try:
            models_response = requests.get(f"{cls.server_url}/api/tags")
            if models_response.status_code == 200:
                models = models_response.json()
                model_names = [model["name"] for model in models.get("models", [])]
                if cls.model_name not in model_names:
                    print(f"Model {cls.model_name} not found. Pulling...")
                    pull_result = subprocess.run(
                        ["ollama", "pull", cls.model_name],
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    if pull_result.returncode != 0:
                        cls.tearDownClass()
                        raise RuntimeError(
                            f"Failed to pull model {cls.model_name}: {pull_result.stderr}"
                        )
                    print(f"Model {cls.model_name} pulled successfully")
                else:
                    print(f"Model {cls.model_name} is already available")
        except Exception as e:
            cls.tearDownClass()
            raise RuntimeError(f"Failed to verify model availability: {e}")

    @classmethod
    def tearDownClass(cls):
        """Terminate Ollama process if we started it."""
        if cls.ollama_process:
            print("Terminating Ollama process...")
            try:
                os.killpg(os.getpgid(cls.ollama_process.pid), signal.SIGTERM)
                cls.ollama_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(cls.ollama_process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            print("Ollama process terminated")

    def test_list_models_endpoint(self):
        """Test the /v1/models endpoint returns expected structure."""
        response = requests.get(f"{self.server_url}/v1/models")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["object"], "list")
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)

        # Check that our test model is in the list
        model_ids = [model["id"] for model in data["data"]]
        self.assertIn(self.model_name, model_ids)

    def test_chat_completion_non_streaming(self):
        """Test non-streaming chat completion."""
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": "What is 2+2?"}],
            "temperature": 0.7,
            "max_tokens": 50,
            "stream": False,
        }

        response = requests.post(f"{self.server_url}/v1/chat/completions", json=payload, timeout=30)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Validate response structure
        self.assertEqual(data["object"], "chat.completion")
        self.assertIn("id", data)
        self.assertEqual(data["model"], self.model_name)
        self.assertIn("choices", data)
        self.assertIn("usage", data)

        # Validate choices structure
        self.assertGreater(len(data["choices"]), 0)
        choice = data["choices"][0]
        self.assertEqual(choice["index"], 0)
        self.assertIn("message", choice)
        self.assertEqual(choice["message"]["role"], "assistant")
        self.assertIn("content", choice["message"])
        self.assertIsInstance(choice["message"]["content"], str)

        # Validate usage structure
        usage = data["usage"]
        self.assertIn("prompt_tokens", usage)
        self.assertIn("completion_tokens", usage)
        self.assertIn("total_tokens", usage)

    def test_chat_completion_streaming(self):
        """Test streaming chat completion."""
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": "Count from 1 to 3"}],
            "temperature": 0.8,
            "max_tokens": 30,
            "stream": True,
        }

        response = requests.post(
            f"{self.server_url}/v1/chat/completions", json=payload, stream=True, timeout=30
        )

        self.assertEqual(response.status_code, 200)
        chunks = []
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data_part = line[6:]  # Remove 'data: ' prefix
                    if data_part == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data_part)
                        chunks.append(chunk_data)
                    except json.JSONDecodeError:
                        continue

        # Validate that we received streaming chunks
        self.assertGreater(len(chunks), 0)

        # Validate chunk structure
        for chunk in chunks:
            self.assertEqual(chunk["object"], "chat.completion.chunk")
            self.assertIn("id", chunk)
            self.assertEqual(chunk["model"], self.model_name)
            self.assertIn("choices", chunk)

            choice = chunk["choices"][0]
            self.assertEqual(choice["index"], 0)
            self.assertIn("delta", choice)

    def test_invalid_model_handling(self):
        """Test server handles invalid model names gracefully."""
        payload = {
            "model": "nonexistent-model",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
            "max_tokens": 50,
        }

        response = requests.post(f"{self.server_url}/v1/chat/completions", json=payload, timeout=10)

        # Should return error for invalid model
        self.assertEqual(response.status_code, 404)

    def test_malformed_request_handling(self):
        """Test server handles malformed requests properly."""
        # Missing required fields
        payload = {
            "model": self.model_name,
            # Missing messages field
            "temperature": 0.7,
        }

        response = requests.post(f"{self.server_url}/v1/chat/completions", json=payload, timeout=10)

        # Should return 422 for validation error
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    # Run the integration tests
    unittest.main(verbosity=2)
