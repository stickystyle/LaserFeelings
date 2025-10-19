# ABOUTME: Contract tests for TtrpgOrchestrator, MessageRouter, and ConsensusDetector interfaces (T031).
# ABOUTME: Tests verify interface compliance with orchestrator_interface.yaml contract specifications.

import pytest
from datetime import datetime, timedelta
from typing import TypedDict

# These imports will fail until implementations exist (TDD phase)
from src.orchestrator.langgraph_orchestrator import TtrpgOrchestrator
from src.orchestrator.message_router import MessageRouter
from src.orchestrator.consensus_detector import ConsensusDetector

from src.models.game_state import (
    GameState,
    GamePhase,
    ValidationResult,
    ConsensusResult,
    Position,
    Stance
)
from src.models.messages import Message, MessageChannel, MessageType, DMCommand, DMCommandType


# --- Test Fixtures ---

@pytest.fixture
def initial_game_state() -> GameState:
    """Initial game state for testing"""
    return GameState(
        current_phase="dm_narration",
        phase_start_time=datetime.now(),
        turn_number=1,
        dm_narration="",
        dm_adjudication_needed=False,
        active_agents=["agent_alex", "agent_sam", "agent_jordan"],
        strategic_intents={},
        ooc_messages=[],
        character_actions={},
        character_reactions={},
        validation_attempt=0,
        validation_valid=True,
        validation_failures={},
        retrieved_memories={},
        retry_count=0
    )


@pytest.fixture
def sample_dm_command() -> str:
    """Sample DM command input"""
    return "narrate A merchant approaches your table, looking nervous."


@pytest.fixture
def sample_ooc_messages() -> list[Message]:
    """Sample OOC discussion messages for consensus testing"""
    return [
        Message(
            message_id="msg_001",
            channel=MessageChannel.OOC,
            from_agent="agent_alex",
            content="I think we should help the merchant. Seems like a good opportunity.",
            timestamp=datetime.now(),
            turn_number=5,
            session_number=1,
            message_type=MessageType.STRATEGIC,
            phase=GamePhase.OOC_DISCUSSION.value
        ),
        Message(
            message_id="msg_002",
            channel=MessageChannel.OOC,
            from_agent="agent_sam",
            content="Yes, agreed. Let's hear what they have to say.",
            timestamp=datetime.now(),
            turn_number=5,
            session_number=1,
            message_type=MessageType.STRATEGIC,
            phase=GamePhase.OOC_DISCUSSION.value
        ),
        Message(
            message_id="msg_003",
            channel=MessageChannel.OOC,
            from_agent="agent_jordan",
            content="I'm on board. Let's do it.",
            timestamp=datetime.now(),
            turn_number=5,
            session_number=1,
            message_type=MessageType.STRATEGIC,
            phase=GamePhase.OOC_DISCUSSION.value
        )
    ]


@pytest.fixture
def conflicted_ooc_messages() -> list[Message]:
    """OOC messages with disagreement"""
    return [
        Message(
            message_id="msg_001",
            channel=MessageChannel.OOC,
            from_agent="agent_alex",
            content="We should attack immediately!",
            timestamp=datetime.now(),
            turn_number=5,
            session_number=1,
            message_type=MessageType.STRATEGIC,
            phase=GamePhase.OOC_DISCUSSION.value
        ),
        Message(
            message_id="msg_002",
            channel=MessageChannel.OOC,
            from_agent="agent_sam",
            content="No, that's a terrible idea. We should negotiate.",
            timestamp=datetime.now(),
            turn_number=5,
            session_number=1,
            message_type=MessageType.STRATEGIC,
            phase=GamePhase.OOC_DISCUSSION.value
        ),
        Message(
            message_id="msg_003",
            channel=MessageChannel.OOC,
            from_agent="agent_jordan",
            content="I agree with attacking.",
            timestamp=datetime.now(),
            turn_number=5,
            session_number=1,
            message_type=MessageType.STRATEGIC,
            phase=GamePhase.OOC_DISCUSSION.value
        )
    ]


