import time
from unittest.mock import MagicMock, patch

import pytest
import ts3
import ts3.definitions
from ts3.response import TS3Response

from bot_squared.plugins.teamspeak.teamspeak import Teamspeak
from bot_squared.plugins.teamspeak.teamspeak_config import (
    TeamspeakConfig,
    InactivityMonitoringConfig,
    ChatConfig,
    NewUserAlertingConfig,
)

# Constants
EXPECTED_ADMIN_COUNT = 2

# Constants for test assertions
MAX_RETRY_ATTEMPTS = 4
LOGIN_RETRY_ATTEMPTS = 3
EXTENDED_RETRY_ATTEMPTS = 5


@pytest.fixture(autouse=True)
def mock_event_handler():
    """Mock the event handler to prevent errors during testing."""
    with patch("bot_squared.integrator._event_handler") as mock_handler:
        mock_handler.publish_event.return_value = None
        yield mock_handler


@pytest.fixture
def test_teamspeak():
    """Fixture that creates a test TeamSpeak instance with basic configuration.

    Returns:
        Teamspeak: A configured TeamSpeak instance for testing.
    """
    # Create a test configuration
    test_config = {
        "ts3_server_ip": "localhost",
        "ts3_server_query_username": "TestBot",
        "ts3_server_query_passwd": "TestPass",
        "ts3_server_id": 1,
        "bot_channel_id": 1,
        "iteration_rate_hz": 1,
        "inactivity_monitoring": {
            "enabled": True,
            "afk_channel_id": 0,
            "inactivity_timeout_minutes": 30,
        },
        "chat" : {
            "enabled": True,
            "command_prefix": "!",
            "commands": {
                "TestCommand1": {"response": "TestResponse1"},
            },
        },
        "new_user_alerting": {
            "new_user_message": "Welcome to the server!",
            "new_user_inform_group": "Server Admin",
        },
    }

    ts = Teamspeak(plugin_name="Test_Teamspeak", config=test_config)
    return ts

@patch("ts3.query.TS3Connection")
def test_process_msg_in_channel_event(mock_connection: MagicMock, test_teamspeak):
    """Test processing of channel message events.

    Verifies that when a command message is received in a channel,
    the bot responds with the correct response in the same channel.
    """
    test_teamspeak.command_prefix = "$"
    test_teamspeak.commands = {
        "TestCommand1": {"response": "TestResponse1"},
        "TestCommand2": {"response": "TestResponse2"},
    }

    test_teamspeak.ts3conn = mock_connection

    event = {
        "msg": "$TestCommand1",
        "targetmode": ts3.definitions.TextMessageTargetMode.CHANNEL,
        "invokerid": 5,
        "invokername": "TestUser",
    }

    test_teamspeak._process_msg_event(event)
    mock_connection.sendtextmessage.assert_called_with(
        msg="TestResponse1", targetmode=ts3.definitions.TextMessageTargetMode.CHANNEL, target=test_teamspeak.bot_channel_id
    )


@patch("ts3.query.TS3Connection")
def test_process_new_user_join_event(mock_connection: MagicMock, test_teamspeak):
    """Test basic processing of new user join events.

    Verifies that when a new user joins without special conditions,
    no messages are sent.
    """
    test_teamspeak.ts3conn = mock_connection

    event = {"cfid": 0, "ctid": 1, "clid": 5, "client_servergroups": "8"}

    test_teamspeak._process_join_event(event)
    mock_connection.sendtextmessage.assert_not_called()


@patch("ts3.query.TS3Connection")
def test_update_user_activity(mock_connection: MagicMock, test_teamspeak):
    """Test user activity timestamp updates.

    Verifies that:
    1. New users get an activity timestamp when first seen
    2. Existing users' timestamps are updated when they are active
    """
    test_teamspeak.ts3conn = mock_connection

    # Test updating activity for a new user
    test_teamspeak._update_user_activity("123")
    assert "123" in test_teamspeak.user_activity_timestamps
    initial_timestamp = test_teamspeak.user_activity_timestamps["123"]

    # Test updating activity for an existing user
    time.sleep(0.1)  # Small delay to ensure different timestamp
    test_teamspeak._update_user_activity("123")
    assert test_teamspeak.user_activity_timestamps["123"] > initial_timestamp


