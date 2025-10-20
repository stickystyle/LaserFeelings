# ABOUTME: Integration tests for LASER FEELINGS question/answer flow from character to DM to P2C message.
# ABOUTME: Tests end-to-end scenarios for exact-match dice rolls with GM questions and insights.

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis import Redis
from rq import Queue

from src.models.dice_models import LasersFeelingRollResult, RollOutcome
from src.models.game_state import GamePhase
from src.models.messages import MessageChannel
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


def _create_mock_job_for_no_laser_feelings_test(func, *args, **kwargs):
    """
    Helper function to create mock RQ job for test_no_laser_feelings_no_p2c_message.

    This function creates a mock job with appropriate results based on the worker function name:
    - formulate_strategic_intent: Returns strategic goal about analyzing alien creature
    - perform_action: Returns character action with gm_question about creature weakness
    - react_to_outcome: Returns character reaction to partial scanner data

    Args:
        func: Worker function (string path or function object)
        *args: Worker function arguments
        **kwargs: Worker function keyword arguments

    Returns:
        MagicMock: Mock job object with appropriate result data
    """
    job = MagicMock()

    # Extract function name from string path or function object
    if isinstance(func, str):
        func_name = func.split(".")[-1]
    else:
        func_name = func.__name__

    # Set basic job attributes
    job.id = f'job_{func_name}'
    job.is_failed = False
    job.refresh = MagicMock()

    # Set result based on function type
    if "formulate_strategic_intent" in func_name:
        job.result = {
            "agent_id": "agent_zara_001",
            "strategic_goal": "Analyze the alien creature",
            "reasoning": "Find weakness",
            "risk_assessment": "Low",
            "fallback_plan": "Retreat"
        }
    elif "perform_action" in func_name:
        job.result = {
            "character_id": "char_zara_001",
            "narrative_text": "I scan the creature for weak points.",
            "task_type": "lasers",
            "is_prepared": True,
            "prepared_justification": "Brought biological scanner",
            "is_expert": True,
            "expert_justification": "Trained in xenobiology",
            "is_helping": False,
            "gm_question": "What is the creature's weakness?"
        }
    elif "react_to_outcome" in func_name:
        job.result = {
            "character_id": "char_zara_001",
            "narrative_text": "My scanner shows partial data."
        }
    else:
        job.result = {}

    return job


@pytest.fixture
def mock_redis_for_laser_feelings():
    """Mock Redis client with stateful behavior for LASER FEELINGS tests"""
    redis = MagicMock(spec=Redis)

    # Track state in a dict
    state_store = {}

    # Track list data (for messages)
    list_store = {}

    def mock_hset(key, field, value):
        if key not in state_store:
            state_store[key] = {}
        state_store[key][field] = value
        return 1

    def mock_hget(key, field):
        return state_store.get(key, {}).get(field)

    def mock_hgetall(key):
        return state_store.get(key, {})

    def mock_exists(key):
        return 1 if key in state_store else 0

    def mock_rpush(key, value):
        if key not in list_store:
            list_store[key] = []
        list_store[key].append(value)
        return len(list_store[key])

    def mock_lrange(key, start, end):
        if key not in list_store:
            return []
        items = list_store[key]
        if start < 0:
            start = max(0, len(items) + start)
        if end < 0:
            end = len(items) + end + 1
        else:
            end = end + 1
        return items[start:end]

    # Configure mock methods
    redis.hset = MagicMock(side_effect=mock_hset)
    redis.hget = MagicMock(side_effect=mock_hget)
    redis.hgetall = MagicMock(side_effect=mock_hgetall)
    redis.exists = MagicMock(side_effect=mock_exists)
    redis.delete = MagicMock(return_value=1)
    redis.rpush = MagicMock(side_effect=mock_rpush)
    redis.lrange = MagicMock(side_effect=mock_lrange)
    redis.lpop = MagicMock(return_value=None)
    redis.set = MagicMock(return_value=True)
    redis.setex = MagicMock(return_value=True)
    redis.expire = MagicMock(return_value=True)
    redis.keys = MagicMock(return_value=[])
    redis.ping = MagicMock(return_value=True)

    return redis


@pytest.fixture
def mock_rq_queue_for_laser_feelings():
    """Mock RQ Queue for LASER FEELINGS worker jobs"""
    queue = MagicMock(spec=Queue)

    def mock_enqueue(func, *args, **kwargs):
        """Mock job enqueue - returns a completed job immediately"""
        job = MagicMock()

        # Extract function name
        if isinstance(func, str):
            func_name = func.split(".")[-1]
        else:
            func_name = func.__name__

        job.id = f"job_{func_name}"
        job.is_failed = False
        job.refresh = MagicMock()

        # Return plausible results based on function name
        if "formulate_strategic_intent" in func_name:
            job.result = {
                "agent_id": args[0] if args else "agent_zara_001",
                "strategic_goal": "Scan the mysterious alien signal",
                "reasoning": "Understanding the signal could reveal its purpose",
                "risk_assessment": "Low risk",
                "fallback_plan": "Retreat if signal appears hostile"
            }
        elif "perform_action" in func_name:
            # Check if we want to include a gm_question
            # Default action includes gm_question
            job.result = {
                "character_id": args[0] if args else "char_zara_001",
                "narrative_text": "I initiate a deep scan of the alien signal, analyzing its frequency patterns and origin vector.",
                "task_type": "lasers",
                "is_prepared": True,
                "prepared_justification": "I calibrated the sensors beforehand",
                "is_expert": True,
                "expert_justification": "Signal analysis is my expertise as engineer",
                "is_helping": False,
                "gm_question": "What is the signal's origin?"
            }
        elif "react_to_outcome" in func_name:
            job.result = {
                "character_id": args[0] if args else "char_zara_001",
                "narrative_text": "My optical sensors brighten with newfound understanding. 'Fascinating,' I murmur."
            }
        else:
            job.result = {}

        return job

    queue.enqueue = MagicMock(side_effect=mock_enqueue)
    return queue


