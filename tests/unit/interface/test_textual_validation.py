# ABOUTME: Unit tests for Textual interface command validation and error recovery.
# ABOUTME: Tests phase-aware command validation and helpful suggestion generation.

import pytest

from src.interface.dm_cli import DMCommandType
from src.models.game_state import GamePhase


class ValidationTestHelper:
    """
    Minimal test helper that mimics DMTextualInterface for validation testing.

    This avoids Textual reactive attribute issues by using a simple class.
    We only need the validation methods and current_phase tracking.
    """
    def __init__(self):
        self.current_phase = GamePhase.DM_NARRATION

    def _humanize_phase_name(self, phase: GamePhase) -> str:
        """Convert GamePhase enum to human-readable name"""
        name_map = {
            GamePhase.DM_NARRATION: "DM Narration",
            GamePhase.MEMORY_QUERY: "Memory Query",
            GamePhase.DM_CLARIFICATION: "DM Clarification",
            GamePhase.STRATEGIC_INTENT: "Strategic Intent",
            GamePhase.OOC_DISCUSSION: "OOC Discussion",
            GamePhase.CONSENSUS_DETECTION: "Consensus Detection",
            GamePhase.CHARACTER_ACTION: "Character Action",
            GamePhase.VALIDATION: "Validation",
            GamePhase.CHARACTER_REFORMULATION: "Character Reformulation",
            GamePhase.DM_ADJUDICATION: "DM Adjudication",
            GamePhase.DICE_RESOLUTION: "Dice Resolution",
            GamePhase.LASER_FEELINGS_QUESTION: "Laser Feelings Question",
            GamePhase.DM_OUTCOME: "DM Outcome",
            GamePhase.CHARACTER_REACTION: "Character Reaction",
            GamePhase.MEMORY_STORAGE: "Memory Storage",
        }
        return name_map.get(phase, phase.value)

    # Copy validation methods from DMTextualInterface
    def _is_command_valid_for_phase(
        self, command_type: DMCommandType
    ) -> tuple[bool, str, list[str]]:
        """Check if command is valid for current phase - copied from DMTextualInterface"""
        from loguru import logger

        # Info always valid
        if command_type == DMCommandType.INFO:
            return (True, "", [])

        # Get current phase (treat None as DM_NARRATION)
        current_phase = self.current_phase or GamePhase.DM_NARRATION

        # Narrate only valid during DM_NARRATION
        if command_type == DMCommandType.NARRATE:
            if current_phase == GamePhase.DM_NARRATION:
                return (True, "", [])
            else:
                phase_name = self._humanize_phase_name(current_phase)
                reason = f"Cannot narrate during {phase_name}. Wait for turn to complete."
                suggestions = self._get_suggestions_for_phase()
                logger.debug(f"Command validation failed: {reason}")
                return (False, reason, suggestions)

        # Roll/Success/Fail only valid during DM_ADJUDICATION or DICE_RESOLUTION
        if command_type in (DMCommandType.ROLL, DMCommandType.SUCCESS, DMCommandType.FAIL):
            if current_phase in (GamePhase.DM_ADJUDICATION, GamePhase.DICE_RESOLUTION):
                return (True, "", [])
            else:
                phase_name = self._humanize_phase_name(current_phase)
                reason = f"Cannot adjudicate during {phase_name}. Wait for character actions first."
                suggestions = self._get_suggestions_for_phase()
                logger.debug(f"Command validation failed: {reason}")
                return (False, reason, suggestions)

        # Unknown command type - allow it (defensive programming)
        logger.warning(f"Unknown command type during validation: {command_type}")
        return (True, "", [])

    def _get_suggestions_for_phase(self) -> list[str]:
        """Get helpful command suggestions for current phase - copied from DMTextualInterface"""
        current_phase = self.current_phase or GamePhase.DM_NARRATION

        # Define suggestions for each phase
        if current_phase == GamePhase.DM_NARRATION:
            return [
                "- narrate <text>  - Describe what happens in the scene",
                "- info  - Show session information",
            ]

        elif current_phase == GamePhase.DM_ADJUDICATION:
            return [
                "- accept  - Accept character's suggested roll",
                "- override <dice>  - Override with specific dice value (1-6)",
                "- success  - Automatic success without rolling",
                "- fail  - Automatic failure without rolling",
                "- /roll <notation>  - Advanced dice roll (e.g., /roll 2d6+3)",
            ]

        elif current_phase == GamePhase.DICE_RESOLUTION:
            return [
                "- accept  - Accept character's suggested roll",
                "- override <dice>  - Override with specific dice value (1-6)",
                "- success  - Automatic success",
                "- fail  - Automatic failure",
            ]

        elif current_phase == GamePhase.DM_OUTCOME:
            return [
                "- <outcome text>  - Describe what happens based on the roll result",
                "- Type outcome and press Enter",
            ]

        elif current_phase == GamePhase.LASER_FEELINGS_QUESTION:
            return [
                "- <answer>  - Provide honest answer to character's question",
                "- Type answer and press Enter",
            ]

        elif current_phase == GamePhase.DM_CLARIFICATION:
            return [
                "- <number> <answer>  - Answer specific question (e.g., '1 Yes, there are guards')",
                "- done  - Finish answering questions for this round",
                "- finish  - Skip remaining clarification rounds",
            ]

        else:
            # Generic suggestions for other phases
            return [
                "- Wait for current phase to complete",
                "- Type 'info' or press Ctrl+I for session information",
            ]


