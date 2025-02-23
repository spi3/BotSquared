from bot_squared.plugins.teamspeak.teamspeak import Teamspeak


def create_plugin(config: dict, loaded_plugins: dict):
    return Teamspeak(config=config, loaded_plugins=loaded_plugins)
