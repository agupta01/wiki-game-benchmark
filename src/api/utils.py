import logging
import os
from typing import Literal

import modal
from dotenv import load_dotenv

APP_NAME = "wiki-game"


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Format: MM/DD HH:MM:SS.sss
        ct = self.converter(record.created)
        t = f"{ct.tm_mon:02d}/{ct.tm_mday:02d} {ct.tm_hour:02d}:{ct.tm_min:02d}:{ct.tm_sec:02d}.{int(record.msecs):03d}"
        return t


# Setup logging
handler = logging.StreamHandler()
formatter = CustomFormatter(fmt="%(asctime)s - %(name)s:%(levelname)s: %(message)s")
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(APP_NAME)


def get_scope() -> Literal["local", "remote"]:
    load_dotenv()
    return "local" if os.getenv("SCOPE", "remote") == "local" else "remote"


app_image = modal.Image.debian_slim().uv_sync().add_local_python_source("src")
app = modal.App(name=APP_NAME, image=app_image)

game_store = modal.Dict.from_name("game-store", create_if_missing=True)


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


game_queue = modal.Queue.from_name("game-queue", create_if_missing=True)
