const API_BASE_URL = '/api'

export interface GameMove {
  article: string
  timestamp: string
}

export interface GameState {
  id: string
  startArticle: string
  endArticle: string
  moves: GameMove[]
  currentArticle: string
  isComplete: boolean
}

export interface CreateGameRequest {
  player: "human" | "ai"
  startArticle: string
  endArticle: string
}

export interface CreateGameResponse {
  id: string
}

export const api = {
  async createGame(data: CreateGameRequest): Promise<CreateGameResponse> {
    const response = await fetch(`${API_BASE_URL}/game`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(errorText || `HTTP ${response.status}: Failed to create game`)
    }
    
    return response.json()
  },

  async getGameState(id: string): Promise<GameState> {
    const response = await fetch(`${API_BASE_URL}/game/${id}`)
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(errorText || `HTTP ${response.status}: Failed to fetch game state`)
    }
    
    return response.json()
  }
}