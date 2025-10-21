# ABOUTME: Unit tests for game state models including GamePhase, ValidationResult, and related models.
# ABOUTME: Tests phase enum values, validation result structure, stance/position models, and consensus results.

import pytest
from pydantic import ValidationError

from src.models.game_state import (
    GamePhase,
    ValidationResult,
    Stance,
    Position,
    ConsensusResult
)


class TestGamePhase:
    """Test suite for GamePhase enum"""

    def test_all_game_phases_exist(self):
        """Test all expected game phases are defined"""
        expected_phases = [
            "dm_narration",
            "memory_query",
            "dm_clarification",
            "strategic_intent",
            "ooc_discussion",
            "consensus_detection",
            "character_action",
            "validation",
            "character_reformulation",
            "dm_adjudication",
            "dice_resolution",
            "laser_feelings_question",
            "dm_outcome",
            "character_reaction",
            "memory_storage"
        ]

        for phase_value in expected_phases:
            # Verify each phase exists by value lookup
            phase = GamePhase(phase_value)
            assert phase.value == phase_value

    def test_game_phase_enum_values(self):
        """Test GamePhase enum can be created from all values"""
        assert GamePhase.DM_NARRATION.value == "dm_narration"
        assert GamePhase.MEMORY_QUERY.value == "memory_query"
        assert GamePhase.DM_CLARIFICATION.value == "dm_clarification"
        assert GamePhase.STRATEGIC_INTENT.value == "strategic_intent"
        assert GamePhase.OOC_DISCUSSION.value == "ooc_discussion"
        assert GamePhase.CONSENSUS_DETECTION.value == "consensus_detection"
        assert GamePhase.CHARACTER_ACTION.value == "character_action"
        assert GamePhase.VALIDATION.value == "validation"
        assert GamePhase.CHARACTER_REFORMULATION.value == "character_reformulation"
        assert GamePhase.DM_ADJUDICATION.value == "dm_adjudication"
        assert GamePhase.DICE_RESOLUTION.value == "dice_resolution"
        assert GamePhase.LASER_FEELINGS_QUESTION.value == "laser_feelings_question"
        assert GamePhase.DM_OUTCOME.value == "dm_outcome"
        assert GamePhase.CHARACTER_REACTION.value == "character_reaction"
        assert GamePhase.MEMORY_STORAGE.value == "memory_storage"

    def test_invalid_game_phase_raises_error(self):
        """Test creating GamePhase with invalid value raises error"""
        with pytest.raises(ValueError):
            GamePhase("invalid_phase")


class TestValidationResult:
    """Test suite for ValidationResult model"""

    def test_valid_validation_result_creation(self):
        """Test creating validation result with valid data"""
        result = ValidationResult(
            valid=True,
            violations=[],
            forbidden_patterns=[],
            suggestion=None,
            method="pattern",
            confidence=1.0
        )
        assert result.valid is True
        assert result.violations == []
        assert result.forbidden_patterns == []
        assert result.suggestion is None
        assert result.method == "pattern"
        assert result.confidence == 1.0

    def test_validation_result_with_violations(self):
        """Test validation result with violations"""
        result = ValidationResult(
            valid=False,
            violations=["Cannot narrate outcomes", "Cannot control other characters"],
            forbidden_patterns=["successfully", "falls unconscious"],
            suggestion="Express intent only, not outcome",
            method="llm",
            confidence=0.95
        )
        assert result.valid is False
        assert len(result.violations) == 2
        assert "Cannot narrate outcomes" in result.violations
        assert len(result.forbidden_patterns) == 2
        assert result.suggestion == "Express intent only, not outcome"

    def test_validation_result_default_values(self):
        """Test validation result has sensible defaults"""
        result = ValidationResult(valid=True)
        assert result.violations == []
        assert result.forbidden_patterns == []
        assert result.suggestion is None
        assert result.method == "pattern"
        assert result.confidence == 1.0

    def test_validation_result_method_validation(self):
        """Test method field must be one of allowed values"""
        # Valid methods
        ValidationResult(valid=True, method="pattern")
        ValidationResult(valid=True, method="llm")
        ValidationResult(valid=True, method="hybrid")

        # Invalid method
        with pytest.raises(ValidationError) as exc_info:
            ValidationResult(valid=True, method="invalid")
        assert "method" in str(exc_info.value)

    def test_validation_result_confidence_range(self):
        """Test confidence must be between 0.0 and 1.0"""
        # Valid boundaries
        ValidationResult(valid=True, confidence=0.0)
        ValidationResult(valid=True, confidence=1.0)

        # Invalid: below 0
        with pytest.raises(ValidationError) as exc_info:
            ValidationResult(valid=True, confidence=-0.1)
        assert "confidence" in str(exc_info.value)

        # Invalid: above 1
        with pytest.raises(ValidationError) as exc_info:
            ValidationResult(valid=True, confidence=1.5)
        assert "confidence" in str(exc_info.value)

    def test_validation_result_serialization(self):
        """Test validation result can be serialized to dict"""
        result = ValidationResult(
            valid=False,
            violations=["Test violation"],
            method="llm",
            confidence=0.8
        )
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["valid"] is False
        assert data["violations"] == ["Test violation"]
        assert data["method"] == "llm"
        assert data["confidence"] == 0.8

    def test_validation_result_required_field(self):
        """Test valid field is required"""
        with pytest.raises(ValidationError) as exc_info:
            ValidationResult()
        assert "valid" in str(exc_info.value)


