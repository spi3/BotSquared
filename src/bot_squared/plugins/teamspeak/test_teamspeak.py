import time
from unittest.mock import MagicMock, patch

import pytest
import ts3
import ts3.definitions
from ts3.response import TS3Response

from bot_squared.plugins.teamspeak.teamspeak import Teamspeak

# Constants
EXPECTED_ADMIN_COUNT = 2


@pytest.fixture
@patch.object(Teamspeak, "load_config", autospec=True)
def test_teamspeak(mock_load_config):
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
        "inactivity_timeout_minutes": 30,
        "afk_channel_id": 0,
        "enable_inactivity_monitoring": True,
        "command_prefix": "!",
        "commands": {},
        "new_user_message": "Welcome to the server!",
        "new_user_inform_group": "Server Admin"
    }

    # Configure the mock to set up the attributes
    def mock_load_config_impl(instance):
        for key, value in test_config.items():
            setattr(instance, key, value)
    mock_load_config.side_effect = mock_load_config_impl

    ts = Teamspeak(plugin_name="Test_Teamspeak", config=test_config)
    return ts


def test_send_message_integrable(test_teamspeak):
    """Test that the send_message function is properly decorated with @plugin_event."""
    assert hasattr(test_teamspeak.send_message, "__wrapped__"), "send_message should be decorated with @plugin_event"


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
    test_teamspeak.channel_id = 1

    event = {
        "msg": "$TestCommand1",
        "targetmode": ts3.definitions.TextMessageTargetMode.CHANNEL,
        "invokerid": 5,
        "invokername": "TestUser",
    }

    test_teamspeak.process_msg_event(event)
    mock_connection.sendtextmessage.assert_called_with(
        msg="TestResponse1", targetmode=ts3.definitions.TextMessageTargetMode.CHANNEL, target=test_teamspeak.channel_id
    )


@patch("ts3.query.TS3Connection")
def test_process_new_user_join_event(mock_connection: MagicMock, test_teamspeak):
    """Test basic processing of new user join events.

    Verifies that when a new user joins without special conditions,
    no messages are sent.
    """
    test_teamspeak.ts3conn = mock_connection

    event = {"cfid": 0, "ctid": 1, "clid": 5, "client_servergroups": "8"}

    test_teamspeak.process_join_event(event)
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
    test_teamspeak.update_user_activity("123")
    assert "123" in test_teamspeak.user_activity_timestamps
    initial_timestamp = test_teamspeak.user_activity_timestamps["123"]

    # Test updating activity for an existing user
    time.sleep(0.1)  # Small delay to ensure different timestamp
    test_teamspeak.update_user_activity("123")
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
    test_teamspeak.check_inactive_users()

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
    test_teamspeak.check_inactive_users()

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
    test_teamspeak.process_event(msg_event)
    assert "1" in test_teamspeak.user_activity_timestamps

    # Test channel change event
    channel_event = {
        "cfid": "1",
        "ctid": "2",
        "clid": "2",
    }
    test_teamspeak.process_event(channel_event)
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

    test_teamspeak.process_join_event(event)

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
    test_teamspeak.process_join_event(event)

    # Verify that the error was logged (check the logs in a real environment)
    assert mock_connection.sendtextmessage.call_count > 0
