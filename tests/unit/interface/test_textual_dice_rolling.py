# ABOUTME: Unit tests for DMTextualInterface dice rolling functionality.
# ABOUTME: Tests character-suggested rolls, DM override rolls, and roll result display.

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from src.interface.dm_textual import DMTextualInterface
from src.models.dice_models import LasersFeelingRollResult, RollOutcome
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


@pytest.fixture
def mock_orchestrator():
    return Mock(spec=TurnOrchestrator)


@pytest.fixture
def mock_router():
    return Mock(spec=MessageRouter)


@pytest.fixture
def app(mock_orchestrator, mock_router):
    app_instance = DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)
    # Mock write_game_log and update_turn_status to avoid Textual screen initialization issues
    app_instance.write_game_log = Mock()
    app_instance.update_turn_status = Mock()
    return app_instance


@pytest.fixture
def sample_character_config():
    """Sample character configuration with number"""
    return {
        "character_id": "char_zara_001",
        "name": "Zara-7",
        "number": 2,
        "agent_id": "agent_alex_001"
    }


@pytest.fixture
def sample_character_actions():
    """Sample character actions dict with roll parameters"""
    return {
        "char_zara_001": {
            "narrative_text": "I repair the engine",
            "task_type": "lasers",
            "is_prepared": True,
            "is_expert": False,
            "is_helping": False,
            "gm_question": None
        }
    }


@pytest.fixture
def sample_turn_result(sample_character_actions):
    """Sample turn result with character actions"""
    return {
        "character_actions": sample_character_actions,
        "phase_completed": "character_action",
        "awaiting_dm_input": True,
        "awaiting_phase": "dm_adjudication"
    }


def test_execute_character_suggested_roll_success(
    app, sample_character_config, sample_character_actions
):
    """Test successful execution of character-suggested roll"""
    # Setup
    app._character_configs["char_zara_001"] = sample_character_config
    app._character_names["char_zara_001"] = "Zara-7"

    # Execute
    result = app._execute_character_suggested_roll(sample_character_actions)

    # Assert
    assert result["success"] is True
    assert "roll_result" in result
    assert isinstance(result["roll_result"], LasersFeelingRollResult)
    assert result["roll_result"].character_number == 2
    assert result["roll_result"].task_type == "lasers"
    assert result["roll_result"].is_prepared is True
    assert result["roll_result"].is_expert is False


def test_execute_character_suggested_roll_uses_current_turn_result(
    app, sample_character_config, sample_turn_result
):
    """Test roll execution uses _current_turn_result when no character_actions provided"""
    # Setup
    app._character_configs["char_zara_001"] = sample_character_config
    app._character_names["char_zara_001"] = "Zara-7"
    app._current_turn_result = sample_turn_result

    # Execute without providing character_actions
    result = app._execute_character_suggested_roll()

    # Assert
    assert result["success"] is True
    assert "roll_result" in result


def test_execute_character_suggested_roll_no_turn_state(app):
    """Test error handling when no turn state available"""
    # Execute without turn state
    result = app._execute_character_suggested_roll()

    # Assert
    assert result["success"] is False
    assert "error" in result
    assert "No turn state available" in result["error"]
    assert "suggestion" in result


def test_execute_character_suggested_roll_no_character_actions(app):
    """Test error handling when character_actions is empty"""
    # Setup
    app._current_turn_result = {"character_actions": {}}

    # Execute
    result = app._execute_character_suggested_roll()

    # Assert
    assert result["success"] is False
    assert "error" in result
    assert "No character actions available" in result["error"]


def test_execute_character_suggested_roll_missing_task_type(app, sample_character_config):
    """Test error handling when no task_type specified"""
    # Setup
    app._character_configs["char_zara_001"] = sample_character_config
    character_actions = {
        "char_zara_001": {
            "narrative_text": "I do something",
            # Missing task_type
        }
    }

    # Execute
    result = app._execute_character_suggested_roll(character_actions)

    # Assert
    assert result["success"] is False
    assert "error" in result
    assert "No dice roll suggestion available" in result["error"]


def test_execute_character_suggested_roll_missing_character_config(app, sample_character_actions):
    """Test error handling when character config not found"""
    # Don't add character config
    # Execute
    result = app._execute_character_suggested_roll(sample_character_actions)

    # Assert
    assert result["success"] is False
    assert "error" in result
    assert "Character config not found" in result["error"]


def test_execute_character_suggested_roll_missing_character_number(app, sample_character_actions):
    """Test error handling when character number missing in config"""
    # Setup with config missing number
    app._character_configs["char_zara_001"] = {
        "character_id": "char_zara_001",
        "name": "Zara-7"
        # Missing number
    }

    # Execute
    result = app._execute_character_suggested_roll(sample_character_actions)

    # Assert
    assert result["success"] is False
    assert "error" in result
    assert "Character number missing" in result["error"]


