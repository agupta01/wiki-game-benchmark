import logging
import os
from collections import deque
from typing import Literal, Tuple

import modal
from dotenv import load_dotenv

from src.models import OllamaSupportedModel, OpenRouterSupportedModel, Provider, SupportedModel

APP_NAME = "wiki-game"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(APP_NAME)


def get_scope() -> Literal["local", "remote"]:
    load_dotenv()
    return "local" if os.getenv("SCOPE", "remote") == "local" else "remote"


app_image = modal.Image.debian_slim().uv_sync().add_local_python_source("src")
app = modal.App(name=APP_NAME, image=app_image)

game_store = (
    modal.Dict.from_name("game-store", create_if_missing=True)
)


class GameQueue:
    def __init__(self, scope: str):
        super().__init__()
        if scope == "local":
            self._queue = []
            self.scope = scope
        elif scope == "remote":
            self._queue = modal.Queue.from_name("game-queue", create_if_missing=True)
            self.scope = scope
        else:
            raise TypeError(f"Scope {scope} not supported")

    def pop(self):
        if self.scope == "remote":
            return self._queue.get(block=False)
        else:
            return self._queue.pop(0)

    def append(self, item: str):
        if self.scope == "remote":
            return self._queue.put(item)
        else:
            return self._queue.append(item)


game_queue = GameQueue(scope=get_scope())


def get_model_config() -> Tuple[Provider, SupportedModel]:
    load_dotenv()
    if get_scope() == "local":
        return Provider.OLLAMA, OllamaSupportedModel(
            os.getenv("OLLAMA_MODEL", OllamaSupportedModel.QWEN3_0_6B)
        )
    else:
        return Provider.OPENROUTER, OpenRouterSupportedModel(
            os.getenv("OPENROUTER_MODEL", OpenRouterSupportedModel.QWEN3_DEEPSEEK_8B)
        )
