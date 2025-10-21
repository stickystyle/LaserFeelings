# ABOUTME: Unit tests for character configuration loading in the Textual DM interface.
# ABOUTME: Tests successful loading, error handling, and character name resolution.

import json
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from src.interface.dm_textual import DMTextualInterface
from src.models.game_state import GamePhase


@pytest.fixture
def mock_orchestrator():
    """Create a mock TurnOrchestrator"""
    mock = Mock()
    mock.get_current_phase.return_value = GamePhase.DM_NARRATION
    mock.get_turn_number.return_value = 1
    return mock


@pytest.fixture
def mock_router():
    """Create a mock MessageRouter"""
    return Mock()


@pytest.fixture
def textual_interface(mock_orchestrator, mock_router):
    """Create DMTextualInterface instance with mocked dependencies"""
    return DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)


@pytest.fixture
def sample_character_config():
    """Sample character configuration"""
    return {
        "character_id": "char_zara_001",
        "agent_id": "agent_alex_001",
        "name": "Zara-7",
        "style": "Android",
        "role": "Engineer",
        "number": 2,
        "character_goal": "Keep the ship running",
        "equipment": ["Multi-tool", "Diagnostic scanner"],
    }


@pytest.fixture
def sample_character_config_2():
    """Second sample character configuration"""
    return {
        "character_id": "char_kai_004",
        "agent_id": "agent_jordan_004",
        "name": "Dr. Kai Chen",
        "style": "Intrepid",
        "role": "Scientist",
        "number": 3,
        "character_goal": "Discover new phenomena",
        "equipment": ["Tricorder", "Sample containers"],
    }


class TestLoadCharacterNames:
    """Tests for _load_character_names method"""

    def test_load_character_names_success(
        self, textual_interface, sample_character_config, sample_character_config_2
    ):
        """Test successful loading of character configs"""
        # Mock Path.exists to return True
        # Mock Path.glob to return two config files
        mock_config_file_1 = MagicMock()
        mock_config_file_1.__str__.return_value = (
            "config/personalities/char_zara_001_character.json"
        )
        mock_config_file_2 = MagicMock()
        mock_config_file_2.__str__.return_value = (
            "config/personalities/char_kai_004_character.json"
        )

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[mock_config_file_1, mock_config_file_2]
        ), patch(
            "builtins.open",
            side_effect=[
                mock_open(read_data=json.dumps(sample_character_config)).return_value,
                mock_open(read_data=json.dumps(sample_character_config_2)).return_value,
            ],
        ):
            textual_interface._load_character_names()

        # Verify character_names dict is populated
        assert len(textual_interface._character_names) == 2
        assert textual_interface._character_names["char_zara_001"] == "Zara-7"
        assert textual_interface._character_names["char_kai_004"] == "Dr. Kai Chen"

        # Verify character_configs dict is populated
        assert len(textual_interface._character_configs) == 2
        assert textual_interface._character_configs["char_zara_001"] == sample_character_config
        assert textual_interface._character_configs["char_kai_004"] == sample_character_config_2

    def test_load_character_names_directory_not_found(self, textual_interface):
        """Test handling when config directory doesn't exist"""
        with patch("pathlib.Path.exists", return_value=False):
            textual_interface._load_character_names()

        # Verify dicts remain empty
        assert len(textual_interface._character_names) == 0
        assert len(textual_interface._character_configs) == 0

    def test_load_character_names_malformed_json(self, textual_interface):
        """Test handling of malformed JSON in config file"""
        mock_config_file = MagicMock()
        mock_config_file.__str__.return_value = "config/personalities/char_bad_character.json"

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[mock_config_file]
        ), patch("builtins.open", mock_open(read_data="{ invalid json }")):
            textual_interface._load_character_names()

        # Verify dicts remain empty (malformed file was skipped)
        assert len(textual_interface._character_names) == 0
        assert len(textual_interface._character_configs) == 0

    def test_load_character_names_missing_fields(self, textual_interface):
        """Test handling of config file missing required fields"""
        incomplete_config = {
            "character_id": "char_test_001",
            # Missing "name" field
            "style": "Heroic",
        }

        mock_config_file = MagicMock()
        mock_config_file.__str__.return_value = "config/personalities/char_test_001_character.json"

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[mock_config_file]
        ), patch("builtins.open", mock_open(read_data=json.dumps(incomplete_config))):
            textual_interface._load_character_names()

        # Verify incomplete config was not added
        assert len(textual_interface._character_names) == 0
        assert len(textual_interface._character_configs) == 0

    def test_load_character_names_file_read_error(self, textual_interface):
        """Test handling when file cannot be read"""
        mock_config_file = MagicMock()
        mock_config_file.__str__.return_value = "config/personalities/char_test_character.json"

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[mock_config_file]
        ), patch("builtins.open", side_effect=OSError("File not found")):
            textual_interface._load_character_names()

        # Verify dicts remain empty
        assert len(textual_interface._character_names) == 0
        assert len(textual_interface._character_configs) == 0