@pytest.fixture
def zara_character_config_laser_feelings(tmp_path, monkeypatch):
    """Create Zara-7 character config file for LASER FEELINGS tests"""
    config_dir = tmp_path / "config" / "personalities"
    config_dir.mkdir(parents=True, exist_ok=True)

    character_config = {
        "agent_id": "agent_zara_001",
        "character_id": "char_zara_001",
        "name": "Zara-7",
        "style": "Android",
        "role": "Engineer",
        "number": 3,  # Balanced for testing both lasers and feelings
        "character_goal": "Protect crew through technical excellence",
        "equipment": ["Omnitool", "Sensor Array"]
    }

    config_file = config_dir / "char_zara_001_character.json"
    with open(config_file, "w") as f:
        json.dump(character_config, f)

    # Patch the module-level mapping to include our test agent
    # This is necessary because the mapping is loaded once at module import time
    import src.orchestration.state_machine as sm_module
    original_mapping = sm_module._AGENT_CHARACTER_MAPPING.copy()
    sm_module._AGENT_CHARACTER_MAPPING["agent_zara_001"] = "char_zara_001"

    yield config_file

    # Restore original mapping after test
    sm_module._AGENT_CHARACTER_MAPPING.clear()
    sm_module._AGENT_CHARACTER_MAPPING.update(original_mapping)


class TestLaserFeelingsFullFlowWithQuestion:
    """Test Scenario 1: Full LASER FEELINGS flow when character suggests a question"""

    @patch("src.orchestration.state_machine.roll_lasers_feelings")
    @patch("src.orchestration.state_machine.Queue")
    @patch("src.config.settings.Settings")
    def test_laser_feelings_with_gm_question_full_flow(
        self,
        mock_settings_class,
        mock_queue_class,
        mock_roll_fn,
        mock_redis_for_laser_feelings,
        mock_rq_queue_for_laser_feelings,
        zara_character_config_laser_feelings,
        tmp_path,
        monkeypatch
    ):
        """
        Test complete LASER FEELINGS flow when character suggests a question and DM provides answer.

        Verifies:
        - Character performs action with gm_question field populated
        - Dice roll results in exact number match (LASER FEELINGS)
        - Roll result contains the gm_question
        - DM input includes laser_feelings_answer
        - Answer is stored in game state
        - P2C message is sent to character with the answer
        - Message format: [LASER FEELINGS Insight]: {answer}
        """
        # Change working directory
        monkeypatch.chdir(tmp_path)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4o"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings_class.return_value = mock_settings

        # Configure Queue mock
        mock_queue_class.return_value = mock_rq_queue_for_laser_feelings

        # Mock dice roll to return LASER FEELINGS (exact match)
        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=True,
            is_helping=False,
            individual_rolls=[3],  # Exact match!
            die_successes=[True],
            laser_feelings_indices=[0],  # First die was exact match
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What is the signal's origin?",
            timestamp=datetime.now(timezone.utc)
        )
        mock_roll_fn.return_value = mock_roll_result

        # Mock OpenAI responses
        mock_openai = MagicMock()

        def mock_create(*args, **kwargs):
            """Context-aware OpenAI responses"""
            messages = kwargs.get("messages", [])
            prompt_content = " ".join([m.get("content", "") for m in messages]).lower()

            if "strategic_goal" in prompt_content:
                content = json.dumps({
                    "agent_id": "agent_zara_001",
                    "strategic_goal": "Scan the alien signal",
                    "reasoning": "Understanding signal purpose",
                    "risk_assessment": "Low",
                    "fallback_plan": "Retreat if hostile"
                })
            elif "narrative_text" in prompt_content and "scene" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I initiate a deep scan of the alien signal.",
                    "task_type": "lasers",
                    "is_prepared": True,
                    "prepared_justification": "Calibrated sensors beforehand",
                    "is_expert": True,
                    "expert_justification": "Signal analysis is my expertise",
                    "is_helping": False,
                    "gm_question": "What is the signal's origin?"
                })
            elif "narrative_text" in prompt_content and "outcome" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "My sensors brighten with understanding."
                })
            else:
                content = "Acknowledged"

            return MagicMock(
                choices=[MagicMock(message=MagicMock(content=content))],
                model="gpt-4o"
            )

        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            # Initialize orchestrator and message router
            orchestrator = TurnOrchestrator(mock_redis_for_laser_feelings)
            router = MessageRouter(mock_redis_for_laser_feelings)

            # Execute turn cycle (interrupts at adjudication)
            turn_result = orchestrator.execute_turn_cycle(
                dm_input="A mysterious alien signal pulses from deep space.",
                active_agents=["agent_zara_001"],
                turn_number=1,
                session_number=1
            )

            # Verify turn interrupted at adjudication
            assert turn_result["awaiting_dm_input"] is True
            assert turn_result["awaiting_phase"] == "dm_adjudication"

            # Verify character action includes gm_question
            character_actions = turn_result["character_actions"]
            assert "char_zara_001" in character_actions
            action_dict = character_actions["char_zara_001"]
            assert action_dict.get("gm_question") == "What is the signal's origin?"

            # Resume with DM adjudication (needs_dice=True, provide LASER FEELINGS answer)
            adjudication_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="adjudication",
                dm_input_data={
                    "needs_dice": True,
                    "laser_feelings_answer": "The signal originates from a derelict colony ship orbiting a dead star"
                }
            )

            # Verify dice roll executed and LASER FEELINGS detected
            # Should interrupt at dm_outcome phase
            assert adjudication_result["awaiting_dm_input"] is True
            assert adjudication_result["awaiting_phase"] == "dm_outcome"

            # Verify dice roll was called with gm_question
            mock_roll_fn.assert_called_once()
            call_kwargs = mock_roll_fn.call_args.kwargs
            assert call_kwargs["gm_question"] == "What is the signal's origin?"

            # Provide DM outcome narration
            final_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="outcome",
                dm_input_data={
                    "outcome_text": "Your sensors lock onto the signal source - it's a derelict colony ship!"
                }
            )

            # Verify turn completed
            assert final_result["success"] is True

            # Verify P2C message was sent to character with LASER FEELINGS answer
            p2c_messages = router.get_messages_for_agent(
                agent_id="char_zara_001",
                agent_type="character",
                limit=50
            )

            # Filter to P2C messages only
            p2c_only = [msg for msg in p2c_messages if msg.channel == MessageChannel.P2C]
            assert len(p2c_only) > 0, "Expected at least one P2C message"

            # Find LASER FEELINGS insight message
            laser_feelings_messages = [
                msg for msg in p2c_only
                if "[LASER FEELINGS Insight]:" in msg.content
            ]
            assert len(laser_feelings_messages) == 1, "Expected exactly one LASER FEELINGS insight message"

            laser_feelings_msg = laser_feelings_messages[0]
            assert "derelict colony ship" in laser_feelings_msg.content
            assert laser_feelings_msg.from_agent == "dm"
            assert "char_zara_001" in (laser_feelings_msg.to_agents or [])


