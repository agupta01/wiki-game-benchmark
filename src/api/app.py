import json
from uuid import uuid4

import modal
from dotenv import load_dotenv
from flask import Flask
from flask_pydantic import validate

from src.api.models import CreateGameRequest, CreateGameResponse, Game, UpdateGameRequest
from src.api.utils import (
    API_APP_NAME,
    app_image,
    cloudflare_secret,
    game_queue,
    game_store,
    get_scope,
    setup_logger,
)
from src.api.worker import manage_queue, worker_app
from src.eval import path_transformer as local_path_transformer
from src.utils import ArticleNotFound
from src.wiki_db import WikiData

load_dotenv()

logger = setup_logger(API_APP_NAME)

app = modal.App(name=API_APP_NAME, image=app_image)
app.include(worker_app)

server = Flask(__name__)


@server.get("/game/<uuid:game_id>")
def get_game(game_id):
    game_id = str(game_id)
    try:
        game: Game = Game(**json.loads(game_store[game_id]))
        return game.to_api_response(), 200
    except KeyError as e:
        logger.exception(e)
        return f"Game {game_id} not found", 404
    except Exception as e:
        logger.exception(e)
        return f"Internal error: {e}", 500


@server.post("/game")
@validate()
def create_game(body: CreateGameRequest):
    try:
        game_id = str(uuid4())
        server.logger.debug(game_id)
        if game_id in game_store:
            return f"Game id {game_id} already in store.", 500
        else:
            game = Game(
                id=game_id,
                start_article=body.start_article,
                end_article=body.end_article,
                player=body.player,
            )

            # Get url for starting article
            index_path = "./index.lmdb" if get_scope() == "local" else "/data/2025-06-01/index.lmdb"
            path_transformer = (
                local_path_transformer
                if get_scope() == "local"
                else (lambda x: x.replace("..", "/data"))
            )

            db = WikiData(index_path, path_transformer)

            start_page = db.get_page(body.start_article)
            db.get_page(body.end_article)

            game.add_move(article=body.start_article, url=start_page.url)
            game_store[game_id] = game.model_dump_json()
            if body.player == "ai":
                logger.info("Adding game to processing queue")
                game_queue.put(game_id)
                # Turn on the queue processor, if not started yet
                stats = manage_queue.get_current_stats()
                logger.info(f"NUM RUNNERS: {stats.num_total_runners}")
                if manage_queue.get_current_stats().backlog < 2 and get_scope() != "local":
                    manage_queue.spawn()
            return CreateGameResponse(id=game_id), 200
    except ArticleNotFound as e:
        logger.exception(e)
        return "Start or end article not found in DB. Try different articles", 400
    except Exception as e:
        logger.exception(e)
        return "Internal error", 500


@server.post("/game/<uuid:game_id>")
@validate()
def update_game(game_id, body: UpdateGameRequest):
    game_id = str(game_id)
    try:
        game: Game = Game(**json.loads(game_store[game_id]))
        game.add_move(article=body.article, url=body.url if body.url else "")
        game_store[game_id] = game.model_dump_json()
        return game.to_api_response(), 200
    except KeyError:
        return f"Game {game_id} not found", 404
    except Exception:
        return "Internal error", 500


@server.route("/game/<uuid:game_id>", methods=["DELETE"])
def delete_game(game_id):
    game_id = str(game_id)
    try:
        game_store.pop(game_id)
        return f"Game {game_id} deleted", 200
    except Exception:
        return "Internal error", 500


@app.function(
    volumes={
        "/data": modal.CloudBucketMount(
            bucket_name="wiki-data",
            bucket_endpoint_url="https://684be30d0e8fbd7eb2bab9bb2823cd14.r2.cloudflarestorage.com",
            secret=cloudflare_secret,
            read_only=True,
        )
    }
)
# @modal.concurrent(max_inputs=10)
@modal.wsgi_app(label="api")
def flask_app():
    load_dotenv()
    return server
