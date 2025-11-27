"""Ollama client wrapper for PBOS AI."""

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Dict, List, Optional, Generator, Tuple, Any

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

        # Model routing enabled?
        self.routing_enabled = getattr(config, "enable_model_routing", False)
        self.routing_config = getattr(config, "model_routing", None)

        # Important keywords for smart trimming
        self.important_keywords = ["created", "error", "warning", "file", "installed", "configured"]

        # Response cache (simple in-memory cache)
        self.response_cache: Dict[str, Tuple[str, float]] = {}  # hash -> (response, timestamp)
        self.cache_ttl_seconds = 3600  # 1 hour
        self.cache_max_size = 100
        self.cache_enabled = getattr(config.features, "enable_response_cache", False)

    def switch_mode(self, model_type: str) -> None:
        """Switch between local and cloud modes without re-instantiating.

        Args:
            model_type: Either "local" or "cloud".
        """
        if model_type not in {"local", "cloud"}:
            raise ValueError("model_type must be 'local' or 'cloud'")

        self.model_type = model_type
        self.model_config = self.config.ollama.local if model_type == "local" else self.config.ollama.cloud
        self.clear_history()

    def set_default_model(self, model_name: str) -> None:
        """Update the default model for the active mode."""
        self.model_config.model = model_name
        if self.model_type == "local":
            self.config.ollama.local.model = model_name
        else:
            self.config.ollama.cloud.model = model_name

    def _select_model(self, user_message: str) -> str:
        """Select the best model for the given message.

        Args:
            user_message: The user's input message.

        Returns:
            The model name to use.
        """
        # If routing is disabled, use default model
        if not self.routing_enabled or not self.routing_config:
            return self.model_config.model

        # Get default model from routing config
        default_model = self.routing_config.get("default_model", self.model_config.model)

        # Check message against triggers
        message_lower = user_message.lower()
        models_dict = self.routing_config.get("models", {})

        # Check each model type's triggers
        for model_type, model_info in models_dict.items():
            triggers = model_info.get("triggers", [])
            for trigger in triggers:
                if trigger.lower() in message_lower:
                    selected = model_info.get("model", default_model)
                    logger.debug(f"Model routing: '{trigger}' matched -> {selected}")
                    return selected

        # No triggers matched, use default
        logger.debug(f"Model routing: No triggers matched -> {default_model}")
        return default_model

    def chat(self, message: str, stream: bool = False, override_model: Optional[str] = None) -> str:
        """Send a chat message to Ollama.

        Args:
            message: User message to send.
            stream: Whether to stream the response.
            override_model: Optional model to use instead of routing selection.

        Returns:
            Assistant's response.

        Raises:
            Exception: If the request fails.
        """
        # Compact history to avoid long prompts / truncation
        self._shrink_history(max_messages=6, max_chars=2000)

        # Select model based on message content (unless overridden)
        selected_model = override_model or self._select_model(message)

        # Check cache for non-streaming requests
        if not stream and self.cache_enabled:
            cache_key = self._get_cache_key(message, selected_model)
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for message: {message[:50]}...")
                # Add to history
                self._add_to_history("user", message)
                self._add_to_history("assistant", cached_response)
                return cached_response

        # Add user message to history with smart trimming
        self._add_to_history("user", message)

        try:
            if stream:
                response = self._stream_chat(selected_model)
            else:
                response = self._standard_chat(selected_model)

            # Cache the response for non-streaming requests
            if not stream and self.cache_enabled:
                self._add_to_cache(cache_key, response)

            return response
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise

    def _standard_chat(self, model: str) -> str:
        """Standard non-streaming chat.

        Args:
            model: Model name to use.

        Returns:
            Complete response from the model.
        """
        if self.model_type == "local":
            return self._local_chat(model)
        else:
            return self._cloud_chat()

    def _local_chat(self, model: str) -> str:
        """Chat with local Ollama instance.

        Args:
            model: Model name to use.

        Returns:
            Model response.
        """
        try:
            response = ollama.chat(
                model=model,
                messages=self.conversation_history,
                options={
                    "temperature": self.model_config.temperature,
                    "top_p": self.model_config.top_p,
                }
            )

            assistant_message = response['message']['content']

            # Add assistant response to history with smart trimming
            self._add_to_history("assistant", assistant_message)

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

            # Add assistant response to history with smart trimming
            self._add_to_history("assistant", assistant_message)

            return assistant_message

        except requests.exceptions.RequestException as e:
            logger.error(f"Cloud Ollama error: {e}")
            raise Exception(f"Failed to communicate with cloud Ollama: {e}")

    def _stream_chat(self, model: str) -> Generator[str, None, None]:
        """Stream chat responses.

        Args:
            model: Model name to use.

        Yields:
            Chunks of the response.
        """
        # Keep stall timeout bounded so we bail out instead of hanging forever
        configured_timeout = getattr(self.model_config, "timeout", 60) or 60
        stall_timeout = min(configured_timeout, 90)

        if self.model_type == "local":
            stream = ollama.chat(
                model=model,
                messages=self.conversation_history,
                stream=True,
                options={
                    "temperature": self.model_config.temperature,
                    "top_p": self.model_config.top_p,
                }
            )

            full_response = ""
            with ThreadPoolExecutor(max_workers=1) as pool:
                iterator = iter(stream)
                while True:
                    future = pool.submit(next, iterator, None)
                    try:
                        chunk = future.result(timeout=stall_timeout)
                    except FuturesTimeout:
                        future.cancel()
                        raise TimeoutError(
                            "No tokens received from local model within timeout window"
                        )

                    if chunk is None:
                        break

                    content = chunk['message']['content']
                    full_response += content
                    yield content

            # Add complete response to history with smart trimming
            self._add_to_history("assistant", full_response)
        else:
            yield from self._stream_cloud_chat(stall_timeout)

    def _stream_cloud_chat(self, stall_timeout: Optional[int] = None) -> Generator[str, None, None]:
        """Stream chat responses from Ollama Cloud when available."""
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
            "stream": True,
        }

        full_response = ""
        last_chunk_time = time.time()
        try:
            with requests.post(
                f"{cloud_config.endpoint}/api/chat",
                headers=headers,
                json=payload,
                timeout=cloud_config.timeout,
                stream=True,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue

                    content = data.get("message", {}).get("content") or data.get("content")
                    if content:
                        full_response += content
                        last_chunk_time = time.time()
                        yield content

                    if stall_timeout and (time.time() - last_chunk_time) > stall_timeout:
                        raise TimeoutError(
                            "No tokens received from cloud model within timeout window"
                        )

        except requests.RequestException as exc:
            logger.error(f"Cloud streaming failed: {exc}")
            fallback = self._cloud_chat()
            full_response += fallback
            yield fallback

        if full_response:
            self._add_to_history("assistant", full_response)

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

    def _add_to_history(self, role: str, content: str) -> None:
        """Add message to conversation history with smart context management.

        Args:
            role: Message role (user, assistant, system).
            content: Message content.
        """
        from datetime import datetime

        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        max_messages = self.config.features.max_context_messages

        # Smart trimming: Keep recent messages + important context
        if len(self.conversation_history) > max_messages:
            # Always keep the most recent messages
            recent = self.conversation_history[-max_messages:]

            # Keep important messages from earlier (file creations, errors, etc.)
            important_old = [
                msg for msg in self.conversation_history[:-max_messages]
                if any(keyword in msg["content"].lower() for keyword in self.important_keywords)
            ]

            # Combine: up to 3 important old messages + all recent messages
            self.conversation_history = important_old[-3:] + recent

    def _shrink_history(self, max_messages: int = 6, max_chars: int = 2000) -> None:
        """Trim conversation history aggressively to avoid prompt truncation and repeated answers."""
        # Limit by message count first
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

        # Limit by total character length
        total_chars = sum(len(msg.get("content", "")) for msg in self.conversation_history)
        if total_chars > max_chars:
            trimmed: list[Dict[str, Any]] = []
            running = 0
            for msg in reversed(self.conversation_history):
                content_len = len(msg.get("content", ""))
                if running + content_len > max_chars:
                    break
                trimmed.append(msg)
                running += content_len
            self.conversation_history = list(reversed(trimmed))

    def get_display_history(self) -> List[Dict[str, Any]]:
        """Get conversation history for display purposes.

        Returns:
            Copy of conversation history.
        """
        return self.conversation_history.copy()

    def get_history_count(self) -> int:
        """Get the number of messages in history.

        Returns:
            Count of messages in history.
        """
        return len(self.conversation_history)

    def _get_cache_key(self, message: str, model: str) -> str:
        """Generate a cache key from message and model.

        Args:
            message: The message to cache.
            model: The model used.

        Returns:
            Hash string for cache key.
        """
        # Include recent context in cache key
        recent_context = self.conversation_history[-3:] if len(self.conversation_history) >= 3 else []
        context_str = json.dumps([{"role": m["role"], "content": m["content"]} for m in recent_context])
        key_string = f"{model}:{message}:{context_str}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get response from cache if available and fresh.

        Args:
            cache_key: Cache key to look up.

        Returns:
            Cached response or None.
        """
        if cache_key not in self.response_cache:
            return None

        response, timestamp = self.response_cache[cache_key]

        # Check if cache entry is still fresh
        if time.time() - timestamp > self.cache_ttl_seconds:
            del self.response_cache[cache_key]
            return None

        return response

    def _add_to_cache(self, cache_key: str, response: str) -> None:
        """Add response to cache.

        Args:
            cache_key: Cache key.
            response: Response to cache.
        """
        # Check cache size limit
        if len(self.response_cache) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = min(self.response_cache.items(), key=lambda x: x[1][1])[0]
            del self.response_cache[oldest_key]

        self.response_cache[cache_key] = (response, time.time())
        logger.debug(f"Cached response (size: {len(self.response_cache)})")

    def clear_response_cache(self) -> None:
        """Clear the response cache."""
        self.response_cache.clear()
        logger.info("Response cache cleared")
