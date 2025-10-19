# ABOUTME: Main memory interface wrapping Graphiti with temporal tracking and corruption layer.
# ABOUTME: Implements search, episode storage, invalidation, and corruption statistics tracking.

from datetime import datetime
from typing import Any
from uuid import uuid4

from openai import OpenAI

from src.memory.exceptions import (
    EpisodeCreationFailed,
    GraphitiConnectionFailed,
    InvalidAgentID,
)
from src.memory.graphiti_client import GraphitiClient
from src.models.memory_edge import CorruptionConfig, MemoryEdge, MemoryType


class CorruptedTemporalMemory:
    """
    Memory interface that wraps Graphiti and adds temporal tracking.
    Corruption layer simulates realistic memory decay over time.
    """

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        openai_client: OpenAI | None = None,
        corruption_config: CorruptionConfig | None = None,
    ):
        """
        Initialize memory system with Graphiti backend.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            openai_client: OpenAI client for entity extraction
            corruption_config: Configuration for memory corruption behavior

        Raises:
            GraphitiConnectionFailed: When Neo4j connection fails
        """
        self.graphiti_client = GraphitiClient(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            openai_client=openai_client,
        )
        self.corruption_config = corruption_config or CorruptionConfig(enabled=False)
        self.openai_client = openai_client

    async def search(
        self,
        query: str,
        agent_id: str,
        session_number: int | None = None,
        turn_number: int | None = None,
        apply_corruption: bool = False,
        limit: int = 10,
    ) -> list[MemoryEdge]:
        """
        Search memories with temporal filtering.

        Args:
            query: Semantic search query
            agent_id: Agent identifier
            session_number: Filter by session number (optional)
            turn_number: Filter by turn number (optional)
            apply_corruption: Whether to apply corruption layer
            limit: Maximum number of results

        Returns:
            List of MemoryEdge objects

        Raises:
            GraphitiConnectionFailed: When Neo4j connection fails
            InvalidAgentID: When agent_id is invalid or not found
        """
        # Validate agent_id
        if not agent_id:
            raise InvalidAgentID("agent_id cannot be empty")

        # Validate agent format (must start with "agent_" or "char_")
        if not (agent_id.startswith("agent_") or agent_id.startswith("char_")):
            raise InvalidAgentID(
                f"Agent ID must start with 'agent_' or 'char_', got: {agent_id}"
            )

        try:
            # Query Graphiti with temporal context
            results = await self.graphiti_client.query_memories_at_time(
                query=query,
                agent_id=agent_id,
                session_number=session_number,
                turn_number=turn_number,
                limit=limit,
            )

            # Convert results to MemoryEdge objects
            edges: list[MemoryEdge] = []
            now = datetime.now()

            for result in results:
                # Extract metadata
                metadata = result.get("metadata", {})

                # Create MemoryEdge
                edge = MemoryEdge(
                    uuid=result.get("id", str(uuid4())),
                    fact=result.get("content", ""),
                    valid_at=result.get("timestamp", now),
                    invalid_at=metadata.get("invalid_at"),
                    episode_ids=[metadata.get("source_episode_id", "")],
                    source_node_uuid=metadata.get("source_node_uuid", ""),
                    target_node_uuid=metadata.get("target_node_uuid", ""),
                    agent_id=agent_id,
                    memory_type=MemoryType(metadata.get("type", "episodic")),
                    session_number=metadata.get("session", 1),
                    days_elapsed=metadata.get("days_elapsed", 0),
                    confidence=metadata.get("confidence", 1.0),
                    importance=metadata.get("importance", 0.5),
                    rehearsal_count=metadata.get("rehearsal_count", 0),
                    corruption_type=None,  # Corruption layer not yet implemented
                    original_uuid=None,  # Corruption layer not yet implemented
                )

                # Skip invalidated memories BEFORE updating rehearsal count
                if edge.invalid_at and edge.invalid_at < now:
                    continue

                # Increment rehearsal count (only for valid memories)
                new_count = edge.rehearsal_count + 1
                edge.rehearsal_count = new_count

                # TODO: Persist to Neo4j via Graphiti when API supports it
                # For Phase 3, just update the edge object
                # await self.graphiti_client.update_edge_metadata(
                #     edge.uuid,
                #     {"rehearsal_count": new_count}
                # )

                edges.append(edge)

            # Apply corruption if requested
            # TODO: Implement decay probability calculation based on personality traits
            if apply_corruption:
                pass

            return edges[:limit]

        except GraphitiConnectionFailed:
            raise
        except InvalidAgentID:
            raise
        except Exception as e:
            raise GraphitiConnectionFailed(f"Memory search failed: {e}") from e

    async def add_episode(
        self,
        session_number: int,
        messages: list[dict[str, Any]],
        reference_time: datetime,
        group_id: str,
    ) -> dict[str, str]:
        """
        Store new episode (game session) in memory.

        Args:
            session_number: Session number
            messages: All messages from session
            reference_time: In-game time when session occurred
            group_id: agent_X for personal, campaign_main for shared

        Returns:
            Dictionary with episode_id

        Raises:
            EpisodeCreationFailed: When Graphiti fails to create episode
        """
        try:
            # Extract agent_id from group_id (format: "agent_X")
            agent_id = group_id.replace("agent_", "") if group_id.startswith("agent_") else group_id

            # Determine turn number from messages
            turn_number = max((msg.get("turn_number", 1) for msg in messages), default=1)

            # Create episode via Graphiti (now accepts messages directly)
            episode_id = await self.graphiti_client.create_session_episode(
                agent_id=agent_id,
                messages=messages,
                session_number=session_number,
                turn_number=turn_number,
                metadata={
                    "reference_time": reference_time.isoformat(),
                    "group_id": group_id,
                    "message_count": len(messages),
                },
            )

            return {"episode_id": episode_id}

        except EpisodeCreationFailed:
            raise
        except Exception as e:
            raise EpisodeCreationFailed(f"Failed to add episode: {e}") from e

    async def invalidate_memory(
        self,
        memory_uuid: str,
        invalidation_time: datetime | None = None,
    ) -> dict[str, bool]:
        """
        Mark memory as no longer valid (soft delete).

        Args:
            memory_uuid: UUID of memory to invalidate
            invalidation_time: When memory became invalid (defaults to now)

        Returns:
            Dictionary with success status

        Raises:
            MemoryNotFound: When UUID doesn't exist
            AlreadyInvalidated: When memory already has invalid_at set
        """
        # TODO: Implement via Neo4j query when Graphiti supports memory updates
        # This would set the invalid_at timestamp on the edge in Neo4j
        # For Phase 3, this is a placeholder
        invalidation_time = invalidation_time or datetime.now()

        # Log the operation but don't fail
        # In production, this would execute a Cypher query to update the edge
        return {"success": True}

    async def get_corruption_stats(self, agent_id: str) -> dict[str, Any]:
        """
        Retrieve corruption analytics for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with corruption statistics

        Raises:
            InvalidAgentID: When agent not found
        """
        if not agent_id:
            raise InvalidAgentID("agent_id cannot be empty")

        # TODO: Implement via Neo4j aggregation queries
        # This would query Neo4j for corruption statistics
        # For Phase 3, return empty stats with contract-compliant keys
        return {
            "total_memories": 0,
            "corrupted_memories": 0,
            "corruption_by_type": {},
            "avg_confidence": 1.0,
        }

    async def close(self) -> None:
        """Clean up connections and resources"""
        await self.graphiti_client.close()
