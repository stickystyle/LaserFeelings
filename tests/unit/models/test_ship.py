# ABOUTME: Unit tests for ShipConfig model validation and narrative description methods.
# ABOUTME: Validates ship strengths, problems, and ensures attributes are narrative-only (no mechanical bonuses).

import pytest
from pydantic import ValidationError

from src.models.ship import ShipConfig


class TestShipConfigValidConstruction:
    """Test suite for valid ShipConfig model construction"""

    def test_valid_ship_config_creation(self):
        """Test creating a valid ship configuration"""
        ship = ShipConfig(
            name="The Raptor",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        assert ship.name == "The Raptor"
        assert ship.strengths == ["Fast", "Nimble"]
        assert ship.problem == "Fuel Hog"

    def test_ship_config_with_different_valid_strengths(self):
        """Test ship with various valid strength combinations"""
        valid_combos = [
            (["Fast", "Well-Armed"], "Only One Medical Pod"),
            (["Nimble", "Powerful Shields"], "Horrible Circuit Breakers"),
            (["Superior Sensors", "Cloaking Device"], "Grim Reputation"),
            (["Fightercraft", "Fast"], "Fuel Hog")
        ]

        for strengths, problem in valid_combos:
            ship = ShipConfig(
                name="Test Ship",
                strengths=strengths,
                problem=problem
            )
            assert ship.strengths == strengths
            assert ship.problem == problem

    def test_all_valid_strengths_accepted(self):
        """Test that all documented strengths from L&F rules are valid"""
        valid_strengths = [
            "Fast",
            "Nimble",
            "Well-Armed",
            "Powerful Shields",
            "Superior Sensors",
            "Cloaking Device",
            "Fightercraft"
        ]

        for strength in valid_strengths:
            ship = ShipConfig(
                name="Test Ship",
                strengths=[strength, "Fast"],  # Pair with "Fast" for variety
                problem="Fuel Hog"
            )
            assert strength in ship.strengths

    def test_all_valid_problems_accepted(self):
        """Test that all documented problems from L&F rules are valid"""
        valid_problems = [
            "Fuel Hog",
            "Only One Medical Pod",
            "Horrible Circuit Breakers",
            "Grim Reputation"
        ]

        for problem in valid_problems:
            ship = ShipConfig(
                name="Test Ship",
                strengths=["Fast", "Nimble"],
                problem=problem
            )
            assert ship.problem == problem


class TestShipConfigStrengthsValidation:
    """Test suite for strengths field validation"""

    def test_requires_exactly_two_strengths(self):
        """Test that ship must have exactly 2 strengths"""
        ship = ShipConfig(
            name="Test Ship",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )
        assert len(ship.strengths) == 2

    def test_rejects_too_few_strengths(self):
        """Test ValidationError when fewer than 2 strengths provided"""
        with pytest.raises(ValidationError, match="List should have at least 2 items"):
            ShipConfig(
                name="Test Ship",
                strengths=["Fast"],  # Only one strength
                problem="Fuel Hog"
            )

    def test_rejects_zero_strengths(self):
        """Test ValidationError when zero strengths provided"""
        with pytest.raises(ValidationError, match="List should have at least 2 items"):
            ShipConfig(
                name="Test Ship",
                strengths=[],  # No strengths
                problem="Fuel Hog"
            )

    def test_rejects_too_many_strengths(self):
        """Test ValidationError when more than 2 strengths provided"""
        with pytest.raises(ValidationError, match="List should have at most 2 items"):
            ShipConfig(
                name="Test Ship",
                strengths=["Fast", "Nimble", "Well-Armed"],  # Three strengths
                problem="Fuel Hog"
            )

    def test_rejects_invalid_strength_value(self):
        """Test ValidationError for strength not in L&F rules"""
        with pytest.raises(ValidationError, match="Input should be"):
            ShipConfig(
                name="Test Ship",
                strengths=["Invalid Strength", "Fast"],
                problem="Fuel Hog"
            )

    def test_rejects_strength_with_wrong_case(self):
        """Test ValidationError for strength with incorrect capitalization"""
        with pytest.raises(ValidationError, match="Input should be"):
            ShipConfig(
                name="Test Ship",
                strengths=["fast", "nimble"],  # Should be "Fast", "Nimble"
                problem="Fuel Hog"
            )

    def test_accepts_duplicate_strengths(self):
        """Test that duplicate strengths are allowed (rules don't forbid)"""
        ship = ShipConfig(
            name="Test Ship",
            strengths=["Fast", "Fast"],  # Same strength twice
            problem="Fuel Hog"
        )
        assert ship.strengths == ["Fast", "Fast"]


class TestShipConfigProblemValidation:
    """Test suite for problem field validation"""

    def test_rejects_invalid_problem_value(self):
        """Test ValidationError for problem not in L&F rules"""
        with pytest.raises(ValidationError, match="Input should be"):
            ShipConfig(
                name="Test Ship",
                strengths=["Fast", "Nimble"],
                problem="Invalid Problem"
            )

    def test_rejects_problem_with_wrong_case(self):
        """Test ValidationError for problem with incorrect capitalization"""
        with pytest.raises(ValidationError, match="Input should be"):
            ShipConfig(
                name="Test Ship",
                strengths=["Fast", "Nimble"],
                problem="fuel hog"  # Should be "Fuel Hog"
            )

    def test_rejects_empty_problem(self):
        """Test ValidationError for empty problem string"""
        with pytest.raises(ValidationError, match="Input should be"):
            ShipConfig(
                name="Test Ship",
                strengths=["Fast", "Nimble"],
                problem=""
            )


class TestShipConfigNameValidation:
    """Test suite for name field validation"""

    def test_accepts_valid_ship_names(self):
        """Test various valid ship name formats"""
        valid_names = [
            "The Raptor",
            "Starlight Runner",
            "USS Enterprise",
            "X-Wing",
            "Serenity",
            "Normandy SR-2",
            "ミレニアム・ファルコン",  # Unicode characters
            "Ship #42"
        ]

        for name in valid_names:
            ship = ShipConfig(
                name=name,
                strengths=["Fast", "Nimble"],
                problem="Fuel Hog"
            )
            assert ship.name == name

    def test_rejects_empty_ship_name(self):
        """Test ValidationError for empty ship name"""
        with pytest.raises(ValidationError, match="String should have at least 1 character"):
            ShipConfig(
                name="",
                strengths=["Fast", "Nimble"],
                problem="Fuel Hog"
            )

    def test_rejects_whitespace_only_ship_name(self):
        """Test ValidationError for whitespace-only ship name"""
        with pytest.raises(ValidationError, match="Ship name cannot be only whitespace"):
            ShipConfig(
                name="   ",
                strengths=["Fast", "Nimble"],
                problem="Fuel Hog"
            )


class TestShipConfigImmutability:
    """Test suite for frozen (immutable) configuration"""

    def test_ship_config_is_frozen(self):
        """Test that ShipConfig cannot be modified after creation"""
        ship = ShipConfig(
            name="The Raptor",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        with pytest.raises(ValidationError, match="Instance is frozen"):
            ship.name = "New Name"

    def test_cannot_modify_strengths_list(self):
        """Test that strengths list cannot be modified"""
        ship = ShipConfig(
            name="The Raptor",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        with pytest.raises(ValidationError, match="Instance is frozen"):
            ship.strengths = ["Well-Armed", "Powerful Shields"]

    def test_cannot_modify_problem(self):
        """Test that problem cannot be modified"""
        ship = ShipConfig(
            name="The Raptor",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        with pytest.raises(ValidationError, match="Instance is frozen"):
            ship.problem = "Grim Reputation"


class TestToNarrativeDescription:
    """Test suite for to_narrative_description() method"""

    def test_narrative_description_format(self):
        """Test that narrative description includes all ship attributes"""
        ship = ShipConfig(
            name="The Raptor",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        desc = ship.to_narrative_description()

        assert "The Raptor" in desc
        assert "Fast" in desc
        assert "Nimble" in desc
        assert "Fuel Hog" in desc

    def test_narrative_description_contains_structure(self):
        """Test that narrative description has expected structure"""
        ship = ShipConfig(
            name="Starlight Runner",
            strengths=["Powerful Shields", "Superior Sensors"],
            problem="Horrible Circuit Breakers"
        )

        desc = ship.to_narrative_description()

        # Should contain ship name, strengths section, and problem section
        assert "Starlight Runner" in desc
        assert "Strengths:" in desc or "strengths:" in desc
        assert "Problem:" in desc or "problem:" in desc

    def test_narrative_description_includes_both_strengths(self):
        """Test that both strengths appear in narrative description"""
        ship = ShipConfig(
            name="Test Ship",
            strengths=["Cloaking Device", "Fightercraft"],
            problem="Grim Reputation"
        )

        desc = ship.to_narrative_description()

        assert "Cloaking Device" in desc
        assert "Fightercraft" in desc

    def test_narrative_description_is_human_readable(self):
        """Test that description is formatted for readability"""
        ship = ShipConfig(
            name="The Falcon",
            strengths=["Fast", "Well-Armed"],
            problem="Only One Medical Pod"
        )

        desc = ship.to_narrative_description()

        # Description should be a single readable string
        assert isinstance(desc, str)
        assert len(desc) > 0
        # Should contain commas or other separators for readability
        assert "," in desc or ";" in desc or "(" in desc


class TestShipConfigSerialization:
    """Test suite for model serialization"""

    def test_ship_config_serializes_to_dict(self):
        """Test that ShipConfig can be serialized to dictionary"""
        ship = ShipConfig(
            name="The Raptor",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        serialized = ship.model_dump()

        assert serialized["name"] == "The Raptor"
        assert serialized["strengths"] == ["Fast", "Nimble"]
        assert serialized["problem"] == "Fuel Hog"

    def test_ship_config_deserializes_from_dict(self):
        """Test that ShipConfig can be created from dictionary"""
        ship_data = {
            "name": "Serenity",
            "strengths": ["Fast", "Nimble"],
            "problem": "Fuel Hog"
        }

        ship = ShipConfig(**ship_data)

        assert ship.name == "Serenity"
        assert ship.strengths == ["Fast", "Nimble"]
        assert ship.problem == "Fuel Hog"

    def test_roundtrip_serialization(self):
        """Test that serialize -> deserialize preserves data"""
        original = ShipConfig(
            name="USS Discovery",
            strengths=["Superior Sensors", "Powerful Shields"],
            problem="Horrible Circuit Breakers"
        )

        serialized = original.model_dump()
        restored = ShipConfig(**serialized)

        assert restored.name == original.name
        assert restored.strengths == original.strengths
        assert restored.problem == original.problem


class TestDocumentedNarrativeOnlyBehavior:
    """Test suite documenting that ship attributes are narrative-only"""

    def test_ship_config_docstring_mentions_narrative_only(self):
        """Test that ShipConfig class docstring mentions narrative-only nature"""
        assert "NARRATIVE" in ShipConfig.__doc__ or "narrative" in ShipConfig.__doc__

    def test_ship_config_docstring_mentions_no_bonuses(self):
        """Test that ShipConfig class docstring warns about no mechanical bonuses"""
        docstring = ShipConfig.__doc__.lower()
        assert "no" in docstring and ("bonus" in docstring or "dice" in docstring or "mechanical" in docstring)

    def test_ship_strengths_do_not_have_numeric_values(self):
        """Test that ship strengths are strings, not numeric bonuses"""
        ship = ShipConfig(
            name="Test Ship",
            strengths=["Fast", "Well-Armed"],
            problem="Fuel Hog"
        )

        # Strengths should be strings, not numbers
        for strength in ship.strengths:
            assert isinstance(strength, str)
            # Should not be numeric strings like "2" or "+3"
            assert not strength.isdigit()

    def test_ship_problem_does_not_have_numeric_penalty(self):
        """Test that ship problem is a string, not a numeric penalty"""
        ship = ShipConfig(
            name="Test Ship",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        # Problem should be a string, not a number
        assert isinstance(ship.problem, str)
        assert not ship.problem.isdigit()


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions"""

    def test_unicode_in_ship_name(self):
        """Test that unicode characters in ship name are handled correctly"""
        ship = ShipConfig(
            name="千年隼号 (Millennium Falcon)",
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        assert "千年隼号" in ship.name

    def test_special_characters_in_ship_name(self):
        """Test that special characters in ship name are allowed"""
        ship = ShipConfig(
            name="Ship-42 (Mark IV)",
            strengths=["Fast", "Well-Armed"],
            problem="Fuel Hog"
        )

        assert ship.name == "Ship-42 (Mark IV)"

    def test_very_long_ship_name(self):
        """Test that very long ship names are accepted"""
        long_name = "The Extraordinarily Long Ship Name That Goes On And On For Testing Purposes" * 2

        ship = ShipConfig(
            name=long_name,
            strengths=["Fast", "Nimble"],
            problem="Fuel Hog"
        )

        assert ship.name == long_name
        assert len(ship.name) > 100

    def test_strengths_order_is_preserved(self):
        """Test that strengths list order is preserved"""
        ship = ShipConfig(
            name="Test Ship",
            strengths=["Nimble", "Fast"],  # Intentionally reversed alphabetical order
            problem="Fuel Hog"
        )

        assert ship.strengths[0] == "Nimble"
        assert ship.strengths[1] == "Fast"
