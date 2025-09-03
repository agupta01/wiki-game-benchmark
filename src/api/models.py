from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Move(BaseModel):
    """Represents a single move in the game."""

    article: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Game(BaseModel):
    """Represents a Wikipedia game state."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    start_article: str = Field(default="")
    end_article: str = Field(default="")
    moves: List[Move] = Field(default_factory=list)
    current_article: str = Field(default="")
    is_complete: bool = Field(default=False)
    player: Literal["human", "ai"] = Field(default="human")

    @property
    def last_move_article(self) -> Optional[str]:
        """Get the article from the last move, if any."""
        return self.moves[-1].article if self.moves else None

    def add_move(self, article: str) -> bool:
        """
        Add a move to the game. Returns True if move was added, False if duplicate or if game is complete.
        Implements idempotency check.
        """
        if self.last_move_article == article or self.is_complete:
            return False  # Duplicate move, don't add

        self.moves.append(Move(article=article))
        self.current_article = article

        if article == self.end_article:
            self.is_complete = True

        return True

    def to_api_response(self) -> dict:
        """Convert game to API response format."""
        return {
            "id": self.id,
            "startArticle": self.start_article,
            "endArticle": self.end_article,
            "moves": [
                {"article": move.article, "timestamp": move.timestamp.isoformat()}
                for move in self.moves
            ],
            "currentArticle": self.current_article,
            "isComplete": self.is_complete,
        }


# Request/Response models for API endpoints
class CreateGameRequest(BaseModel):
    player: Literal["human", "ai"] = "human"
    start_article: str = Field(alias="startArticle")
    end_article: str = Field(alias="endArticle")


class CreateGameResponse(BaseModel):
    id: str


class UpdateGameRequest(BaseModel):
    article: str
