import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useRef } from 'react'
import {
  Box,
  Container,
  Flex,
  Heading,
  Text,
  VStack,
  HStack,
  Badge,
  Spinner,
  useBreakpointValue,
  Button,
} from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function GamePlay() {
  const { gameId } = useParams<{ gameId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const isMobile = useBreakpointValue({ base: true, lg: false })
  const hasNotified = useRef(false)
  
  const notifyWhenDone = location.state?.notifyWhenDone || false

  if (!gameId) {
    navigate('/')
    return null
  }

  const { data: gameState, isLoading, error } = useQuery({
    queryKey: ['game', gameId],
    queryFn: () => api.getGameState(gameId),
    refetchInterval: (query) => {
      return query.state.data?.isComplete ? false : 10000
    },
    refetchIntervalInBackground: true,
  })

  // Send notification when game is complete
  useEffect(() => {
    if (gameState?.isComplete && notifyWhenDone && !hasNotified.current && 'Notification' in window && Notification.permission === 'granted') {
      hasNotified.current = true
      new Notification('Wikipedia Game Complete!', {
        body: `AI successfully navigated from "${gameState.startArticle}" to "${gameState.endArticle}" in ${gameState.moves.length} moves!`,
        icon: '/favicon.ico',
      })
    }
  }, [gameState?.isComplete, notifyWhenDone, gameState?.startArticle, gameState?.endArticle, gameState?.moves.length])

  const getWikipediaUrl = (article: string) => {
    return `https://en.wikipedia.org/wiki/${encodeURIComponent(article.replace(/ /g, '_'))}`
  }

  if (isLoading) {
    return (
      <Box bg="gray.50" minH="100vh" display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.500" />
          <Text fontSize="lg" color="gray.600">Loading game...</Text>
        </VStack>
      </Box>
    )
  }

  if (error || !gameState) {
    return (
      <Box bg="gray.50" minH="100vh" display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={4}>
          <Text fontSize="lg" color="red.500">Failed to load game state</Text>
          <Button onClick={() => navigate('/')}>Back to Start</Button>
        </VStack>
      </Box>
    )
  }

  const Timeline = () => (
    <VStack spacing={4} align="stretch" w="full">
      <VStack spacing={2} align="start">
        <Heading size="md" color="gray.800">Game Progress</Heading>
        <HStack>
          <Badge colorScheme="blue" variant="subtle">
            {gameState.moves.length} moves
          </Badge>
          {gameState.isComplete && (
            <Badge colorScheme="green" variant="subtle">
              <HStack spacing={1}>
                <Box w={3} h={3} bg="green.500" rounded="full" />
                <Text>Complete!</Text>
              </HStack>
            </Badge>
          )}
        </HStack>
      </VStack>

      <Box bg="white" rounded="lg" shadow="sm" p={4}>
        <VStack spacing={3} align="stretch">
          <HStack>
            <Box
              w={3}
              h={3}
              bg="green.500"
              rounded="full"
            />
            <Text fontWeight="semibold" color="green.600">
              Start: {gameState.startArticle}
            </Text>
          </HStack>

          {gameState.moves.map((move, index) => (
            <Box key={index}>
              <HStack spacing={2} pl={6}>
                <Box w={0} h={0} borderLeft="6px solid transparent" borderRight="6px solid transparent" borderTop="8px solid" borderTopColor="gray.400" />
                <VStack align="start" spacing={0}>
                  <Text fontWeight="medium">{move.article}</Text>
                  <Text fontSize="sm" color="gray.500">
                    {new Date(move.timestamp).toLocaleTimeString()}
                  </Text>
                </VStack>
              </HStack>
            </Box>
          ))}

          <HStack>
            <Box
              w={3}
              h={3}
              bg={gameState.isComplete ? "green.500" : "orange.500"}
              rounded="full"
            />
            <Text fontWeight="semibold" color={gameState.isComplete ? "green.600" : "orange.600"}>
              Target: {gameState.endArticle}
            </Text>
          </HStack>
        </VStack>
      </Box>

      {!gameState.isComplete && (
        <Box bg="blue.50" p={4} rounded="lg" border="1px" borderColor="blue.200">
          <HStack spacing={2}>
            <Spinner size="sm" color="blue.500" />
            <Text color="blue.700" fontWeight="medium">
              AI is thinking...
            </Text>
          </HStack>
          <Text fontSize="sm" color="blue.600" mt={1}>
            Currently on: {gameState.currentArticle}
          </Text>
        </Box>
      )}

      <Button variant="outline" onClick={() => navigate('/')} mt={4}>
        Start New Game
      </Button>
    </VStack>
  )

  const WikipediaFrame = () => (
    <Box w="full" h={{ base: "400px", lg: "600px" }}>
      <Box
        as="iframe"
        src={getWikipediaUrl(gameState.currentArticle)}
        w="full"
        h="full"
        border="none"
        rounded="lg"
        shadow="md"
        bg="white"
      />
    </Box>
  )

  return (
    <Box bg="gray.50" minH="100vh" py={6}>
      <Container maxW="7xl">
        {isMobile ? (
          <VStack spacing={6}>
            <Timeline />
            <WikipediaFrame />
          </VStack>
        ) : (
          <Flex gap={6} h="calc(100vh - 3rem)">
            <Box w="350px" flexShrink={0}>
              <Timeline />
            </Box>
            <Box flex={1}>
              <WikipediaFrame />
            </Box>
          </Flex>
        )}
      </Container>
    </Box>
  )
}