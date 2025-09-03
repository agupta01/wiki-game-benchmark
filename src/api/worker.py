import json
import time

import modal
from dotenv import dotenv_values, load_dotenv

from src.api.models import Game
from src.api.utils import app, game_queue, game_store, get_scope, logger
from src.eval import create_client, get_next_article, path_transformer
from src.models import OpenRouterSupportedModel, Provider
from src.wiki_db import WikiData


@app.function()
def manage_queue():
    while True:
        if game_queue.len():
            logger.info("Processing queue item")

            if get_scope() == "remote":
                process_queue.spawn()
            else:
                process_queue.local()
        else:
            logger.info("No tasks in queue. Waiting for tasks...")
            time.sleep(1)


@app.function(secrets=[modal.Secret.from_dict(dotenv_values() | {"SCOPE": None})])
def process_queue():
    top_game_id = None
    try:
        top_game_id = game_queue.get(block=False)
        # Iterate on the game
        game: Game = Game(**json.loads(game_store[top_game_id]))

        provider, model = Provider.OPENROUTER, OpenRouterSupportedModel.QWEN3_DEEPSEEK_8B

        logger.info(f"Processing game {top_game_id} with provider {provider} and model {model}")

        client = create_client(provider, model)
        db = WikiData("./index.lmdb", path_transformer)  # TODO: needs remote implementation

        current_article_name = (
            game.current_article if game.current_article != "" else game.start_article
        )
        current_article = db.get_page(current_article_name)

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

    except Exception as e:
        logger.exception(e)
        if top_game_id:
            game_queue.put(top_game_id)


if __name__ == "__main__":
    load_dotenv()
    manage_queue.local()
