"""
Steam Plugin Module for Bot Squared

This module provides functionality to monitor and query Steam game servers using the A2S protocol.
It implements a plugin that periodically checks the status of a specified Steam game server,
including player count and server availability.
"""

import logging
import time
from typing import Any, Dict

import a2s

from bot_squared.integrator import plugin_event
from bot_squared.plugins.plugin_base import PluginBase

# Default time in seconds between server status checks
DEFAULT_UPDATE_INTERVAL = 60


class Steam(PluginBase):
    """
    Steam plugin for monitoring Steam game servers.

    This plugin implements functionality to periodically query Steam game servers
    using the A2S protocol. It provides information about server status, current
    player count, and maximum player capacity.

    Attributes:
        plugin_name (str): Name identifier for the plugin instance
        config (dict): Configuration dictionary containing server settings
        update_interval (int): Time in seconds between status checks
        steam_server (str): IP address or hostname of the Steam game server
        steam_port (int): Port number of the Steam game server

    Required Config Keys:
        - steam_server: IP address or hostname of the Steam game server
        - steam_port: Port number of the Steam game server

    Optional Config Keys:
        - update_interval_seconds: Custom interval for status checks (default: 60)
    """

    def __init__(self, plugin_name: str, config: dict) -> None:
        """
        Initialize the Steam plugin.

        Args:
            plugin_name (str): Name identifier for the plugin instance
            config (dict): Configuration dictionary containing server settings

        Raises:
            ValueError: If required configuration keys are missing
        """
        super().__init__()
        self.plugin_name = plugin_name
        self.config = config

        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Initializing Steam plugin with config: {config}")

        # Validate required configuration parameters
        if "steam_server" not in self.config:
            msg = f'Plugin {plugin_name} self.config must have an "steam_server" key'
            self.logger.error(msg)
            raise ValueError(msg)
        if "steam_port" not in self.config:
            msg = f'Plugin {plugin_name} self.config must have a "steam_port" key'
            self.logger.error(msg)
            raise ValueError(msg)

        # Set update interval from config or use default
        self.update_interval = DEFAULT_UPDATE_INTERVAL
        if "update_interval_seconds" in self.config:
            self.update_interval = self.config["update_interval_seconds"]
            self.logger.debug(f"Using custom update interval: {self.update_interval} seconds")
        else:
            self.logger.debug(f"Using default update interval: {DEFAULT_UPDATE_INTERVAL} seconds")

        # Store server connection details
        self.steam_server = self.config["steam_server"]
        self.steam_port = self.config["steam_port"]
        self.logger.info(f"Steam plugin configured for server {self.steam_server}:{self.steam_port}")

    def _format_server_info(self, info: Any) -> Dict[str, Any]:
        """
        Format server information into a standardized dictionary.

        Args:
            info: Server information object from A2S query

        Returns:
            dict: Formatted server information
        """
        self.logger.debug(f"Raw server info: {info}")
        return {
            "status": "Online",
            "player_count": info.player_count,
            "max_players": info.max_players,
            "server_name": getattr(info, "server_name", None) or "Unknown",
            "map_name": getattr(info, "map_name", None) or "Unknown",
            "game": getattr(info, "game", None) or "Unknown",
        }

    @plugin_event
    def get_server_status(self) -> Dict[str, Any]:
        """
        Query the game server status using the A2S protocol.

        This method attempts to connect to the configured Steam game server
        and retrieve its current status information using the A2S protocol.

        Returns:
            dict: Server status information with the following keys:
                - status (str): 'Online' if server is reachable, 'Offline' otherwise
                - player_count (int): Number of players currently on the server
                - max_players (int): Maximum player capacity of the server
                - server_name (str): Name of the server if available
                - map_name (str): Current map name if available
                - game (str): Game name if available

        Note:
            If the server query fails, returns an offline status with zero players.
        """
        self.logger.debug(f"Attempting to query server status for {self.steam_server}:{self.steam_port}")
        try:
            # Query server using python-a2s library
            start_time = time.time()
            info = a2s.info((self.steam_server, self.steam_port))
            query_time = time.time() - start_time

            self.logger.debug(f"Server query successful. Response time: {query_time:.2f} seconds")

            status_info = self._format_server_info(info)
            self.logger.info(
                f"Server status - Online | Players: {status_info['player_count']}/{status_info['max_players']} | "
                f"Map: {status_info['map_name']} | Game: {status_info['game']}"
            )
            return status_info

        except a2s.BrokenMessageError as e:
            self.logger.error(f"Received malformed response from server: {e}")
            return {"status": "Offline", "player_count": 0, "max_players": 0}
        except a2s.BufferExhaustedError as e:
            self.logger.error(f"Incomplete response from server: {e}")
            return {"status": "Offline", "player_count": 0, "max_players": 0}
        except TimeoutError as e:
            self.logger.warning(f"Server query timed out: {e}")
            return {"status": "Offline", "player_count": 0, "max_players": 0}
        except Exception as e:
            self.logger.error(
                f"Unexpected error querying game server {self.steam_server}:{self.steam_port}: {e}", exc_info=True
            )
            return {"status": "Offline", "player_count": 0, "max_players": 0}

    def run(self):
        """
        Main plugin execution loop.

        This method runs continuously, periodically checking the server status
        and handling any pending integration functions. The check interval is
        determined by the update_interval configuration.
        """
        self.logger.info(f"{self.plugin_name} - Starting main loop")
        consecutive_failures = 0

        while True:
            loop_start_time = time.time()

            try:
                # Process any pending integration functions
                self.logger.debug("Processing integration function queue")
                self.handle_integration_function_queue()

                # Query and log server status
                status = self.get_server_status()
                if status["status"] == "Online":
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    self.logger.warning(f"Server appears offline. Consecutive failures: {consecutive_failures}")

                # Log long processing times
                processing_time = time.time() - loop_start_time
                if processing_time > (self.update_interval / 4):
                    self.logger.warning(f"Long processing time detected: {processing_time:.2f} seconds")

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                consecutive_failures += 1

            finally:
                time.sleep(self.update_interval)
