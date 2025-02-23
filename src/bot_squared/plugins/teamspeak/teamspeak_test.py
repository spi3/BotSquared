import unittest
from unittest.mock import MagicMock, patch

import ts3
import ts3.definitions

from bot_squared.plugins.teamspeak.teamspeak import Teamspeak


class TestTeamspeak(unittest.TestCase):
    def test_create(self):
        self.assertIsInstance(Teamspeak(), Teamspeak)

    def test_load_default_config(self):
        ts = Teamspeak()
        ts.load_config()
        self.assertIsNotNone(ts.iteration_rate_hz)
        self.assertIsNotNone(ts.command_prefix)

    def test_load_config_iteration_rate_hz(self):
        ts = Teamspeak(
            {
                'iteration_rate_hz': 5
            }
        )
        ts.load_config()
        self.assertEqual(ts.iteration_rate_hz, 5)

    def test_load_config_ts3_server_ip(self):
        ts = Teamspeak(
            {
                'ts3_server_ip': '1.1.1.1'
            }
        )
        ts.load_config()
        self.assertEqual(ts.ts3_server_ip, '1.1.1.1')

    def test_load_config_ts3_server_query_username(self):
        ts = Teamspeak(
            {
                'ts3_server_query_username': 'test_username'
            }
        )
        ts.load_config()
        self.assertEqual(ts.ts3_server_query_username, 'test_username')

    def test_load_config_ts3_server_query_passwd(self):
        ts = Teamspeak(
            {
                'ts3_server_query_passwd': 'test_pass'
            }
        )
        ts.load_config()
        self.assertEqual(ts.ts3_server_query_passwd, 'test_pass')

    def test_load_config_ts3_server_id(self):
        ts = Teamspeak(
            {
                'ts3_server_id': 5
            }
        )
        ts.load_config()
        self.assertEqual(ts.ts3_server_id, 5)

    def test_load_config_chat_channel_name(self):
        ts = Teamspeak(
            {
                'chat_channel_name': 'TestChannel'
            }
        )
        ts.load_config()
        self.assertEqual(ts.chat_channel_name, 'TestChannel')

    def test_load_config_name(self):
        ts = Teamspeak(
            {
                'name': 'TestName'
            }
        )
        ts.load_config()
        self.assertEqual(ts.name, 'TestName')

    def test_load_config_command_prefix(self):
        ts = Teamspeak(
            {
                'command_prefix': 'abc'
            }
        )
        ts.load_config()
        self.assertEqual(ts.command_prefix, 'abc')

    def test_load_config_commands(self):
        ts = Teamspeak(
            {
                'commands': {'TestCommand' : 'TestResponse'}
            },
            {}
        )
        ts.load_config()
        self.assertTrue('TestCommand' in ts.commands)
        self.assertEqual(ts.commands['TestCommand'], 'TestResponse')

    @patch('ts3.query.TS3Connection')
    def test_process_msg_in_channel_event(self, mock_connection: MagicMock):
        ts = Teamspeak(
            config={
                'command_prefix': '$',
                'commands': {
                    'TestCommand1': {
                        'response': 'TestResponse1'
                    },
                    'TestCommand2': {
                        'response': 'TestResponse2'
                    }
                }
            },
            loaded_plugins={}
        )

        ts.ts3conn = mock_connection
        ts.channel_id = 1

        event = {
            'msg': '$TestCommand1',
            'targetmode': ts3.definitions.TextMessageTargetMode.CHANNEL,
            'invokerid': 5,
            'invokername': 'TestUser'
        }

        ts.process_msg_event(event)
        mock_connection.sendtextmessage.assert_called_with(msg='TestResponse1',
                                                           targetmode=ts3.definitions.TextMessageTargetMode.CHANNEL,
                                                           target=ts.channel_id)

    @patch('ts3.query.TS3Connection')
    def test_process_new_user_join_event(self, mock_connection):
        ts = Teamspeak()
        ts.ts3conn = mock_connection

        event = {
            'cfid': 0,
            'ctid': 1,
            'clid': 5,
            'client_servergroups': '8'
        }

        ts.process_join_event(event)
        mock_connection.sendtextmessage.assert_not_called()

if __name__ == '__main__':
    unittest.main()
