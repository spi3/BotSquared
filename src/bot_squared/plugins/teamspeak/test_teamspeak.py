from unittest.mock import MagicMock, patch

import pytest
import ts3
import ts3.definitions

from bot_squared import integrator
from bot_squared.plugins.teamspeak.teamspeak import Teamspeak


@pytest.fixture
@patch.object(Teamspeak, 'load_config')
def test_teamspeak(mock_load_config):
    ts = Teamspeak(plugin_name='Test_Teamspeak', config={})

    return ts


def test_send_message_integrable(test_teamspeak):
    assert integrator.get_integrations(test_teamspeak.plugin_name)['send_message'] == test_teamspeak.send_message


@patch('ts3.query.TS3Connection')
def test_process_msg_in_channel_event(mock_connection: MagicMock, test_teamspeak):
    test_teamspeak.command_prefix = '$'
    test_teamspeak.commands = {
        'TestCommand1': {'response': 'TestResponse1'},
        'TestCommand2': {'response': 'TestResponse2'},
    }

    test_teamspeak.ts3conn = mock_connection
    test_teamspeak.channel_id = 1

    event = {
        'msg': '$TestCommand1',
        'targetmode': ts3.definitions.TextMessageTargetMode.CHANNEL,
        'invokerid': 5,
        'invokername': 'TestUser',
    }

    test_teamspeak.process_msg_event(event)
    mock_connection.sendtextmessage.assert_called_with(
        msg='TestResponse1', targetmode=ts3.definitions.TextMessageTargetMode.CHANNEL, target=test_teamspeak.channel_id
    )


@patch('ts3.query.TS3Connection')
def test_process_new_user_join_event(mock_connection: MagicMock, test_teamspeak):
    test_teamspeak.ts3conn = mock_connection

    event = {'cfid': 0, 'ctid': 1, 'clid': 5, 'client_servergroups': '8'}

    test_teamspeak.process_join_event(event)
    mock_connection.sendtextmessage.assert_not_called()
