# ABOUTME: Tests for dm_clarification two-node pattern with conditional interrupt.
# ABOUTME: Verifies that the collect node runs without interrupting, and wait node only pauses when questions exist.

import pytest
from redis import Redis
from unittest.mock import MagicMock, patch

from src.orchestration.nodes.clarification_nodes import (
    _create_dm_clarification_collect_node,
    _create_dm_clarification_wait_node,
)
from src.orchestration.nodes.conditional_edges import (
    check_clarification_after_collect,
    check_clarification_after_wait,
)
from src.models.game_state import GamePhase


class TestDMClarificationCollectNode:
    """Test dm_clarification_collect_node behavior"""

    @pytest.fixture
    def mock_queue(self):
        """Mock RQ Queue"""
        queue = MagicMock()
        mock_job = MagicMock()
        mock_job.result = None
        mock_job.is_failed = False
        queue.enqueue.return_value = mock_job
        return queue

    @pytest.fixture
    def mock_router(self):
        """Mock MessageRouter"""
        return MagicMock()

    @pytest.fixture
    def collect_node(self, mock_queue, mock_router):
        """Create collect node with mocked dependencies"""
        return _create_dm_clarification_collect_node(mock_queue, mock_router)

    @patch('src.orchestration.nodes.clarification_nodes._poll_job_with_backoff')
    def test_collect_node_returns_memory_query_phase_when_no_questions(
        self, mock_poll, collect_node, mock_queue
    ):
        """When no questions exist, collect node sets phase to MEMORY_QUERY to skip wait node"""
        # Mock all players returning None (no questions)
        mock_job = MagicMock()
        mock_job.result = None  # No question
        mock_job.is_failed = False
        mock_queue.enqueue.return_value = mock_job

        # Mock polling to do nothing (job already "complete")
        mock_poll.return_value = None

        state = {
            "turn_number": 1,
            "active_agents": ["agent_001"],
            "dm_narration": "You enter a room",
            "retrieved_memories": {"agent_001": []}
        }

        result = collect_node(state)

        # Should set phase to MEMORY_QUERY (not DM_CLARIFICATION)
        assert result["current_phase"] == GamePhase.MEMORY_QUERY.value
        assert result["clarification_round"] == 1

        # Verify polling was called once per agent
        assert mock_poll.call_count == 1

    @patch('src.orchestration.nodes.clarification_nodes._poll_job_with_backoff')
    def test_collect_node_returns_dm_clarification_phase_when_questions_exist(
        self, mock_poll, collect_node, mock_queue, mock_router
    ):
        """When questions exist, collect node keeps phase as DM_CLARIFICATION to route to wait"""
        # Mock player returning a question
        mock_job = MagicMock()
        mock_job.result = {"question": "What's in the room?"}
        mock_job.is_failed = False
        mock_queue.enqueue.return_value = mock_job

        # Mock polling to do nothing (job already "complete")
        mock_poll.return_value = None

        state = {
            "turn_number": 1,
            "active_agents": ["agent_001"],
            "dm_narration": "You enter a room",
            "retrieved_memories": {"agent_001": []},
            "session_number": 1
        }

        result = collect_node(state)

        # Should keep phase as DM_CLARIFICATION to route to wait node
        assert result["current_phase"] == GamePhase.DM_CLARIFICATION.value
        assert result["awaiting_dm_clarifications"] is True
        assert "agent_001" in result["clarifying_questions_this_round"]

        # Verify question was routed to OOC
        mock_router.add_message.assert_called_once()

        # Verify polling was called once per agent
        assert mock_poll.call_count == 1


class TestDMClarificationWaitNode:
    """Test dm_clarification_wait_node behavior"""

    @pytest.fixture
    def mock_router(self):
        """Mock MessageRouter"""
        return MagicMock()

    @pytest.fixture
    def wait_node(self, mock_router):
        """Create wait node with mocked dependencies"""
        return _create_dm_clarification_wait_node(mock_router)

    def test_wait_node_preserves_dm_clarification_phase(self, wait_node):
        """Wait node keeps phase as DM_CLARIFICATION"""
        state = {
            "turn_number": 1,
            "clarification_round": 1,
            "current_phase": GamePhase.DM_CLARIFICATION.value
        }

        result = wait_node(state)

        assert result["current_phase"] == GamePhase.DM_CLARIFICATION.value

    def test_wait_node_updates_phase_start_time(self, wait_node):
        """Wait node updates phase_start_time"""
        state = {
            "turn_number": 1,
            "clarification_round": 1,
            "current_phase": GamePhase.DM_CLARIFICATION.value
        }

        result = wait_node(state)

        assert "phase_start_time" in result


