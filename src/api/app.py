import json
from uuid import uuid4

import modal
from dotenv import load_dotenv
from flask import Flask
from flask_pydantic import validate

from src.api.models import CreateGameRequest, CreateGameResponse, Game, UpdateGameRequest
from src.api.utils import app, game_queue, game_store, logger

load_dotenv()

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
            game_store[game_id] = Game(
                id=game_id,
                start_article=body.start_article,
                end_article=body.end_article,
                player=body.player,
            ).model_dump_json()
            if body.player == "ai":
                logger.info("Adding game to processing queue")
                game_queue.put(game_id)
            return CreateGameResponse(id=game_id), 200
    except Exception:
        return "Internal error", 500


@server.post("/game/<uuid:game_id>")
@validate()
def update_game(game_id, body: UpdateGameRequest):
    game_id = str(game_id)
    try:
        game: Game = Game(**json.loads(game_store[game_id]))
        game.add_move(article=body.article)
        game_store[game_id] = game.model_dump_json()
        return game.to_api_response(), 200
    except KeyError:
        return f"Game {game_id} not found", 404
    except Exception:
        return "Internal error", 500


@app.function()
# @modal.concurrent(max_inputs=10)
@modal.wsgi_app(label="api")
def flask_app():
    load_dotenv()
    return server