def test_execute_character_suggested_roll_extracts_all_modifiers(app, sample_character_config):
    """Test that all modifiers are correctly extracted from action_dict"""
    # Setup
    app._character_configs["char_zara_001"] = sample_character_config
    app._character_names["char_zara_001"] = "Zara-7"
    character_actions = {
        "char_zara_001": {
            "task_type": "feelings",
            "is_prepared": True,
            "is_expert": True,
            "is_helping": False,
            "gm_question": "How many guards are there?"
        }
    }

    # Execute
    result = app._execute_character_suggested_roll(character_actions)

    # Assert
    assert result["success"] is True
    roll_result = result["roll_result"]
    assert roll_result.task_type == "feelings"
    assert roll_result.is_prepared is True
    assert roll_result.is_expert is True
    assert roll_result.gm_question == "How many guards are there?"
    # Should roll 3d6 (base + prepared + expert)
    assert roll_result.dice_count == 3


def test_execute_character_suggested_roll_calculates_dice_count(app, sample_character_config):
    """Test that dice count is calculated correctly based on modifiers"""
    # Setup
    app._character_configs["char_zara_001"] = sample_character_config
    app._character_names["char_zara_001"] = "Zara-7"

    # Test base roll (1d6)
    character_actions = {
        "char_zara_001": {
            "task_type": "lasers",
            "is_prepared": False,
            "is_expert": False,
            "is_helping": False
        }
    }
    result = app._execute_character_suggested_roll(character_actions)
    assert result["success"] is True
    assert result["roll_result"].dice_count == 1

    # Test prepared only (2d6)
    character_actions["char_zara_001"]["is_prepared"] = True
    result = app._execute_character_suggested_roll(character_actions)
    assert result["success"] is True
    assert result["roll_result"].dice_count == 2

    # Test prepared + expert (3d6, max)
    character_actions["char_zara_001"]["is_expert"] = True
    result = app._execute_character_suggested_roll(character_actions)
    assert result["success"] is True
    assert result["roll_result"].dice_count == 3


def test_display_roll_result_shows_outcome(app):
    """Test that roll result is displayed with correct outcome"""
    # Create sample roll result
    roll_result = LasersFeelingRollResult(
        character_number=3,
        task_type="lasers",
        is_prepared=True,
        is_expert=False,
        is_helping=False,
        individual_rolls=[2, 1],
        die_successes=[True, True],
        laser_feelings_indices=[],
        total_successes=2,
        outcome=RollOutcome.SUCCESS,
        gm_question=None,
        timestamp=datetime.now(UTC)
    )

    # We can't easily test the UI output, but we can verify the method doesn't crash
    app._display_roll_result(roll_result)


def test_display_roll_result_shows_laser_feelings(app):
    """Test that LASER FEELINGS is displayed when applicable"""
    # Create roll result with LASER FEELINGS
    roll_result = LasersFeelingRollResult(
        character_number=3,
        task_type="lasers",
        is_prepared=False,
        is_expert=False,
        is_helping=False,
        individual_rolls=[3],
        die_successes=[True],
        laser_feelings_indices=[0],
        total_successes=1,
        outcome=RollOutcome.BARELY,
        gm_question="How many guards are there?",
        timestamp=datetime.now(UTC)
    )

    # Verify method doesn't crash with LASER FEELINGS
    app._display_roll_result(roll_result)


def test_display_roll_result_all_outcomes(app):
    """Test display for all possible outcomes"""
    outcomes = [
        (RollOutcome.FAILURE, 0),
        (RollOutcome.BARELY, 1),
        (RollOutcome.SUCCESS, 2),
        (RollOutcome.CRITICAL, 3)
    ]

    for outcome, successes in outcomes:
        roll_result = LasersFeelingRollResult(
            character_number=3,
            task_type="lasers",
            is_prepared=False,
            is_expert=False,
            is_helping=False,
            individual_rolls=[1] * successes if successes > 0 else [6],
            die_successes=[True] * successes if successes > 0 else [False],
            laser_feelings_indices=[],
            total_successes=successes,
            outcome=outcome,
            gm_question=None,
            timestamp=datetime.now(UTC)
        )

        # Verify no crash for any outcome
        app._display_roll_result(roll_result)


def test_roll_execution_handles_invalid_task_type(app, sample_character_config):
    """Test error handling for invalid task_type"""
    # Setup
    app._character_configs["char_zara_001"] = sample_character_config
    character_actions = {
        "char_zara_001": {
            "task_type": "invalid_type",  # Invalid
            "is_prepared": False,
            "is_expert": False
        }
    }

    # Execute
    result = app._execute_character_suggested_roll(character_actions)

    # Assert - should fail validation
    assert result["success"] is False
    assert "error" in result
    assert "Roll execution failed" in result["error"]


def test_current_turn_result_stored_in_display(app, sample_turn_result):
    """Test that turn result is stored when display_turn_result is called"""
    # Execute
    app.display_turn_result(sample_turn_result)

    # Assert
    assert app._current_turn_result is not None
    assert app._current_turn_result == sample_turn_result


def test_current_turn_result_cleared_on_complete(app, sample_character_actions):
    """Test that turn result is cleared when turn completes"""
    # Setup - complete turn result (no awaiting_dm_input)
    turn_result = {
        "character_actions": sample_character_actions,
        "phase_completed": "character_reaction",
        "awaiting_dm_input": False
    }

    # Execute
    app.display_turn_result(turn_result)

    # Assert - should be cleared
    assert app._current_turn_result is None
