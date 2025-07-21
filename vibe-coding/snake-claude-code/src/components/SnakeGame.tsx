import { useState, useEffect, useCallback } from 'react'

const BOARD_SIZE = 20
const INITIAL_SNAKE = [{ x: 10, y: 10 }]
const INITIAL_FOOD = { x: 15, y: 15 }
const GAME_SPEED = 100

type Position = { x: number; y: number }
type Direction = 'UP' | 'DOWN' | 'LEFT' | 'RIGHT'

function SnakeGame() {
  const [snake, setSnake] = useState<Position[]>(INITIAL_SNAKE)
  const [food, setFood] = useState<Position>(INITIAL_FOOD)
  const [direction, setDirection] = useState<Direction>('RIGHT')
  const [gameRunning, setGameRunning] = useState(false)
  const [gameOver, setGameOver] = useState(false)
  const [score, setScore] = useState(0)

  const generateFood = useCallback((): Position => {
    let newFood: Position
    do {
      newFood = {
        x: Math.floor(Math.random() * BOARD_SIZE),
        y: Math.floor(Math.random() * BOARD_SIZE)
      }
    } while (snake.some(segment => segment.x === newFood.x && segment.y === newFood.y))
    return newFood
  }, [snake])

  const checkWallCollision = (head: Position): boolean => {
    return head.x < 0 || head.x >= BOARD_SIZE || head.y < 0 || head.y >= BOARD_SIZE
  }

  const checkSelfCollision = (head: Position): boolean => {
    return snake.some(segment => segment.x === head.x && segment.y === head.y)
  }

  const moveSnake = useCallback(() => {
    if (!gameRunning || gameOver) return

    setSnake(currentSnake => {
      const newSnake = [...currentSnake]
      const head = { ...newSnake[0] }

      switch (direction) {
        case 'UP':
          head.y -= 1
          break
        case 'DOWN':
          head.y += 1
          break
        case 'LEFT':
          head.x -= 1
          break
        case 'RIGHT':
          head.x += 1
          break
      }

      if (checkWallCollision(head) || checkSelfCollision(head)) {
        setGameOver(true)
        setGameRunning(false)
        return currentSnake
      }

      newSnake.unshift(head)

      if (head.x === food.x && head.y === food.y) {
        setScore(prev => prev + 10)
        setFood(generateFood())
      } else {
        newSnake.pop()
      }

      return newSnake
    })
  }, [direction, food, gameRunning, gameOver, generateFood])

  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (!gameRunning) return

      switch (e.key) {
        case 'ArrowUp':
        case 'w':
        case 'W':
          e.preventDefault()
          setDirection(prev => prev !== 'DOWN' ? 'UP' : prev)
          break
        case 'ArrowDown':
        case 's':
        case 'S':
          e.preventDefault()
          setDirection(prev => prev !== 'UP' ? 'DOWN' : prev)
          break
        case 'ArrowLeft':
        case 'a':
        case 'A':
          e.preventDefault()
          setDirection(prev => prev !== 'RIGHT' ? 'LEFT' : prev)
          break
        case 'ArrowRight':
        case 'd':
        case 'D':
          e.preventDefault()
          setDirection(prev => prev !== 'LEFT' ? 'RIGHT' : prev)
          break
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [gameRunning])

  useEffect(() => {
    if (gameRunning && !gameOver) {
      const gameInterval = setInterval(moveSnake, GAME_SPEED)
      return () => clearInterval(gameInterval)
    }
  }, [moveSnake, gameRunning, gameOver])

  const startGame = () => {
    setSnake(INITIAL_SNAKE)
    setFood(INITIAL_FOOD)
    setDirection('RIGHT')
    setGameOver(false)
    setScore(0)
    setGameRunning(true)
  }

  const resetGame = () => {
    setGameRunning(false)
    setGameOver(false)
    setSnake(INITIAL_SNAKE)
    setFood(INITIAL_FOOD)
    setDirection('RIGHT')
    setScore(0)
  }

  return (
    <div className="text-center">
      <h1 className="text-4xl font-bold text-white mb-4">Snake Game</h1>
      
      <div className="mb-4">
        <span className="text-white text-xl">Score: {score}</span>
      </div>

      <div 
        className="grid gap-0 border-2 border-gray-600 mx-auto mb-4"
        style={{
          gridTemplateColumns: `repeat(${BOARD_SIZE}, 1fr)`,
          width: '400px',
          height: '400px'
        }}
      >
        {Array.from({ length: BOARD_SIZE * BOARD_SIZE }).map((_, index) => {
          const x = index % BOARD_SIZE
          const y = Math.floor(index / BOARD_SIZE)
          
          const isSnake = snake.some(segment => segment.x === x && segment.y === y)
          const isFood = food.x === x && food.y === y
          const isHead = snake.length > 0 && snake[0].x === x && snake[0].y === y

          let cellClass = 'w-full h-full border border-gray-800'
          
          if (isSnake) {
            cellClass += isHead ? ' bg-green-400' : ' bg-green-600'
          } else if (isFood) {
            cellClass += ' bg-red-500'
          } else {
            cellClass += ' bg-gray-800'
          }

          return <div key={index} className={cellClass} />
        })}
      </div>

      <div className="space-x-4">
        {!gameRunning && !gameOver && (
          <button
            onClick={startGame}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Start Game
          </button>
        )}
        
        {gameOver && (
          <>
            <div className="text-red-500 text-xl mb-4">Game Over!</div>
            <button
              onClick={startGame}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors mr-2"
            >
              Play Again
            </button>
          </>
        )}
        
        {gameRunning && (
          <button
            onClick={resetGame}
            className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      <div className="mt-4 text-gray-400 text-sm">
        Use arrow keys or WASD to control the snake
      </div>
    </div>
  )
}

export default SnakeGame