@patch("ts3.query.TS3Connection")
def test_check_inactive_users(mock_connection: MagicMock, test_teamspeak):
    """Test the inactive user checking mechanism.

    Verifies that:
    1. Inactive users are moved to the AFK channel
    2. Active users are not moved
    3. Bot users are ignored
    4. Users already in AFK channel are not moved
    5. Moved users receive an inactivity notification
    """
    test_teamspeak.ts3conn = mock_connection
    test_teamspeak.afk_channel_id = 10
    test_teamspeak.inactivity_timeout_minutes = 30

    # Mock client list response
    mock_connection.clientlist.return_value = [
        {"clid": "1", "client_nickname": "ActiveUser", "cid": "1", "client_type": "0"},
        {"clid": "2", "client_nickname": "InactiveUser", "cid": "1", "client_type": "0"},
        {"clid": "3", "client_nickname": "BotUser", "cid": "1", "client_type": "1"},  # Server query client
        {"clid": "4", "client_nickname": "AFKUser", "cid": "10", "client_type": "0"},  # Already in AFK channel
    ]

    # Set up activity timestamps
    current_time = time.time()
    test_teamspeak.user_activity_timestamps = {
        "1": current_time,  # Active user
        "2": current_time - (35 * 60),  # Inactive user (35 minutes)
        "3": current_time,  # Bot user
        "4": current_time - (60 * 60),  # User already in AFK
    }

    # Run the check
    test_teamspeak._check_inactive_users()

    # Verify that only the inactive user was moved
    mock_connection.clientmove.assert_called_once_with(cid=10, clid="2")

    # Verify that the inactive user was notified
    mock_connection.sendtextmessage.assert_called_once()
    call_args = mock_connection.sendtextmessage.call_args[1]
    assert call_args["target"] == "2"
    assert "30 minutes of inactivity" in call_args["msg"]


@patch("ts3.query.TS3Connection")
def test_inactivity_monitoring_disabled(mock_connection: MagicMock, test_teamspeak):
    """Test that when inactivity monitoring is disabled, no actions are taken.

    Verifies that no client list is fetched and no users are moved or notified
    when the inactivity monitoring feature is disabled.
    """
    test_teamspeak.ts3conn = mock_connection
    test_teamspeak.enable_inactivity_monitoring = False

    # Run the check
    test_teamspeak._check_inactive_users()

    # Verify that no actions were taken
    mock_connection.clientlist.assert_not_called()
    mock_connection.clientmove.assert_not_called()
    mock_connection.sendtextmessage.assert_not_called()


@patch("ts3.query.TS3Connection")
def test_process_event_updates_activity(mock_connection: MagicMock, test_teamspeak):
    """Test that user activity is updated for various event types.

    Verifies that user activity timestamps are updated when:
    1. A user sends a message
    2. A user changes channels
    """
    test_teamspeak.ts3conn = mock_connection

    # Test message event
    msg_event = {
        "msg": "test message",
        "invokerid": "1",
        "invokername": "TestUser",
    }
    test_teamspeak._process_event(msg_event)
    assert "1" in test_teamspeak.user_activity_timestamps

    # Test channel change event
    channel_event = {
        "cfid": "1",
        "ctid": "2",
        "clid": "2",
    }
    test_teamspeak._process_event(channel_event)
    assert "2" in test_teamspeak.user_activity_timestamps


@patch("ts3.query.TS3Connection")
def test_process_new_user_join_event_with_notifications(mock_connection: MagicMock, test_teamspeak):
    """Test the full new user join event processing with notifications.

    Verifies that:
    1. New users receive a welcome message
    2. All server admins are notified about the new user
    3. The correct number of admins are notified
    4. Messages contain the correct content and are sent to correct targets
    """
    test_teamspeak.ts3conn = mock_connection

    # Mock server group list response
    mock_connection.servergrouplist.return_value = [
        {"sgid": "8", "name": "Guest"},
        {"sgid": "10", "name": "Server Admin"},
    ]

    # Mock admin group client list
    mock_connection.servergroupclientlist.return_value = [{"cldbid": "100"}, {"cldbid": "101"}]

    # Test event for a new user
    event = {"cfid": "0", "ctid": "1", "clid": "5", "client_servergroups": "8", "client_nickname": "NewUser"}

    test_teamspeak._process_join_event(event)

    # Verify welcome message was sent to new user
    welcome_call = mock_connection.sendtextmessage.call_args_list[0][1]
    assert welcome_call["target"] == "5"
    assert welcome_call["msg"] == "Welcome to the server!"

    # Verify admin notifications
    admin_calls = mock_connection.sendtextmessage.call_args_list[1:]
    assert len(admin_calls) == EXPECTED_ADMIN_COUNT  # Should notify both admins
    for call, admin_id in zip(admin_calls, ["100", "101"]):
        assert call[1]["target"] == admin_id
        assert call[1]["msg"] == "New user joined: NewUser"


