import { useEffect, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getGame, type GameState } from '../lib/api'

export default function Game() {
	const { id } = useParams()
	const gameId = id as string

	const query = useQuery<GameState>({
		queryKey: ['game', gameId],
		queryFn: () => getGame(gameId),
		refetchInterval: 10000,
		refetchOnMount: true,
		refetchOnWindowFocus: true,
	})

	const lastUrl = useMemo(() => {
		if (!query.data) return null
		const list = query.data.moves
		return list.length ? list[list.length - 1].url : null
	}, [query.data])

	return (
		<div className="min-h-screen bg-[#faf9f7] text-slate-900">
			<header className="border-b bg-white/70 backdrop-blur supports-[backdrop-filter]:bg-white/50">
				<div className="container py-4">
					<h1 className="text-xl font-semibold">Wikipedia Game AI</h1>
					{query.data && (
						<p className="text-sm text-slate-600">{query.data.startArticle} → {query.data.endArticle}</p>
					)}
				</div>
			</header>

			<main className="container py-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
				<section className="order-1">
					<h2 className="text-lg font-medium mb-3">Timeline</h2>
					<div className="rounded-lg border bg-white p-4 h-[50vh] lg:h-[78vh] overflow-auto">
						{query.isLoading ? (
							<div className="flex items-center justify-center h-full">
								<Spinner label="Loading game state..." />
							</div>
						) : query.isError ? (
							<p className="text-red-600">{(query.error as Error).message}</p>
						) : (
							<ul className="space-y-3">
								{query.data!.moves.map((m, idx) => (
									<li key={idx} className="relative pl-6">
										<span className="absolute left-0 top-2 h-3 w-3 rounded-full bg-slate-900" />
										<div className="text-sm font-medium">{m.article}</div>
										<div className="text-xs text-slate-500">{new Date(m.timestamp).toLocaleString()}</div>
									</li>
								))}
								{query.data!.moves.length === 0 && (
									<li className="text-sm text-slate-500">Awaiting first move…</li>
								)}
							</ul>
						)}
					</div>
					{query.isFetching && (
						<div className="mt-3 text-xs text-slate-500 inline-flex items-center gap-2">
							<SmallSpinner /> Refreshing…
						</div>
					)}
				</section>

				<section className="order-2">
					<h2 className="text-lg font-medium mb-3">Current page</h2>
					<div className="rounded-lg border bg-white h-[40vh] lg:h-[78vh] overflow-hidden flex items-center justify-center">
						{!lastUrl ? (
							<div className="text-slate-500 flex flex-col items-center gap-3">
								<Spinner />
								<span className="text-sm">Waiting for the AI to load a page…</span>
							</div>
						) : (
							<iframe key={lastUrl} src={lastUrl} className="w-full h-full" title="Wikipedia page" />
						)}
					</div>
				</section>
			</main>
		</div>
	)
}

function Spinner({ label }: { label?: string }) {
	useEffect(() => {}, [])
	return (
		<div className="inline-flex items-center gap-2 text-slate-600">
			<svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24">
				<circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" className="opacity-25" />
				<path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" className="opacity-75" />
			</svg>
			{label && <span className="text-sm">{label}</span>}
		</div>
	)
}

function SmallSpinner() {
	return (
		<svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24">
			<circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" className="opacity-25" />
			<path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" className="opacity-75" />
		</svg>
	)
}