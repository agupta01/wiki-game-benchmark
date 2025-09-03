import json
import time

import modal
from dotenv import dotenv_values, load_dotenv

from src.api.models import Game
from src.api.utils import (
    WORKER_APP_NAME,
    app_image,
    cloudflare_secret,
    game_queue,
    game_store,
    get_scope,
    setup_logger,
)
from src.eval import create_client, get_next_article
from src.eval import path_transformer as local_path_transformer
from src.models import GroqSupportedModel, Provider
from src.wiki_db import WikiData

load_dotenv()

logger = setup_logger(WORKER_APP_NAME)

worker_app = modal.App(name=WORKER_APP_NAME, image=app_image)


@worker_app.function(
    timeout=86400, max_inputs=1, max_containers=1, min_containers=0, scaledown_window=2
)
def manage_queue():
    poll_until = time.time() + 5
    while time.time() < poll_until:
        if game_queue.len():
            logger.info("Processing queue item")

            if get_scope() == "remote":
                process_queue_item.spawn()
            else:
                process_queue_item.local()

            # Reset poll_until
            poll_until = time.time() + 5
        else:
            logger.info(
                "No tasks in queue. Waiting for tasks... (will stop in %d seconds)"
                % int(poll_until - time.time())
            )

        time.sleep(1)


@worker_app.function(
    volumes={
        "/data": modal.CloudBucketMount(
            bucket_name="wiki-data",
            bucket_endpoint_url="https://684be30d0e8fbd7eb2bab9bb2823cd14.r2.cloudflarestorage.com",
            secret=cloudflare_secret,
            read_only=True,
        )
    },
    secrets=[modal.Secret.from_dict(dotenv_values() | {"SCOPE": None})],
)
def process_queue_item():
    top_game_id = None
    try:
        top_game_id = game_queue.get()
        # Iterate on the game
        game: Game = Game(**json.loads(game_store[top_game_id]))

        provider, model = Provider.GROQ, GroqSupportedModel.GPT_OSS_20B

        logger.info(f"Processing game {top_game_id} with provider {provider} and model {model}")

        client = create_client(provider, model)

        index_path = "./index.lmdb" if get_scope() == "local" else "/data/2025-06-01/index.lmdb"
        path_transformer = (
            local_path_transformer
            if get_scope() == "local"
            else (lambda x: x.replace("..", "/data"))
        )

        db = WikiData(index_path, path_transformer)

        current_article_name = (
            game.current_article if game.current_article != "" else game.start_article
        )
        current_article = db.get_page(current_article_name)

        # Prune previously visited pages from the available links list
        visited_pages = set(map(lambda move: move.article, game.moves))
        current_article.links = list(
            filter(lambda link: link not in visited_pages, current_article.links)
        )

        next_article = get_next_article(
            current_article=current_article,
            goal=game.end_article,
            invoke=client.invoke,
            wiki_data=db,
            ctrl_f=True,
        )

        # Update game with next step
        game.add_move(next_article.title)
        game_store[top_game_id] = game.model_dump_json()

        # If not complete, push back to queue
        if not game.is_complete and top_game_id:
            game_queue.put(top_game_id)
            # Restart manager if shut down
            if get_scope() != "local":
                manage_queue.spawn()
    except KeyError as e:
        logger.exception(e)
        # Game not found, was deleted from store. We don't want to re-queue it in this case
        logger.error(f"Game not found, was deleted from store. Game ID: {top_game_id}")
    except Exception as e:
        logger.exception(e)
        if top_game_id:
            game_queue.put(top_game_id)


if __name__ == "__main__":
    load_dotenv()
    manage_queue.local()
