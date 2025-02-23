import importlib
import logging
import threading


class Plugin:
    def __init__(self,
                 plugin_name: str,
                 plugin_type: str,
                 plugin_conf: dict,
                 loaded_plugins: dict):
        self.name = plugin_name
        self.plugin_type = plugin_type
        self.logger = logging.getLogger(__name__)
        self.module = importlib.import_module(f'plugins.{plugin_type}')
        self.instance = self.module.create_plugin(plugin_conf, loaded_plugins)

        # Run the plugin in a thread
        self.logger.info(f'Starting: {plugin_name}:{plugin_type}')
        self.thread = threading.Thread(target=self.instance.run)
        self.thread.start()

    def is_alive(self):
        return self.thread.is_alive()
