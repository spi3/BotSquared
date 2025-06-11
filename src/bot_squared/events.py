from dataclasses import dataclass
from queue import Queue, Empty
import logging
import threading
import time
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PluginEvent:
    """Immutable event data structure for plugin events."""
    plugin_name: str
    function_name: str
    return_value: Any


class EventHandler:
    """Event handler that processes plugin events and manages integrations."""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._integrations: Dict[str, Dict[str, list]] = {}
        self._running = threading.Event()
        self._running.set()
        self._event_queue: Queue[PluginEvent] = Queue()
        
        # Start event processing thread
        self._event_thread = threading.Thread(target=self._process_events, daemon=True)
        self._event_thread.start()

    def register_integration(self, plugin_name: str, integration: dict) -> None:
        """Register integrations for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            integration: Integration configuration from the plugin's config
        """
        if not integration:
            return

        if plugin_name not in self._integrations:
            self._integrations[plugin_name] = {}

        self._integrations[plugin_name] = integration
        self.logger.debug(f"Registered integrations for {plugin_name}: {integration}")

    def publish_event(self, event: PluginEvent) -> None:
        """Publish an event to the event queue.
        
        Args:
            event: The PluginEvent to publish
        """
        self._event_queue.put(event)

    def _process_events(self) -> None:
        """Process events from the queue and invoke corresponding integrations."""
        while self._running.is_set():
            try:
                # Get next event with timeout to allow for clean shutdown
                try:
                    event = self._event_queue.get(timeout=1.0)
                except Empty:
                    continue

                try:
                    # Get integrations for the source plugin
                    plugin_integrations = self._integrations.get(event.plugin_name, {})
                    if not plugin_integrations:
                        continue

                    # Get integrations for this specific function
                    function_integrations = plugin_integrations.get(event.function_name, [])
                    if not function_integrations:
                        continue

                    # Process each integration
                    for integration in function_integrations:
                        try:
                            # Get the target plugin
                            from bot_squared.integrator import get_plugin
                            target_plugin = integration.get("plugin_name")
                            if not target_plugin:
                                continue
                                
                            plugin = get_plugin(target_plugin)
                            if not plugin:
                                self.logger.error(f"Target plugin not found: {target_plugin}")
                                continue

                            # Get the target function
                            target_function = integration.get("function")
                            if not target_function:
                                continue

                            # Prepare arguments
                            args = {}
                            if "args" in integration:
                                for arg_name, arg_template in integration["args"].items():
                                    if isinstance(arg_template, str):
                                        # Format the argument using the event's return value
                                        args[arg_name] = arg_template.format(
                                            **event.return_value if isinstance(event.return_value, dict)
                                            else {"return_val": event.return_value}
                                        )
                                    else:
                                        args[arg_name] = arg_template

                            # Queue the function call in the target plugin
                            plugin.instance.add_to_queue(target_function, args)
                            self.logger.debug(
                                f"Event from {event.plugin_name}.{event.function_name} "
                                f"processed for {target_plugin}.{target_function}"
                            )

                        except Exception as e:
                            self.logger.error(
                                f"Error processing event from {event.plugin_name}.{event.function_name} "
                                f"for integration {integration}: {e}"
                            )
                finally:
                    # Mark task as done regardless of success or failure
                    self._event_queue.task_done()

            except Exception as e:
                if self._running.is_set():
                    self.logger.error(f"Error in event processing: {e}")

    def stop(self) -> None:
        """Stop the event handler gracefully."""
        self._running.clear()
        if self._event_thread.is_alive():
            self._event_thread.join(timeout=5.0)

    def reset(self) -> None:
        """Reset the event handler for testing purposes."""
        self.stop()
        self._event_queue = Queue()
        self._integrations = {}
        self._running.set()
        self._event_thread = threading.Thread(target=self._process_events, daemon=True)
        self._event_thread.start() 