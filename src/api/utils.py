import logging
import os
from typing import Literal

import modal
from dotenv import load_dotenv

API_APP_NAME = "wiki-game"
WORKER_APP_NAME = "wiki-worker"


class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Format: MM/DD HH:MM:SS.sss
        ct = self.converter(record.created)
        t = f"{ct.tm_mon:02d}/{ct.tm_mday:02d} {ct.tm_hour:02d}:{ct.tm_min:02d}:{ct.tm_sec:02d}.{int(record.msecs):03d}"
        return t


def setup_logger(app_name: str) -> logging.Logger:
    handler = logging.StreamHandler()
    formatter = CustomFormatter(fmt="%(asctime)s - %(name)s:%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    return logging.getLogger(app_name)


def get_scope() -> Literal["local", "remote"]:
    load_dotenv()
    return "local" if os.getenv("SCOPE", "remote") == "local" else "remote"


app_image = modal.Image.debian_slim().uv_sync().add_local_python_source("src")
cloudflare_secret = modal.Secret.from_name(
    "r2-secret", required_keys=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
)

game_store = modal.Dict.from_name("game-store", create_if_missing=True)

game_queue = modal.Queue.from_name("game-queue", create_if_missing=True)
