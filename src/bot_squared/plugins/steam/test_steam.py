"""
Unit tests for the Steam plugin module.

This module contains test cases for the Steam plugin class, covering initialization,
server querying, and response formatting functionality.
"""

from unittest.mock import Mock, patch

import a2s
import pytest

from bot_squared.plugins.steam.steam import DEFAULT_UPDATE_INTERVAL, Steam

# Test constants
TEST_PLAYER_COUNT = 5
TEST_MAX_PLAYERS = 20


@pytest.fixture
def valid_config():
    """Provides a standard valid configuration for testing."""
    return {
        "steam_server": "test.server.com",
        "steam_port": 27015,
    }


@pytest.fixture
def mock_server_info():
    """Provides a mock server info response with all attributes."""
    info = Mock()
    info.player_count = 10
    info.max_players = 32
    info.server_name = "Test Server"
    info.map_name = "test_map"
    info.game = "Test Game"
    return info


@pytest.fixture(autouse=True)
def mock_plugin_event():
    """Mock the plugin_event decorator to do nothing."""
    with patch("bot_squared.plugins.steam.steam.plugin_event") as mock_decorator, \
         patch("bot_squared.integrator._event_handler") as mock_event_handler:
        mock_decorator.side_effect = lambda func: func
        mock_event_handler.publish_event.return_value = None
        yield mock_decorator


def test_successful_initialization(valid_config):
    """Test successful plugin initialization with valid config."""
    plugin = Steam("test_plugin", valid_config)

    assert plugin.plugin_name == "test_plugin"
    assert plugin.steam_server == valid_config["steam_server"]
    assert plugin.steam_port == valid_config["steam_port"]
    assert plugin.update_interval == DEFAULT_UPDATE_INTERVAL


def test_initialization_with_custom_interval(valid_config):
    """Test initialization with custom update interval."""
    custom_interval = 120
    config = valid_config.copy()
    config["update_interval_seconds"] = custom_interval

    plugin = Steam("test_plugin", config)
    assert plugin.update_interval == custom_interval


@pytest.mark.parametrize("missing_key", ["steam_server", "steam_port"])
def test_initialization_missing_required_config(valid_config, missing_key):
    """Test initialization fails when required config keys are missing."""
    config = valid_config.copy()
    del config[missing_key]

    with pytest.raises(ValueError) as exc_info:
        Steam("test_plugin", config)
    assert missing_key in str(exc_info.value)


@patch("a2s.info")
def test_successful_server_query(mock_a2s_info, valid_config, mock_server_info):
    """Test successful server status query with all attributes."""
    mock_a2s_info.return_value = mock_server_info
    plugin = Steam("test_plugin", valid_config)

    status = plugin.get_server_status()

    assert status["status"] == "Online"
    assert status["player_count"] == mock_server_info.player_count
    assert status["max_players"] == mock_server_info.max_players
    assert status["server_name"] == mock_server_info.server_name
    assert status["map_name"] == mock_server_info.map_name
    assert status["game"] == mock_server_info.game


@pytest.mark.parametrize(
    "exception,expected_status",
    [
        (a2s.BrokenMessageError("Broken message"), "Offline"),
        (a2s.BufferExhaustedError("Buffer exhausted"), "Offline"),
        (TimeoutError("Connection timeout"), "Offline"),
        (Exception("Generic error"), "Offline"),
    ],
)
@patch("a2s.info")
def test_server_query_exceptions(mock_a2s_info, valid_config, exception, expected_status):
    """Test handling of various exceptions during server query."""
    mock_a2s_info.side_effect = exception
    plugin = Steam("test_plugin", valid_config)

    status = plugin.get_server_status()

    assert status["status"] == expected_status
    assert status["player_count"] == 0
    assert status["max_players"] == 0


def test_format_server_info_missing_attributes(valid_config):
    """Test handling of missing optional attributes in server info."""
    # Create mock info with only required attributes
    info = Mock()
    info.player_count = TEST_PLAYER_COUNT
    info.max_players = TEST_MAX_PLAYERS

    # Configure mock to return None for missing attributes
    info.server_name = None
    info.map_name = None
    info.game = None

    plugin = Steam("test_plugin", valid_config)
    formatted_info = plugin._format_server_info(info)

    assert formatted_info["status"] == "Online"
    assert formatted_info["player_count"] == TEST_PLAYER_COUNT
    assert formatted_info["max_players"] == TEST_MAX_PLAYERS
    assert formatted_info["server_name"] == "Unknown"
    assert formatted_info["map_name"] == "Unknown"
    assert formatted_info["game"] == "Unknown"