class TestStance:
    """Test suite for Stance enum"""

    def test_all_stance_values(self):
        """Test all stance enum values exist"""
        assert Stance.AGREE.value == "agree"
        assert Stance.DISAGREE.value == "disagree"
        assert Stance.NEUTRAL.value == "neutral"
        assert Stance.SILENT.value == "silent"

    def test_stance_from_string(self):
        """Test creating Stance from string value"""
        assert Stance("agree") == Stance.AGREE
        assert Stance("disagree") == Stance.DISAGREE
        assert Stance("neutral") == Stance.NEUTRAL
        assert Stance("silent") == Stance.SILENT

    def test_invalid_stance_raises_error(self):
        """Test invalid stance value raises error"""
        with pytest.raises(ValueError):
            Stance("invalid")


class TestPosition:
    """Test suite for Position model"""

    def test_valid_position_creation(self):
        """Test creating position with valid data"""
        position = Position(
            agent_id="agent_001",
            stance=Stance.AGREE,
            confidence=0.9,
            supporting_text="I think we should proceed cautiously"
        )
        assert position.agent_id == "agent_001"
        # use_enum_values=True converts to string
        assert position.stance == "agree"
        assert position.confidence == 0.9
        assert position.supporting_text == "I think we should proceed cautiously"

    def test_position_confidence_range_validation(self):
        """Test confidence must be between 0.0 and 1.0"""
        # Valid boundaries
        Position(
            agent_id="agent_001",
            stance=Stance.AGREE,
            confidence=0.0
        )
        Position(
            agent_id="agent_001",
            stance=Stance.AGREE,
            confidence=1.0
        )

        # Invalid: below 0
        with pytest.raises(ValidationError) as exc_info:
            Position(
                agent_id="agent_001",
                stance=Stance.AGREE,
                confidence=-0.1
            )
        assert "confidence" in str(exc_info.value)

        # Invalid: above 1
        with pytest.raises(ValidationError) as exc_info:
            Position(
                agent_id="agent_001",
                stance=Stance.AGREE,
                confidence=1.5
            )
        assert "confidence" in str(exc_info.value)

    def test_position_supporting_text_optional(self):
        """Test supporting_text is optional and defaults to None"""
        position = Position(
            agent_id="agent_001",
            stance=Stance.NEUTRAL,
            confidence=0.5
        )
        assert position.supporting_text is None

    def test_position_all_stance_values(self):
        """Test position can be created with all stance values"""
        for stance in [Stance.AGREE, Stance.DISAGREE, Stance.NEUTRAL, Stance.SILENT]:
            position = Position(
                agent_id="agent_001",
                stance=stance,
                confidence=0.8
            )
            assert isinstance(position.stance, str)

    def test_position_serialization(self):
        """Test position can be serialized to dict"""
        position = Position(
            agent_id="agent_001",
            stance=Stance.AGREE,
            confidence=0.9,
            supporting_text="Test"
        )
        data = position.model_dump()
        assert isinstance(data, dict)
        assert data["agent_id"] == "agent_001"
        assert data["stance"] == "agree"
        assert data["confidence"] == 0.9

    def test_position_required_fields(self):
        """Test agent_id, stance, and confidence are required"""
        with pytest.raises(ValidationError) as exc_info:
            Position()
        error_str = str(exc_info.value)
        assert "agent_id" in error_str
        assert "stance" in error_str
        assert "confidence" in error_str


