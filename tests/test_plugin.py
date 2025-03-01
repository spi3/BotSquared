from time import sleep
from unittest.mock import MagicMock, patch

import pytest

from bot_squared.plugins.plugin import Plugin


@pytest.fixture
def plugin_args():
    return {'plugin_name': 'test_plugin', 'plugin_type': 'test_plugin_type', 'plugin_conf': {'key': 'value'}}


@patch('bot_squared.plugins.plugin.importlib.import_module')
def test_plugin_initialization(mock_import_module, plugin_args):
    mock_module = MagicMock()
    mock_instance = MagicMock()
    mock_import_module.return_value = mock_module
    mock_module.create_plugin.return_value = mock_instance

    testing = True

    def mock_run():
        while testing:
            sleep(0.1)

    mock_instance.run = mock_run

    plugin = Plugin(**plugin_args)

    mock_import_module.assert_called_once_with(f"plugins.{plugin_args['plugin_type']}")
    mock_module.create_plugin.assert_called_once_with(plugin_args['plugin_conf'])
    assert plugin.name == plugin_args['plugin_name']
    assert plugin.plugin_type == plugin_args['plugin_type']
    assert plugin.conf == plugin_args['plugin_conf']
    assert plugin.instance == mock_instance
    assert plugin.thread.is_alive()
    testing = False


@patch('bot_squared.plugins.plugin.importlib.import_module')
def test_plugin_run_method_called(mock_import_module, plugin_args):
    mock_module = MagicMock()
    mock_instance = MagicMock()
    mock_import_module.return_value = mock_module
    mock_module.create_plugin.return_value = mock_instance

    Plugin(**plugin_args)

    mock_instance.run.assert_called_once()
