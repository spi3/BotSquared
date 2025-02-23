from bot_squared.plugins.discord.discord import Discord


def create_plugin(config: dict, loaded_plugins: dict):
    return Discord(config=config, loaded_plugins=loaded_plugins)