class TestLaserFeelingsWithoutGMQuestion:
    """Test Scenario 2: LASER FEELINGS without GM question (free-form insight)"""

    @patch("src.orchestration.state_machine.roll_lasers_feelings")
    @patch("src.orchestration.state_machine.Queue")
    @patch("src.config.settings.Settings")
    def test_laser_feelings_without_gm_question(
        self,
        mock_settings_class,
        mock_queue_class,
        mock_roll_fn,
        mock_redis_for_laser_feelings,
        zara_character_config_laser_feelings,
        tmp_path,
        monkeypatch
    ):
        """
        Test LASER FEELINGS flow when character does NOT suggest a question.

        Verifies:
        - Character action has gm_question=None
        - Dice roll results in LASER FEELINGS
        - DM can still provide free-form answer
        - Answer flows through correctly to P2C message
        """
        monkeypatch.chdir(tmp_path)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4o"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings_class.return_value = mock_settings

        # Mock RQ queue that returns action WITHOUT gm_question
        queue = MagicMock(spec=Queue)

        def mock_enqueue(func, *args, **kwargs):
            job = MagicMock()
            func_name = func.split(".")[-1] if isinstance(func, str) else func.__name__
            job.id = f"job_{func_name}"
            job.is_failed = False
            job.refresh = MagicMock()

            if "formulate_strategic_intent" in func_name:
                job.result = {
                    "agent_id": "agent_zara_001",
                    "strategic_goal": "Navigate the asteroid field",
                    "reasoning": "Need to reach the station",
                    "risk_assessment": "Moderate",
                    "fallback_plan": "Find alternate route"
                }
            elif "perform_action" in func_name:
                # Action WITHOUT gm_question
                job.result = {
                    "character_id": "char_zara_001",
                    "narrative_text": "I deftly maneuver through the asteroid field.",
                    "task_type": "lasers",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "gm_question": None  # No question
                }
            elif "react_to_outcome" in func_name:
                job.result = {
                    "character_id": "char_zara_001",
                    "narrative_text": "I smile with relief as we clear the field."
                }
            else:
                job.result = {}

            return job

        queue.enqueue = MagicMock(side_effect=mock_enqueue)
        mock_queue_class.return_value = queue

        # Mock dice roll to return LASER FEELINGS
        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            is_helping=False,
            individual_rolls=[3],  # Exact match
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question=None,  # No question
            timestamp=datetime.now(timezone.utc)
        )
        mock_roll_fn.return_value = mock_roll_result

        # Mock OpenAI
        mock_openai = MagicMock()

        def mock_create(*args, **kwargs):
            return MagicMock(
                choices=[MagicMock(message=MagicMock(content="{}"))],
                model="gpt-4o"
            )

        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            orchestrator = TurnOrchestrator(mock_redis_for_laser_feelings)
            router = MessageRouter(mock_redis_for_laser_feelings)

            # Execute turn
            turn_result = orchestrator.execute_turn_cycle(
                dm_input="You enter a dense asteroid field.",
                active_agents=["agent_zara_001"],
                turn_number=1,
                session_number=1
            )

            assert turn_result["awaiting_dm_input"] is True

            # Verify gm_question is None in action
            action_dict = turn_result["character_actions"]["char_zara_001"]
            assert action_dict.get("gm_question") is None

            # DM provides free-form insight despite no question
            adjudication_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="adjudication",
                dm_input_data={
                    "needs_dice": True,
                    "laser_feelings_answer": "You notice a hidden shortcut through the asteroids"
                }
            )

            assert adjudication_result["awaiting_dm_input"] is True

            # Provide outcome
            final_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="outcome",
                dm_input_data={
                    "outcome_text": "You spot a clear path and navigate through safely."
                }
            )

            assert final_result["success"] is True

            # Verify P2C message sent with free-form insight
            p2c_messages = router.get_messages_for_agent(
                agent_id="char_zara_001",
                agent_type="character",
                limit=50
            )

            laser_feelings_messages = [
                msg for msg in p2c_messages
                if msg.channel == MessageChannel.P2C and "[LASER FEELINGS Insight]:" in msg.content
            ]
            assert len(laser_feelings_messages) == 1

            laser_feelings_msg = laser_feelings_messages[0]
            assert "hidden shortcut" in laser_feelings_msg.content


