import concurrent.futures
import queue
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from bot_squared.event_handler import EventHandler, PluginEvent

# Constants for test configuration
NUM_CONCURRENT_EVENTS = 10
NUM_BULK_EVENTS = 100
NUM_OVERFLOW_EVENTS = 1000
NUM_EXPECTED_EMPTY_EVENTS = 3


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
        "test_function": [{"plugin_name": "target_plugin", "function": "target_function", "args": {"arg1": "value1"}}]
    }
    event_handler.register_integration("test_plugin", test_integration)
    assert event_handler._integrations["test_plugin"] == test_integration


def test_publish_event(event_handler):
    """Test publishing events to the queue."""
    event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value="test_value")

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
                "args": {"arg1": "{value1}", "arg2": "{value2}"},
            }
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(
        plugin_name="test_plugin", function_name="test_function", return_value={"value1": "test1", "value2": "test2"}
    )
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify the plugin was called with formatted arguments
    mock_plugin.instance.add_to_queue.assert_called_once_with("target_function", {"arg1": "test1", "arg2": "test2"})


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_scalar_return(mock_get_plugin, event_handler):
    """Test processing events with scalar return values."""
    mock_plugin = MagicMock()
    mock_get_plugin.return_value = mock_plugin

    # Set up test integration
    test_integration = {
        "test_function": [
            {"plugin_name": "target_plugin", "function": "target_function", "args": {"arg": "{return_val}"}}
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value="test_value")
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify the plugin was called with formatted arguments
    mock_plugin.instance.add_to_queue.assert_called_once_with("target_function", {"arg": "test_value"})


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_static_value(mock_get_plugin, event_handler):
    """Test processing events with static argument values."""
    mock_plugin = MagicMock()
    mock_get_plugin.return_value = mock_plugin

    # Set up test integration with static value
    test_integration = {
        "test_function": [
            {"plugin_name": "target_plugin", "function": "target_function", "args": {"arg": "static_value"}}
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value="test_value",  # This should not affect the static arg
    )
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify the plugin was called with static argument
    mock_plugin.instance.add_to_queue.assert_called_once_with("target_function", {"arg": "static_value"})


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_multiple_integrations(mock_get_plugin, event_handler):
    """Test processing events with multiple target integrations."""
    mock_plugin1 = MagicMock()
    mock_plugin2 = MagicMock()
    mock_get_plugin.side_effect = lambda x: mock_plugin1 if x == "target_plugin1" else mock_plugin2

    # Set up test integration with multiple targets
    test_integration = {
        "test_function": [
            {"plugin_name": "target_plugin1", "function": "target_function1", "args": {"arg1": "{return_val}"}},
            {"plugin_name": "target_plugin2", "function": "target_function2", "args": {"arg2": "{return_val}"}},
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value="test_value")
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify both plugins were called with correct arguments
    mock_plugin1.instance.add_to_queue.assert_called_once_with("target_function1", {"arg1": "test_value"})
    mock_plugin2.instance.add_to_queue.assert_called_once_with("target_function2", {"arg2": "test_value"})


def test_error_handling(event_handler):
    """Test error handling in event processing."""
    # Test with non-existent plugin
    test_integration = {
        "test_function": [
            {"plugin_name": "non_existent_plugin", "function": "target_function", "args": {"arg": "value"}}
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value="test_value")
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
        "test_function": [{"plugin_name": "target_plugin", "function": "target_function", "args": {"arg": "value"}}]
    }
    event_handler.register_integration("test_plugin", test_integration)
    event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value="test_value")
    event_handler.publish_event(event)

    # Reset the handler
    event_handler.reset()

    # Verify everything is reset
    assert event_handler._event_queue.empty()
    assert not event_handler._integrations
    assert event_handler._running.is_set()
    assert event_handler._event_thread.is_alive()


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_none_return(mock_get_plugin, event_handler):
    """Test processing events with None return value."""
    mock_plugin = MagicMock()
    mock_get_plugin.return_value = mock_plugin

    # Set up test integration
    test_integration = {
        "test_function": [
            {"plugin_name": "target_plugin", "function": "target_function", "args": {"arg": "{return_val}"}}
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event with None return value
    event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value=None)
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # Verify the plugin was called with "None" as string
    mock_plugin.instance.add_to_queue.assert_called_once_with("target_function", {"arg": "None"})


@patch("bot_squared.integrator.get_plugin")
def test_process_events_with_malformed_format(mock_get_plugin, event_handler):
    """Test processing events with malformed format strings in args."""
    mock_plugin = MagicMock()
    mock_get_plugin.return_value = mock_plugin

    # Set up test integration with malformed format string
    test_integration = {
        "test_function": [
            {"plugin_name": "target_plugin", "function": "target_function", "args": {"arg": "{invalid_key}"}}
        ]
    }
    event_handler.register_integration("test_plugin", test_integration)

    # Create and publish test event
    event = PluginEvent(
        plugin_name="test_plugin",
        function_name="test_function",
        return_value={"valid_key": "test_value"},  # Doesn't contain invalid_key
    )
    event_handler.publish_event(event)

    # Wait for event processing with timeout
    event_handler._event_queue.join()
    time.sleep(0.1)  # Give time for the processing to complete

    # The event should be processed without error, even though format string is invalid
    # Logger should have recorded an error
    assert event_handler._event_queue.empty()


def test_queue_overflow(event_handler):
    """Test behavior when event queue receives many events rapidly."""
    # Create a large number of events
    events = [
        PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value=f"value_{i}")
        for i in range(1000)
    ]

    # Publish events in parallel to simulate overflow scenario
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(event_handler.publish_event, event) for event in events]
        concurrent.futures.wait(futures)

    # Verify all events are eventually processed
    event_handler._event_queue.join()
    assert event_handler._event_queue.empty()


def test_concurrent_publishing(event_handler):
    """Test concurrent event publishing from multiple threads."""
    mock_plugin = MagicMock()
    with patch("bot_squared.integrator.get_plugin", return_value=mock_plugin):
        # Set up test integration
        test_integration = {
            "test_function": [
                {"plugin_name": "target_plugin", "function": "target_function", "args": {"arg": "{return_val}"}}
            ]
        }
        event_handler.register_integration("test_plugin", test_integration)

        # Create events
        events = [
            PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value=f"value_{i}")
            for i in range(NUM_CONCURRENT_EVENTS)
        ]

        # Publish events concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(event_handler.publish_event, event) for event in events]
            concurrent.futures.wait(futures)

        # Wait for processing to complete
        event_handler._event_queue.join()
        time.sleep(0.1)

        # Verify all events were processed
        assert mock_plugin.instance.add_to_queue.call_count == NUM_CONCURRENT_EVENTS


