import logging
from typing import Optional
from enum import Enum

from bot_squared.interfaces.plugin_interface import PluginInterface

class ChatPluginIntegrationFunctions(Enum):
[
    'receive_message': 'receive_message',
]

class ChatPlugin(PluginInterface):
    def __init__(self, config: dict, loaded_plugins: dict, logger: Optional[logging.Logger]) -> None:
        self.loaded_plugins = loaded_plugins if loaded_plugins is not None else {}
        self.config = config if config is not None else {}
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def has_integrations(self) -> bool:
        return ('integrations' in self.config and
                'receive_message' in self.config['integrations'])

    def run_integration(self, msg: str, calling_function: str) -> None:
        has_integrations = self.has_integrations()

        if not has_integrations:
            return

        if calling_function not in self.config['integrations']:
            return

        integration = self.config['integrations'][calling_function]

        for plugin in integration:
            if plugin not in self.loaded_plugins:
                self.logger.error(f'Integration invalid - Plugin {plugin} not loaded')
                continue

            try:
                function = getattr(self.loaded_plugins[plugin].instance, integration[plugin].function)
                function(msg)

            except Exception as e:
                self.logger.error(
                    f'Error in integration {plugin} calling function: {integration[plugin]["function"]} - {e}')

    def receive_message(self, msg: str):
        self.run_integration('receive_message', msg)
