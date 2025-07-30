#!/bin/bash

# invoke-server.sh - Test script for Ollama's native OpenAI-compatible API
# Usage: ./invoke-server.sh

SERVER_URL="http://localhost:11434"
MODEL="qwen3:0.6b"

echo "Testing Ollama's native API at $SERVER_URL"
echo "==========================================="

# Check if Ollama is running
if ! curl -s "$SERVER_URL/api/tags" > /dev/null; then
    echo "ERROR: Ollama is not running. Please start it with: ollama serve"
    exit 1
fi

# Test 1: List available models
echo "1. Testing /v1/models endpoint..."
curl -s "$SERVER_URL/v1/models" | jq '.'
echo -e "\n"

# Test 2: Simple chat completion
echo "2. Testing /v1/chat/completions endpoint..."
curl -s -X POST "$SERVER_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'$MODEL'",
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }' | jq '.'
echo -e "\n"

# Test 3: Streaming response
echo "3. Testing streaming response..."
curl -s -X POST "$SERVER_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'$MODEL'",
    "messages": [
      {"role": "user", "content": "Tell me a short joke"}
    ],
    "temperature": 0.8,
    "max_tokens": 50,
    "stream": true
  }'
echo -e "\n\n"

echo "Testing complete!"
