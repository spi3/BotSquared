import logging
import time

import a2s

from bot_squared.integrator import integrates
from bot_squared.plugins.plugin_base import PluginBase

DEFAULT_UPDATE_INTERVAL = 60


class Steam(PluginBase):
    def __init__(self, plugin_name: str, config: dict) -> None:
        super().__init__()
        self.plugin_name = plugin_name
        self.config = config

        self.logger = logging.getLogger(__name__)

        if 'steam_server' not in self.config:
            msg = f'Plugin {plugin_name} self.config must have an "steam_server" key'
            raise ValueError(msg)
        if 'steam_port' not in self.config:
            msg = f'Plugin {plugin_name} self.config must have a "steam_port" key'
            raise ValueError(msg)

        self.update_interval = DEFAULT_UPDATE_INTERVAL
        if 'update_interval_seconds' in self.config:
            self.update_interval = self.config['update_interval_seconds']

        self.steam_server = self.config['steam_server']
        self.steam_port = self.config['steam_port']

    @integrates
    def get_server_status(self) -> dict:
        """
        Query the game server status using the A2S protocol with python-a2s.

        Returns:
            dict: Server status with 'status', 'player_count', and 'max_players' keys.
        """
        try:
            info = a2s.info((self.steam_server, self.steam_port))  # Query server using python-a2s
            return {
                'status': 'Online',
                'player_count': info.player_count,  # Access attributes directly
                'max_players': info.max_players,
            }
        except Exception as e:
            self.logger.warning(f'Failed to query game server {self.steam_server}:{self.steam_port}: {e}')
            return {'status': 'Offline', 'player_count': 0, 'max_players': 0}

    def run(self):
        self.logger.info(f'{self.plugin_name} - Running')
        while True:
            self.handle_integration_function_queue()

            self.logger.info(f'{self.plugin_name} - {self.get_server_status()}')
            time.sleep(self.update_interval)
