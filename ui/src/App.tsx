import { Routes, Route } from 'react-router-dom'
import { GameStart } from './components/GameStart'
import { GamePlay } from './components/GamePlay'

function App() {
  return (
    <Routes>
      <Route path="/" element={<GameStart />} />
      <Route path="/game/:gameId" element={<GamePlay />} />
    </Routes>
  )
}

export default App
