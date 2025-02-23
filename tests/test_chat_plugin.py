from unittest import TestCase
from unittest.mock import MagicMock, patch

from bot_squared.interfaces.chat_plugin import ChatPlugin


class TestChatPlugin(TestCase):
    def setUp(self):
        self.config = {
            'integrations': {
                'receive_message': {
                    'plugin1': {'function': 'handle_message'}
                }
            }
        }
        mock_plugin = MagicMock()
        mock_plugin.instance = MagicMock()
        
        self.loaded_plugins = {
            'plugin1': mock_plugin
        }
        self.logger = MagicMock()
        self.chat_plugin = ChatPlugin(config=self.config, loaded_plugins=self.loaded_plugins, logger=self.logger)

    def test_has_integrations(self):
        self.assertTrue(self.chat_plugin.has_integrations())

    def test_run_integration_no_integrations(self):
        self.chat_plugin.config = {}
        self.chat_plugin.run_integration('test_message', 'receive_message')
        self.logger.error.assert_not_called()

    def test_run_integration_plugin_not_loaded(self):
        self.chat_plugin.loaded_plugins = {}
        self.chat_plugin.run_integration('test_message', 'receive_message')
        self.logger.error.assert_called_with('Integration invalid - Plugin plugin1 not loaded')

    def test_run_integration_function_called(self):
        msg = 'test_message'
        self.chat_plugin.run_integration(msg, 'receive_message')
        self.loaded_plugins['plugin1'].instance.handle_message.assert_called_with(msg)

    def test_receive_message(self):
        with patch.object(self.chat_plugin, 'run_integration') as mock_run_integration:
            self.chat_plugin.receive_message('test_message')
            mock_run_integration.assert_called_with('receive_message', 'test_message')
