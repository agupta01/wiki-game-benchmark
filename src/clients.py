import os
import random
import signal
import subprocess
import time
from abc import ABC, abstractmethod
from warnings import warn

import dspy
import requests
from dotenv import load_dotenv

from src import models
from src.signatures import get_next_page, get_next_page_chain
from src.utils import NotImplementedWarning


class BaseModelClient(ABC):
    def __init__(self, provider_name: str, model_name: str):
        if not self._is_supported_model(model_name):
            raise ValueError(f"Model {model_name} is not supported by provider.")
        self.model_name = model_name
        self.api_key = self.get_api_key(provider_name)
        self.temperature = 0.0
        self.lm = None

    @abstractmethod
    def _is_supported_model(self, model_name: str) -> bool:
        """Determines if the model is supported by this client."""
        warn(
            "Implement this to check if the model is supported by this provider.",
            NotImplementedWarning,
        )
        return True

    def invoke(self, page: models.Page, goal_page_title: str) -> str:
        if not self.lm:
            raise NotImplementedError("Language model not initialized.")
        with dspy.context(lm=self.lm):
            try:
                model_output = get_next_page(
                    input=models.StepInput(
                        current_page=page,
                        goal_page_title=goal_page_title,
                    ),
                )

                if (next_link := model_output.output.selected_link) not in page.links:
                    print("Raw predict failed to return a valid link. Attempting CoT...")
                    model_output = get_next_page_chain(
                        input=models.StepInput(
                            current_page=page,
                            goal_page_title=goal_page_title,
                        ),
                    )
                    next_link = model_output.output.selected_link

                # If still not there, return random link
                if next_link not in page.links:
                    print("CoT predict failed to return a valid link. Returning random link...")
                    next_link = random.choice(page.links)
            except Exception as e:
                print(f"Error occurred during prediction: {e}. Returning random link...")
                next_link = random.choice(page.links)
            finally:
                return next_link

    def get_api_key(self, provider_name: str) -> str:
        load_dotenv(dotenv_path=os.path.abspath(os.path.join(os.pardir, ".env")))
        api_key = os.getenv(f"{provider_name.upper()}_API_KEY")
        if not api_key:
            raise ValueError(f"API key for {provider_name} not found in .env file.")
        return api_key


class OllamaClient(BaseModelClient):
    def __init__(self, model_name: str):
        super().__init__(models.Provider.OLLAMA, model_name)
        self.server_url = "http://localhost:11434"
        self.ollama_process = None
        self.setup_ollama_process()
        self.lm = dspy.LM(
            api_base=f"{self.server_url}",
            api_key=self.api_key,
            model=f"ollama_chat/{self.model_name}",
            model_type="chat",
            temperature=self.temperature,
        )

    def __del__(self):
        self.terminate_ollama_process()

    def _is_supported_model(self, model_name: str) -> bool:
        return model_name in models.OllamaSupportedModel

    def setup_ollama_process(self):
        # Check if Ollama is already running
        try:
            response = requests.get(f"{self.server_url}/api/tags", timeout=2)
            if response.status_code == 200:
                print("Ollama is already running")
                self.ollama_process = None
            else:
                raise requests.exceptions.RequestException()
        except requests.exceptions.RequestException:
            print("Starting Ollama server...")
            # Start Ollama server
            self.ollama_process = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
            )

            # Wait for Ollama to start
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{self.server_url}/api/tags", timeout=2)
                    if response.status_code == 200:
                        print(f"Ollama started successfully after {i+1} retries")
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)
            else:
                self.terminate_ollama_process()
                raise RuntimeError("Ollama failed to start within timeout period")

        # Ensure model is available
        print(f"Checking if model {self.model_name} is available...")
        try:
            models_response = requests.get(f"{self.server_url}/api/tags")
            if models_response.status_code == 200:
                models = models_response.json()
                model_names = [model["name"] for model in models.get("models", [])]
                if self.model_name not in model_names:
                    print(f"Model {self.model_name} not found. Pulling...")
                    pull_result = subprocess.run(
                        ["ollama", "pull", self.model_name],
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    if pull_result.returncode != 0:
                        self.terminate_ollama_process()
                        raise RuntimeError(
                            f"Failed to pull model {self.model_name}: {pull_result.stderr}"
                        )
                    print(f"Model {self.model_name} pulled successfully")
                else:
                    print(f"Model {self.model_name} is already available")
        except Exception as e:
            self.terminate_ollama_process()
            raise RuntimeError(f"Failed to verify model availability: {e}")

    def terminate_ollama_process(self):
        """Terminate Ollama process if we started it."""
        if self.ollama_process:
            print("Terminating Ollama process...")
            try:
                os.killpg(os.getpgid(self.ollama_process.pid), signal.SIGTERM)
                self.ollama_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    os.killpg(os.getpgid(self.ollama_process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            print("Ollama process terminated")


class OpenRouterClient(BaseModelClient):
    def __init__(self, model_name: str):
        super().__init__(models.Provider.OPENROUTER, model_name)
        self.lm = dspy.LM(
            f"openrouter/{self.model_name}",
            api_key=self.api_key,
            temperature=self.temperature,
        )

    def _is_supported_model(self, model_name: str) -> bool:
        return model_name in models.OpenRouterSupportedModel


class CerebrasClient(BaseModelClient):
    def __init__(self, model_name: str):
        super().__init__(models.Provider.CEREBRAS, model_name)
        self.lm = dspy.LM(
            f"cerebras/{self.model_name}",
            api_key=self.api_key,
            temperature=self.temperature,
        )

    def _is_supported_model(self, model_name: str) -> bool:
        return model_name in models.CerebrasSupportedModel


def create_client(provider: str, model: str) -> BaseModelClient:
    """Factory function to create the appropriate client based on provider type.

    Args:
        provider: The provider name (e.g., "ollama", "openrouter")
        model: The model name

    Returns:
        Appropriate client instance

    Raises:
        ValueError: If provider is not supported
    """
    if provider == models.Provider.OLLAMA:
        return OllamaClient(model)
    elif provider == models.Provider.OPENROUTER:
        return OpenRouterClient(model)
    elif provider == models.Provider.CEREBRAS:
        return CerebrasClient(model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")