class TestNoLaserFeelings:
    """Test Scenario 3: No LASER FEELINGS occurs (no exact match)"""

    @patch("src.orchestration.state_machine.roll_lasers_feelings")
    @patch("src.orchestration.state_machine.Queue")
    @patch("src.config.settings.Settings")
    def test_no_laser_feelings_no_p2c_message(
        self,
        mock_settings_class,
        mock_queue_class,
        mock_roll_fn,
        mock_redis_for_laser_feelings,
        mock_rq_queue_for_laser_feelings,
        zara_character_config_laser_feelings,
        tmp_path,
        monkeypatch
    ):
        """
        Test that when NO LASER FEELINGS occurs, no P2C message is sent.

        Verifies:
        - Character action includes gm_question
        - Dice roll does NOT result in exact match
        - No P2C message is sent
        - State has no laser_feelings_answer
        """
        monkeypatch.chdir(tmp_path)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4o"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings_class.return_value = mock_settings

        # Configure Queue mock
        mock_queue_class.return_value = mock_rq_queue_for_laser_feelings

        # Mock dice roll to NOT return LASER FEELINGS (no exact match)
        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=True,
            is_helping=False,
            individual_rolls=[2],  # NOT exact match (rolled 2, number is 3)
            die_successes=[True],  # Success because lasers task: roll < 3
            laser_feelings_indices=[],  # No exact matches
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What is the creature's weakness?",  # Question present but no LASER FEELINGS
            timestamp=datetime.now(timezone.utc)
        )
        mock_roll_fn.return_value = mock_roll_result

        # Override mock RQ queue to return specific gm_question for this test
        mock_queue_class.return_value.enqueue.side_effect = _create_mock_job_for_no_laser_feelings_test

        # Mock OpenAI
        mock_openai = MagicMock()

        def mock_create(*args, **kwargs):
            return MagicMock(
                choices=[MagicMock(message=MagicMock(content="{}"))],
                model="gpt-4o"
            )

        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            orchestrator = TurnOrchestrator(mock_redis_for_laser_feelings)
            router = MessageRouter(mock_redis_for_laser_feelings)

            # Execute turn
            turn_result = orchestrator.execute_turn_cycle(
                dm_input="A strange alien creature blocks your path.",
                active_agents=["agent_zara_001"],
                turn_number=1,
                session_number=1
            )

            assert turn_result["awaiting_dm_input"] is True

            # Verify gm_question is present
            action_dict = turn_result["character_actions"]["char_zara_001"]
            assert action_dict.get("gm_question") == "What is the creature's weakness?"

            # DM does NOT provide laser_feelings_answer (no exact match occurred)
            adjudication_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="adjudication",
                dm_input_data={
                    "needs_dice": True
                    # No laser_feelings_answer field
                }
            )

            assert adjudication_result["awaiting_dm_input"] is True

            # Provide outcome
            final_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="outcome",
                dm_input_data={
                    "outcome_text": "Your scan reveals partial information about the creature."
                }
            )

            assert final_result["success"] is True

            # Verify NO P2C message with LASER FEELINGS insight was sent
            p2c_messages = router.get_messages_for_agent(
                agent_id="char_zara_001",
                agent_type="character",
                limit=50
            )

            laser_feelings_messages = [
                msg for msg in p2c_messages
                if msg.channel == MessageChannel.P2C and "[LASER FEELINGS Insight]:" in msg.content
            ]
            assert len(laser_feelings_messages) == 0, "Should not send LASER FEELINGS message when no exact match"


