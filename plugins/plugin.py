import importlib
import threading

class Plugin:
    def __init__(self, pluginName: str, pluginConf: dict = {}):
        self.name = pluginName

        self.module = importlib.import_module(f"plugins.{pluginName}")
        self.instance = self.module.create_plugin(pluginConf)

        # Run the plugin in a thread
        print(f"Starting: {pluginName}")
        self.thread = threading.Thread(target=self.instance.run)
        self.thread.start()