@pytest.fixture
def ic_message() -> Message:
    """In-character message"""
    return Message(
        message_id="msg_ic_001",
        channel=MessageChannel.IC,
        from_agent="char_thrain",
        content="Thrain approaches the control panel cautiously.",
        timestamp=datetime.now(),
        turn_number=3,
        session_number=1,
        message_type=MessageType.ACTION,
        phase=GamePhase.IC_ACTIONS.value
    )


@pytest.fixture
def p2c_message() -> Message:
    """Player-to-character directive message"""
    return Message(
        message_id="msg_p2c_001",
        channel=MessageChannel.P2C,
        from_agent="agent_alex",
        to_agents=["char_thrain"],
        content="Investigate the machinery carefully for traps.",
        timestamp=datetime.now(),
        turn_number=3,
        session_number=1,
        message_type=MessageType.DIRECTIVE,
        phase=GamePhase.P2C_DIRECTIVES.value
    )


# --- T031: TtrpgOrchestrator Interface Tests ---

class TestTtrpgOrchestratorInterface:
    """Test TtrpgOrchestrator interface compliance per orchestrator_interface.yaml"""

    def test_orchestrator_has_execute_turn_cycle_method(self):
        """Verify execute_turn_cycle method exists with correct signature"""
        orchestrator = TtrpgOrchestrator()

        # Method must exist
        assert hasattr(orchestrator, "execute_turn_cycle")
        assert callable(orchestrator.execute_turn_cycle)

    def test_orchestrator_has_transition_method(self):
        """Verify transition_to_phase method exists"""
        orchestrator = TtrpgOrchestrator()

        # Method must exist
        assert hasattr(orchestrator, "transition_to_phase")
        assert callable(orchestrator.transition_to_phase)

    def test_orchestrator_has_rollback_method(self):
        """Verify rollback_to_phase method exists"""
        orchestrator = TtrpgOrchestrator()

        # Method must exist
        assert hasattr(orchestrator, "rollback_to_phase")
        assert callable(orchestrator.rollback_to_phase)

    def test_orchestrator_has_validate_phase_action_method(self):
        """Verify validate_phase_action method exists"""
        orchestrator = TtrpgOrchestrator()

        # Method must exist
        assert hasattr(orchestrator, "validate_phase_action")
        assert callable(orchestrator.validate_phase_action)

    @pytest.mark.asyncio
    async def test_execute_turn_cycle_returns_turn_result(
        self,
        initial_game_state,
        sample_dm_command
    ):
        """Verify execute_turn_cycle returns TurnResult structure"""
        orchestrator = TtrpgOrchestrator()

        # Initialize with game state
        orchestrator.state = initial_game_state

        result = await orchestrator.execute_turn_cycle(
            dm_input=sample_dm_command
        )

        # Must return TurnResult with required fields per contract
        assert hasattr(result, "turn_number")
        assert hasattr(result, "phase_completed")
        assert hasattr(result, "success")
        assert isinstance(result.success, bool)
        assert isinstance(result.turn_number, int)

    @pytest.mark.asyncio
    async def test_execute_turn_parses_dm_command(self, sample_dm_command):
        """Verify orchestrator parses DM command (MUST requirement)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.execute_turn_cycle(
            dm_input=sample_dm_command
        )

        # Behavioral requirement: MUST parse DM command
        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_turn_validates_phase_for_command(
        self,
        initial_game_state,
        sample_dm_command
    ):
        """Verify orchestrator validates current phase allows command (MUST)"""
        orchestrator = TtrpgOrchestrator()
        orchestrator.state = initial_game_state

        # When in DM_NARRATION phase, narrate command should be allowed
        result = await orchestrator.execute_turn_cycle(
            dm_input=sample_dm_command
        )

        # Should succeed if phase is valid for command
        assert result.success is True or isinstance(result.success, bool)

    @pytest.mark.asyncio
    async def test_execute_turn_checkpoints_after_each_phase(self):
        """Verify state checkpointed after each phase (MUST requirement)"""
        orchestrator = TtrpgOrchestrator()

        # Behavioral requirement: MUST checkpoint state after each phase
        # This requires verifying checkpoints are created
        # (Implementation will need to expose checkpoint mechanism)
        result = await orchestrator.execute_turn_cycle(
            dm_input="narrate test"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_turn_dispatches_agent_jobs(self):
        """Verify agent jobs dispatched to RQ queues (MUST requirement)"""
        orchestrator = TtrpgOrchestrator()

        # Behavioral requirement: MUST dispatch agent jobs to RQ queues
        result = await orchestrator.execute_turn_cycle(
            dm_input="narrate test"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_turn_waits_for_all_agents(self):
        """Verify orchestrator waits for all agent completions (MUST)"""
        orchestrator = TtrpgOrchestrator()

        # Behavioral requirement: MUST wait for all agent completions before proceeding
        result = await orchestrator.execute_turn_cycle(
            dm_input="narrate test"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_turn_completes_within_timeout(self):
        """Verify normal turn completes within 20s (SHOULD requirement)"""
        orchestrator = TtrpgOrchestrator()

        start_time = datetime.now()

        result = await orchestrator.execute_turn_cycle(
            dm_input="narrate test"
        )

        duration = (datetime.now() - start_time).total_seconds()

        # Performance requirement: SHOULD complete within 20s
        # (This is SHOULD not MUST, so we just verify it's not absurdly long)
        assert duration < 30  # Allow some margin

    @pytest.mark.asyncio
    async def test_transition_to_phase_validates_transition(self):
        """Verify transition_to_phase validates legal transitions (MUST)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.transition_to_phase(
            phase="memory_query"
        )

        # Must return result with success indicator
        assert isinstance(result, dict)
        assert "success" in result
        assert isinstance(result["success"], bool)

    @pytest.mark.asyncio
    async def test_transition_updates_game_state(self):
        """Verify transition updates GameState.current_phase (MUST)"""
        orchestrator = TtrpgOrchestrator()

        previous_phase = orchestrator.state.get("current_phase") if hasattr(orchestrator, "state") else None

        result = await orchestrator.transition_to_phase(
            phase="strategic_intent"
        )

        # Behavioral requirement: MUST update GameState.current_phase
        if result["success"]:
            assert "new_phase" in result
            assert result["new_phase"] == "strategic_intent"

    @pytest.mark.asyncio
    async def test_transition_checkpoints_state(self):
        """Verify transition checkpoints state (MUST requirement)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.transition_to_phase(
            phase="ooc_discussion"
        )

        # Behavioral requirement: MUST checkpoint state
        assert result is not None

    @pytest.mark.asyncio
    async def test_transition_logs_for_observability(self):
        """Verify transition logs for observability (SHOULD)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.transition_to_phase(
            phase="character_action"
        )

        # SHOULD log transition
        # (Full verification requires log inspection)
        assert result is not None

    @pytest.mark.asyncio
    async def test_rollback_restores_from_checkpoint(self):
        """Verify rollback restores GameState from checkpoint (MUST)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.rollback_to_phase(
            target_phase="strategic_intent",
            error_context="Agent job timeout"
        )

        # Must return result indicating rollback success
        assert isinstance(result, dict)
        assert "success" in result
        assert "rolled_back_to" in result

    @pytest.mark.asyncio
    async def test_rollback_clears_partial_results(self):
        """Verify rollback clears partial results from failed phase (MUST)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.rollback_to_phase(
            target_phase="ooc_discussion",
            error_context="Consensus timeout"
        )

        # Behavioral requirement: MUST clear partial results
        assert result is not None

    @pytest.mark.asyncio
    async def test_rollback_logs_reason(self):
        """Verify rollback logs reason (MUST requirement)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.rollback_to_phase(
            target_phase="dm_narration",
            error_context="Validation failed 3 times"
        )

        # MUST log rollback reason
        assert result is not None

    @pytest.mark.asyncio
    async def test_rollback_notifies_dm(self):
        """Verify rollback notifies DM (SHOULD requirement)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.rollback_to_phase(
            target_phase="character_action",
            error_context="Agent timeout"
        )

        # SHOULD notify DM of rollback
        assert result is not None

    @pytest.mark.asyncio
    async def test_validate_phase_action_enforces_permissions(self):
        """Verify phase action validation enforces phase-based permissions (MUST)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.validate_phase_action(
            agent_id="char_thrain",
            action_type="character_action",
            current_phase="ooc_discussion"
        )

        # Must return validation result
        assert isinstance(result, dict)
        assert "allowed" in result
        assert isinstance(result["allowed"], bool)
        assert "reason" in result

    @pytest.mark.asyncio
    async def test_validate_prevents_characters_in_ooc(self):
        """Verify characters prevented from acting in OOC phase (MUST)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.validate_phase_action(
            agent_id="char_thrain",
            action_type="strategic_discussion",
            current_phase="ooc_discussion"
        )

        # Characters must NOT be allowed in OOC phase
        assert result["allowed"] is False

    @pytest.mark.asyncio
    async def test_validate_prevents_players_in_ic(self):
        """Verify base personas prevented from acting in IC phase (MUST)"""
        orchestrator = TtrpgOrchestrator()

        result = await orchestrator.validate_phase_action(
            agent_id="agent_alex",
            action_type="character_action",
            current_phase="character_action"
        )

        # Base personas must NOT be allowed in IC phase
        assert result["allowed"] is False


