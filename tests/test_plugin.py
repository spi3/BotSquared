from unittest import TestCase
from unittest.mock import MagicMock, patch

from bot_squared.plugins import Plugin


class TestPlugin(TestCase):
    @patch('plugins.plugin.importlib.import_module')
    def test_plugin_initialization(self, mock_import_module):
        mock_module = MagicMock()
        mock_instance = MagicMock()
        mock_import_module.return_value = mock_module
        mock_module.create_plugin.return_value = mock_instance

        plugin_name = 'test_plugin'
        plugin_conf = {'key': 'value'}
        plugin = Plugin(plugin_name, plugin_conf)

        mock_import_module.assert_called_once_with(f'plugins.{plugin_name}')
        mock_module.create_plugin.assert_called_once_with(plugin_conf)
        self.assertEqual(plugin.name, plugin_name)
        self.assertEqual(plugin.instance, mock_instance)
        self.assertTrue(plugin.thread.is_alive())

    @patch('plugins.plugin.importlib.import_module')
    def test_plugin_run_method_called(self, mock_import_module):
        mock_module = MagicMock()
        mock_instance = MagicMock()
        mock_import_module.return_value = mock_module
        mock_module.create_plugin.return_value = mock_instance

        plugin_name = 'test_plugin'
        Plugin(plugin_name)

        mock_instance.run.assert_called_once()
