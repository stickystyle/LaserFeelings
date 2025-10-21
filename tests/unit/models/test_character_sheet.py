# ABOUTME: Unit tests for CharacterSheet model validation and Lasers & Feelings mechanics.
# ABOUTME: Tests character creation, number range, approach_bias property, and list field handling.

import pytest
from pydantic import ValidationError

from src.models.personality import CharacterSheet, CharacterStyle, CharacterRole


class TestCharacterSheet:
    """Test suite for CharacterSheet model"""

    def test_valid_character_creation(self):
        """Test creating character with valid data"""
        character = CharacterSheet(
            name="Kai Nova",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Discover ancient ruins",
            equipment=["Scanner", "Grappling hook"],
            speech_patterns=["Enthusiastic"],
            mannerisms=["Points at things"]
        )
        assert character.name == "Kai Nova"
        assert character.style == CharacterStyle.INTREPID
        assert character.role == CharacterRole.EXPLORER
        assert character.number == 3
        assert character.character_goal == "Discover ancient ruins"
        assert character.equipment == ["Scanner", "Grappling hook"]
        assert character.speech_patterns == ["Enthusiastic"]
        assert character.mannerisms == ["Points at things"]

    def test_character_name_validation(self):
        """Test character name is required and must be string"""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number=3,
                character_goal="Discover things"
            )
        assert "name" in str(exc_info.value)

    def test_character_style_enum_validation(self):
        """Test character style must be valid CharacterStyle enum"""
        # Valid enum value
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.ALIEN,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal"
        )
        # use_enum_values=True means we get the string value
        assert character.style == "Alien"

        # Invalid enum value
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                style="InvalidStyle",
                role=CharacterRole.EXPLORER,
                number=3,
                character_goal="Test goal"
            )
        assert "style" in str(exc_info.value)

    def test_character_role_enum_validation(self):
        """Test character role must be valid CharacterRole enum"""
        # Valid enum value
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.SCIENTIST,
            number=3,
            character_goal="Test goal"
        )
        # use_enum_values=True means we get the string value
        assert character.role == "Scientist"

        # Invalid enum value
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role="InvalidRole",
                number=3,
                character_goal="Test goal"
            )
        assert "role" in str(exc_info.value)

    def test_number_range_validation_minimum(self):
        """Test number must be at least 2"""
        # Valid minimum
        CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=2,
            character_goal="Test goal"
        )

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number=1,
                character_goal="Test goal"
            )
        assert "number" in str(exc_info.value)

    def test_number_range_validation_maximum(self):
        """Test number must be at most 5"""
        # Valid maximum
        CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=5,
            character_goal="Test goal"
        )

        # Invalid: above maximum
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number=6,
                character_goal="Test goal"
            )
        assert "number" in str(exc_info.value)

    def test_number_all_valid_values(self):
        """Test all valid number values (2-5)"""
        for num in [2, 3, 4, 5]:
            character = CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number=num,
                character_goal="Test goal"
            )
            assert character.number == num

    def test_character_goal_required(self):
        """Test character_goal field is required"""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number=3
            )
        assert "character_goal" in str(exc_info.value)

    def test_equipment_default_empty_list(self):
        """Test equipment defaults to empty list"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal"
        )
        assert character.equipment == []

    def test_equipment_list_validation(self):
        """Test equipment accepts list of strings"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal",
            equipment=["Item 1", "Item 2", "Item 3"]
        )
        assert len(character.equipment) == 3
        assert "Item 1" in character.equipment

    def test_speech_patterns_default_empty_list(self):
        """Test speech_patterns defaults to empty list"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal"
        )
        assert character.speech_patterns == []

    def test_speech_patterns_none_converts_to_empty_list(self):
        """Test speech_patterns None is converted to empty list by validator"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal",
            speech_patterns=None
        )
        assert character.speech_patterns == []

    def test_speech_patterns_list_validation(self):
        """Test speech_patterns accepts list of strings"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal",
            speech_patterns=["Formal", "Technical", "Verbose"]
        )
        assert len(character.speech_patterns) == 3
        assert "Formal" in character.speech_patterns

    def test_mannerisms_default_empty_list(self):
        """Test mannerisms defaults to empty list"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal"
        )
        assert character.mannerisms == []

    def test_mannerisms_none_converts_to_empty_list(self):
        """Test mannerisms None is converted to empty list by validator"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal",
            mannerisms=None
        )
        assert character.mannerisms == []

    def test_mannerisms_list_validation(self):
        """Test mannerisms accepts list of strings"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal",
            mannerisms=["Fidgets", "Smiles often", "Touches hair"]
        )
        assert len(character.mannerisms) == 3
        assert "Fidgets" in character.mannerisms

    def test_approach_bias_lasers(self):
        """Test approach_bias returns 'lasers' for number=2"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.SAVVY,
            role=CharacterRole.SCIENTIST,
            number=2,
            character_goal="Test goal"
        )
        assert character.approach_bias == "lasers"

    def test_approach_bias_feelings(self):
        """Test approach_bias returns 'feelings' for number=5"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.HEROIC,
            role=CharacterRole.ENVOY,
            number=5,
            character_goal="Test goal"
        )
        assert character.approach_bias == "feelings"

    def test_approach_bias_balanced(self):
        """Test approach_bias returns 'balanced' for numbers 3-4"""
        for num in [3, 4]:
            character = CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number=num,
                character_goal="Test goal"
            )
            assert character.approach_bias == "balanced"

    def test_model_immutability(self):
        """Test character sheet model is frozen (immutable)"""
        character = CharacterSheet(
            name="Test",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Test goal"
        )
        with pytest.raises(ValidationError):
            character.number = 4

    def test_model_serialization_to_dict(self):
        """Test character sheet can be serialized to dict"""
        character = CharacterSheet(
            name="Kai Nova",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Discover ancient ruins",
            equipment=["Scanner"],
            speech_patterns=["Enthusiastic"],
            mannerisms=["Points at things"]
        )
        data = character.model_dump()
        assert isinstance(data, dict)
        assert data["name"] == "Kai Nova"
        # use_enum_values=True means enums are converted to their values
        assert data["style"] == "Intrepid"
        assert data["role"] == "Explorer"
        assert data["number"] == 3
        assert data["character_goal"] == "Discover ancient ruins"
        assert data["equipment"] == ["Scanner"]

    def test_model_serialization_to_json(self):
        """Test character sheet can be serialized to JSON"""
        character = CharacterSheet(
            name="Kai Nova",
            style=CharacterStyle.INTREPID,
            role=CharacterRole.EXPLORER,
            number=3,
            character_goal="Discover ancient ruins"
        )
        json_str = character.model_dump_json()
        assert isinstance(json_str, str)
        assert "Kai Nova" in json_str
        assert "Intrepid" in json_str

    def test_all_character_styles(self):
        """Test all CharacterStyle enum values are valid"""
        styles = [
            CharacterStyle.ALIEN,
            CharacterStyle.ANDROID,
            CharacterStyle.DANGEROUS,
            CharacterStyle.HEROIC,
            CharacterStyle.HOT_SHOT,
            CharacterStyle.INTREPID,
            CharacterStyle.SAVVY
        ]
        for style in styles:
            character = CharacterSheet(
                name="Test",
                style=style,
                role=CharacterRole.EXPLORER,
                number=3,
                character_goal="Test goal"
            )
            # use_enum_values=True converts to string value
            assert isinstance(character.style, str)

    def test_all_character_roles(self):
        """Test all CharacterRole enum values are valid"""
        roles = [
            CharacterRole.DOCTOR,
            CharacterRole.ENVOY,
            CharacterRole.ENGINEER,
            CharacterRole.EXPLORER,
            CharacterRole.PILOT,
            CharacterRole.SCIENTIST,
            CharacterRole.SOLDIER
        ]
        for role in roles:
            character = CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role=role,
                number=3,
                character_goal="Test goal"
            )
            # use_enum_values=True converts to string value
            assert isinstance(character.role, str)

    def test_invalid_number_type(self):
        """Test number must be integer"""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number="3",  # Should be int
                character_goal="Test goal"
            )
        assert "number" in str(exc_info.value)

    def test_empty_name_invalid(self):
        """Test empty string name is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="",
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number=3,
                character_goal="Test goal"
            )
        assert "name" in str(exc_info.value)

    def test_empty_character_goal_invalid(self):
        """Test empty string character_goal is invalid"""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                style=CharacterStyle.INTREPID,
                role=CharacterRole.EXPLORER,
                number=3,
                character_goal=""
            )
        assert "character_goal" in str(exc_info.value)
