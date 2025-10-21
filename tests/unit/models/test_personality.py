# ABOUTME: Unit tests for PlayerPersonality model validation and computed properties.
# ABOUTME: Tests personality trait ranges, decision_style property, and immutability.

import pytest
from pydantic import ValidationError

from src.models.personality import PlayerPersonality, PlayStyle


class TestPlayerPersonality:
    """Test suite for PlayerPersonality model"""

    def test_valid_personality_creation(self):
        """Test creating personality with valid data"""
        personality = PlayerPersonality(
            analytical_score=0.7,
            risk_tolerance=0.5,
            detail_oriented=0.6,
            emotional_memory=0.4,
            assertiveness=0.6,
            cooperativeness=0.7,
            openness=0.7,
            rule_adherence=0.7,
            roleplay_intensity=0.8,
            base_decay_rate=0.5
        )
        assert personality.analytical_score == 0.7
        assert personality.risk_tolerance == 0.5
        assert personality.detail_oriented == 0.6
        assert personality.emotional_memory == 0.4
        assert personality.assertiveness == 0.6
        assert personality.cooperativeness == 0.7
        assert personality.openness == 0.7
        assert personality.rule_adherence == 0.7
        assert personality.roleplay_intensity == 0.8
        assert personality.base_decay_rate == 0.5

    def test_analytical_score_range_validation(self):
        """Test analytical_score must be between 0.0 and 1.0"""
        # Valid boundaries
        PlayerPersonality(
            analytical_score=0.0,
            risk_tolerance=0.5,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        PlayerPersonality(
            analytical_score=1.0,
            risk_tolerance=0.5,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )

        # Invalid: below 0
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=-0.1,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "analytical_score" in str(exc_info.value)

        # Invalid: above 1
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=1.1,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "analytical_score" in str(exc_info.value)

    def test_risk_tolerance_range_validation(self):
        """Test risk_tolerance must be between 0.0 and 1.0"""
        # Valid boundaries
        PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.0,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=1.0,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )

        # Invalid: below 0
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=-0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "risk_tolerance" in str(exc_info.value)

        # Invalid: above 1
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=2.0,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "risk_tolerance" in str(exc_info.value)

    def test_detail_oriented_range_validation(self):
        """Test detail_oriented must be between 0.0 and 1.0"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=-0.1,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "detail_oriented" in str(exc_info.value)

    def test_emotional_memory_range_validation(self):
        """Test emotional_memory must be between 0.0 and 1.0"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=1.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "emotional_memory" in str(exc_info.value)

    def test_assertiveness_range_validation(self):
        """Test assertiveness must be between 0.0 and 1.0"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=-1.0,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "assertiveness" in str(exc_info.value)

    def test_cooperativeness_range_validation(self):
        """Test cooperativeness must be between 0.0 and 1.0"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=1.1,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "cooperativeness" in str(exc_info.value)

    def test_openness_range_validation(self):
        """Test openness must be between 0.0 and 1.0"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=2.0,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "openness" in str(exc_info.value)

    def test_rule_adherence_range_validation(self):
        """Test rule_adherence must be between 0.0 and 1.0"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=-0.5,
                roleplay_intensity=0.5
            )
        assert "rule_adherence" in str(exc_info.value)

    def test_roleplay_intensity_range_validation(self):
        """Test roleplay_intensity must be between 0.0 and 1.0"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=1.5
            )
        assert "roleplay_intensity" in str(exc_info.value)

    def test_base_decay_rate_range_validation(self):
        """Test base_decay_rate must be between 0.0 and 1.0"""
        # Valid boundaries
        PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.5,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5,
            base_decay_rate=0.0
        )
        PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.5,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5,
            base_decay_rate=1.0
        )

        # Invalid: below 0
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5,
                base_decay_rate=-0.1
            )
        assert "base_decay_rate" in str(exc_info.value)

        # Invalid: above 1
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score=0.5,
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5,
                base_decay_rate=1.1
            )
        assert "base_decay_rate" in str(exc_info.value)

    def test_base_decay_rate_default_value(self):
        """Test base_decay_rate has default value of 0.5"""
        personality = PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.5,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        assert personality.base_decay_rate == 0.5

    def test_decision_style_analytical_planner(self):
        """Test decision_style returns analytical_planner for high analytical_score"""
        personality = PlayerPersonality(
            analytical_score=0.8,
            risk_tolerance=0.3,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        assert personality.decision_style == PlayStyle.ANALYTICAL_PLANNER.value

    def test_decision_style_bold_improviser(self):
        """Test decision_style returns bold_improviser for high risk_tolerance"""
        personality = PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.9,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        assert personality.decision_style == PlayStyle.BOLD_IMPROVISER.value

    def test_decision_style_team_coordinator(self):
        """Test decision_style returns team_coordinator for high cooperativeness"""
        personality = PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.5,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.9,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        assert personality.decision_style == PlayStyle.TEAM_COORDINATOR.value

    def test_decision_style_balanced_strategist(self):
        """Test decision_style returns balanced_strategist for moderate values"""
        personality = PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.5,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        assert personality.decision_style == PlayStyle.BALANCED_STRATEGIST.value

    def test_decision_style_priority_analytical(self):
        """Test decision_style prioritizes analytical over other traits"""
        personality = PlayerPersonality(
            analytical_score=0.8,  # High analytical
            risk_tolerance=0.9,    # Also high risk
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.9,   # Also high cooperation
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        # Analytical takes precedence
        assert personality.decision_style == PlayStyle.ANALYTICAL_PLANNER.value

    def test_decision_style_priority_risk(self):
        """Test decision_style prioritizes risk over cooperativeness"""
        personality = PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.9,    # High risk
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.9,   # Also high cooperation
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        # Risk takes precedence over cooperation
        assert personality.decision_style == PlayStyle.BOLD_IMPROVISER.value

    def test_model_immutability(self):
        """Test personality model is frozen (immutable)"""
        personality = PlayerPersonality(
            analytical_score=0.5,
            risk_tolerance=0.5,
            detail_oriented=0.5,
            emotional_memory=0.5,
            assertiveness=0.5,
            cooperativeness=0.5,
            openness=0.5,
            rule_adherence=0.5,
            roleplay_intensity=0.5
        )
        with pytest.raises(ValidationError):
            personality.analytical_score = 0.9

    def test_model_serialization_to_dict(self):
        """Test personality model can be serialized to dict"""
        personality = PlayerPersonality(
            analytical_score=0.7,
            risk_tolerance=0.5,
            detail_oriented=0.6,
            emotional_memory=0.4,
            assertiveness=0.6,
            cooperativeness=0.7,
            openness=0.7,
            rule_adherence=0.7,
            roleplay_intensity=0.8,
            base_decay_rate=0.5
        )
        data = personality.model_dump()
        assert isinstance(data, dict)
        assert data["analytical_score"] == 0.7
        assert data["risk_tolerance"] == 0.5
        assert data["detail_oriented"] == 0.6
        assert data["emotional_memory"] == 0.4
        assert data["assertiveness"] == 0.6
        assert data["cooperativeness"] == 0.7
        assert data["openness"] == 0.7
        assert data["rule_adherence"] == 0.7
        assert data["roleplay_intensity"] == 0.8
        assert data["base_decay_rate"] == 0.5

    def test_model_serialization_to_json(self):
        """Test personality model can be serialized to JSON"""
        personality = PlayerPersonality(
            analytical_score=0.7,
            risk_tolerance=0.5,
            detail_oriented=0.6,
            emotional_memory=0.4,
            assertiveness=0.6,
            cooperativeness=0.7,
            openness=0.7,
            rule_adherence=0.7,
            roleplay_intensity=0.8,
            base_decay_rate=0.5
        )
        json_str = personality.model_dump_json()
        assert isinstance(json_str, str)
        assert "analytical_score" in json_str
        assert "0.7" in json_str

    def test_required_fields_validation(self):
        """Test all required fields must be provided"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality()
        error_str = str(exc_info.value)
        assert "analytical_score" in error_str
        assert "risk_tolerance" in error_str
        assert "detail_oriented" in error_str
        assert "emotional_memory" in error_str
        assert "assertiveness" in error_str
        assert "cooperativeness" in error_str
        assert "openness" in error_str
        assert "rule_adherence" in error_str
        assert "roleplay_intensity" in error_str

    def test_invalid_field_type_raises_error(self):
        """Test invalid field type raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            PlayerPersonality(
                analytical_score="high",  # Should be float
                risk_tolerance=0.5,
                detail_oriented=0.5,
                emotional_memory=0.5,
                assertiveness=0.5,
                cooperativeness=0.5,
                openness=0.5,
                rule_adherence=0.5,
                roleplay_intensity=0.5
            )
        assert "analytical_score" in str(exc_info.value)