class TestLaserFeelingsDMProvidesNoAnswer:
    """Test Scenario 4: LASER FEELINGS occurs but DM provides no answer"""

    @patch("src.orchestration.state_machine.roll_lasers_feelings")
    @patch("src.orchestration.state_machine.Queue")
    @patch("src.config.settings.Settings")
    def test_laser_feelings_dm_no_answer_graceful_handling(
        self,
        mock_settings_class,
        mock_queue_class,
        mock_roll_fn,
        mock_redis_for_laser_feelings,
        mock_rq_queue_for_laser_feelings,
        zara_character_config_laser_feelings,
        tmp_path,
        monkeypatch
    ):
        """
        Test graceful handling when LASER FEELINGS occurs but DM provides no answer.

        Verifies:
        - Dice roll results in LASER FEELINGS
        - DM input has laser_feelings_answer: None
        - No P2C message is sent
        - No errors occur
        """
        monkeypatch.chdir(tmp_path)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4o"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings_class.return_value = mock_settings

        # Configure Queue mock
        mock_queue_class.return_value = mock_rq_queue_for_laser_feelings

        # Mock dice roll to return LASER FEELINGS
        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=False,
            is_helping=False,
            individual_rolls=[3],  # Exact match
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="Who built this ancient station?",
            timestamp=datetime.now(timezone.utc)
        )
        mock_roll_fn.return_value = mock_roll_result

        # Mock OpenAI
        mock_openai = MagicMock()

        def mock_create(*args, **kwargs):
            messages = kwargs.get("messages", [])
            prompt_content = " ".join([m.get("content", "") for m in messages]).lower()

            if "strategic_goal" in prompt_content:
                content = json.dumps({
                    "agent_id": "agent_zara_001",
                    "strategic_goal": "Investigate the ancient station",
                    "reasoning": "Discover its origin",
                    "risk_assessment": "Low",
                    "fallback_plan": "Document findings"
                })
            elif "narrative_text" in prompt_content and "scene" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I examine the station's architecture for clues.",
                    "task_type": "lasers",
                    "is_prepared": True,
                    "prepared_justification": "Studied archaeological methods",
                    "is_expert": False,
                    "is_helping": False,
                    "gm_question": "Who built this ancient station?"
                })
            elif "narrative_text" in prompt_content and "outcome" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I record my observations methodically."
                })
            else:
                content = "Acknowledged"

            return MagicMock(
                choices=[MagicMock(message=MagicMock(content=content))],
                model="gpt-4o"
            )

        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            orchestrator = TurnOrchestrator(mock_redis_for_laser_feelings)
            router = MessageRouter(mock_redis_for_laser_feelings)

            # Execute turn
            turn_result = orchestrator.execute_turn_cycle(
                dm_input="You arrive at an ancient, abandoned space station.",
                active_agents=["agent_zara_001"],
                turn_number=1,
                session_number=1
            )

            assert turn_result["awaiting_dm_input"] is True

            # DM provides laser_feelings_answer: None (explicitly chooses not to answer)
            adjudication_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="adjudication",
                dm_input_data={
                    "needs_dice": True,
                    "laser_feelings_answer": None  # DM declines to provide insight
                }
            )

            assert adjudication_result["awaiting_dm_input"] is True

            # Provide outcome
            final_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="outcome",
                dm_input_data={
                    "outcome_text": "You find some clues but no definitive answers."
                }
            )

            # Verify turn completed without errors
            assert final_result["success"] is True

            # Verify NO P2C message sent (DM chose not to provide insight)
            p2c_messages = router.get_messages_for_agent(
                agent_id="char_zara_001",
                agent_type="character",
                limit=50
            )

            laser_feelings_messages = [
                msg for msg in p2c_messages
                if msg.channel == MessageChannel.P2C and "[LASER FEELINGS Insight]:" in msg.content
            ]
            assert len(laser_feelings_messages) == 0, "Should not send message when DM provides no answer"


