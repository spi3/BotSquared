from bot_squared.plugins.teamspeak.teamspeak import Teamspeak


def create_plugin(plugin_name: str, config: dict):
    return Teamspeak(plugin_name=plugin_name, config=config)
