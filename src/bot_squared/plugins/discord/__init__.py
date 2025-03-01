from bot_squared.plugins.discord.discord import Discord


def create_plugin(plugin_name: str, config: dict):
    return Discord(plugin_name=plugin_name, config=config)