class TestLaserFeelingsAnswerProvidedDuringOutcome:
    """Test Scenario 5: LASER FEELINGS answer provided during outcome phase instead of adjudication"""

    @patch("src.orchestration.state_machine.roll_lasers_feelings")
    @patch("src.orchestration.state_machine.Queue")
    @patch("src.config.settings.Settings")
    def test_laser_feelings_answer_during_outcome_phase(
        self,
        mock_settings_class,
        mock_queue_class,
        mock_roll_fn,
        mock_redis_for_laser_feelings,
        mock_rq_queue_for_laser_feelings,
        zara_character_config_laser_feelings,
        tmp_path,
        monkeypatch
    ):
        """
        Test that LASER FEELINGS answer can be provided during outcome phase.

        Verifies:
        - DM can skip providing answer during adjudication
        - DM can provide answer during outcome phase
        - P2C message is sent correctly regardless of when answer is provided
        """
        monkeypatch.chdir(tmp_path)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4o"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings_class.return_value = mock_settings

        # Configure Queue mock
        mock_queue_class.return_value = mock_rq_queue_for_laser_feelings

        # Mock dice roll to return LASER FEELINGS
        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="feelings",
            is_prepared=False,
            is_expert=False,
            is_helping=False,
            individual_rolls=[3],  # Exact match
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What is the captain really feeling?",
            timestamp=datetime.now(timezone.utc)
        )
        mock_roll_fn.return_value = mock_roll_result

        # Mock OpenAI
        mock_openai = MagicMock()

        def mock_create(*args, **kwargs):
            messages = kwargs.get("messages", [])
            prompt_content = " ".join([m.get("content", "") for m in messages]).lower()

            if "strategic_goal" in prompt_content:
                content = json.dumps({
                    "agent_id": "agent_zara_001",
                    "strategic_goal": "Read the captain's emotions",
                    "reasoning": "Understand their true state of mind",
                    "risk_assessment": "Low",
                    "fallback_plan": "Ask directly"
                })
            elif "narrative_text" in prompt_content and "scene" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I observe the captain's body language carefully.",
                    "task_type": "feelings",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "gm_question": "What is the captain really feeling?"
                })
            elif "narrative_text" in prompt_content and "outcome" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I process the subtle emotional cues."
                })
            else:
                content = "Acknowledged"

            return MagicMock(
                choices=[MagicMock(message=MagicMock(content=content))],
                model="gpt-4o"
            )

        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            orchestrator = TurnOrchestrator(mock_redis_for_laser_feelings)
            router = MessageRouter(mock_redis_for_laser_feelings)

            # Execute turn
            turn_result = orchestrator.execute_turn_cycle(
                dm_input="The captain stands silently, staring at the viewscreen.",
                active_agents=["agent_zara_001"],
                turn_number=1,
                session_number=1
            )

            assert turn_result["awaiting_dm_input"] is True

            # DM does NOT provide answer during adjudication
            adjudication_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="adjudication",
                dm_input_data={
                    "needs_dice": True
                    # No laser_feelings_answer
                }
            )

            assert adjudication_result["awaiting_dm_input"] is True

            # DM provides answer during OUTCOME phase
            final_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="outcome",
                dm_input_data={
                    "outcome_text": "You sense deep regret and guilt in the captain's demeanor.",
                    "laser_feelings_answer": "The captain feels overwhelming guilt about abandoning their former crew"
                }
            )

            assert final_result["success"] is True

            # Verify P2C message sent with answer
            p2c_messages = router.get_messages_for_agent(
                agent_id="char_zara_001",
                agent_type="character",
                limit=50
            )

            laser_feelings_messages = [
                msg for msg in p2c_messages
                if msg.channel == MessageChannel.P2C and "[LASER FEELINGS Insight]:" in msg.content
            ]
            assert len(laser_feelings_messages) == 1

            laser_feelings_msg = laser_feelings_messages[0]
            assert "overwhelming guilt" in laser_feelings_msg.content
            assert "abandoning their former crew" in laser_feelings_msg.content


class TestLaserFeelingsFallbackMapping:
    """Test Scenario 6: Character ID fallback mapping verification"""

    @patch("src.orchestration.state_machine.roll_lasers_feelings")
    @patch("src.orchestration.state_machine.Queue")
    @patch("src.config.settings.Settings")
    def test_character_id_fallback_to_agent_mapping(
        self,
        mock_settings_class,
        mock_queue_class,
        mock_roll_fn,
        mock_redis_for_laser_feelings,
        mock_rq_queue_for_laser_feelings,
        zara_character_config_laser_feelings,
        tmp_path,
        monkeypatch
    ):
        """
        Test that when dice_action_character is not in state, fallback to agent mapping works.

        Verifies:
        - dice_action_character is not set in state initially
        - System falls back to using active_agents and mapping to character
        - P2C message is still sent successfully via fallback path
        - No errors occur during fallback

        This tests the else branch at line 626-628 in state_machine.py:
            if not character_id:
                if state["active_agents"]:
                    agent_id = state["active_agents"][0]
                    character_id = _get_character_id_for_agent(agent_id)
        """
        monkeypatch.chdir(tmp_path)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4o"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings_class.return_value = mock_settings

        # Configure Queue mock
        mock_queue_class.return_value = mock_rq_queue_for_laser_feelings

        # Mock dice roll to return LASER FEELINGS
        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=True,
            is_helping=False,
            individual_rolls=[3],  # Exact match
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What powers this ancient device?",
            timestamp=datetime.now(timezone.utc)
        )
        mock_roll_fn.return_value = mock_roll_result

        # Mock OpenAI
        mock_openai = MagicMock()

        def mock_create(*args, **kwargs):
            messages = kwargs.get("messages", [])
            prompt_content = " ".join([m.get("content", "") for m in messages]).lower()

            if "strategic_goal" in prompt_content:
                content = json.dumps({
                    "agent_id": "agent_zara_001",
                    "strategic_goal": "Examine the ancient device",
                    "reasoning": "Understand its power source",
                    "risk_assessment": "Low",
                    "fallback_plan": "Document findings"
                })
            elif "narrative_text" in prompt_content and "scene" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I analyze the device's energy signature.",
                    "task_type": "lasers",
                    "is_prepared": True,
                    "prepared_justification": "Brought energy scanner",
                    "is_expert": True,
                    "expert_justification": "Expert in power systems",
                    "is_helping": False,
                    "gm_question": "What powers this ancient device?"
                })
            elif "narrative_text" in prompt_content and "outcome" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I record the energy readings carefully."
                })
            else:
                content = "Acknowledged"

            return MagicMock(
                choices=[MagicMock(message=MagicMock(content=content))],
                model="gpt-4o"
            )

        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            orchestrator = TurnOrchestrator(mock_redis_for_laser_feelings)
            router = MessageRouter(mock_redis_for_laser_feelings)

            # Execute turn
            turn_result = orchestrator.execute_turn_cycle(
                dm_input="You discover an ancient alien device.",
                active_agents=["agent_zara_001"],
                turn_number=1,
                session_number=1
            )

            assert turn_result["awaiting_dm_input"] is True

            # Resume with DM adjudication and LASER FEELINGS answer
            adjudication_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="adjudication",
                dm_input_data={
                    "needs_dice": True,
                    "laser_feelings_answer": "The device draws power from subspace"
                }
            )

            assert adjudication_result["awaiting_dm_input"] is True

            # Provide outcome
            final_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="outcome",
                dm_input_data={
                    "outcome_text": "Your scanner reveals the device's power source."
                }
            )

            # Verify turn completed successfully
            assert final_result["success"] is True

            # Verify P2C message was sent (fallback path worked)
            p2c_messages = router.get_messages_for_agent(
                agent_id="char_zara_001",
                agent_type="character",
                limit=50
            )

            laser_feelings_messages = [
                msg for msg in p2c_messages
                if msg.channel == MessageChannel.P2C and "[LASER FEELINGS Insight]:" in msg.content
            ]
            assert len(laser_feelings_messages) == 1, "Should send P2C message via fallback mapping"

            laser_feelings_msg = laser_feelings_messages[0]
            assert "subspace" in laser_feelings_msg.content
            assert laser_feelings_msg.from_agent == "dm"
            assert "char_zara_001" in (laser_feelings_msg.to_agents or [])


