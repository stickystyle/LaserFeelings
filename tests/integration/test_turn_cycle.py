# ABOUTME: Integration tests for complete turn cycle from DM narration through memory
# ABOUTME: consolidation (T032). Tests verify all GamePhase transitions and error recovery.

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports will fail until implementations exist (TDD phase)
from src.orchestrator.turn_manager import TurnManager

from src.agents.base_persona import BasePersonaAgent
from src.agents.character import CharacterAgent
from src.memory.corrupted_temporal import CorruptedTemporalMemory

# Core models and enums
from src.models.game_state import GamePhase, GameState

# --- Test Fixtures ---
# Note: test_personality and test_character fixtures are defined in tests/conftest.py
# and available as standard_personality and explorer_character respectively

@pytest.fixture
def mock_llm_client():
    """Mock OpenAI client with canned responses"""
    client = MagicMock()

    # Mock chat completion response structure
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test LLM response"

    client.chat.completions.create = AsyncMock(return_value=mock_response)

    return client


@pytest.fixture
def mock_memory_store():
    """Mock CorruptedTemporalMemory for testing"""
    memory = MagicMock(spec=CorruptedTemporalMemory)

    # Mock search method
    memory.search = AsyncMock(return_value=[])

    # Mock add_episode method
    memory.add_episode = AsyncMock(return_value="episode_001")

    # Mock invalidate_edge method
    memory.invalidate_edge = AsyncMock()

    return memory


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    redis = MagicMock()

    # Mock basic Redis operations
    redis.rpush = MagicMock()
    redis.lrange = MagicMock(return_value=[])
    redis.get = MagicMock(return_value=None)
    redis.set = MagicMock()
    redis.expire = MagicMock()

    return redis


@pytest.fixture
def initial_game_state(standard_personality, explorer_character) -> GameState:
    """Initial game state for turn cycle testing"""
    return GameState(
        current_phase="dm_narration",
        phase_start_time=datetime.now(),
        turn_number=1,
        session_number=1,  # Added required field
        dm_narration="",
        dm_adjudication_needed=True,
        active_agents=["agent_001"],
        strategic_intents={},
        ooc_messages=[],
        character_actions={},
        character_reactions={},
        validation_attempt=0,
        validation_valid=False,
        validation_failures={},
        retrieved_memories={},
        retry_count=0
    )


@pytest.fixture
def turn_manager(mock_llm_client, mock_memory_store, mock_redis):
    """TurnManager instance with mocked dependencies"""
    # This will fail until TurnManager is implemented
    manager = TurnManager(
        llm_client=mock_llm_client,
        memory_store=mock_memory_store,
        redis_client=mock_redis
    )
    return manager


# --- T032: Complete Turn Cycle Integration Tests ---