class TestConsensusResult:
    """Test suite for ConsensusResult model"""

    def test_valid_consensus_result_creation(self):
        """Test creating consensus result with valid data"""
        positions = {
            "agent_001": Position(
                agent_id="agent_001",
                stance=Stance.AGREE,
                confidence=0.9
            ),
            "agent_002": Position(
                agent_id="agent_002",
                stance=Stance.AGREE,
                confidence=0.8
            )
        }
        result = ConsensusResult(
            result="unanimous",
            positions=positions,
            round_count=3,
            duration_seconds=45.2,
            agreed_agents=["agent_001", "agent_002"],
            disagreed_agents=[],
            neutral_agents=[]
        )
        assert result.result == "unanimous"
        assert len(result.positions) == 2
        assert result.round_count == 3
        assert result.duration_seconds == 45.2
        assert len(result.agreed_agents) == 2

    def test_consensus_result_types(self):
        """Test all consensus result types are valid"""
        for result_type in ["unanimous", "majority", "conflicted", "timeout"]:
            result = ConsensusResult(
                result=result_type,
                positions={},
                round_count=1,
                duration_seconds=10.0
            )
            assert result.result == result_type

    def test_consensus_result_invalid_type(self):
        """Test invalid result type raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ConsensusResult(
                result="invalid",
                positions={},
                round_count=1,
                duration_seconds=10.0
            )
        assert "result" in str(exc_info.value)

    def test_consensus_result_default_agent_lists(self):
        """Test agent lists default to empty"""
        result = ConsensusResult(
            result="timeout",
            positions={},
            round_count=5,
            duration_seconds=120.0
        )
        assert result.agreed_agents == []
        assert result.disagreed_agents == []
        assert result.neutral_agents == []

    def test_agreement_percentage_calculation(self):
        """Test agreement_percentage property calculates correctly"""
        positions = {
            "agent_001": Position(agent_id="agent_001", stance=Stance.AGREE, confidence=0.9),
            "agent_002": Position(agent_id="agent_002", stance=Stance.AGREE, confidence=0.8),
            "agent_003": Position(agent_id="agent_003", stance=Stance.DISAGREE, confidence=0.7),
            "agent_004": Position(agent_id="agent_004", stance=Stance.NEUTRAL, confidence=0.5)
        }
        result = ConsensusResult(
            result="majority",
            positions=positions,
            round_count=2,
            duration_seconds=30.0,
            agreed_agents=["agent_001", "agent_002"],
            disagreed_agents=["agent_003"],
            neutral_agents=["agent_004"]
        )
        # 2 agreed out of 4 total = 50%
        assert result.agreement_percentage == 0.5

    def test_agreement_percentage_unanimous(self):
        """Test agreement_percentage is 1.0 for unanimous"""
        positions = {
            "agent_001": Position(agent_id="agent_001", stance=Stance.AGREE, confidence=0.9),
            "agent_002": Position(agent_id="agent_002", stance=Stance.AGREE, confidence=0.8)
        }
        result = ConsensusResult(
            result="unanimous",
            positions=positions,
            round_count=1,
            duration_seconds=15.0,
            agreed_agents=["agent_001", "agent_002"]
        )
        assert result.agreement_percentage == 1.0

    def test_agreement_percentage_no_positions(self):
        """Test agreement_percentage is 0.0 when no positions"""
        result = ConsensusResult(
            result="timeout",
            positions={},
            round_count=5,
            duration_seconds=120.0
        )
        assert result.agreement_percentage == 0.0

    def test_consensus_result_serialization(self):
        """Test consensus result can be serialized to dict"""
        positions = {
            "agent_001": Position(
                agent_id="agent_001",
                stance=Stance.AGREE,
                confidence=0.9
            )
        }
        result = ConsensusResult(
            result="unanimous",
            positions=positions,
            round_count=2,
            duration_seconds=20.5,
            agreed_agents=["agent_001"]
        )
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["result"] == "unanimous"
        assert data["round_count"] == 2
        assert data["duration_seconds"] == 20.5

    def test_consensus_result_required_fields(self):
        """Test required fields must be provided"""
        with pytest.raises(ValidationError) as exc_info:
            ConsensusResult()
        error_str = str(exc_info.value)
        assert "result" in error_str
        assert "positions" in error_str
        assert "round_count" in error_str
        assert "duration_seconds" in error_str

    def test_consensus_result_with_mixed_stances(self):
        """Test consensus result with all stance types"""
        positions = {
            "agent_001": Position(agent_id="agent_001", stance=Stance.AGREE, confidence=0.9),
            "agent_002": Position(agent_id="agent_002", stance=Stance.DISAGREE, confidence=0.8),
            "agent_003": Position(agent_id="agent_003", stance=Stance.NEUTRAL, confidence=0.6),
            "agent_004": Position(agent_id="agent_004", stance=Stance.SILENT, confidence=0.3)
        }
        result = ConsensusResult(
            result="conflicted",
            positions=positions,
            round_count=4,
            duration_seconds=60.0,
            agreed_agents=["agent_001"],
            disagreed_agents=["agent_002"],
            neutral_agents=["agent_003", "agent_004"]
        )
        assert len(result.positions) == 4
        assert len(result.agreed_agents) == 1
        assert len(result.disagreed_agents) == 1
        assert len(result.neutral_agents) == 2
        assert result.agreement_percentage == 0.25  # 1 out of 4