@patch("ts3.query.TS3Connection")
def test_process_new_user_join_event_error_handling(mock_connection: MagicMock, test_teamspeak):
    """Test error handling during new user join event processing.

    Verifies that:
    1. TS3QueryErrors are caught and handled gracefully
    2. The function continues execution without raising exceptions
    3. Error logging is triggered (in a real environment)
    """
    test_teamspeak.ts3conn = mock_connection

    # Mock server group list response
    mock_connection.servergrouplist.return_value = [
        {"sgid": "8", "name": "Guest"},
        {"sgid": "10", "name": "Server Admin"},
    ]

    # Mock admin group client list
    mock_connection.servergroupclientlist.return_value = [{"cldbid": "100"}]

    # Create a proper TS3QueryError with a mock response
    mock_response = MagicMock(spec=TS3Response)
    mock_response.error = {"id": "1", "msg": "Test error"}
    mock_connection.sendtextmessage.side_effect = ts3.query.TS3QueryError(mock_response)

    # Test event for a new user
    event = {"cfid": "0", "ctid": "1", "clid": "5", "client_servergroups": "8", "client_nickname": "NewUser"}

    # This should not raise an exception
    test_teamspeak._process_join_event(event)

    # Verify that the error was logged (check the logs in a real environment)
    assert mock_connection.sendtextmessage.call_count > 0


@patch("ts3.query.TS3Connection")
@patch("time.sleep")  # Mock sleep to speed up tests
def test_connect_retry_mechanism(mock_sleep: MagicMock, mock_connection: MagicMock, test_teamspeak):
    """Test the connection retry mechanism with exponential backoff.

    Verifies that:
    1. Connection attempts are retried on failure
    2. Backoff delay increases exponentially
    3. Delay is capped at max_retry_delay
    4. Success is returned when connection is established
    """
    # Configure the mock to fail 3 times then succeed
    mock_connection.side_effect = [
        Exception("Test error"),  # First attempt fails
        Exception("Test error"),  # Second attempt fails
        Exception("Test error"),  # Third attempt fails
        MagicMock(),  # Fourth attempt succeeds
    ]

    # Set retry parameters for test
    test_teamspeak.initial_retry_delay = 2
    test_teamspeak.retry_backoff_factor = 2
    test_teamspeak.max_retry_delay = 8

    # Attempt connection
    result = test_teamspeak._connect()

    # Verify connection was attempted 4 times
    assert mock_connection.call_count == MAX_RETRY_ATTEMPTS

    # Verify sleep delays follow exponential backoff pattern
    expected_delays = [2, 4, 8]  # Initial, 2x, 4x (capped at 8)
    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
    assert sleep_calls == expected_delays

    # Verify final result
    assert result is True


@patch("ts3.query.TS3Connection")
@patch("time.sleep")
def test_connect_retry_with_query_error(mock_sleep: MagicMock, mock_connection: MagicMock, test_teamspeak):
    """Test the connection retry mechanism with TS3QueryError.

    Verifies that:
    1. TS3QueryError is handled properly
    2. Retry mechanism works with different types of errors
    """
    # Create a TS3QueryError with a mock response
    mock_response = MagicMock(spec=ts3.response.TS3Response)
    mock_response.error = {"id": "1", "msg": "Test error"}
    query_error = ts3.query.TS3QueryError(mock_response)

    # Configure connection to fail with different errors then succeed
    connection_instance = MagicMock()
    connection_instance.login.side_effect = [
        query_error,  # First attempt fails with TS3QueryError
        Exception("Test error"),  # Second attempt fails with connection error
        None,  # Third attempt succeeds
    ]
    mock_connection.return_value = connection_instance

    # Set retry parameters
    test_teamspeak.initial_retry_delay = 1
    test_teamspeak.retry_backoff_factor = 2
    test_teamspeak.max_retry_delay = 4

    # Attempt connection
    result = test_teamspeak._connect()

    # Verify connection was attempted 3 times
    assert connection_instance.login.call_count == LOGIN_RETRY_ATTEMPTS

    # Verify sleep delays
    expected_delays = [1, 2]  # Initial, 2x
    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
    assert sleep_calls == expected_delays

    # Verify final result
    assert result is True


