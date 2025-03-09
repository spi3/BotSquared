from unittest.mock import MagicMock, patch

import pytest

from bot_squared.integrator import integrates


class TestPlugin:
    def __init__(self, plugin_name):
        self.plugin_name = plugin_name

    @integrates
    def test_integration_function_dict(self, *args, **kwargs):
        return {"return_value1": "some_argument_1", "return_value2": "some_argument_2"}

    @integrates
    def test_integration_function_dict_with_static_value(self, *args, **kwargs):
        return {"return_value1": "some_argument_1", "return_value2": "some_argument_2"}

    @integrates
    def test_integration_function_value(self, *args, **kwargs):
        return "some_value"


@pytest.fixture
def integrations():
    return {
        "test_plugin": {
            "test_integration_function_dict": [
                {
                    "plugin_name": "test_integration_plugin",
                    "function": "test_integration_plugin_function",
                    "args": {"arg1": "{return_value1}", "arg2": "{return_value2}"}
                }
            ],
            "test_integration_function_dict_with_static_value": [
                {
                    "plugin_name": "test_integration_plugin",
                    "function": "test_integration_plugin_function",
                    "args": {"arg1": "{return_value1}", "arg2": "{return_value2}", "arg3": "some_static_value"}
                }
            ],
            "test_integration_function_value": [
                {
                    "plugin_name": "test_integration_plugin",
                    "function": "test_integration_plugin_function",
                    "args": {"arg": "{return_val}"},
                }
            ]
        }
    }


@patch("bot_squared.integrator._logger")
def test_integrable_dict_return(logger_mock, integrations):
    mock_plugin = MagicMock()
    with (
        patch("bot_squared.integrator._loaded_plugins", {"test_integration_plugin": mock_plugin}),
        patch("bot_squared.integrator._integrations", integrations),
    ):
        logger_mock.debug = print
        logger_mock.error = print

        test_plugin = TestPlugin("test_plugin")
        test_plugin.test_integration_function_dict()
        instance = mock_plugin.instance
        instance.add_to_queue.assert_called_once_with(
            "test_integration_plugin_function",
            {"arg1": "some_argument_1", "arg2": "some_argument_2"}
        )


@patch("bot_squared.integrator._logger")
def test_integrable_value_return(logger_mock, integrations):
    mock_plugin = MagicMock()

    with (
        patch("bot_squared.integrator._loaded_plugins", {"test_integration_plugin": mock_plugin}),
        patch("bot_squared.integrator._integrations", integrations),
    ):
        logger_mock.debug = print
        logger_mock.error = print

        test_plugin = TestPlugin("test_plugin")
        test_plugin.test_integration_function_value()
        instance = mock_plugin.instance
        instance.add_to_queue.assert_called_once_with(
            "test_integration_plugin_function",
            {"arg": "some_value"}
        )


@patch("bot_squared.integrator._logger")
def test_integrable_dict_return_static_value(logger_mock, integrations):
    mock_plugin = MagicMock()
    with (
        patch("bot_squared.integrator._loaded_plugins", {"test_integration_plugin": mock_plugin}),
        patch("bot_squared.integrator._integrations", integrations),
    ):
        logger_mock.debug = print
        logger_mock.error = print

        test_plugin = TestPlugin("test_plugin")
        test_plugin.test_integration_function_dict_with_static_value()
        instance = mock_plugin.instance
        instance.add_to_queue.assert_called_once_with(
            "test_integration_plugin_function",
            {"arg1": "some_argument_1", "arg2": "some_argument_2", "arg3": "some_static_value"}
        )