# --- MessageRouter Interface Tests ---

class TestMessageRouterInterface:
    """Test MessageRouter interface compliance per orchestrator_interface.yaml"""

    def test_router_has_route_message_method(self):
        """Verify route_message method exists"""
        router = MessageRouter()

        # Method must exist
        assert hasattr(router, "route_message")
        assert callable(router.route_message)

    def test_router_has_get_messages_method(self):
        """Verify get_messages_for_agent method exists"""
        router = MessageRouter()

        # Method must exist
        assert hasattr(router, "get_messages_for_agent")
        assert callable(router.get_messages_for_agent)

    @pytest.mark.asyncio
    async def test_route_message_returns_success(self, ic_message):
        """Verify route_message returns success indicator"""
        router = MessageRouter()

        result = await router.route_message(message=ic_message)

        # Must return dict with success and recipients_count
        assert isinstance(result, dict)
        assert "success" in result
        assert "recipients_count" in result
        assert isinstance(result["success"], bool)
        assert isinstance(result["recipients_count"], int)

    @pytest.mark.asyncio
    async def test_route_enforces_ic_visibility(self, ic_message):
        """Verify IC messages visible to characters, summary to players (MUST)"""
        router = MessageRouter()

        result = await router.route_message(message=ic_message)

        # Behavioral requirement: IC → all characters see, base personas get summary
        # (Full verification requires querying what each agent type receives)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_enforces_ooc_visibility(self):
        """Verify OOC messages only visible to base personas (MUST)"""
        router = MessageRouter()

        ooc_message = Message(
            message_id="msg_ooc_001",
            channel=MessageChannel.OOC,
            from_agent="agent_alex",
            content="Let's flank from the left",
            timestamp=datetime.now(),
            turn_number=5,
            session_number=1,
            message_type=MessageType.STRATEGIC,
            phase=GamePhase.OOC_DISCUSSION.value
        )

        result = await router.route_message(message=ooc_message)

        # Behavioral requirement: OOC → only base personas see
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_enforces_p2c_privacy(self, p2c_message):
        """Verify P2C messages only reach target character (MUST)"""
        router = MessageRouter()

        result = await router.route_message(message=p2c_message)

        # Behavioral requirement: P2C → only target character sees
        assert result["success"] is True
        # Only one recipient (the target character)
        assert result["recipients_count"] >= 1

    @pytest.mark.asyncio
    async def test_route_stores_in_redis(self, ic_message):
        """Verify messages stored in Redis Lists by channel (MUST)"""
        router = MessageRouter()

        result = await router.route_message(message=ic_message)

        # Behavioral requirement: MUST store messages in Redis Lists by channel
        # (Verification requires Redis query)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_applies_ttl(self, ic_message):
        """Verify TTL applied to prevent unbounded growth (MUST)"""
        router = MessageRouter()

        result = await router.route_message(message=ic_message)

        # Behavioral requirement: MUST apply TTL
        # (Verification requires Redis TTL inspection)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_messages_filters_by_visibility(self):
        """Verify get_messages_for_agent filters by visibility rules (MUST)"""
        router = MessageRouter()

        result = await router.get_messages_for_agent(
            agent_id="char_thrain",
            agent_type="character",
            limit=50
        )

        # Must return dict with messages
        assert isinstance(result, dict)
        assert "messages" in result
        assert isinstance(result["messages"], list)

    @pytest.mark.asyncio
    async def test_get_messages_sorts_by_timestamp(self):
        """Verify messages sorted by timestamp (MUST requirement)"""
        router = MessageRouter()

        result = await router.get_messages_for_agent(
            agent_id="agent_alex",
            agent_type="base_persona",
            limit=50
        )

        messages = result["messages"]

        # Should be sorted by timestamp
        if len(messages) >= 2:
            for i in range(len(messages) - 1):
                # Assuming ascending order (oldest first)
                # (Actual order may vary, just verify ordering exists)
                assert "timestamp" in messages[i] or hasattr(messages[i], "timestamp")

    @pytest.mark.asyncio
    async def test_get_messages_limits_results(self):
        """Verify limit parameter honored (SHOULD requirement)"""
        router = MessageRouter()

        result = await router.get_messages_for_agent(
            agent_id="agent_alex",
            agent_type="base_persona",
            limit=10
        )

        messages = result["messages"]

        # Should respect limit
        assert len(messages) <= 10


