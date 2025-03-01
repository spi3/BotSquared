from unittest.mock import MagicMock, patch

import pytest

from bot_squared.integrator import integrates


class TestPlugin:
    def __init__(self, plugin_name):
        self.plugin_name = plugin_name

    @integrates
    def test_integration_function(self, *args, **kwargs):
        return {'return_arg1': 'some_argument_1', 'return_arg2': 'some_argument_2'}


@pytest.fixture
def integrations():
    return {
        'test_plugin': {
            'test_integration_function': {
                'test_integration_plugin': {
                    'function': 'test_integration_plugin_function',
                    'args': {'arg1': '{return_arg1}', 'arg2': '{return_arg2}'},
                }
            }
        }
    }


@patch('bot_squared.integrator._logger')
def test_integrable(logger_mock, integrations):
    mock_plugin = MagicMock()
    with (
        patch('bot_squared.integrator._loaded_plugins', {'test_integration_plugin': mock_plugin}),
        patch('bot_squared.integrator._integrations', integrations),
    ):
        logger_mock.debug = print
        logger_mock.error = print

        test_plugin = TestPlugin('test_plugin')
        test_plugin.test_integration_function()
        instance = mock_plugin.instance
        instance.test_integration_plugin_function.assert_called_once_with(
            {'arg1': 'some_argument_1', 'arg2': 'some_argument_2'}
        )
