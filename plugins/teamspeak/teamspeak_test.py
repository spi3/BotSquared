import unittest
from plugins.teamspeak.teamspeak import Teamspeak

class TestTeamspeak(unittest.TestCase):
    def test_create(self):
        self.assertIsInstance(Teamspeak(), Teamspeak)
        
    def test_load_default_config(self):
        ts = Teamspeak()
        ts.load_config()
        self.assertIsNotNone(ts.iteration_rate_hz)

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
                'chat_channel_name': "TestChannel"
            }
        )
        ts.load_config()
        self.assertEqual(ts.chat_channel_name, "TestChannel")
        

if __name__ == '__main__':
    unittest.main()