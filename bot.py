import yaml
from plugins.plugin import Plugin
import logging
import sys

def main():
    # Configure logging
    logging.basicConfig(filename='bot.log', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # Load the plugins
    plugins = None

    # Load the plugins file
    with open('plugins.yaml', 'r') as plugins_file:
        plugins = yaml.safe_load(plugins_file)

    if plugins is None:
        print("No plugins found")
        return
    
    print(plugins)

    loaded_plugins = {}

    # Load the plugins
    for plugin in plugins:
        print(f"Loading: {plugin}")

        # Load the plugin
        loaded_plugins[plugin] = Plugin(pluginName=plugin,pluginConf=plugins[plugin])

    

if __name__ == "__main__":
    main()
