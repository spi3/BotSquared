import logging
from functools import wraps
from typing import Dict, Optional

from bot_squared.events import EventHandler, PluginEvent
from bot_squared.plugins.plugin import Plugin

_loaded_plugins: Dict[str, Plugin] = {}
_logger = logging.getLogger(__name__)
_event_handler = EventHandler()


def add_loaded_plugins(plugin_name: str, plugin: Plugin) -> None:
    """Add a plugin to the loaded plugins registry."""
    _loaded_plugins[plugin_name] = plugin


def get_plugin(plugin_name: str) -> Optional[Plugin]:
    """Get a plugin by name from the loaded plugins registry."""
    return _loaded_plugins.get(plugin_name)


def register_integrations(plugin_name: str, integrations: dict) -> None:
    """Register integrations for a plugin with the event handler."""
    _event_handler.register_integration(plugin_name, integrations)


def plugin_event(func):
    """Decorator that makes a plugin method publish events.

    This decorator enables event-driven integration between plugins. When a decorated
    method is called, it will:
    1. Execute the original method
    2. Create a PluginEvent with the result
    3. Publish the event to the event handler

    The integration configuration should be defined in the plugin's config under the
    'integrations' key. Each integration should specify:
    - plugin_name: The target plugin to integrate with
    - function: The function to call in the target plugin
    - args: Arguments to pass to the target function
        - Use {return_val} to reference a simple return value
        - Use {key_name} to reference keys from a dictionary return value

    Example config:
        integrations:
            send_message: [
                {
                    "plugin_name": "discord",
                    "function": "relay_message",
                    "args": {
                        "content": "{message}",
                        "channel": "general"
                    }
                }
            ]
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Call the original function
        result = func(self, *args, **kwargs)

        # Create and publish the event
        event = PluginEvent(plugin_name=self.plugin_name, function_name=func.__name__, return_value=result)
        _event_handler.publish_event(event)

        return result

    return wrapper


def stop_event_handler() -> None:
    """Stop the event handler gracefully."""
    _event_handler.stop()


def get_event_handler() -> EventHandler:
    """Get the event handler instance."""
    return _event_handler
