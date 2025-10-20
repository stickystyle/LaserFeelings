# ABOUTME: Three-channel message router with visibility enforcement for IC/OOC/P2C channels.
# ABOUTME: Routes messages to appropriate Redis lists and filters by agent type visibility rules.

import json
from datetime import datetime
from typing import Literal
from uuid import uuid4

from loguru import logger
from redis import Redis

from src.models.messages import (
    ICMessageSummary,
    Message,
    MessageChannel,
    MessageType,
)


class MessageRouter:
    """
    Routes messages across three channels with architectural visibility enforcement.

    Channels:
    - IC (in_character): Characters see full, players get summary
    - OOC (out_of_character): Only players see
    - P2C (player_to_character): Only target character sees
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize message router.

        Args:
            redis_client: Redis connection for message storage
        """
        self.redis = redis_client
        self.message_ttl = 86400  # 24 hours

    def route_message(self, message: Message) -> dict:
        """
        Route message to appropriate channels based on visibility rules.

        Args:
            message: Message to route

        Returns:
            dict with success status and recipients_count

        Raises:
            ValueError: If channel not recognized or recipient invalid
        """
        logger.debug(
            f"Routing message {message.message_id} to channel {message.channel}"
        )

        recipients_count = 0

        if message.channel == MessageChannel.IC:
            # In-character: visible to all characters, summary to players
            recipients_count = self._broadcast_to_characters(message)
            self._create_summary_for_players(message)

        elif message.channel == MessageChannel.OOC:
            # Out-of-character: only players see this
            recipients_count = self._broadcast_to_players(message)

        elif message.channel == MessageChannel.P2C:
            # Player-to-character: private directive
            if not message.to_agents or len(message.to_agents) == 0:
                raise ValueError("P2C messages must specify to_agents")
            recipients_count = self._send_to_character(message)

        else:
            raise ValueError(f"Unknown channel: {message.channel}")

        logger.info(
            f"Routed message {message.message_id} to {recipients_count} recipients"
        )

        return {
            "success": True,
            "recipients_count": recipients_count
        }

    def _broadcast_to_characters(self, message: Message) -> int:
        """
        Add message to IC channel for character visibility.

        Args:
            message: IC message

        Returns:
            Number of recipients (stored once, visible to all)
        """
        key = "channel:ic:messages"
        self.redis.rpush(key, json.dumps(message.model_dump(), default=str))
        self.redis.expire(key, self.message_ttl)

        logger.debug(f"Broadcast IC message to {key}")
        return 1  # Stored once, visible to all characters

    def _create_summary_for_players(self, message: Message) -> None:
        """
        Create summarized version of IC message for player layer.

        Args:
            message: IC message to summarize
        """
        # Extract character_id from message
        character_id = message.from_agent if message.from_agent != "dm" else "dm"

        summary = ICMessageSummary(
            character_id=character_id,
            action_summary=self._summarize_action(message.content),
            outcome_summary=None,  # Filled in by outcome phase
            turn_number=message.turn_number,
            timestamp=message.timestamp
        )

        key = "channel:ic:summaries"
        self.redis.rpush(key, json.dumps(summary.model_dump(), default=str))
        self.redis.expire(key, self.message_ttl)

        logger.debug("Created IC summary for players")

    def _summarize_action(self, content: str) -> str:
        """
        Create high-level summary of action for player visibility.

        For MVP, uses simple truncation. In production, could use LLM.

        Args:
            content: Full action text

        Returns:
            Summarized action (max 100 chars)
        """
        # Simple summarization for MVP
        if len(content) <= 100:
            return content
        return content[:97] + "..."

    def _broadcast_to_players(self, message: Message) -> int:
        """
        Add message to OOC channel for player visibility.

        Args:
            message: OOC message

        Returns:
            Number of recipients (stored once, visible to all players)
        """
        key = "channel:ooc:messages"
        self.redis.rpush(key, json.dumps(message.model_dump(), default=str))
        self.redis.expire(key, self.message_ttl)

        logger.debug(f"Broadcast OOC message to {key}")
        return 1  # Stored once, visible to all players

    def _send_to_character(self, message: Message) -> int:
        """
        Send private directive to specific character.

        Args:
            message: P2C message with to_agents set

        Returns:
            Number of recipients
        """
        if not message.to_agents:
            raise ValueError("P2C message must have to_agents")

        recipients = 0
        for character_id in message.to_agents:
            key = f"channel:p2c:{character_id}"
            self.redis.rpush(key, json.dumps(message.model_dump(), default=str))
            self.redis.expire(key, self.message_ttl)
            # Track active P2C channels using Set for efficient clearing
            self.redis.sadd("active_p2c_channels", key)
            recipients += 1

        logger.debug(f"Sent P2C message to {recipients} characters")
        return recipients

    def get_messages_for_agent(
        self,
        agent_id: str,
        agent_type: Literal["base_persona", "character"],
        limit: int = 50
    ) -> list[Message]:
        """
        Retrieve messages visible to specific agent based on visibility rules.

        Args:
            agent_id: Agent identifier
            agent_type: Type of agent (base_persona or character)
            limit: Maximum messages to retrieve

        Returns:
            List of Message objects sorted by timestamp

        Raises:
            ValueError: If agent_type invalid
        """
        if agent_type not in ["base_persona", "character"]:
            raise ValueError(f"Invalid agent_type: {agent_type}")

        messages: list[Message] = []

        if agent_type == "character":
            # Characters see IC messages
            messages.extend(self._get_ic_messages_for_character(limit))
            # Characters see P2C directives addressed to them
            messages.extend(self._get_p2c_messages_for_character(agent_id, limit))

        elif agent_type == "base_persona":
            # Players see OOC messages
            messages.extend(self.get_ooc_messages_for_player(limit))
            # Players see IC summaries (not full IC messages)
            # (summaries are fetched separately via get_ic_summaries)

        # Sort by timestamp
        messages.sort(key=lambda m: m.timestamp)

        # Apply limit
        return messages[-limit:]

    def _get_ic_messages_for_character(self, limit: int) -> list[Message]:
        """Retrieve IC messages for character visibility"""
        key = "channel:ic:messages"
        raw_messages = self.redis.lrange(key, -limit, -1)

        messages = []
        for raw in raw_messages:
            # Decode bytes if needed (decode_responses=False)
            text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
            data = json.loads(text)
            # Parse datetime strings
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            messages.append(Message(**data))

        return messages

    def _get_p2c_messages_for_character(
        self,
        character_id: str,
        limit: int
    ) -> list[Message]:
        """Retrieve P2C directives for specific character"""
        key = f"channel:p2c:{character_id}"
        raw_messages = self.redis.lrange(key, -limit, -1)

        messages = []
        for raw in raw_messages:
            # Decode bytes if needed (decode_responses=False)
            text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
            data = json.loads(text)
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            messages.append(Message(**data))

        return messages

    def get_ooc_messages_for_player(self, limit: int = 50) -> list[Message]:
        """
        Retrieve OOC messages for player visibility.

        Public API for accessing OOC channel messages.

        Args:
            limit: Maximum number of recent messages to retrieve

        Returns:
            List of Message objects from OOC channel
        """
        key = "channel:ooc:messages"
        raw_messages = self.redis.lrange(key, -limit, -1)

        messages = []
        for raw in raw_messages:
            # Decode bytes if needed (decode_responses=False)
            text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
            data = json.loads(text)
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            messages.append(Message(**data))

        return messages

    def get_ic_summaries_for_player(self, limit: int = 50) -> list[ICMessageSummary]:
        """
        Retrieve IC message summaries for player layer visibility.

        Args:
            limit: Maximum summaries to retrieve

        Returns:
            List of ICMessageSummary objects
        """
        key = "channel:ic:summaries"
        raw_summaries = self.redis.lrange(key, -limit, -1)

        summaries = []
        for raw in raw_summaries:
            # Decode bytes if needed (decode_responses=False)
            text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
            data = json.loads(text)
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            summaries.append(ICMessageSummary(**data))

        return summaries

    def clear_channel(self, channel: MessageChannel) -> None:
        """
        Clear all messages from a specific channel (for testing/reset).

        Args:
            channel: Channel to clear
        """
        if channel == MessageChannel.IC:
            self.redis.delete("channel:ic:messages")
            self.redis.delete("channel:ic:summaries")
        elif channel == MessageChannel.OOC:
            self.redis.delete("channel:ooc:messages")
        elif channel == MessageChannel.P2C:
            # Use Set iteration instead of keys() to avoid O(N) blocking operation
            keys = list(self.redis.sscan_iter("active_p2c_channels"))
            if keys:
                self.redis.delete(*keys)
                self.redis.delete("active_p2c_channels")

        logger.info(f"Cleared channel {channel.value}")

    def add_message(
        self,
        channel: MessageChannel,
        from_agent: str,
        content: str,
        message_type: MessageType,
        phase: str,
        turn_number: int,
        to_agents: list[str] | None = None,
        session_number: int | None = None
    ) -> Message:
        """
        Create and route a new message.

        Convenience method for creating and routing in one call.

        Args:
            channel: Message channel
            from_agent: Sender agent_id or 'dm'
            content: Message content
            message_type: Type of message
            phase: Current game phase
            turn_number: Current turn number
            to_agents: Recipient agent_ids (for P2C)
            session_number: Current session number

        Returns:
            Created Message object
        """
        message = Message(
            message_id=f"msg_{uuid4().hex[:8]}",
            channel=channel,
            from_agent=from_agent,
            to_agents=to_agents,
            content=content,
            timestamp=datetime.now(),
            message_type=message_type,
            phase=phase,
            turn_number=turn_number,
            session_number=session_number
        )

        self.route_message(message)
        return message
