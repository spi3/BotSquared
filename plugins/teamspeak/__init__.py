from plugins.teamspeak.teamspeak import Teamspeak 

def create_plugin(config: dict = {}):
    return Teamspeak(config=config)