class TestConditionalEdgePredicates:
    """Test conditional edge routing logic"""

    def test_check_clarification_after_collect_returns_skip_when_no_questions(self):
        """When collect sets phase to MEMORY_QUERY, edge routes to skip"""
        state = {
            "current_phase": GamePhase.MEMORY_QUERY.value
        }

        result = check_clarification_after_collect(state)

        assert result == "skip"

    def test_check_clarification_after_collect_returns_wait_when_questions_exist(self):
        """When collect keeps phase as DM_CLARIFICATION, edge routes to wait"""
        state = {
            "current_phase": GamePhase.DM_CLARIFICATION.value
        }

        result = check_clarification_after_collect(state)

        assert result == "wait"

    def test_check_clarification_after_wait_loops_back_when_under_max_rounds(self):
        """After wait, if rounds < 3, loop back to collect"""
        state = {
            "clarification_round": 2
        }

        result = check_clarification_after_wait(state)

        assert result == "loop"

    def test_check_clarification_after_wait_proceeds_when_max_rounds_reached(self):
        """After wait, if rounds >= 3, proceed to memory query"""
        state = {
            "clarification_round": 3
        }

        result = check_clarification_after_wait(state)

        assert result == "proceed"

    def test_check_clarification_after_wait_defaults_to_loop_when_no_round(self):
        """If no clarification_round in state, defaults to 1 and loops"""
        state = {}

        result = check_clarification_after_wait(state)

        assert result == "loop"


class TestTwoNodePatternIntegration:
    """Integration tests for the full two-node pattern"""

    @pytest.fixture
    def mock_queue(self):
        """Mock RQ Queue"""
        queue = MagicMock()
        return queue

    @pytest.fixture
    def mock_router(self):
        """Mock MessageRouter"""
        return MagicMock()

    @patch('src.orchestration.nodes.clarification_nodes._poll_job_with_backoff')
    def test_no_questions_path_skips_wait_node(self, mock_poll, mock_queue, mock_router):
        """When no questions, collect → skip → memory_query (wait node is never entered)"""
        collect_node = _create_dm_clarification_collect_node(mock_queue, mock_router)

        # Mock no questions from any player
        mock_job = MagicMock()
        mock_job.result = None
        mock_job.is_failed = False
        mock_queue.enqueue.return_value = mock_job

        # Mock polling to do nothing (job already "complete")
        mock_poll.return_value = None

        state = {
            "turn_number": 1,
            "active_agents": ["agent_001"],
            "dm_narration": "You enter a room",
            "retrieved_memories": {"agent_001": []}
        }

        # Step 1: Run collect node
        result = collect_node(state)

        # Verify phase is MEMORY_QUERY
        assert result["current_phase"] == GamePhase.MEMORY_QUERY.value

        # Step 2: Check conditional edge
        edge_result = check_clarification_after_collect(result)

        # Should skip to second_memory_query
        assert edge_result == "skip"

        # Verify polling was called
        assert mock_poll.call_count == 1

    @patch('src.orchestration.nodes.clarification_nodes._poll_job_with_backoff')
    def test_questions_exist_path_enters_wait_node(self, mock_poll, mock_queue, mock_router):
        """When questions exist, collect → wait → (interrupt) → loop → collect"""
        collect_node = _create_dm_clarification_collect_node(mock_queue, mock_router)
        wait_node = _create_dm_clarification_wait_node(mock_router)

        # Mock player asking a question
        mock_job = MagicMock()
        mock_job.result = {"question": "What's in the room?"}
        mock_job.is_failed = False
        mock_queue.enqueue.return_value = mock_job

        # Mock polling to do nothing (job already "complete")
        mock_poll.return_value = None

        state = {
            "turn_number": 1,
            "active_agents": ["agent_001"],
            "dm_narration": "You enter a room",
            "retrieved_memories": {"agent_001": []},
            "clarification_round": 1,
            "session_number": 1
        }

        # Step 1: Run collect node
        result_after_collect = collect_node(state)

        # Verify phase is still DM_CLARIFICATION
        assert result_after_collect["current_phase"] == GamePhase.DM_CLARIFICATION.value

        # Step 2: Check conditional edge after collect
        edge_after_collect = check_clarification_after_collect(result_after_collect)

        # Should route to wait
        assert edge_after_collect == "wait"

        # Step 3: Run wait node (would interrupt here in real execution)
        result_after_wait = wait_node(result_after_collect)

        # Wait node preserves phase
        assert result_after_wait["current_phase"] == GamePhase.DM_CLARIFICATION.value

        # Step 4: Simulate DM answering (increment round)
        result_after_wait["clarification_round"] = 2

        # Step 5: Check conditional edge after wait
        edge_after_wait = check_clarification_after_wait(result_after_wait)

        # Should loop back to collect
        assert edge_after_wait == "loop"

        # Verify polling was called
        assert mock_poll.call_count == 1
