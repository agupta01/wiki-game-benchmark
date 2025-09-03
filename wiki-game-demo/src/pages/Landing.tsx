import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createGame } from '../lib/api'

export default function Landing() {
	const navigate = useNavigate()
	const [startArticle, setStartArticle] = useState('Python (programming language)')
	const [endArticle, setEndArticle] = useState('Artificial intelligence')
	const [isSubmitting, setIsSubmitting] = useState(false)
	const [error, setError] = useState<string | null>(null)

	async function onSubmit(e: FormEvent) {
		e.preventDefault()
		setError(null)
		setIsSubmitting(true)
		try {
			const data = await createGame({ startArticle, endArticle })
			navigate(`/game/${data.id}`)
		} catch (err) {
			setError((err as Error).message)
		} finally {
			setIsSubmitting(false)
		}
	}

	return (
		<div className="min-h-screen bg-[#faf9f7] text-slate-900 flex items-center">
			<div className="container max-w-2xl mx-auto p-6">
				<div className="text-center space-y-4">
					<h1 className="text-4xl font-bold tracking-tight">Wikipedia Game AI</h1>
					<p className="text-slate-600">Watch an AI play the Wikipedia Game from one page to another using only in-article links.</p>
				</div>
				<form onSubmit={onSubmit} className="mt-10 space-y-6">
					<div className="grid grid-cols-1 gap-6">
						<label className="block">
							<span className="block text-sm font-medium text-slate-700">Start article</span>
							<input
								type="text"
								value={startArticle}
								onChange={(e) => setStartArticle(e.target.value)}
								className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
								placeholder="e.g., Alan Turing"
								required
							/>
						</label>
						<label className="block">
							<span className="block text-sm font-medium text-slate-700">End article</span>
							<input
								type="text"
								value={endArticle}
								onChange={(e) => setEndArticle(e.target.value)}
								className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
								placeholder="e.g., Space exploration"
								required
							/>
						</label>
					</div>

					<button
						type="submit"
						disabled={isSubmitting}
						className="inline-flex items-center justify-center rounded-md bg-slate-900 px-5 py-2.5 text-white font-medium shadow hover:bg-slate-800 disabled:opacity-60 disabled:cursor-not-allowed w-full"
					>
						{isSubmitting ? (
							<span className="inline-flex items-center gap-2">
								<svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
									<circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" className="opacity-25" />
									<path d="M22 12a10 10 0 0 1-10 10" stroke="currentColor" strokeWidth="4" className="opacity-75" />
								</svg>
								Starting game…
							</span>
						) : (
							"Start game"
						)}
					</button>

					{error && (
						<p className="text-sm text-red-600 text-center">{error}</p>
					)}
				</form>
			</div>
		</div>
	)
}