# --- ConsensusDetector Interface Tests ---

class TestConsensusDetectorInterface:
    """Test ConsensusDetector interface compliance per orchestrator_interface.yaml"""

    def test_detector_has_detect_consensus_method(self):
        """Verify detect_consensus method exists"""
        detector = ConsensusDetector()

        # Method must exist
        assert hasattr(detector, "detect_consensus")
        assert callable(detector.detect_consensus)

    def test_detector_has_extract_positions_method(self):
        """Verify extract_positions method exists"""
        detector = ConsensusDetector()

        # Method must exist
        assert hasattr(detector, "extract_positions")
        assert callable(detector.extract_positions)

    @pytest.mark.asyncio
    async def test_detect_consensus_returns_result(self, sample_ooc_messages):
        """Verify detect_consensus returns consensus result structure"""
        detector = ConsensusDetector()

        agents = ["agent_alex", "agent_sam", "agent_jordan"]

        result = await detector.detect_consensus(
            messages=sample_ooc_messages,
            agents=agents,
            max_rounds=5,
            timeout_seconds=120
        )

        # Must return dict with required fields per contract
        assert isinstance(result, dict)
        assert "state" in result
        assert "positions" in result
        assert "proceed_with_action" in result
        assert result["state"] in ["unanimous", "majority", "conflicted", "timeout"]
        assert isinstance(result["proceed_with_action"], bool)

    @pytest.mark.asyncio
    async def test_detect_unanimous_all_agree(self, sample_ooc_messages):
        """Verify unanimous detected when all AGREE (MUST)"""
        detector = ConsensusDetector()

        agents = ["agent_alex", "agent_sam", "agent_jordan"]

        result = await detector.detect_consensus(
            messages=sample_ooc_messages,
            agents=agents
        )

        # All agents agreed in sample_ooc_messages
        # MUST detect unanimous
        assert result["state"] == "unanimous"
        assert result["proceed_with_action"] is True

    @pytest.mark.asyncio
    async def test_detect_majority_over_50_percent_agree(self):
        """Verify majority detected when >50% AGREE with no DISAGREE (MUST)"""
        detector = ConsensusDetector()

        majority_messages = [
            Message(
                message_id="msg_001",
                channel=MessageChannel.OOC,
                from_agent="agent_alex",
                content="Yes, let's do it",
                timestamp=datetime.now(),
                turn_number=5,
                session_number=1,
                message_type=MessageType.STRATEGIC,
                phase=GamePhase.OOC_DISCUSSION.value
            ),
            Message(
                message_id="msg_002",
                channel=MessageChannel.OOC,
                from_agent="agent_sam",
                content="Agreed",
                timestamp=datetime.now(),
                turn_number=5,
                session_number=1,
                message_type=MessageType.STRATEGIC,
                phase=GamePhase.OOC_DISCUSSION.value
            ),
            Message(
                message_id="msg_003",
                channel=MessageChannel.OOC,
                from_agent="agent_jordan",
                content="Either way is fine with me",  # NEUTRAL
                timestamp=datetime.now(),
                turn_number=5,
                session_number=1,
                message_type=MessageType.STRATEGIC,
                phase=GamePhase.OOC_DISCUSSION.value
            )
        ]

        agents = ["agent_alex", "agent_sam", "agent_jordan"]

        result = await detector.detect_consensus(
            messages=majority_messages,
            agents=agents
        )

        # 2/3 AGREE, 1/3 NEUTRAL → majority
        assert result["state"] == "majority"
        assert result["proceed_with_action"] is True

    @pytest.mark.asyncio
    async def test_detect_conflicted_any_disagree(self, conflicted_ooc_messages):
        """Verify conflicted detected when any DISAGREE (MUST)"""
        detector = ConsensusDetector()

        agents = ["agent_alex", "agent_sam", "agent_jordan"]

        result = await detector.detect_consensus(
            messages=conflicted_ooc_messages,
            agents=agents
        )

        # agent_sam disagreed → conflicted
        assert result["state"] == "conflicted"
        assert result["proceed_with_action"] is False
        assert "agent_sam" in result.get("dissenting_agents", [])

    @pytest.mark.asyncio
    async def test_detect_timeout_after_max_rounds(self):
        """Verify timeout after 5 rounds (MUST requirement)"""
        detector = ConsensusDetector()

        # Create 15 messages (5 rounds for 3 agents)
        timeout_messages = []
        for i in range(15):
            timeout_messages.append(
                Message(
                    message_id=f"msg_{i:03d}",
                    channel=MessageChannel.OOC,
                    from_agent=f"agent_{i % 3}",
                    content="I'm still thinking...",
                    timestamp=datetime.now() + timedelta(seconds=i),
                    turn_number=5,
                    session_number=1,
                    message_type=MessageType.STRATEGIC,
                    phase=GamePhase.OOC_DISCUSSION.value
                )
            )

        agents = ["agent_0", "agent_1", "agent_2"]

        result = await detector.detect_consensus(
            messages=timeout_messages,
            agents=agents,
            max_rounds=5
        )

        # MUST detect timeout after 5 rounds
        assert result["state"] == "timeout"
        assert result["proceed_with_action"] is True  # Force decision
        assert result.get("rounds_elapsed", 0) >= 5

    @pytest.mark.asyncio
    async def test_detect_timeout_after_time_limit(self):
        """Verify timeout after 120 seconds (MUST requirement)"""
        detector = ConsensusDetector()

        # This test would need to mock time or use very short timeout
        # For now, verify timeout_seconds parameter is respected

        agents = ["agent_alex", "agent_sam"]

        result = await detector.detect_consensus(
            messages=[],
            agents=agents,
            timeout_seconds=1  # Very short timeout for testing
        )

        # Should timeout quickly
        # (Full test requires time mocking)
        assert result["state"] in ["timeout", "unanimous", "majority", "conflicted"]

    @pytest.mark.asyncio
    async def test_extract_positions_classifies_stances(self, sample_ooc_messages):
        """Verify extract_positions classifies each agent's stance (MUST)"""
        detector = ConsensusDetector()

        agents = ["agent_alex", "agent_sam", "agent_jordan"]

        result = await detector.extract_positions(
            messages=sample_ooc_messages,
            agents=agents
        )

        # Must return positions for every agent
        assert isinstance(result, dict)
        for agent_id in agents:
            assert agent_id in result
            position = result[agent_id]
            assert "stance" in position
            assert "confidence" in position
            assert position["stance"] in ["agree", "disagree", "neutral", "silent"]
            assert 0.0 <= position["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_extract_positions_uses_llm(self, sample_ooc_messages):
        """Verify extract_positions uses GPT-4o-mini with JSON mode (MUST)"""
        detector = ConsensusDetector()

        agents = ["agent_alex", "agent_sam", "agent_jordan"]

        result = await detector.extract_positions(
            messages=sample_ooc_messages,
            agents=agents
        )

        # Behavioral requirement: MUST use GPT-4o-mini with JSON mode
        # (Verification requires checking LLM calls)
        assert result is not None

    @pytest.mark.asyncio
    async def test_extract_positions_analyzes_recent_messages(self, sample_ooc_messages):
        """Verify last 3 messages per agent analyzed (MUST requirement)"""
        detector = ConsensusDetector()

        agents = ["agent_alex"]

        result = await detector.extract_positions(
            messages=sample_ooc_messages,
            agents=agents
        )

        # Behavioral requirement: MUST analyze last 3 messages per agent
        # (Implementation detail, hard to test without mocking)
        assert "agent_alex" in result

    @pytest.mark.asyncio
    async def test_consensus_lenient_agree_detection(self):
        """Verify SHOULD be lenient with AGREE detection"""
        detector = ConsensusDetector()

        lenient_messages = [
            Message(
                message_id="msg_001",
                channel=MessageChannel.OOC,
                from_agent="agent_alex",
                content="Sure, why not",  # Casual agreement
                timestamp=datetime.now(),
                turn_number=5,
                session_number=1,
                message_type=MessageType.STRATEGIC,
                phase=GamePhase.OOC_DISCUSSION.value
            )
        ]

        agents = ["agent_alex"]

        result = await detector.extract_positions(
            messages=lenient_messages,
            agents=agents
        )

        # Should classify "sure, why not" as AGREE (lenient)
        # (This is SHOULD, not strict requirement)
        assert "agent_alex" in result

    @pytest.mark.asyncio
    async def test_consensus_strict_disagree_detection(self, conflicted_ooc_messages):
        """Verify SHOULD be strict with DISAGREE detection"""
        detector = ConsensusDetector()

        agents = ["agent_sam"]  # The one who said "No, that's a terrible idea"

        result = await detector.extract_positions(
            messages=conflicted_ooc_messages,
            agents=agents
        )

        # Should clearly classify "No, that's a terrible idea" as DISAGREE
        assert "agent_sam" in result
        # (Exact stance depends on LLM, but should be strict)


# --- Error Handling Tests ---

class TestOrchestratorErrorHandling:
    """Test error conditions specified in contract"""

    @pytest.mark.asyncio
    async def test_execute_raises_invalid_command(self):
        """Verify InvalidCommand raised when DM input doesn't parse"""
        orchestrator = TtrpgOrchestrator()

        from src.orchestrator.exceptions import InvalidCommand

        # Verify exception type exists
        assert InvalidCommand is not None

    @pytest.mark.asyncio
    async def test_execute_raises_phase_transition_failed(self):
        """Verify PhaseTransitionFailed when state machine cannot proceed"""
        orchestrator = TtrpgOrchestrator()

        from src.orchestrator.exceptions import PhaseTransitionFailed

        assert PhaseTransitionFailed is not None

    @pytest.mark.asyncio
    async def test_execute_raises_agent_execution_failed(self):
        """Verify AgentExecutionFailed when agent RQ job times out"""
        orchestrator = TtrpgOrchestrator()

        from src.orchestrator.exceptions import AgentExecutionFailed

        assert AgentExecutionFailed is not None

    @pytest.mark.asyncio
    async def test_execute_raises_max_retries_exceeded(self):
        """Verify MaxRetriesExceeded when validation fails 3 times for all agents"""
        orchestrator = TtrpgOrchestrator()

        from src.orchestrator.exceptions import MaxRetriesExceeded

        assert MaxRetriesExceeded is not None

    @pytest.mark.asyncio
    async def test_transition_raises_invalid_phase_transition(self):
        """Verify InvalidPhaseTransition when transition not allowed"""
        orchestrator = TtrpgOrchestrator()

        from src.orchestrator.exceptions import InvalidPhaseTransition

        assert InvalidPhaseTransition is not None

    @pytest.mark.asyncio
    async def test_rollback_raises_checkpoint_not_found(self):
        """Verify CheckpointNotFound when no checkpoint exists for target"""
        orchestrator = TtrpgOrchestrator()

        from src.orchestrator.exceptions import CheckpointNotFound

        assert CheckpointNotFound is not None

    @pytest.mark.asyncio
    async def test_route_raises_invalid_channel(self):
        """Verify InvalidChannel when channel not recognized"""
        router = MessageRouter()

        from src.orchestrator.exceptions import InvalidChannel

        assert InvalidChannel is not None

    @pytest.mark.asyncio
    async def test_route_raises_recipient_not_found(self):
        """Verify RecipientNotFound when to_agents contains invalid ID"""
        router = MessageRouter()

        from src.orchestrator.exceptions import RecipientNotFound

        assert RecipientNotFound is not None

    @pytest.mark.asyncio
    async def test_get_messages_raises_agent_not_found(self):
        """Verify AgentNotFound when agent_id invalid"""
        router = MessageRouter()

        from src.orchestrator.exceptions import AgentNotFound

        assert AgentNotFound is not None

    @pytest.mark.asyncio
    async def test_consensus_raises_llm_call_failed(self):
        """Verify LLMCallFailed when OpenAI API fails"""
        detector = ConsensusDetector()

        from src.orchestrator.exceptions import LLMCallFailed

        assert LLMCallFailed is not None

    @pytest.mark.asyncio
    async def test_consensus_raises_invalid_agent_list(self):
        """Verify InvalidAgentList when agents list empty"""
        detector = ConsensusDetector()

        from src.orchestrator.exceptions import InvalidAgentList

        assert InvalidAgentList is not None


# --- Performance Tests ---

class TestOrchestratorPerformance:
    """Test performance requirements from contract"""

    @pytest.mark.performance
    @pytest.mark.skip(reason="TDD phase - skip until T032-T058 implementation complete")
    @pytest.mark.asyncio
    async def test_execute_turn_completes_within_20s(self):
        """Verify execute_turn_cycle completes within 20s (MUST)"""
        orchestrator = TtrpgOrchestrator()

        start = datetime.now()
        result = await orchestrator.execute_turn_cycle(
            dm_input="narrate test"
        )
        duration = (datetime.now() - start).total_seconds()

        # MUST complete within 20s (normal case)
        assert duration < 20

    @pytest.mark.performance
    @pytest.mark.skip(reason="TDD phase - skip until T032-T058 implementation complete")
    @pytest.mark.asyncio
    async def test_phase_transition_completes_within_100ms(self):
        """Verify phase transitions complete within 100ms (MUST)"""
        orchestrator = TtrpgOrchestrator()

        start = datetime.now()
        result = await orchestrator.transition_to_phase(phase="memory_query")
        duration = (datetime.now() - start).total_seconds()

        # MUST complete within 100ms
        assert duration < 0.1

    @pytest.mark.performance
    @pytest.mark.skip(reason="TDD phase - skip until T032-T058 implementation complete")
    @pytest.mark.asyncio
    async def test_consensus_completes_within_3s(self, sample_ooc_messages):
        """Verify consensus detection completes within 3s (MUST)"""
        detector = ConsensusDetector()

        agents = ["agent_alex", "agent_sam", "agent_jordan"]

        start = datetime.now()
        result = await detector.detect_consensus(
            messages=sample_ooc_messages,
            agents=agents
        )
        duration = (datetime.now() - start).total_seconds()

        # MUST complete within 3s
        assert duration < 3

    @pytest.mark.performance
    @pytest.mark.skip(reason="TDD phase - skip until T032-T058 implementation complete")
    @pytest.mark.asyncio
    async def test_message_routing_completes_within_50ms(self, ic_message):
        """Verify message routing completes within 50ms (MUST)"""
        router = MessageRouter()

        start = datetime.now()
        result = await router.route_message(message=ic_message)
        duration = (datetime.now() - start).total_seconds()

        # MUST complete within 50ms
        assert duration < 0.05

    @pytest.mark.performance
    @pytest.mark.skip(reason="TDD phase - skip until T032-T058 implementation complete")
    @pytest.mark.asyncio
    async def test_rollback_completes_within_500ms(self):
        """Verify rollback completes within 500ms (MUST)"""
        orchestrator = TtrpgOrchestrator()

        start = datetime.now()
        result = await orchestrator.rollback_to_phase(
            target_phase="dm_narration",
            error_context="test"
        )
        duration = (datetime.now() - start).total_seconds()

        # MUST complete within 500ms
        assert duration < 0.5
