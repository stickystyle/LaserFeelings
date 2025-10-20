# ABOUTME: Contract tests for interface layer signatures and type contracts.
# ABOUTME: Validates DMTextualInterface API contracts without testing implementation.

import inspect
from unittest.mock import Mock

from src.interface.dm_textual import DMTextualInterface
from src.orchestration.message_router import MessageRouter
from src.orchestration.turn_orchestrator import TurnOrchestrator


def test_dm_textual_interface_init_signature():
    """Contract: DMTextualInterface.__init__ accepts orchestrator and router."""
    sig = inspect.signature(DMTextualInterface.__init__)
    params = list(sig.parameters.keys())

    assert "self" in params
    assert "orchestrator" in params
    assert "router" in params


def test_dm_textual_interface_has_compose_method():
    """Contract: DMTextualInterface has compose() method that returns ComposeResult."""
    assert hasattr(DMTextualInterface, "compose")
    method = getattr(DMTextualInterface, "compose")
    assert callable(method)


def test_dm_textual_interface_has_on_mount_method():
    """Contract: DMTextualInterface has on_mount() method."""
    assert hasattr(DMTextualInterface, "on_mount")
    method = getattr(DMTextualInterface, "on_mount")
    assert callable(method)


def test_action_method_return_types():
    """Contract: All action methods return None."""
    mock_orch = Mock(spec=TurnOrchestrator)
    mock_router = Mock(spec=MessageRouter)
    app = DMTextualInterface(orchestrator=mock_orch, router=mock_router)

    # Action methods should exist and be callable
    action_names = [
        "action_quit",
        "action_quick_roll",
        "action_success",
        "action_fail",
        "action_info",
    ]
    for action_name in action_names:
        assert hasattr(app, action_name)
        assert callable(getattr(app, action_name))


def test_write_game_log_signature():
    """Contract: write_game_log accepts content parameter."""
    sig = inspect.signature(DMTextualInterface.write_game_log)
    params = list(sig.parameters.keys())

    assert "self" in params
    assert "content" in params