class TestLaserFeelingsMultipleDice:
    """Test Scenario 7: Multiple dice showing exact match (LASER FEELINGS)"""

    @patch("src.orchestration.state_machine.roll_lasers_feelings")
    @patch("src.orchestration.state_machine.Queue")
    @patch("src.config.settings.Settings")
    def test_multiple_laser_feelings_dice(
        self,
        mock_settings_class,
        mock_queue_class,
        mock_roll_fn,
        mock_redis_for_laser_feelings,
        mock_rq_queue_for_laser_feelings,
        zara_character_config_laser_feelings,
        tmp_path,
        monkeypatch
    ):
        """
        Test rolling multiple dice where 2+ dice show exact match.

        Verifies:
        - Dice roll with 3d6 where 2 dice match character number
        - laser_feelings_indices contains multiple indices
        - Single P2C message is sent (not multiple messages)
        - P2C message acknowledges the insight
        """
        monkeypatch.chdir(tmp_path)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4o"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings_class.return_value = mock_settings

        # Configure Queue mock
        mock_queue_class.return_value = mock_rq_queue_for_laser_feelings

        # Mock dice roll to return MULTIPLE LASER FEELINGS (2 exact matches out of 3 dice)
        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=True,
            is_expert=True,
            is_helping=True,  # Rolling 3 dice
            individual_rolls=[3, 2, 3],  # First and third dice are exact matches!
            die_successes=[True, True, True],  # All successes
            laser_feelings_indices=[0, 2],  # Two exact matches
            total_successes=3,
            outcome=RollOutcome.CRITICAL,  # 3 successes = CRITICAL
            gm_question="How can we prevent the reactor meltdown?",
            timestamp=datetime.now(timezone.utc)
        )
        mock_roll_fn.return_value = mock_roll_result

        # Mock OpenAI
        mock_openai = MagicMock()

        def mock_create(*args, **kwargs):
            messages = kwargs.get("messages", [])
            prompt_content = " ".join([m.get("content", "") for m in messages]).lower()

            if "strategic_goal" in prompt_content:
                content = json.dumps({
                    "agent_id": "agent_zara_001",
                    "strategic_goal": "Stabilize the reactor",
                    "reasoning": "Prevent catastrophic failure",
                    "risk_assessment": "High",
                    "fallback_plan": "Evacuate immediately"
                })
            elif "narrative_text" in prompt_content and "scene" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "Working with the crew, I analyze the reactor core.",
                    "task_type": "lasers",
                    "is_prepared": True,
                    "prepared_justification": "Prepared emergency protocols",
                    "is_expert": True,
                    "expert_justification": "Reactor specialist",
                    "is_helping": True,
                    "gm_question": "How can we prevent the reactor meltdown?"
                })
            elif "narrative_text" in prompt_content and "outcome" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "My calculations reveal the solution!"
                })
            else:
                content = "Acknowledged"

            return MagicMock(
                choices=[MagicMock(message=MagicMock(content=content))],
                model="gpt-4o"
            )

        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            orchestrator = TurnOrchestrator(mock_redis_for_laser_feelings)
            router = MessageRouter(mock_redis_for_laser_feelings)

            # Execute turn
            turn_result = orchestrator.execute_turn_cycle(
                dm_input="The reactor core begins to destabilize!",
                active_agents=["agent_zara_001"],
                turn_number=1,
                session_number=1
            )

            assert turn_result["awaiting_dm_input"] is True

            # Resume with DM adjudication and LASER FEELINGS answer
            adjudication_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="adjudication",
                dm_input_data={
                    "needs_dice": True,
                    "laser_feelings_answer": "Reverse the polarity of the antimatter containment field"
                }
            )

            assert adjudication_result["awaiting_dm_input"] is True

            # Provide outcome
            final_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="outcome",
                dm_input_data={
                    "outcome_text": "Your brilliant insight saves the ship!"
                }
            )

            assert final_result["success"] is True

            # Verify P2C message sent
            p2c_messages = router.get_messages_for_agent(
                agent_id="char_zara_001",
                agent_type="character",
                limit=50
            )

            laser_feelings_messages = [
                msg for msg in p2c_messages
                if msg.channel == MessageChannel.P2C and "[LASER FEELINGS Insight]:" in msg.content
            ]

            # Should send exactly ONE message even with multiple exact matches
            assert len(laser_feelings_messages) == 1, "Should send single P2C message even with multiple exact matches"

            laser_feelings_msg = laser_feelings_messages[0]
            assert "antimatter containment field" in laser_feelings_msg.content
            assert laser_feelings_msg.from_agent == "dm"
            assert "char_zara_001" in (laser_feelings_msg.to_agents or [])


