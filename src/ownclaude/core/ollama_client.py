"""Ollama client wrapper for OwnClaude."""

import json
from typing import Dict, List, Optional, Generator

import ollama
import requests
from loguru import logger

from .config import Config, OllamaLocalConfig, OllamaCloudConfig


class OllamaClient:
    """Wrapper for Ollama API interactions."""

    def __init__(self, config: Config):
        """Initialize Ollama client.

        Args:
            config: Application configuration.
        """
        self.config = config
        self.model_type = config.model_type
        self.conversation_history: List[Dict[str, str]] = []

        if self.model_type == "local":
            self.model_config = config.ollama.local
        else:
            self.model_config = config.ollama.cloud

    def chat(self, message: str, stream: bool = False) -> str:
        """Send a chat message to Ollama.

        Args:
            message: User message to send.
            stream: Whether to stream the response.

        Returns:
            Assistant's response.

        Raises:
            Exception: If the request fails.
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })

        # Limit conversation history
        max_messages = self.config.features.max_context_messages
        if len(self.conversation_history) > max_messages:
            # Keep system message and recent messages
            self.conversation_history = self.conversation_history[-max_messages:]

        try:
            if stream:
                return self._stream_chat()
            else:
                return self._standard_chat()
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise

    def _standard_chat(self) -> str:
        """Standard non-streaming chat.

        Returns:
            Complete response from the model.
        """
        if self.model_type == "local":
            return self._local_chat()
        else:
            return self._cloud_chat()

    def _local_chat(self) -> str:
        """Chat with local Ollama instance.

        Returns:
            Model response.
        """
        try:
            response = ollama.chat(
                model=self.model_config.model,
                messages=self.conversation_history,
                options={
                    "temperature": self.model_config.temperature,
                    "top_p": self.model_config.top_p,
                }
            )

            assistant_message = response['message']['content']

            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return assistant_message

        except Exception as e:
            logger.error(f"Local Ollama error: {e}")
            raise Exception(f"Failed to communicate with local Ollama: {e}")

    def _cloud_chat(self) -> str:
        """Chat with cloud Ollama API.

        Returns:
            Model response.
        """
        cloud_config: OllamaCloudConfig = self.model_config

        headers = {
            "Authorization": f"Bearer {cloud_config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": cloud_config.model,
            "messages": self.conversation_history,
            "temperature": cloud_config.temperature,
            "top_p": cloud_config.top_p,
            # Force non-streaming responses so we can parse a single JSON object
            "stream": False,
        }

        try:
            response = requests.post(
                f"{cloud_config.endpoint}/api/chat",
                headers=headers,
                json=payload,
                timeout=cloud_config.timeout
            )
            response.raise_for_status()

            try:
                result = response.json()
            except json.JSONDecodeError:
                # Some endpoints may return newline-delimited JSON chunks; parse the first one
                first_line = response.text.strip().splitlines()[0]
                result = json.loads(first_line)

            assistant_message = result['message']['content']

            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return assistant_message

        except requests.exceptions.RequestException as e:
            logger.error(f"Cloud Ollama error: {e}")
            raise Exception(f"Failed to communicate with cloud Ollama: {e}")

    def _stream_chat(self) -> Generator[str, None, None]:
        """Stream chat responses.

        Yields:
            Chunks of the response.
        """
        if self.model_type == "local":
            stream = ollama.chat(
                model=self.model_config.model,
                messages=self.conversation_history,
                stream=True,
                options={
                    "temperature": self.model_config.temperature,
                    "top_p": self.model_config.top_p,
                }
            )

            full_response = ""
            for chunk in stream:
                content = chunk['message']['content']
                full_response += content
                yield content

            # Add complete response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": full_response
            })
        else:
            # Cloud streaming would go here
            # For now, fall back to standard chat
            yield self._cloud_chat()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def set_system_prompt(self, system_prompt: str) -> None:
        """Set a system prompt for the conversation.

        Args:
            system_prompt: System instructions for the model.
        """
        # Remove existing system message if present
        self.conversation_history = [
            msg for msg in self.conversation_history
            if msg.get("role") != "system"
        ]

        # Add new system message at the beginning
        self.conversation_history.insert(0, {
            "role": "system",
            "content": system_prompt
        })

        logger.info("System prompt set")

    def check_connection(self) -> bool:
        """Check if connection to Ollama is working.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            if self.model_type == "local":
                # Try to list models to check connection
                ollama.list()
                return True
            else:
                # Try to ping cloud endpoint
                cloud_config: OllamaCloudConfig = self.model_config
                headers = {
                    "Authorization": f"Bearer {cloud_config.api_key}",
                }
                response = requests.get(
                    f"{cloud_config.endpoint}/api/tags",
                    headers=headers,
                    timeout=5
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False

    def get_available_models(self) -> List[str]:
        """Get list of available models.

        Returns:
            List of available model names.
        """
        try:
            if self.model_type == "local":
                models = ollama.list()
                return [model['name'] for model in models.get('models', [])]
            else:
                # Would query cloud API for available models
                return [self.model_config.model]
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []
