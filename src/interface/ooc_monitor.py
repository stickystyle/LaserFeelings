# ABOUTME: Standalone OOC (Out-of-Character) message monitor for observing AI player strategy.
# ABOUTME: Supports real-time console display and JSONL file logging with duplicate filtering.

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

from loguru import logger
from redis import Redis
from redis.exceptions import ConnectionError, RedisError

from src.config.settings import get_settings
from src.models.messages import Message


class OOCMonitor:
    """
    Monitor OOC (Out-of-Character) strategic discussions between AI players.

    Polls Redis channel:ooc:messages and displays new messages in real-time.
    Supports console (formatted) and file (JSONL) output modes.
    """

    def __init__(
        self,
        output_mode: Literal["console", "file"] = "console",
        log_path: str | None = None,
        redis_url: str | None = None,
        poll_interval: float = 0.5
    ):
        """
        Initialize OOC monitor.

        Args:
            output_mode: Display mode - "console" or "file"
            log_path: Path for JSONL output (required if output_mode="file")
            redis_url: Redis connection URL (uses settings if None)
            poll_interval: Polling interval in seconds
        """
        self.output_mode = output_mode
        self.log_path = log_path
        self.poll_interval = poll_interval

        # Track seen messages to avoid duplicates
        self._seen_message_ids: set[str] = set()

        # File handle for JSONL output (opened once, closed on cleanup)
        self._log_file_handle = None

        # Initialize Redis connection
        if redis_url is None:
            settings = get_settings()
            redis_url = settings.redis_url

        try:
            self.redis = Redis.from_url(redis_url, decode_responses=False)
            self.redis.ping()
            logger.debug(f"Connected to Redis at {redis_url}")
        except ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

        # Validate output mode
        if output_mode == "file" and not log_path:
            raise ValueError("log_path is required when output_mode='file'")

        # Create log directory and open file handle for file mode
        if output_mode == "file" and log_path:
            log_file = Path(log_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            # Open file once with line buffering for better performance
            self._log_file_handle = open(log_path, "a", buffering=1)

    def format_message_console(self, message: Message, agent_name: str | None = None) -> str:
        """
        Format OOC message for console display.

        Args:
            message: Message to format
            agent_name: Human-readable agent name (falls back to agent_id)

        Returns:
            Formatted string like: "[2025-10-19 14:32:15] Alex (Player): message content"
        """
        timestamp_str = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        display_name = agent_name or message.from_agent

        return f"[{timestamp_str}] {display_name} (Player): \"{message.content}\""

    def format_message_jsonl(self, message: Message, agent_name: str | None = None) -> str:
        """
        Format OOC message as JSONL (JSON Lines).

        Args:
            message: Message to format
            agent_name: Human-readable agent name (falls back to agent_id)

        Returns:
            JSON string (single line, no newline)
        """
        display_name = agent_name or message.from_agent

        data = {
            "timestamp": message.timestamp.isoformat(),
            "agent_id": message.from_agent,
            "agent_name": display_name,
            "content": message.content,
            "turn_number": message.turn_number,
            "session_number": message.session_number
        }

        return json.dumps(data)

    def is_new_message(self, message: Message) -> bool:
        """
        Check if message has been seen before.

        Args:
            message: Message to check

        Returns:
            True if message is new, False if duplicate
        """
        if message.message_id in self._seen_message_ids:
            return False

        self._seen_message_ids.add(message.message_id)
        return True

    def fetch_ooc_messages(self) -> list[Message]:
        """
        Fetch all OOC messages from Redis.

        Returns:
            List of Message objects from channel:ooc:messages
        """
        if not self.redis:
            logger.error("Redis connection not available")
            return []

        try:
            raw_messages = self.redis.lrange("channel:ooc:messages", 0, -1)

            messages = []
            for raw in raw_messages:
                try:
                    # Decode bytes if needed
                    text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                    data = json.loads(text)

                    # Parse datetime
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])

                    messages.append(Message(**data))
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse message: {e}")
                    continue

            return messages

        except RedisError as e:
            logger.error(f"Redis error fetching messages: {e}")
            return []

    def write_message(self, message: Message, agent_name: str | None = None) -> None:
        """
        Write message to output (console or file).

        Args:
            message: Message to write
            agent_name: Human-readable agent name
        """
        if self.output_mode == "console":
            formatted = self.format_message_console(message, agent_name)
            print(formatted)
        elif self.output_mode == "file" and self._log_file_handle:
            jsonl_line = self.format_message_jsonl(message, agent_name)
            self._log_file_handle.write(jsonl_line + "\n")

    def close(self) -> None:
        """Clean up resources (close file handle if open)"""
        if self._log_file_handle:
            self._log_file_handle.close()
            self._log_file_handle = None

    def run(self) -> None:
        """
        Run continuous monitoring loop.

        Polls Redis every poll_interval seconds and displays new messages.
        Exits gracefully on Ctrl+C.
        """
        if not self.redis:
            print("Error: Could not connect to Redis. Make sure Redis is running.")
            print("Start Redis with: docker-compose up -d")
            sys.exit(1)

        # Display header
        print("=== OOC Strategic Layer Monitor ===")
        print("Monitoring OOC channel (Ctrl+C to stop)...")
        print()

        try:
            while True:
                messages = self.fetch_ooc_messages()

                for message in messages:
                    if self.is_new_message(message):
                        # TODO: Map agent_id to agent_name from config
                        # For now, use agent_id
                        self.write_message(message)

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
            if self.output_mode == "file":
                print(f"Log saved to: {self.log_path}")
        finally:
            # Ensure file handle is closed on exit
            self.close()


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Monitor OOC (Out-of-Character) strategic discussions between AI players"
    )

    parser.add_argument(
        "--output",
        choices=["console", "file"],
        default="console",
        help="Output mode: console (formatted) or file (JSONL)"
    )

    parser.add_argument(
        "--log-path",
        type=str,
        default="logs/ooc_chat.jsonl",
        help="Path for JSONL log file (used when output=file)"
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        help="Polling interval in seconds (default: 0.5)"
    )

    return parser.parse_args()


def main():
    """Entry point for OOC monitor CLI"""
    args = parse_args()

    # Initialize monitor
    monitor = OOCMonitor(
        output_mode=args.output,
        log_path=args.log_path if args.output == "file" else None,
        poll_interval=args.poll_interval
    )

    # Run monitoring loop
    monitor.run()


if __name__ == "__main__":
    main()
