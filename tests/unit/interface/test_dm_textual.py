# ABOUTME: Unit tests for DMTextualInterface Textual app structure and composition.
# ABOUTME: Tests instantiation, bindings, action methods, CSS, and stored dependencies.

from unittest.mock import Mock

import pytest

from src.interface.dm_textual import DMTextualInterface
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
    return DMTextualInterface(orchestrator=mock_orchestrator, router=mock_router)


def test_dm_textual_app_instantiation(app):
    """Test DMTextualInterface can be instantiated with valid dependencies."""
    assert app is not None
    assert app.orchestrator is not None
    assert app.router is not None


def test_dm_textual_app_has_bindings(app):
    """Test DMTextualInterface has required keyboard bindings."""
    binding_keys = {binding[0] for binding in app.BINDINGS}
    assert "ctrl+q" in binding_keys
    assert "ctrl+r" in binding_keys
    assert "ctrl+s" in binding_keys
    assert "ctrl+f" in binding_keys
    assert "ctrl+i" in binding_keys


def test_dm_textual_app_action_methods_exist(app):
    """Test all action methods defined in BINDINGS exist."""
    assert hasattr(app, "action_quit")
    assert hasattr(app, "action_quick_roll")
    assert hasattr(app, "action_success")
    assert hasattr(app, "action_fail")
    assert hasattr(app, "action_info")


def test_write_game_log_method_exists(app):
    """Test write_game_log method exists and is callable."""
    assert hasattr(app, "write_game_log")
    assert callable(app.write_game_log)


def test_dm_textual_css_is_defined(app):
    """Test CSS styling is defined."""
    assert app.CSS is not None
    assert len(app.CSS) > 0
    assert "#main" in app.CSS
    assert "#game-log" in app.CSS
    assert "#ooc-log" in app.CSS
    assert "#dm-input" in app.CSS


def test_orchestrator_and_router_stored(app):
    """Test orchestrator and router are stored as instance attributes."""
    assert hasattr(app, "orchestrator")
    assert hasattr(app, "router")
    assert app.orchestrator is not None
    assert app.router is not None
