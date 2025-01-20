# from interfaces.chat_bot import ChatBot
import yaml
import logging
import time
from interfaces.chat_bot import ChatBot
import ts3

class Teamspeak(ChatBot):
    def __init__(self, config: dict = {}):
        self.logger = logging.getLogger(__name__)
        self.default_config = None
        self.config = config

        # Config fields
        self.iteration_rate_hz = None

        self.logger.info("Teamspeak initializing...")

        # Hack to ensure config is not None
        if self.config is None:
            self.config = {}
        self.load_config()

    def __connect(self):
        # Connect to the server
        self.ts3conn = ts3.query.TS3Connection(self.ts3_server_ip)
  
        # Authenticate with the server
        self.ts3conn.login(
            client_login_name=self.ts3_server_query_username,
            client_login_password=self.ts3_server_query_passwd
        )

        # Join the server
        self.ts3conn.use(sid=1)

        #get the channel list
        channels = self.ts3conn.channellist()
        
        #find the channel
        channel = next(channel for channel in channels if channel["channel_name"] == self.chat_channel_name)
        
        #get my data
        serverQueryName = self.ts3conn.whoami()[0]['client_nickname']
        serverQueryID = self.ts3conn.whoami()[0]['client_id']
        
        #move the user to the channel
        self.ts3conn.clientmove(cid=channel["cid"], clid=serverQueryID)

        self.logger.info(f"{self.name} - Connected to {self.chat_channel_name}@{self.ts3_server_ip}")

    def send_message(self, message):
        pass
    
    def get_messages(self):
        pass

    def run(self):
        # Connect to the server
        self.__connect()

        timeouts = 0
        while True:
            self.ts3conn.send_keepalive()

    def load_config(self):
        # Load the default config
        with open('plugins/teamspeak/teamspeak_default_config.yaml', 'r') as plugins_file:
            self.default_config = yaml.safe_load(plugins_file)

        if self.default_config is None:
            self.logger.error("No default config found")
            return
        
        if 'iteration_rate_hz' in self.config:
            self.iteration_rate_hz = self.config['iteration_rate_hz']
        else:
            self.iteration_rate_hz = self.default_config['iteration_rate_hz']

        if 'ts3_server_ip' in self.config:
            self.ts3_server_ip = self.config['ts3_server_ip']
        else:
            self.ts3_server_ip = self.default_config['ts3_server_ip']
        
        if 'ts3_server_query_username' in self.config:
            self.ts3_server_query_username = self.config['ts3_server_query_username']
        else:
            self.ts3_server_query_username = self.default_config['ts3_server_query_username']

        if 'ts3_server_query_passwd' in self.config:
            self.ts3_server_query_passwd = self.config['ts3_server_query_passwd']
        else:
            self.ts3_server_query_passwd = self.default_config['ts3_server_query_passwd']    

        if 'ts3_server_id' in self.config:
            self.ts3_server_id = self.config['ts3_server_id']
        else:
            self.ts3_server_id = self.default_config['ts3_server_id']

        if 'chat_channel_name' in self.config:
            self.chat_channel_name = self.config['chat_channel_name']
        else:
            self.chat_channel_name = self.default_config['chat_channel_name']