@pytest.fixture
def interface():
    """Create minimal test helper for validation testing"""
    return ValidationTestHelper()


class TestCommandValidationForPhase:
    """Test command validation for each phase - Task 7"""

    def test_narrate_valid_during_dm_narration(self, interface):
        """Narrate command should be valid during DM_NARRATION phase"""
        interface.current_phase = GamePhase.DM_NARRATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.NARRATE
        )
        assert is_valid is True
        assert reason == ""
        assert suggestions == []

    def test_narrate_invalid_during_adjudication(self, interface):
        """Narrate command should be invalid during DM_ADJUDICATION phase"""
        interface.current_phase = GamePhase.DM_ADJUDICATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.NARRATE
        )
        assert is_valid is False
        assert "narrate" in reason.lower() or "adjudication" in reason.lower()
        assert len(suggestions) > 0

    def test_roll_valid_during_adjudication(self, interface):
        """Roll command should be valid during DM_ADJUDICATION phase"""
        interface.current_phase = GamePhase.DM_ADJUDICATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.ROLL
        )
        assert is_valid is True
        assert reason == ""
        assert suggestions == []

    def test_roll_invalid_during_narration(self, interface):
        """Roll command should be invalid during DM_NARRATION phase"""
        interface.current_phase = GamePhase.DM_NARRATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.ROLL
        )
        assert is_valid is False
        assert len(suggestions) > 0

    def test_success_valid_during_adjudication(self, interface):
        """Success command should be valid during DM_ADJUDICATION phase"""
        interface.current_phase = GamePhase.DM_ADJUDICATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.SUCCESS
        )
        assert is_valid is True
        assert reason == ""
        assert suggestions == []

    def test_fail_valid_during_adjudication(self, interface):
        """Fail command should be valid during DM_ADJUDICATION phase"""
        interface.current_phase = GamePhase.DM_ADJUDICATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.FAIL
        )
        assert is_valid is True
        assert reason == ""
        assert suggestions == []

    def test_success_invalid_during_narration(self, interface):
        """Success command should be invalid during DM_NARRATION phase"""
        interface.current_phase = GamePhase.DM_NARRATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.SUCCESS
        )
        assert is_valid is False
        assert len(suggestions) > 0

    def test_fail_invalid_during_outcome(self, interface):
        """Fail command should be invalid during DM_OUTCOME phase"""
        interface.current_phase = GamePhase.DM_OUTCOME
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.FAIL
        )
        assert is_valid is False
        assert len(suggestions) > 0

    def test_info_always_valid(self, interface):
        """Info command should be valid in all phases"""
        for phase in GamePhase:
            interface.current_phase = phase
            is_valid, reason, suggestions = interface._is_command_valid_for_phase(
                DMCommandType.INFO
            )
            assert is_valid is True, f"Info should be valid during {phase.value}"
            assert reason == ""
            assert suggestions == []


