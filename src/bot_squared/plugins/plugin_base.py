import logging
import threading
from queue import Queue
from typing import Dict, NamedTuple


class FunctionCall(NamedTuple):
    """Immutable function call data structure"""

    function_name: str
    args: Dict


class PluginBase:
    def __init__(self):
        self.function_queue: Queue[FunctionCall] = Queue()
        # Use Event for thread-safe state management
        self._running = threading.Event()
        self._running.set()
        # Initialize logger
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_to_queue(self, function_name: str, args: dict) -> None:
        """Add a function call to the queue using immutable message."""
        self.function_queue.put(FunctionCall(function_name, args))

    def handle_integration_function_queue(self) -> None:
        """Process function calls from the queue."""
        while not self.function_queue.empty():
            try:
                call = self.function_queue.get_nowait()

                if not hasattr(self, call.function_name):
                    self.logger.error(f"Error: {call.function_name} not found")
                    continue

                # Get and execute the requested function
                requested_function = getattr(self, call.function_name)
                requested_function(**call.args)

            except Exception as e:
                self.logger.error(f"Error processing function call: {e}")

    def stop(self) -> None:
        """Gracefully stop the plugin."""
        self._running.clear()

    def is_running(self) -> bool:
        """Check if the plugin is still running."""
        return self._running.is_set()