@patch("ts3.query.TS3Connection")
@patch("time.sleep")
def test_connect_max_retry_delay(mock_sleep: MagicMock, mock_connection: MagicMock, test_teamspeak):
    """Test that the retry delay is properly capped at max_retry_delay.

    Verifies that:
    1. Delay increases exponentially up to max_retry_delay
    2. Delay remains at max_retry_delay for subsequent retries
    """
    # Configure the mock to fail multiple times then succeed
    mock_connection.side_effect = [
        Exception("Test error"),  # First attempt fails
        Exception("Test error"),  # Second attempt fails
        Exception("Test error"),  # Third attempt fails
        Exception("Test error"),  # Fourth attempt fails
        MagicMock(),  # Fifth attempt succeeds
    ]

    # Set retry parameters
    test_teamspeak.initial_retry_delay = 1
    test_teamspeak.retry_backoff_factor = 2
    test_teamspeak.max_retry_delay = 4

    # Attempt connection
    result = test_teamspeak._connect()

    # Verify connection was attempted 5 times
    assert mock_connection.call_count == EXTENDED_RETRY_ATTEMPTS

    # Verify sleep delays are capped at max_retry_delay
    expected_delays = [1, 2, 4, 4]  # Initial, 2x, 4x (max), 4x (max)
    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
    assert sleep_calls == expected_delays

    # Verify final result
    assert result is True


@patch("ts3.query.TS3Connection")
def test_connect_immediate_success(mock_connection: MagicMock, test_teamspeak):
    """Test successful connection on first attempt.

    Verifies that:
    1. Connection succeeds immediately without retries
    2. No sleep delays are introduced
    3. Proper connection sequence is followed
    """
    # Configure mock for successful connection
    connection_instance = MagicMock()
    mock_connection.return_value = connection_instance
    connection_instance.whoami.return_value = [{"client_id": "1"}]

    # Attempt connection
    result = test_teamspeak._connect()

    # Verify connection was attempted only once
    assert mock_connection.call_count == 1

    # Verify proper connection sequence
    connection_instance.login.assert_called_once_with(
        client_login_name=test_teamspeak.ts3_server_query_username,
        client_login_password=test_teamspeak.ts3_server_query_passwd,
    )
    connection_instance.use.assert_called_once_with(sid=1)
    connection_instance.whoami.assert_called_once()
    connection_instance.clientmove.assert_called_once()

    # Verify final result
    assert result is True