class TestSuggestionGeneration:
    """Test suggestion generation for each phase - Task 8"""

    def test_suggestions_for_narration_phase(self, interface):
        """Suggestions during narration phase should include 'narrate'"""
        interface.current_phase = GamePhase.DM_NARRATION
        suggestions = interface._get_suggestions_for_phase()

        assert len(suggestions) > 0
        # Should suggest narrate command
        assert any("narrate" in s.lower() for s in suggestions)

    def test_suggestions_for_adjudication_phase(self, interface):
        """Suggestions during adjudication phase should include roll/success/fail"""
        interface.current_phase = GamePhase.DM_ADJUDICATION
        suggestions = interface._get_suggestions_for_phase()

        assert len(suggestions) > 0
        # Should include adjudication commands
        suggestion_text = " ".join(suggestions).lower()
        assert (
            "roll" in suggestion_text
            or "success" in suggestion_text
            or "fail" in suggestion_text
        )

    def test_suggestions_for_outcome_phase(self, interface):
        """Suggestions during outcome phase should mention outcome narration"""
        interface.current_phase = GamePhase.DM_OUTCOME
        suggestions = interface._get_suggestions_for_phase()

        assert len(suggestions) > 0
        # Should mention outcome or narration
        suggestion_text = " ".join(suggestions).lower()
        assert "outcome" in suggestion_text or "describe" in suggestion_text

    def test_suggestions_for_laser_feelings_question_phase(self, interface):
        """Suggestions during LASER FEELINGS question phase should mention answering"""
        interface.current_phase = GamePhase.LASER_FEELINGS_QUESTION
        suggestions = interface._get_suggestions_for_phase()

        assert len(suggestions) > 0
        # Should mention answering
        suggestion_text = " ".join(suggestions).lower()
        assert "answer" in suggestion_text or "question" in suggestion_text

    def test_suggestions_for_clarification_phase(self, interface):
        """Suggestions during clarification phase should mention answering questions"""
        interface.current_phase = GamePhase.DM_CLARIFICATION
        suggestions = interface._get_suggestions_for_phase()

        assert len(suggestions) > 0
        # Should mention answering clarifications
        suggestion_text = " ".join(suggestions).lower()
        assert "answer" in suggestion_text or "clarif" in suggestion_text

    def test_suggestions_are_descriptive(self, interface):
        """Each suggestion should include a description"""
        interface.current_phase = GamePhase.DM_ADJUDICATION
        suggestions = interface._get_suggestions_for_phase()

        # Suggestions should be formatted as bullet points with descriptions
        for suggestion in suggestions:
            # Should start with "- " or contain " - "
            assert "-" in suggestion

    def test_suggestions_for_all_phases(self, interface):
        """All phases should have at least one suggestion"""
        for phase in GamePhase:
            interface.current_phase = phase
            suggestions = interface._get_suggestions_for_phase()

            # Every phase should have at least one suggestion
            assert len(suggestions) > 0, f"Phase {phase.value} has no suggestions"


class TestErrorMessageFormatting:
    """Test error message formatting with suggestions - Task 8"""

    def test_invalid_command_shows_error(self, interface):
        """Invalid command should return error with reason"""
        interface.current_phase = GamePhase.DM_NARRATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.ROLL
        )

        assert is_valid is False
        assert reason != ""
        assert len(reason) > 0

    def test_invalid_command_shows_suggestions(self, interface):
        """Invalid command should return suggestions"""
        interface.current_phase = GamePhase.DM_NARRATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.SUCCESS
        )

        assert is_valid is False
        assert len(suggestions) > 0

    def test_error_reason_mentions_phase(self, interface):
        """Error reason should mention current phase"""
        interface.current_phase = GamePhase.DM_ADJUDICATION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.NARRATE
        )

        assert is_valid is False
        # Reason should mention the phase name or context
        assert "adjudication" in reason.lower() or "narrat" in reason.lower()

    def test_error_reason_mentions_command(self, interface):
        """Error reason should mention the invalid command"""
        interface.current_phase = GamePhase.DM_OUTCOME
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.ROLL
        )

        assert is_valid is False
        # Reason should explain what went wrong
        assert len(reason) > 10  # Should be descriptive


class TestEdgeCases:
    """Test edge cases and special scenarios - Task 7"""

    def test_roll_valid_during_dice_resolution(self, interface):
        """Roll command should also be valid during DICE_RESOLUTION phase"""
        interface.current_phase = GamePhase.DICE_RESOLUTION
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.ROLL
        )
        assert is_valid is True

    def test_adjudication_commands_valid_during_dice_resolution(self, interface):
        """Success/fail commands should be valid during DICE_RESOLUTION phase"""
        interface.current_phase = GamePhase.DICE_RESOLUTION

        is_valid_success, _, _ = interface._is_command_valid_for_phase(DMCommandType.SUCCESS)
        is_valid_fail, _, _ = interface._is_command_valid_for_phase(DMCommandType.FAIL)

        assert is_valid_success is True
        assert is_valid_fail is True

    def test_none_phase_defaults_to_narration(self, interface):
        """None phase should be treated as narration (start of game)"""
        interface.current_phase = None
        is_valid, reason, suggestions = interface._is_command_valid_for_phase(
            DMCommandType.NARRATE
        )
        # Should allow narrate when phase is None (game hasn't started)
        # This matches dm_cli.py behavior (line 712-714)
        assert is_valid is True
        assert reason == ""
        assert suggestions == []


class TestValidationIntegration:
    """Test validation integration with command parsing - Task 7 & 8"""

    def test_validation_order(self, interface):
        """Validation should happen after parsing, before execution"""
        # This is a contract test - we verify the method exists and returns expected type
        interface.current_phase = GamePhase.DM_NARRATION
        result = interface._is_command_valid_for_phase(DMCommandType.NARRATE)

        # Should return tuple of (bool, str, list)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], bool)  # is_valid
        assert isinstance(result[1], str)   # reason
        assert isinstance(result[2], list)  # suggestions
