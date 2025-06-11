import importlib
import logging
import threading
from typing import Dict, Optional

from bot_squared import integrator


class Plugin:
    def __init__(self, plugin_name: str, plugin_type: str, plugin_conf: dict) -> None:
        self.name = plugin_name
        self.plugin_type = plugin_type
        self.conf = plugin_conf
        self.logger = logging.getLogger(__name__)

        # Load and initialize the plugin module
        self.module = importlib.import_module(f"plugins.{plugin_type}")
        self.instance = self.module.create_plugin(plugin_name, plugin_conf)

        # Register integrations if any
        if 'integrations' in plugin_conf:
            integrator.register_integrations(plugin_name, plugin_conf['integrations'])

        # Use Event for thread-safe state management
        self._running = threading.Event()
        self._running.set()

        # Run the plugin in a thread
        self.logger.info(f"Starting: {plugin_name}:{plugin_type}")
        self.thread = threading.Thread(target=self._run_wrapper, daemon=True)
        self.thread.start()

    def _run_wrapper(self):
        """Wrapper around the plugin's run method to ensure proper cleanup"""
        try:
            self.instance.run()
        except Exception as e:
            self.logger.error(f"Plugin {self.name} crashed: {e}")
        finally:
            self._running.clear()
            self.instance.stop()

    def is_alive(self) -> bool:
        """Thread-safe check if the plugin is alive and running"""
        return self.thread.is_alive() and self._running.is_set()

    def stop(self) -> None:
        """Gracefully stop the plugin"""
        if self._running.is_set():
            self._running.clear()
            self.instance.stop()
            self.thread.join(timeout=5.0)  # Wait up to 5 seconds for thread to finish