def test_concurrent_registration(event_handler):
    """Test concurrent registration of integrations from multiple threads."""

    def register_integration(plugin_name):
        integration = {
            "test_function": [
                {"plugin_name": f"target_plugin_{plugin_name}", "function": "target_function", "args": {"arg": "value"}}
            ]
        }
        event_handler.register_integration(plugin_name, integration)

    # Register integrations concurrently
    plugin_names = [f"plugin_{i}" for i in range(NUM_CONCURRENT_EVENTS)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(register_integration, name) for name in plugin_names]
        concurrent.futures.wait(futures)

    # Verify all integrations were registered
    assert len(event_handler._integrations) == NUM_CONCURRENT_EVENTS
    for plugin_name in plugin_names:
        assert plugin_name in event_handler._integrations


def test_stop_during_processing(event_handler):
    """Test stopping the handler while events are being processed."""
    # Create a large number of events
    events = [
        PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value=f"value_{i}")
        for i in range(NUM_BULK_EVENTS)
    ]

    # Start publishing events
    for event in events[:50]:  # Publish half the events
        event_handler.publish_event(event)

    # Stop the handler while events are in queue
    event_handler.stop()

    # Verify handler is stopped
    assert not event_handler._running.is_set()
    assert not event_handler._event_thread.is_alive()

    # Try to publish more events after stopping
    with pytest.raises(queue.Empty):  # Queue should be empty after stopping
        for event in events[50:]:
            event_handler.publish_event(event)


def test_missing_integration_fields(event_handler):
    """Test handling of incomplete integration configurations."""
    # Test missing plugin_name
    incomplete_integration = {
        "test_function": [
            {"function": "target_function", "args": {"arg": "value"}}  # Missing plugin_name
        ]
    }
    event_handler.register_integration("test_plugin", incomplete_integration)

    # Test missing function
    incomplete_integration = {
        "test_function": [
            {"plugin_name": "target_plugin", "args": {"arg": "value"}}  # Missing function
        ]
    }
    event_handler.register_integration("test_plugin2", incomplete_integration)

    # Create and publish test event
    event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value="test_value")
    event_handler.publish_event(event)

    # Wait for processing and verify no errors
    event_handler._event_queue.join()
    assert event_handler._event_queue.empty()


def test_invalid_integration_structure(event_handler):
    """Test handling of malformed integration configurations."""
    # Test with non-dict integration
    event_handler.register_integration("test_plugin", ["invalid"])

    # Test with invalid inner structure
    invalid_integration = {
        "test_function": "not_a_list"  # Should be a list
    }
    event_handler.register_integration("test_plugin2", invalid_integration)

    # Test with completely invalid type
    event_handler.register_integration("test_plugin3", None)

    # Verify handler remains functional
    assert isinstance(event_handler._integrations, dict)


def test_cleanup_scenarios(event_handler):
    """Test various cleanup scenarios."""
    # Test double stop
    event_handler.stop()
    event_handler.stop()  # Should not raise error
    assert not event_handler._running.is_set()

    # Test reset after stop
    event_handler.reset()
    assert event_handler._running.is_set()
    assert event_handler._event_thread.is_alive()
    assert isinstance(event_handler._event_queue, queue.Queue)
    assert len(event_handler._integrations) == 0

    # Test stop after reset
    event_handler.stop()
    assert not event_handler._running.is_set()
    assert not event_handler._event_thread.is_alive()


def test_empty_event_values(event_handler):
    """Test handling of empty and None values in events."""
    mock_plugin = MagicMock()
    with patch("bot_squared.integrator.get_plugin", return_value=mock_plugin):
        test_integration = {
            "test_function": [
                {"plugin_name": "target_plugin", "function": "target_function", "args": {"arg": "{return_val}"}}
            ]
        }
        event_handler.register_integration("test_plugin", test_integration)

        # Test with empty dict
        event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value={})
        event_handler.publish_event(event)

        # Test with empty list
        event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value=[])
        event_handler.publish_event(event)

        # Test with empty string
        event = PluginEvent(plugin_name="test_plugin", function_name="test_function", return_value="")
        event_handler.publish_event(event)

        # Wait for processing
        event_handler._event_queue.join()
        time.sleep(0.1)

        # Verify all events were processed
        assert mock_plugin.instance.add_to_queue.call_count == NUM_EXPECTED_EMPTY_EVENTS
