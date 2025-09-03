# Wikipedia Game AI Demo

A simple React + Vite + TypeScript demo that showcases an AI playing the Wikipedia Game.

- React + Vite
- Tailwind CSS (v4)
- shadcn-inspired theme tokens
- TanStack Query
- React Router

## Getting Started

```bash
cd /workspace/wiki-game-demo
npm install
npm run dev
```

Then open the URL printed by Vite (typically http://localhost:5173).

## Build

```bash
npm run build
npm run preview
```

## How it works

- Landing page lets you enter a start and end Wikipedia article and starts a game via `POST /game`.
- Game page polls `GET /game/:id` every 10 seconds, shows a timeline of visited pages on the left (top on mobile), and displays the current page in an iframe on the right (bottom on mobile).

API base: `https://wiki-game-dev--api.modal.run`
