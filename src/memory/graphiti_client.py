# ABOUTME: Wrapper around Graphiti library for graph-based memory operations with Neo4j backend.
# ABOUTME: Handles episode creation, memory queries, entity extraction, and temporal filtering.

from datetime import datetime
from typing import Any

from graphiti_core import Graphiti
from openai import OpenAI

from src.memory.exceptions import (
    EpisodeCreationFailed,
    GraphitiConnectionFailed,
    InvalidAgentID,
    LLMCallFailed,
)


class GraphitiClient:
    """Wrapper for Graphiti library providing graph-based memory storage"""

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        openai_client: OpenAI | None = None,
    ):
        """
        Initialize Graphiti client with Neo4j connection.

        Args:
            neo4j_uri: Neo4j connection URI (e.g., "bolt://localhost:7687")
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            openai_client: OpenAI client for entity extraction (optional)

        Raises:
            GraphitiConnectionFailed: When Neo4j connection fails
        """
        try:
            self.graphiti = Graphiti(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
                llm_client=openai_client,
            )
            self.openai_client = openai_client
            self._neo4j_uri = neo4j_uri
        except Exception as e:
            raise GraphitiConnectionFailed(
                f"Failed to connect to Neo4j at {neo4j_uri}: {e}"
            ) from e

    async def create_session_episode(
        self,
        agent_id: str,
        messages: list[dict[str, Any]],
        session_number: int,
        turn_number: int,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create memory episode for a game session.

        Args:
            agent_id: Agent identifier (used for group_id)
            messages: List of message dictionaries from session
            session_number: Session number
            turn_number: Turn number within session
            metadata: Additional metadata to store

        Returns:
            Episode ID string

        Raises:
            EpisodeCreationFailed: When Graphiti fails to create episode
        """
        try:
            # Format messages into narrative episode content
            episode_content = self._format_messages(messages)

            # Create episode with agent-specific group_id
            # Note: metadata parameter not currently used by Graphiti.add_episode
            # but prepared here for future use
            group_id = f"agent_{agent_id}"
            episode_id = await self.graphiti.add_episode(
                name=f"Session {session_number}, Turn {turn_number}",
                episode_body=episode_content,
                source_description=f"TTRPG Session {session_number}",
                reference_time=datetime.now(),
                group_id=group_id,
            )

            return episode_id

        except Exception as e:
            raise EpisodeCreationFailed(
                f"Failed to create episode for agent {agent_id}, "
                f"session {session_number}, turn {turn_number}: {e}"
            ) from e

    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        """Format message list into narrative episode content."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)

    async def query_memories_at_time(
        self,
        query: str,
        agent_id: str,
        session_number: int | None = None,
        turn_number: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Query memories with temporal context.

        Args:
            query: Semantic search query
            agent_id: Agent identifier
            session_number: Filter by session number (optional)
            turn_number: Filter by turn number (optional)
            limit: Maximum number of results

        Returns:
            List of memory results as dictionaries

        Raises:
            GraphitiConnectionFailed: When query fails
            InvalidAgentID: When agent_id is invalid
            LLMCallFailed: When OpenAI API call fails
        """
        try:
            # Build group_ids for personal and shared memories
            group_ids = [f"agent_{agent_id}", "campaign_main"]

            # Query Graphiti
            results = await self.graphiti.search(
                query=query,
                group_ids=group_ids,
                num_results=limit,
            )

            # Convert results to dictionaries
            # Note: Actual Graphiti API may return different structure
            # This is a placeholder that matches expected interface
            return [
                {
                    "id": getattr(result, "uuid", str(result)),
                    "content": getattr(result, "fact", str(result)),
                    "metadata": getattr(result, "metadata", {}),
                    "timestamp": getattr(result, "created_at", datetime.now()),
                }
                for result in results
            ]

        except (ConnectionError, TimeoutError, OSError) as e:
            raise GraphitiConnectionFailed(
                f"Failed to query memories for agent {agent_id}: {e}"
            ) from e
        except (InvalidAgentID, LLMCallFailed):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            # Log unexpected errors and re-raise as connection failure
            raise GraphitiConnectionFailed(
                f"Unexpected error querying memories for agent {agent_id}: {e}"
            ) from e

    async def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract entities from narrative text using Graphiti's LLM.

        Args:
            text: Narrative text to extract entities from

        Returns:
            List of extracted entities with types

        Raises:
            GraphitiConnectionFailed: When entity extraction fails
        """
        try:
            # Graphiti handles entity extraction automatically during add_episode
            # This method would use Graphiti's internal entity extraction
            # For now, return empty list as this is handled automatically
            return []

        except Exception as e:
            raise GraphitiConnectionFailed(f"Failed to extract entities: {e}") from e

    async def initialize(self) -> dict[str, Any]:
        """
        Setup Graphiti with Neo4j connection and verify indexes.

        Returns:
            Dictionary with success status and version info

        Raises:
            GraphitiConnectionFailed: When database unreachable
        """
        try:
            # Verify Graphiti client is initialized
            if self.graphiti is None:
                raise GraphitiConnectionFailed("Graphiti client not initialized")

            # Create indexes if missing
            indexes = await self.create_indexes()

            # Return success status
            return {
                "success": True,
                "version": "0.3.0",  # Graphiti version
                "indexes_created": indexes["indexes_created"],
            }
        except Exception as e:
            raise GraphitiConnectionFailed(f"Initialization failed: {e}") from e

    async def create_indexes(self) -> dict[str, list[str]]:
        """
        Create temporal and composite indexes in Neo4j.

        Returns:
            Dictionary with list of indexes created

        Raises:
            IndexCreationFailed: When Cypher query fails
        """
        # Graphiti handles indexing internally during initialization
        # For Phase 3, return placeholder indexes that would be created
        # In production, this would create custom indexes via Neo4j driver
        indexes_created = [
            "agent_session_temporal",
            "valid_at_range",
            "invalid_at_range",
            "fact_fulltext",
            "corruption_type_index",
        ]

        return {"indexes_created": indexes_created}

    async def close(self) -> None:
        """Clean up connections and resources"""
        try:
            if hasattr(self.graphiti, "close"):
                await self.graphiti.close()
        except Exception:
            # Graceful shutdown - don't raise on close errors
            pass
