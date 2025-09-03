const PROD_BASE = 'https://wiki-game-dev--api.modal.run'
export const API_BASE = import.meta.env.DEV ? '/api' : PROD_BASE

export type Move = {
	article: string
	timestamp: string
	url: string
}

export type GameState = {
	id: string
	startArticle: string
	endArticle: string
	moves: Move[]
	currentArticle: string
	isComplete: boolean
}

export async function createGame(params: { startArticle: string; endArticle: string }): Promise<{ id: string }> {
	const res = await fetch(`${API_BASE}/game`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ player: 'ai', ...params }),
	})
	if (!res.ok) throw new Error(`Failed to create game: ${res.status}`)
	return res.json()
}

export async function getGame(id: string): Promise<GameState> {
	const res = await fetch(`${API_BASE}/game/${id}`)
	if (!res.ok) throw new Error(`Failed to load game: ${res.status}`)
	return res.json()
}