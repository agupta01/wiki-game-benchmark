import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Container,
  FormControl,
  FormLabel,
  Heading,
  Input,
  Text,
  VStack,
  Checkbox,
  useToast,
} from "@chakra-ui/react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../api/client";

export function GameStart() {
  const [startArticle, setStartArticle] = useState("");
  const [endArticle, setEndArticle] = useState("");
  const [notifyWhenDone, setNotifyWhenDone] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();

  const requestNotificationPermission = async () => {
    if (!("Notification" in window)) {
      toast({
        title: "Notifications not supported",
        description: "Your browser does not support notifications.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return false;
    }

    if (Notification.permission === "granted") {
      return true;
    }

    if (Notification.permission === "denied") {
      toast({
        title: "Notifications blocked",
        description: "Please enable notifications in your browser settings.",
        status: "warning",
        duration: 5000,
        isClosable: true,
      });
      return false;
    }

    const permission = await Notification.requestPermission();
    return permission === "granted";
  };

  const handleNotifyCheckboxChange = async (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const checked = e.target.checked;
    if (checked) {
      const granted = await requestNotificationPermission();
      setNotifyWhenDone(granted);
    } else {
      setNotifyWhenDone(false);
    }
  };

  const createGameMutation = useMutation({
    mutationFn: api.createGame,
    onSuccess: (data) => {
      navigate(`/game/${data.id}`, { state: { notifyWhenDone } });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description:
          error.message || "Failed to create game. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!startArticle.trim() || !endArticle.trim()) {
      toast({
        title: "Missing information",
        description: "Please enter both start and end articles.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    createGameMutation.mutate({
      player: "ai",
      startArticle: startArticle.trim(),
      endArticle: endArticle.trim(),
    });
  };

  return (
    <Box bg="gray.50" minH="100vh" py={20}>
      <Container maxW="md" centerContent>
        <VStack spacing={8} w="full">
          <VStack spacing={4} textAlign="center">
            <Heading size="xl" color="gray.800">
              Wikipedia Game AI
            </Heading>
            <Text fontSize="lg" color="gray.600" maxW="lg">
              Watch GPT OSS navigate from one Wikipedia article to another using
              only the links within each page. Enter a starting point and
              destination to begin, and open a new tab and race to beat it!
            </Text>
          </VStack>

          <Box
            as="form"
            onSubmit={handleSubmit}
            w="full"
            bg="white"
            p={8}
            rounded="lg"
            shadow="md"
          >
            <VStack spacing={6}>
              <FormControl>
                <FormLabel>Start Article</FormLabel>
                <Input
                  value={startArticle}
                  onChange={(e) => setStartArticle(e.target.value)}
                  placeholder="e.g., Apple"
                  size="lg"
                />
              </FormControl>

              <FormControl>
                <FormLabel>End Article</FormLabel>
                <Input
                  value={endArticle}
                  onChange={(e) => setEndArticle(e.target.value)}
                  placeholder="e.g., Solar System"
                  size="lg"
                />
              </FormControl>

              <Checkbox
                isChecked={notifyWhenDone}
                onChange={handleNotifyCheckboxChange}
                colorScheme="blue"
              >
                Notify when done
              </Checkbox>

              <Button
                type="submit"
                colorScheme="blue"
                size="lg"
                w="full"
                isLoading={createGameMutation.isPending}
                loadingText="Creating Game..."
              >
                Start Game
              </Button>
            </VStack>
          </Box>
        </VStack>
      </Container>
    </Box>
  );
}
