import threading
import time
from unittest.mock import MagicMock, patch
import pytest
from queue import Empty
from bot_squared.events import EventHandler, PluginEvent
from bot_squared.integrator import get_event_handler


@pytest.fixture
def event_handler():
    handler = EventHandler()
    yield handler
    # Cleanup after test
    handler.stop()


def test_initialization(event_handler):
    """Test that EventHandler is properly initialized."""
    assert isinstance(event_handler.logger, object)
    assert isinstance(event_handler._integrations, dict)
    assert isinstance(event_handler._running, threading.Event)
    assert event_handler._running.is_set()
    assert event_handler._event_thread.is_alive()
    assert event_handler._event_thread.daemon


def test_register_integration(event_handler):
    """Test registering integrations."""
    # Test with empty integration
    event_handler.register_integration("test_plugin", {})
    assert "test_plugin" not in event_handler._integrations

    # Test with valid integration
    test_integration = {
        "test_function": [
            {
                "plugin_name": "target_plugin",
                "function": "target_function",
                "args": {"arg1": "value1"}
            }
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)
    assert event_handler._integrations["test_plugin"] == test_integration


def test_publish_event(event_handler):
    """Test publishing events to the queue."""
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value="test_value"
    )
    
    event_handler.publish_event(event)
    assert event_handler._event_queue.qsize() == 1
    queued_event = event_handler._event_queue.get()
    assert queued_event == event
    assert queued_event.plugin_name == "test_plugin"
    assert queued_event.function_name == "test_function"
    assert queued_event.return_value == "test_value"


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_dict_return(mock_get_plugin, event_handler):
    """Test processing events with dictionary return values."""
    mock_plugin = MagicMock()
    mock_get_plugin.return_value = mock_plugin

    # Set up test integration
    test_integration = {
        "test_function": [
            {
                "plugin_name": "target_plugin",
                "function": "target_function",
                "args": {
                    "arg1": "{value1}",
                    "arg2": "{value2}"
                }
            }
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value={"value1": "test1", "value2": "test2"}
    )
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify the plugin was called with formatted arguments
    mock_plugin.instance.add_to_queue.assert_called_once_with(
        "target_function",
        {"arg1": "test1", "arg2": "test2"}
    )


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_scalar_return(mock_get_plugin, event_handler):
    """Test processing events with scalar return values."""
    mock_plugin = MagicMock()
    mock_get_plugin.return_value = mock_plugin

    # Set up test integration
    test_integration = {
        "test_function": [
            {
                "plugin_name": "target_plugin",
                "function": "target_function",
                "args": {"arg": "{return_val}"}
            }
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value="test_value"
    )
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify the plugin was called with formatted arguments
    mock_plugin.instance.add_to_queue.assert_called_once_with(
        "target_function",
        {"arg": "test_value"}
    )


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_static_value(mock_get_plugin, event_handler):
    """Test processing events with static argument values."""
    mock_plugin = MagicMock()
    mock_get_plugin.return_value = mock_plugin

    # Set up test integration with static value
    test_integration = {
        "test_function": [
            {
                "plugin_name": "target_plugin",
                "function": "target_function",
                "args": {"arg": "static_value"}
            }
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value="test_value"  # This should not affect the static arg
    )
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify the plugin was called with static argument
    mock_plugin.instance.add_to_queue.assert_called_once_with(
        "target_function",
        {"arg": "static_value"}
    )


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_multiple_integrations(mock_get_plugin, event_handler):
    """Test processing events with multiple target integrations."""
    mock_plugin1 = MagicMock()
    mock_plugin2 = MagicMock()
    mock_get_plugin.side_effect = lambda x: mock_plugin1 if x == "target_plugin1" else mock_plugin2

    # Set up test integration with multiple targets
    test_integration = {
        "test_function": [
            {
                "plugin_name": "target_plugin1",
                "function": "target_function1",
                "args": {"arg1": "{return_val}"}
            },
            {
                "plugin_name": "target_plugin2",
                "function": "target_function2",
                "args": {"arg2": "{return_val}"}
            }
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value="test_value"
    )
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify both plugins were called with correct arguments
    mock_plugin1.instance.add_to_queue.assert_called_once_with(
        "target_function1",
        {"arg1": "test_value"}
    )
    mock_plugin2.instance.add_to_queue.assert_called_once_with(
        "target_function2",
        {"arg2": "test_value"}
    )


def test_error_handling(event_handler):
    """Test error handling in event processing."""
    # Test with non-existent plugin
    test_integration = {
        "test_function": [
            {
                "plugin_name": "non_existent_plugin",
                "function": "target_function",
                "args": {"arg": "value"}
            }
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value="test_value"
    )
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete
    # No assertion needed - just verify it doesn't raise an exception


def test_stop_handler(event_handler):
    """Test stopping the event handler."""
    assert event_handler._running.is_set()
    assert event_handler._event_thread.is_alive()

    event_handler.stop()
    assert not event_handler._running.is_set()
    assert not event_handler._event_thread.is_alive()


def test_reset(event_handler):
    """Test resetting the event handler."""
    # Add some test data
    test_integration = {
        "test_function": [
            {
                "plugin_name": "target_plugin",
                "function": "target_function",
                "args": {"arg": "value"}
            }
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value="test_value"
    )
    event_handler.publish_event(event)

    # Reset the handler
    event_handler.reset()

    # Verify everything is reset
    assert event_handler._event_queue.empty()
    assert not event_handler._integrations
    assert event_handler._running.is_set()
    assert event_handler._event_thread.is_alive() 