# Tests for TeamspeakConfig dataclass
class TestTeamspeakConfig:
    """Test suite for TeamspeakConfig dataclass and its methods."""

    def test_from_dict_complete_config(self):
        """Test creating TeamspeakConfig from a complete configuration dictionary.
        
        Verifies that all configuration sections are properly converted to their
        respective dataclass instances with correct values.
        """
        config_dict = {
            "ts3_server_ip": "192.168.1.100",
            "ts3_server_query_username": "TestBot",
            "ts3_server_query_passwd": "SecretPassword",
            "ts3_server_id": 1,
            "bot_channel_id": 5,
            "iteration_rate_hz": 2.5,
            "inactivity_monitoring": {
                "enabled": True,
                "afk_channel_id": 10,
                "inactivity_timeout_minutes": 45,
            },
            "chat": {
                "enabled": False,
                "command_prefix": "$",
                "commands": {
                    "help": {"response": "Available commands: help, info"},
                    "info": {"response": "Bot information"},
                },
            },
            "new_user_alerting": {
                "new_user_message": "Welcome to our TeamSpeak server!",
                "new_user_inform_group": "Moderators",
            },
        }

        config = TeamspeakConfig.from_dict(config_dict)

        # Test main configuration
        assert config.ts3_server_ip == "192.168.1.100"
        assert config.ts3_server_query_username == "TestBot"
        assert config.ts3_server_query_passwd == "SecretPassword"
        assert config.ts3_server_id == 1
        assert config.bot_channel_id == 5
        assert config.iteration_rate_hz == 2.5

        # Test inactivity monitoring configuration
        assert isinstance(config.inactivity_monitoring, InactivityMonitoringConfig)
        assert config.inactivity_monitoring.enabled is True
        assert config.inactivity_monitoring.afk_channel_id == 10
        assert config.inactivity_monitoring.inactivity_timeout_minutes == 45

        # Test chat configuration
        assert isinstance(config.chat, ChatConfig)
        assert config.chat.enabled is False
        assert config.chat.command_prefix == "$"
        assert config.chat.commands == {
            "help": {"response": "Available commands: help, info"},
            "info": {"response": "Bot information"},
        }

        # Test new user alerting configuration
        assert isinstance(config.new_user_alerting, NewUserAlertingConfig)
        assert config.new_user_alerting.new_user_message == "Welcome to our TeamSpeak server!"
        assert config.new_user_alerting.new_user_inform_group == "Moderators"

    def test_from_dict_minimal_config(self):
        """Test creating TeamspeakConfig with only required fields.
        
        Verifies that:
        1. Required fields are properly set
        2. Optional sections are initialized with default values
        3. All optional sections are proper dataclass instances
        """
        config_dict = {
            "ts3_server_ip": "localhost",
            "ts3_server_query_username": "MinimalBot",
            "ts3_server_query_passwd": "password123",
            "ts3_server_id": 2,
            "bot_channel_id": 1,
            "iteration_rate_hz": 1.0,
        }

        config = TeamspeakConfig.from_dict(config_dict)

        # Test main configuration
        assert config.ts3_server_ip == "localhost"
        assert config.ts3_server_query_username == "MinimalBot"
        assert config.ts3_server_query_passwd == "password123"
        assert config.ts3_server_id == 2
        assert config.bot_channel_id == 1
        assert config.iteration_rate_hz == 1.0

        # Test that optional sections are initialized with defaults
        assert isinstance(config.inactivity_monitoring, InactivityMonitoringConfig)
        assert config.inactivity_monitoring.enabled is True
        assert config.inactivity_monitoring.afk_channel_id == 0
        assert config.inactivity_monitoring.inactivity_timeout_minutes == 30

        assert isinstance(config.chat, ChatConfig)
        assert config.chat.enabled is True
        assert config.chat.command_prefix == "!"
        assert config.chat.commands == {}

        assert isinstance(config.new_user_alerting, NewUserAlertingConfig)
        assert config.new_user_alerting.new_user_message == "Welcome to the server!"
        assert config.new_user_alerting.new_user_inform_group == "Server Admin"

    def test_from_dict_partial_optional_sections(self):
        """Test creating TeamspeakConfig with partial optional configurations.
        
        Verifies that:
        1. Provided optional configuration values are used
        2. Missing values in optional sections use defaults
        3. Empty optional sections still create proper dataclass instances
        """
        config_dict = {
            "ts3_server_ip": "10.0.0.1",
            "ts3_server_query_username": "PartialBot",
            "ts3_server_query_passwd": "partial123",
            "ts3_server_id": 3,
            "bot_channel_id": 2,
            "iteration_rate_hz": 0.5,
            "inactivity_monitoring": {
                "enabled": False,
                # Missing afk_channel_id and inactivity_timeout_minutes
            },
            "chat": {
                "command_prefix": "#",
                # Missing enabled and commands
            },
            "new_user_alerting": {
                "new_user_message": "Hello there!",
                # Missing new_user_inform_group
            },
        }

        config = TeamspeakConfig.from_dict(config_dict)

        # Test inactivity monitoring with partial config
        assert config.inactivity_monitoring.enabled is False
        assert config.inactivity_monitoring.afk_channel_id == 0  # Default
        assert config.inactivity_monitoring.inactivity_timeout_minutes == 30  # Default

        # Test chat with partial config
        assert config.chat.enabled is True  # Default
        assert config.chat.command_prefix == "#"
        assert config.chat.commands == {}  # Default

        # Test new user alerting with partial config
        assert config.new_user_alerting.new_user_message == "Hello there!"
        assert config.new_user_alerting.new_user_inform_group == "Server Admin"  # Default

    def test_from_dict_empty_optional_sections(self):
        """Test creating TeamspeakConfig with empty optional sections.
        
        Verifies that empty dictionaries for optional sections still create
        proper dataclass instances with all default values.
        """
        config_dict = {
            "ts3_server_ip": "example.com",
            "ts3_server_query_username": "EmptyBot",
            "ts3_server_query_passwd": "empty456",
            "ts3_server_id": 4,
            "bot_channel_id": 3,
            "iteration_rate_hz": 3.0,
            "inactivity_monitoring": {},
            "chat": {},
            "new_user_alerting": {},
        }

        config = TeamspeakConfig.from_dict(config_dict)

        # All optional sections should have default values
        assert config.inactivity_monitoring.enabled is True
        assert config.inactivity_monitoring.afk_channel_id == 0
        assert config.inactivity_monitoring.inactivity_timeout_minutes == 30

        assert config.chat.enabled is True
        assert config.chat.command_prefix == "!"
        assert config.chat.commands == {}

        assert config.new_user_alerting.new_user_message == "Welcome to the server!"
        assert config.new_user_alerting.new_user_inform_group == "Server Admin"

    def test_from_dict_missing_required_fields(self):
        """Test that TeamspeakConfig.from_dict raises KeyError for missing required fields.
        
        Verifies that proper exceptions are raised when required configuration
        fields are missing from the input dictionary.
        """
        # Test missing ts3_server_ip
        incomplete_config = {
            "ts3_server_query_username": "TestBot",
            "ts3_server_query_passwd": "password",
            "ts3_server_id": 1,
            "bot_channel_id": 1,
            "iteration_rate_hz": 1.0,
        }

        with pytest.raises(KeyError, match="ts3_server_ip"):
            TeamspeakConfig.from_dict(incomplete_config)

        # Test missing multiple required fields
        very_incomplete_config = {
            "ts3_server_ip": "localhost",
        }

        with pytest.raises(KeyError):
            TeamspeakConfig.from_dict(very_incomplete_config)

    def test_from_dict_complex_commands_structure(self):
        """Test creating TeamspeakConfig with complex command configurations.
        
        Verifies that complex nested command structures are properly preserved
        in the chat configuration.
        """
        config_dict = {
            "ts3_server_ip": "complex.example.com",
            "ts3_server_query_username": "ComplexBot",
            "ts3_server_query_passwd": "complex789",
            "ts3_server_id": 5,
            "bot_channel_id": 4,
            "iteration_rate_hz": 1.5,
            "chat": {
                "enabled": True,
                "command_prefix": ">>",
                "commands": {
                    "weather": {
                        "response": "Current weather: Sunny",
                        "permissions": ["user", "admin"],
                        "cooldown": 30,
                    },
                    "ban": {
                        "response": "User has been banned",
                        "permissions": ["admin"],
                        "log": True,
                    },
                    "help": {
                        "response": "Available commands: weather, ban, help",
                    },
                },
            },
        }

        config = TeamspeakConfig.from_dict(config_dict)

        # Test that complex command structure is preserved
        assert config.chat.command_prefix == ">>"
        assert len(config.chat.commands) == 3
        
        weather_cmd = config.chat.commands["weather"]
        assert weather_cmd["response"] == "Current weather: Sunny"
        assert weather_cmd["permissions"] == ["user", "admin"]
        assert weather_cmd["cooldown"] == 30

        ban_cmd = config.chat.commands["ban"]
        assert ban_cmd["response"] == "User has been banned"
        assert ban_cmd["permissions"] == ["admin"]
        assert ban_cmd["log"] is True

        help_cmd = config.chat.commands["help"]
        assert help_cmd["response"] == "Available commands: weather, ban, help"

    def test_post_init_behavior(self):
        """Test the __post_init__ behavior of TeamspeakConfig.
        
        Verifies that when creating a TeamspeakConfig directly (not from dict),
        None optional sections are properly initialized with default instances.
        """
        config = TeamspeakConfig(
            ts3_server_ip="direct.example.com",
            ts3_server_query_username="DirectBot",
            ts3_server_query_passwd="direct123",
            ts3_server_id=6,
            bot_channel_id=5,
            iteration_rate_hz=2.0,
            # Optional sections are None, should be initialized by __post_init__
            inactivity_monitoring=None,
            chat=None,
            new_user_alerting=None,
        )

        # Verify that None values were replaced with default instances
        assert isinstance(config.inactivity_monitoring, InactivityMonitoringConfig)
        assert isinstance(config.chat, ChatConfig)
        assert isinstance(config.new_user_alerting, NewUserAlertingConfig)

        # Verify default values
        assert config.inactivity_monitoring.enabled is True
        assert config.chat.enabled is True
        assert config.new_user_alerting.new_user_message == "Welcome to the server!"