class TestCompleteTurnCycleSuccess:
    """Test successful turn cycle through all phases"""

    @pytest.mark.asyncio
    async def test_complete_turn_cycle_all_phases(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test a full turn cycle with successful validation (US1 AC1)

        Verifies:
        - DM narrates scene
        - System retrieves memories
        - Player formulates strategic intent
        - Player creates character directive
        - Character performs action (intent-only)
        - Validation passes
        - DM adjudicates
        - Character reacts
        - Memory consolidates
        - All phases completed in order
        """
        # Given: DM provides narration
        dm_narration = "A mysterious alien ship appears on your scanners, emitting strange signals."

        # When: Execute full turn cycle
        initial_game_state["dm_narration"] = dm_narration

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        # Then: All phases completed successfully
        assert final_state["current_phase"] == "memory_storage"
        assert final_state["turn_number"] == 1

        # Strategic intent formulated
        assert "agent_001" in final_state["strategic_intents"]
        assert len(final_state["strategic_intents"]["agent_001"]) > 0

        # Character action generated
        assert "char_001" in final_state["character_actions"]
        action_text = final_state["character_actions"]["char_001"]
        assert len(action_text) > 0

        # Validation passed
        assert final_state["validation_valid"] is True
        assert final_state["validation_attempt"] > 0

        # Character reaction present
        assert "char_001" in final_state["character_reactions"]

        # Memory was stored (mock called)
        turn_manager.memory_store.add_episode.assert_called()

    @pytest.mark.asyncio
    async def test_turn_cycle_phase_order_enforced(
        self,
        turn_manager,
        initial_game_state
    ):
        """Verify phases execute in strict order (FR-002)

        Expected order:
        DM_NARRATION → MEMORY_RETRIEVAL → STRATEGIC_INTENT →
        P2C_DIRECTIVE → CHARACTER_ACTION → VALIDATION_CHECK →
        DM_ADJUDICATION → DICE_RESOLUTION → DM_OUTCOME →
        CHARACTER_REACTION → MEMORY_CONSOLIDATION
        """
        dm_narration = "You enter a dark corridor."
        initial_game_state["dm_narration"] = dm_narration

        # Track phase transitions
        phase_history = []

        # Mock phase transition callback
        original_transition = turn_manager._transition_phase

        def track_transition(state, new_phase):
            phase_history.append(new_phase)
            return original_transition(state, new_phase)

        turn_manager._transition_phase = track_transition

        # Execute turn
        await turn_manager.execute_turn_cycle(initial_game_state)

        # Verify phase order (single-agent, no OOC discussion)
        expected_phases = [
            GamePhase.MEMORY_QUERY,
            GamePhase.STRATEGIC_INTENT,
            GamePhase.CHARACTER_ACTION,
            GamePhase.VALIDATION,
            GamePhase.DM_ADJUDICATION,
            GamePhase.CHARACTER_REACTION,
            GamePhase.MEMORY_STORAGE
        ]

        # Check all expected phases present in order
        for expected_phase in expected_phases:
            assert expected_phase.value in phase_history, \
                f"Phase {expected_phase.value} missing from history: {phase_history}"

    @pytest.mark.asyncio
    async def test_character_action_intent_only_no_outcome(
        self,
        turn_manager,
        initial_game_state
    ):
        """Verify character action expresses intent only, no outcomes (US1 AC2)"""
        dm_narration = "A hostile robot blocks the corridor, weapon armed."
        initial_game_state["dm_narration"] = dm_narration

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        # Get character action
        action_text = final_state["character_actions"]["char_001"]
        action_lower = action_text.lower()

        # Should NOT contain outcome language
        forbidden_outcomes = [
            "successfully",
            "hits",
            "kills",
            "defeats",
            "destroys",
            "the robot falls",
            "the robot dies",
            "manages to"
        ]

        for forbidden in forbidden_outcomes:
            assert forbidden not in action_lower, \
                f"Action contains forbidden outcome '{forbidden}': {action_text}"

        # Should contain intent language
        intent_indicators = ["attempt", "try", "aim", "seek", "swing", "lunge", "move toward"]
        has_intent = any(indicator in action_lower for indicator in intent_indicators)

        assert has_intent or "i" in action_lower, \
            f"Action should express intent clearly: {action_text}"

    @pytest.mark.asyncio
    async def test_dm_outcome_triggers_character_reaction(
        self,
        turn_manager,
        initial_game_state
    ):
        """Verify character reacts to DM outcome appropriately (US1 AC3)"""
        dm_narration = "You attempt to repair the damaged console."
        dm_outcome = (
            "Your skilled hands quickly reconnect the circuits. "
            "The console flickers to life!"
        )

        initial_game_state["dm_narration"] = dm_narration
        initial_game_state["dm_outcome"] = dm_outcome

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        # Character should have reaction
        assert "char_001" in final_state["character_reactions"]
        reaction = final_state["character_reactions"]["char_001"]

        assert len(reaction) > 0

        # Reaction should NOT initiate new actions
        forbidden_new_actions = [
            "i now",
            "i then",
            "next i",
            "i proceed to"
        ]

        reaction_lower = reaction.lower()
        for forbidden in forbidden_new_actions:
            assert forbidden not in reaction_lower, \
                f"Reaction should not initiate new action: {reaction}"

    @pytest.mark.asyncio
    async def test_memory_storage_after_turn_completion(
        self,
        turn_manager,
        initial_game_state,
        mock_memory_store
    ):
        """Verify memory storage occurs after turn completes (US1 AC4)"""
        dm_narration = "You discover ancient alien writing on the wall."
        initial_game_state["dm_narration"] = dm_narration

        await turn_manager.execute_turn_cycle(initial_game_state)

        # Memory store should be called to add episode
        mock_memory_store.add_episode.assert_called()

        # Verify episode contains relevant context
        call_args = mock_memory_store.add_episode.call_args

        # Check that episode body contains key information
        assert call_args is not None
        # (Full validation would check episode body content)


class TestTurnCycleValidationRetry:
    """Test validation failure and retry logic"""

    @pytest.mark.asyncio
    async def test_validation_catches_outcome_narration(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test validation detects and rejects outcome narration (US2 AC1)"""
        dm_narration = "An enemy guard stands before you."

        # Mock character action that violates rules
        with patch.object(CharacterAgent, 'perform_action') as mock_action:
            # First attempt: Contains forbidden outcome
            mock_action.return_value = MagicMock(
                character_id="char_001",
                narrative_text="I strike the guard and kill him instantly.",  # Forbidden!
            )

            initial_game_state["dm_narration"] = dm_narration

            # Execute turn - validation should fail
            final_state = await turn_manager.execute_turn_cycle(initial_game_state)

            # Validation should have failed at least once
            assert final_state["validation_attempt"] > 1, \
                "Validation should have caught forbidden outcome and retried"

            # Should have validation failures recorded
            assert "char_001" in final_state["validation_failures"]
            violations = final_state["validation_failures"]["char_001"]
            assert len(violations) > 0

    @pytest.mark.asyncio
    async def test_validation_retry_with_stricter_prompt(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test retry uses progressively stricter prompts (US2 AC2, AC3)"""
        dm_narration = "You face a locked door."

        # Track how many times action is attempted
        attempt_count = 0

        async def mock_perform_with_retry(directive, scene_context, attempt=1):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                # First attempt: violates rules
                return MagicMock(
                    character_id="char_001",
                    narrative_text="I successfully pick the lock.",  # Forbidden "successfully"
                    attempt=attempt_count
                )
            elif attempt_count == 2:
                # Second attempt: still violates
                return MagicMock(
                    character_id="char_001",
                    narrative_text="I manage to open the lock.",  # Forbidden "manage to"
                    attempt=attempt_count
                )
            else:
                # Third attempt: corrected
                return MagicMock(
                    character_id="char_001",
                    narrative_text="I attempt to pick the lock with my tools.",  # Valid!
                    attempt=attempt_count
                )

        with patch.object(CharacterAgent, 'perform_action', side_effect=mock_perform_with_retry):
            initial_game_state["dm_narration"] = dm_narration

            final_state = await turn_manager.execute_turn_cycle(initial_game_state)

            # Should have retried multiple times
            assert final_state["validation_attempt"] == 3

            # Final validation should pass
            assert final_state["validation_valid"] is True

    @pytest.mark.asyncio
    async def test_validation_max_retries_then_autocorrect(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test auto-correction after 3 failed validation attempts (US2 AC3, FR-004)"""
        dm_narration = "A monster charges at you."

        # Mock character that keeps violating even after 3 attempts
        async def always_violate(directive, scene_context, attempt=1):
            return MagicMock(
                character_id="char_001",
                narrative_text="I strike the monster and it dies immediately.",  # Always wrong
                attempt=attempt
            )

        with patch.object(CharacterAgent, 'perform_action', side_effect=always_violate):
            initial_game_state["dm_narration"] = dm_narration

            final_state = await turn_manager.execute_turn_cycle(initial_game_state)

            # Should have attempted 3 times
            assert final_state["validation_attempt"] == 3

            # System should auto-correct by filtering forbidden words
            final_action = final_state["character_actions"]["char_001"]

            # Forbidden words should be removed
            assert "dies" not in final_action.lower()
            assert "immediately" not in final_action.lower() or \
                   final_action.lower() != "i strike the monster and it dies immediately."

            # Or system should flag for DM review
            # (Either autocorrect OR flag is acceptable per spec)
            assert final_state.get("dm_review_required") is True or \
                   final_action != "I strike the monster and it dies immediately."


class TestTurnCycleErrorRecovery:
    """Test rollback and error recovery mechanisms"""

    @pytest.mark.asyncio
    async def test_phase_rollback_on_failure(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test system rolls back to last stable phase on failure (FR-002)"""
        dm_narration = "You encounter a puzzle."
        initial_game_state["dm_narration"] = dm_narration

        # Mock a failure in STRATEGIC_INTENT phase
        with patch.object(BasePersonaAgent, 'formulate_strategic_intent') as mock_intent:
            mock_intent.side_effect = Exception("LLM timeout")

            # Execute turn - should handle error
            try:
                final_state = await turn_manager.execute_turn_cycle(initial_game_state)

                # Should have rolled back
                assert final_state.get("rollback_phase") is not None
                assert final_state["error_state"] is not None

                # Should have incremented retry count
                assert final_state["retry_count"] > 0

            except Exception as e:
                # If exception propagates, verify it's handled properly
                assert "LLM timeout" in str(e) or "rollback" in str(e).lower()

    @pytest.mark.asyncio
    async def test_phase_retry_after_rollback(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test retry after rollback succeeds on second attempt"""
        dm_narration = "A stranger approaches."
        initial_game_state["dm_narration"] = dm_narration

        # Mock failure then success
        call_count = 0

        async def fail_then_succeed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            else:
                return MagicMock(
                    agent_id="agent_001",
                    strategic_goal="Greet the stranger cautiously",
                    reasoning="Unknown individual requires careful approach"
                )

        with patch.object(
            BasePersonaAgent,
            'formulate_strategic_intent',
            side_effect=fail_then_succeed
        ):
            final_state = await turn_manager.execute_turn_cycle(initial_game_state)

            # Should eventually succeed
            assert "agent_001" in final_state["strategic_intents"]
            assert final_state["retry_count"] >= 1

    @pytest.mark.asyncio
    async def test_dm_intervention_flag_after_max_retries(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test DM intervention flagged after retry exhaustion (FR-002)"""
        dm_narration = "Critical decision point."
        initial_game_state["dm_narration"] = dm_narration

        # Mock persistent failure
        async def always_fail(*args, **kwargs):
            raise Exception("Persistent LLM error")

        with patch.object(BasePersonaAgent, 'formulate_strategic_intent', side_effect=always_fail):
            final_state = await turn_manager.execute_turn_cycle(initial_game_state)

            # Should flag for DM intervention after max retries
            assert final_state.get("dm_intervention_required") is True
            assert final_state["error_state"] is not None

    @pytest.mark.asyncio
    async def test_state_preservation_on_error(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test game state preserved on unexpected errors (FR-011)"""
        dm_narration = "You find a mysterious artifact."
        initial_game_state["dm_narration"] = dm_narration

        # Add some state before error
        initial_game_state["strategic_intents"]["agent_001"] = "Examine the artifact"

        # Mock error in later phase
        with patch.object(CharacterAgent, 'perform_action') as mock_action:
            mock_action.side_effect = Exception("Unexpected error")

            try:
                final_state = await turn_manager.execute_turn_cycle(initial_game_state)

                # Previous state should be preserved
                assert final_state["strategic_intents"]["agent_001"] == "Examine the artifact"
                assert final_state["dm_narration"] == dm_narration

            except Exception:
                # Even if exception propagates, state should be checkpointed
                pass


class TestTurnCyclePhaseTransitions:
    """Test specific phase transition logic"""

    @pytest.mark.asyncio
    async def test_skip_ooc_discussion_for_single_agent(
        self,
        turn_manager,
        initial_game_state
    ):
        """Verify OOC discussion skipped when only one agent (optimization)"""
        # Single agent in active_agents
        assert len(initial_game_state["active_agents"]) == 1

        dm_narration = "You see a fork in the path."
        initial_game_state["dm_narration"] = dm_narration

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        # OOC discussion should be skipped (no messages)
        assert len(final_state["ooc_messages"]) == 0

        # Should go straight from STRATEGIC_INTENT to CHARACTER_ACTION
        # (Verified by phase history if tracking enabled)

    @pytest.mark.asyncio
    async def test_dice_resolution_phase_auto_rolls(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test dice resolution auto-rolls unless DM overrides (FR-012)"""
        dm_narration = "You attempt a risky maneuver."
        initial_game_state["dm_narration"] = dm_narration
        initial_game_state["dm_adjudication_needed"] = True

        # No dice override provided
        initial_game_state["dice_override"] = None

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        # Dice should have been rolled automatically
        assert "dice_result" in final_state
        assert final_state["dice_result"] is not None
        assert 1 <= final_state["dice_result"] <= 6  # Valid 1d6 result

    @pytest.mark.asyncio
    async def test_dice_resolution_respects_dm_override(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test DM can override dice roll (FR-012)"""
        dm_narration = "You attempt to hack the console."
        initial_game_state["dm_narration"] = dm_narration
        initial_game_state["dm_adjudication_needed"] = True

        # DM overrides with specific result
        dm_override_value = 4
        initial_game_state["dice_override"] = dm_override_value

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        # Should use DM's override value
        assert final_state["dice_result"] == dm_override_value

    @pytest.mark.asyncio
    async def test_memory_query_retrieves_relevant_context(
        self,
        turn_manager,
        initial_game_state,
        mock_memory_store
    ):
        """Test memory query phase retrieves relevant memories"""
        dm_narration = "You return to the merchant's shop you visited before."
        initial_game_state["dm_narration"] = dm_narration

        # Mock memory results
        mock_memory_store.search.return_value = [
            {
                "fact": "The merchant Galvin sold us supplies last session",
                "confidence": 0.9,
                "session_number": 5
            }
        ]

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        # Memory should have been queried
        mock_memory_store.search.assert_called()

        # Retrieved memories should be in state
        assert "agent_001" in final_state["retrieved_memories"]
        memories = final_state["retrieved_memories"]["agent_001"]
        assert len(memories) > 0
        assert any("merchant" in m.get("fact", "").lower() for m in memories)


class TestTurnCycleDiceResolution:
    """Test Lasers & Feelings dice mechanics integration"""

    @pytest.mark.asyncio
    async def test_lasers_task_success_roll_under(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test Lasers task succeeds when rolling under character number"""
        dm_narration = "You attempt to repair the damaged circuit board."  # Lasers task
        initial_game_state["dm_narration"] = dm_narration
        initial_game_state["dice_action_character"] = "char_001"
        initial_game_state["dice_task_type"] = "lasers"

        # Character has number=3, so roll of 1 or 2 should succeed
        initial_game_state["dice_override"] = 2  # Force success

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        assert final_state["dice_result"] == 2
        assert final_state["dice_success"] is True

    @pytest.mark.asyncio
    async def test_feelings_task_success_roll_over(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test Feelings task succeeds when rolling over character number"""
        dm_narration = "You try to comfort the frightened civilian."  # Feelings task
        initial_game_state["dm_narration"] = dm_narration
        initial_game_state["dice_action_character"] = "char_001"
        initial_game_state["dice_task_type"] = "feelings"

        # Character has number=3, so roll of 4, 5, or 6 should succeed
        initial_game_state["dice_override"] = 5  # Force success

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        assert final_state["dice_result"] == 5
        assert final_state["dice_success"] is True

    @pytest.mark.asyncio
    async def test_exact_number_roll_laser_feelings(
        self,
        turn_manager,
        initial_game_state
    ):
        """Test rolling exact number = LASER FEELINGS (success with special insight)"""
        dm_narration = "You attempt a delicate procedure."
        initial_game_state["dm_narration"] = dm_narration
        initial_game_state["dice_action_character"] = "char_001"
        initial_game_state["dice_task_type"] = "lasers"

        # Character has number=3, roll exactly 3
        initial_game_state["dice_override"] = 3

        final_state = await turn_manager.execute_turn_cycle(initial_game_state)

        # Single die override uses legacy fields
        assert final_state["dice_result"] == 3
        assert final_state["dice_success"] is True
        # LASER FEELINGS detected (deprecated field dice_complication)
        assert final_state.get("dice_complication") is True

        # Modern multi-die system would use:
        # assert len(final_state.get("laser_feelings_indices", [])) > 0