class TestLoadAgentToCharacterMapping:
    """Tests for _load_agent_to_character_mapping method"""

    def test_load_agent_to_character_mapping_success(
        self, textual_interface, sample_character_config, sample_character_config_2
    ):
        """Test successful loading of agent-to-character mappings"""
        mock_config_file_1 = MagicMock()
        mock_config_file_1.__str__.return_value = (
            "config/personalities/char_zara_001_character.json"
        )
        mock_config_file_2 = MagicMock()
        mock_config_file_2.__str__.return_value = (
            "config/personalities/char_kai_004_character.json"
        )

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[mock_config_file_1, mock_config_file_2]
        ), patch(
            "builtins.open",
            side_effect=[
                mock_open(read_data=json.dumps(sample_character_config)).return_value,
                mock_open(read_data=json.dumps(sample_character_config_2)).return_value,
            ],
        ):
            textual_interface._load_agent_to_character_mapping()

        # Verify agent_to_character dict is populated
        assert len(textual_interface._agent_to_character) == 2
        assert textual_interface._agent_to_character["agent_alex_001"] == "char_zara_001"
        assert textual_interface._agent_to_character["agent_jordan_004"] == "char_kai_004"

    def test_load_agent_to_character_mapping_directory_not_found(self, textual_interface):
        """Test handling when config directory doesn't exist"""
        with patch("pathlib.Path.exists", return_value=False):
            textual_interface._load_agent_to_character_mapping()

        # Verify dict remains empty
        assert len(textual_interface._agent_to_character) == 0

    def test_load_agent_to_character_mapping_malformed_json(self, textual_interface):
        """Test handling of malformed JSON in config file"""
        mock_config_file = MagicMock()
        mock_config_file.__str__.return_value = "config/personalities/char_bad_character.json"

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[mock_config_file]
        ), patch("builtins.open", mock_open(read_data="{ invalid json }")):
            textual_interface._load_agent_to_character_mapping()

        # Verify dict remains empty
        assert len(textual_interface._agent_to_character) == 0

    def test_load_agent_to_character_mapping_missing_fields(self, textual_interface):
        """Test handling of config file missing required fields"""
        incomplete_config = {
            "character_id": "char_test_001",
            # Missing "agent_id" field
            "name": "Test Character",
        }

        mock_config_file = MagicMock()
        mock_config_file.__str__.return_value = "config/personalities/char_test_001_character.json"

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.glob", return_value=[mock_config_file]
        ), patch("builtins.open", mock_open(read_data=json.dumps(incomplete_config))):
            textual_interface._load_agent_to_character_mapping()

        # Verify incomplete config was not added
        assert len(textual_interface._agent_to_character) == 0


class TestGetCharacterName:
    """Tests for _get_character_name helper method"""

    def test_get_character_name_found(self, textual_interface):
        """Test retrieving character name when ID exists"""
        textual_interface._character_names["char_zara_001"] = "Zara-7"

        result = textual_interface._get_character_name("char_zara_001")

        assert result == "Zara-7"

    def test_get_character_name_not_found(self, textual_interface):
        """Test retrieving character name when ID doesn't exist (fallback to ID)"""
        result = textual_interface._get_character_name("char_unknown_999")

        assert result == "char_unknown_999"

    def test_get_character_name_empty_dict(self, textual_interface):
        """Test retrieving character name when dict is empty"""
        result = textual_interface._get_character_name("char_test_001")

        assert result == "char_test_001"