class TestLaserFeelingsEmptyStringAnswer:
    """Test Scenario 8: Empty string laser_feelings_answer handling"""

    @patch("src.orchestration.state_machine.roll_lasers_feelings")
    @patch("src.orchestration.state_machine.Queue")
    @patch("src.config.settings.Settings")
    def test_empty_string_laser_feelings_answer_no_message(
        self,
        mock_settings_class,
        mock_queue_class,
        mock_roll_fn,
        mock_redis_for_laser_feelings,
        mock_rq_queue_for_laser_feelings,
        zara_character_config_laser_feelings,
        tmp_path,
        monkeypatch
    ):
        """
        Test that empty string laser_feelings_answer does not send P2C message.

        Verifies:
        - Dice roll results in LASER FEELINGS
        - DM provides laser_feelings_answer="" (empty string)
        - Empty string is treated as falsy (same as None)
        - No P2C message is sent
        - Conditional `if laser_feelings_answer:` properly filters empty strings
        """
        monkeypatch.chdir(tmp_path)

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4o"
        mock_settings.redis_url = "redis://localhost:6379"
        mock_settings_class.return_value = mock_settings

        # Configure Queue mock
        mock_queue_class.return_value = mock_rq_queue_for_laser_feelings

        # Mock dice roll to return LASER FEELINGS
        mock_roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="feelings",
            is_prepared=False,
            is_expert=False,
            is_helping=False,
            individual_rolls=[3],  # Exact match
            die_successes=[True],
            laser_feelings_indices=[0],
            total_successes=1,
            outcome=RollOutcome.BARELY,
            gm_question="What motivates the ambassador?",
            timestamp=datetime.now(timezone.utc)
        )
        mock_roll_fn.return_value = mock_roll_result

        # Mock OpenAI
        mock_openai = MagicMock()

        def mock_create(*args, **kwargs):
            messages = kwargs.get("messages", [])
            prompt_content = " ".join([m.get("content", "") for m in messages]).lower()

            if "strategic_goal" in prompt_content:
                content = json.dumps({
                    "agent_id": "agent_zara_001",
                    "strategic_goal": "Understand the ambassador",
                    "reasoning": "Learn their motivations",
                    "risk_assessment": "Low",
                    "fallback_plan": "Observe behavior"
                })
            elif "narrative_text" in prompt_content and "scene" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I study the ambassador's reactions.",
                    "task_type": "feelings",
                    "is_prepared": False,
                    "is_expert": False,
                    "is_helping": False,
                    "gm_question": "What motivates the ambassador?"
                })
            elif "narrative_text" in prompt_content and "outcome" in prompt_content:
                content = json.dumps({
                    "character_id": "char_zara_001",
                    "narrative_text": "I process my observations carefully."
                })
            else:
                content = "Acknowledged"

            return MagicMock(
                choices=[MagicMock(message=MagicMock(content=content))],
                model="gpt-4o"
            )

        mock_openai.chat.completions.create = AsyncMock(side_effect=mock_create)

        with patch("openai.AsyncOpenAI", return_value=mock_openai):
            orchestrator = TurnOrchestrator(mock_redis_for_laser_feelings)
            router = MessageRouter(mock_redis_for_laser_feelings)

            # Execute turn
            turn_result = orchestrator.execute_turn_cycle(
                dm_input="The ambassador enters the room with an unreadable expression.",
                active_agents=["agent_zara_001"],
                turn_number=1,
                session_number=1
            )

            assert turn_result["awaiting_dm_input"] is True

            # Resume with DM adjudication - provide EMPTY STRING answer
            adjudication_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="adjudication",
                dm_input_data={
                    "needs_dice": True,
                    "laser_feelings_answer": ""  # Empty string (should be treated as falsy)
                }
            )

            assert adjudication_result["awaiting_dm_input"] is True

            # Provide outcome
            final_result = orchestrator.resume_turn_with_dm_input(
                session_number=1,
                dm_input_type="outcome",
                dm_input_data={
                    "outcome_text": "The ambassador remains enigmatic."
                }
            )

            assert final_result["success"] is True

            # Verify NO P2C message sent (empty string treated as falsy)
            p2c_messages = router.get_messages_for_agent(
                agent_id="char_zara_001",
                agent_type="character",
                limit=50
            )

            laser_feelings_messages = [
                msg for msg in p2c_messages
                if msg.channel == MessageChannel.P2C and "[LASER FEELINGS Insight]:" in msg.content
            ]
            assert len(laser_feelings_messages) == 0, "Should not send P2C message when answer is empty string"
