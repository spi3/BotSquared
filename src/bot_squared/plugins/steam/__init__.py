from bot_squared.plugins.steam.steam import Steam


def create_plugin(plugin_name: str, config: dict):
    return Steam(plugin_name=plugin_name, config=config)
