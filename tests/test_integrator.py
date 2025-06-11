import time
from unittest.mock import MagicMock, patch

import pytest

from bot_squared.integrator import get_event_handler, plugin_event


class TestPlugin:
    def __init__(self, name):
        self.name = name
        self.plugin_name = name  # Required by the plugin_event decorator

    @plugin_event
    def test_integration_function_dict(self):
        return {"return_value1": "test1", "return_value2": "test2"}

    @plugin_event
    def test_integration_function_value(self):
        return "test_value"

    @plugin_event
    def test_integration_function_dict_with_static_value(self):
        return {"return_value1": "test1", "return_value2": "test2"}


@pytest.fixture
def integrations():
    return {
        "test_plugin": {
            "test_integration_function_dict": [
                {
                    "plugin_name": "test_integration_plugin",
                    "function": "test_integration_plugin_function",
                    "args": {"arg1": "{return_value1}", "arg2": "{return_value2}"},
                }
            ],
            "test_integration_function_value": [
                {
                    "plugin_name": "test_integration_plugin",
                    "function": "test_integration_plugin_function",
                    "args": {"arg": "{return_val}"},
                }
            ],
            "test_integration_function_dict_with_static_value": [
                {
                    "plugin_name": "test_integration_plugin",
                    "function": "test_integration_plugin_function",
                    "args": {"arg": "static_value"},
                }
            ],
        }
    }


@pytest.fixture(autouse=True)
def reset_event_handler():
    """Reset the event handler before each test."""
    event_handler = get_event_handler()
    event_handler.reset()
    yield
    event_handler.stop()


@patch("bot_squared.integrator._logger")
def test_integrable_dict_return(logger_mock, integrations):
    mock_plugin = MagicMock()
    event_handler = get_event_handler()

    with (
        patch("bot_squared.integrator.get_plugin", return_value=mock_plugin),
        patch.object(event_handler, "_integrations", integrations),
    ):
        logger_mock.debug = print
        logger_mock.error = print

        test_plugin = TestPlugin("test_plugin")
        test_plugin.test_integration_function_dict()

        # Wait for event processing with timeout
        event_handler._event_queue.join()
        time.sleep(0.1)  # Give time for the processing to complete

        mock_plugin.instance.add_to_queue.assert_called_once_with(
            "test_integration_plugin_function", {"arg1": "test1", "arg2": "test2"}
        )


@patch("bot_squared.integrator._logger")
def test_integrable_value_return(logger_mock, integrations):
    mock_plugin = MagicMock()
    event_handler = get_event_handler()

    with (
        patch("bot_squared.integrator.get_plugin", return_value=mock_plugin),
        patch.object(event_handler, "_integrations", integrations),
    ):
        logger_mock.debug = print
        logger_mock.error = print

        test_plugin = TestPlugin("test_plugin")
        test_plugin.test_integration_function_value()

        # Wait for event processing with timeout
        event_handler._event_queue.join()
        time.sleep(0.1)  # Give time for the processing to complete

        mock_plugin.instance.add_to_queue.assert_called_once_with(
            "test_integration_plugin_function", {"arg": "test_value"}
        )


@patch("bot_squared.integrator._logger")
def test_integrable_dict_return_static_value(logger_mock, integrations):
    mock_plugin = MagicMock()
    event_handler = get_event_handler()

    with (
        patch("bot_squared.integrator.get_plugin", return_value=mock_plugin),
        patch.object(event_handler, "_integrations", integrations),
    ):
        logger_mock.debug = print
        logger_mock.error = print

        test_plugin = TestPlugin("test_plugin")
        test_plugin.test_integration_function_dict_with_static_value()

        # Wait for event processing with timeout
        event_handler._event_queue.join()
        time.sleep(0.1)  # Give time for the processing to complete

        mock_plugin.instance.add_to_queue.assert_called_once_with(
            "test_integration_plugin_function", {"arg": "static_value"}
        )
