import logging

import discord
import yaml

from bot_squared.plugins.plugin_base import PluginBase


class Discord(PluginBase):
    def __init__(self, plugin_name: str, config: dict):
        super().__init__()
        self.plugin_name = plugin_name
        self.config = config

        self.logger = logging.getLogger(__name__)

        self.ready = False
        self.client = None

        # Config fields
        self.iteration_rate_hz = None

        self.logger.info('Discord initializing...')

        # Hack to ensure config is not None
        if self.config is None:
            self.config = {}
        self.__load_config()

        self.__connect()

    def __connect(self):
        intents = discord.Intents.default()
        intents.messages = True

        client = discord.Client(intents=intents)
        self.client = client

        @client.event
        async def on_ready():
            self.logger.info(f'Logged in as {self.client.user}')
            self.ready = True

        @client.event
        async def on_message(message):
            if message.author == self.client.user:
                return

    def send_message(self, message, to):
        if self.ready:
            channel = self.client.get_channel(to)
            channel.send(message)
            return True
        else:
            return False

    def __load_config(self):
        with open('plugins/discord/default_config.yaml') as default_config_file:
            self.default_config = yaml.safe_load(default_config_file)

        if self.default_config is None:
            self.logger.error('No default config found')
            return

        if 'iteration_rate_hz' in self.config:
            self.iteration_rate_hz = self.config['iteration_rate_hz']
        else:
            self.iteration_rate_hz = self.default_config['iteration_rate_hz']

        if 'token' in self.config:
            self.token = self.config['token']
        else:
            self.token = self.default_config['token']

        if 'channel_id' in self.config:
            self.channel_id = self.config['channel_id']
        else:
            self.channel_id = self.default_config['channel_id']
