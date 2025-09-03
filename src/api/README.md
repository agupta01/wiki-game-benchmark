# API Design

## Lifecycle

### Create Game
```
POST /game

Request:
{
  player: "human" | "ai"
  startArticle: str
  endArticle: str
}

Response:
{
  id: uuidv4
}
```

### Get Game State
```
GET /game/{id}

Response:
{
  id: uuidv4
  startArticle: string
  endArticle: string
  moves: [
    {
      article: string
      timestamp: ISO8601
    }
  ]
  currentArticle: string
  isComplete: boolean
}
```

### Update Game State
```
POST /game/{id}

Request:
{
  article: string
}

Response:
{
  id: uuidv4
  startArticle: string
  endArticle: string
  moves: [
    {
      article: string
      timestamp: ISO8601
    }
  ]
  currentArticle: string
  isComplete: boolean
}
```

## AI Player Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Dict as Modal Dict
    participant Queue as Modal Queue
    participant Worker

    User->>API: POST /game (player: "ai")
    API->>Dict: Store game object
    API->>Queue: Put game id
    API-->>User: Return game id

    loop Until queue empty
        Worker->>Queue: Get game id (blocking)
        Queue-->>Worker: Return game id (removes from queue)
        Worker->>API: GET /game/{id}
        API->>Dict: Fetch game object
        Dict-->>API: Return game object
        API-->>Worker: Return game state
        Worker->>Worker: Run inference for next move
        Worker->>API: PATCH /game/{id} (article, isComplete)
        Note over API: Idempotency check:<br/>if moves[-1].article == article,<br/>return current state (no-op)
        API->>Dict: Update game object (if not duplicate)
        API-->>Worker: Return updated game state
        alt Game not complete
            Worker->>Queue: Put game id back (to end of queue)
        end
    end
```

### Reliability Strategy

- **Simple queue operations**: Just get/put, no partitions needed
- **Idempotent PATCH**: API checks if the last move's article matches the incoming article
  - If match: return current state without modification (no-op)
  - If different: add new move with timestamp
- **Worker crash handling**: If worker crashes after get(), the queue timeout returns the game ID to queue automatically
- **No orphaned games**: Duplicate processing is safe due to idempotency
