# from interfaces.chat_bot import ChatBot
import logging
import time

import ts3
import ts3.definitions
import yaml
from bot_squared.integrator import integrates

MAX_TIMEOUTS: int = 5


class Teamspeak:
    """Teamspeak plugin"""

    def __init__(self, plugin_name: str, config: dict):
        self.plugin_name = plugin_name
        self.config = config

        self.logger = logging.getLogger(__name__)
        self.default_config = None

        # Config fields
        self.iteration_rate_hz = None

        self.logger.info('Teamspeak initializing...')

        self.load_config()

    def __connect(self):
        # Connect to the server
        self.ts3conn = ts3.query.TS3Connection(self.ts3_server_ip)

        # Authenticate with the server
        self.ts3conn.login(
            client_login_name=self.ts3_server_query_username, client_login_password=self.ts3_server_query_passwd
        )

        # Join the server
        self.ts3conn.use(sid=1)

        # get the channel list
        channels = self.ts3conn.channellist()

        # find the channel
        channel = next(channel for channel in channels if channel['channel_name'] == self.chat_channel_name)
        self.channel_id = channel['cid']

        # get my data
        # serverQueryName = self.ts3conn.whoami()[0]['client_nickname']
        server_query_id = self.ts3conn.whoami()[0]['client_id']

        # move the user to the channel
        self.ts3conn.clientmove(cid=self.channel_id, clid=server_query_id)

        self.logger.info(f'{self.name} - Connected to {self.chat_channel_name}@{self.ts3_server_ip}')

    def send_message(self, message, to):
        pass

    def get_messages(self):
        pass

    def run(self):
        # Connect to the server
        try:
            self.__connect()
        except Exception as e:
            self.logger.error(f'{self.name} - Failed to connect to server: {e}')
            return

        # Register for the event.
        self.ts3conn.servernotifyregister(event='server')
        self.ts3conn.servernotifyregister(event='channel', id_=self.channel_id)

        # If all events are registered at the same time the client
        # gets flagged for flooding, therefore sleep between calls
        time.sleep(1)
        self.ts3conn.servernotifyregister(event='textchannel')
        self.ts3conn.servernotifyregister(event='textprivate')
        self.ts3conn.servernotifyregister(event='textserver')

        timeouts = 0
        while True:
            self.ts3conn.send_keepalive()

            try:
                # This method blocks, but we must sent the keepalive message at
                # least once in 5 minutes to avoid the sever side idle client
                # disconnect. So we set the timeout parameter simply to 1 minute.
                events = self.ts3conn.wait_for_event(timeout=1)

                self.logger.debug(f'{events}')
                for event in events:
                    self.logger.debug(f'{self.name} - Event: {event}')
                    self.process_event(event)

            except ts3.query.TS3TimeoutError:
                timeouts += 1
                if timeouts >= MAX_TIMEOUTS:
                    pass

    def process_event(self, event):
        # Ignore events from the plugin
        if 'invokername' in event and event['invokername'] == self.ts3_server_query_username:
            return

        if 'msg' in event:
            self.process_msg_event(event)
        elif 'cfid' in event:
            self.process_join_event(event)
        else:
            pass

    def process_join_event(self, event):
        joining_user_groups = None
        if 'client_servergroups' in event:
            joining_user_groups = event['client_servergroups']
            joining_user_groups = joining_user_groups.split(',')

        if len(joining_user_groups) == 1:
            # If user only has one group upon joining, and that
            # group is the guest group, then send them a welcome message
            for group in self.ts3conn.servergrouplist():
                if group['sgid'] == joining_user_groups[0] and group['name'] == 'Guest':
                    self.ts3conn.sendtextmessage(
                        targetmode=ts3.definitions.TextMessageTargetMode.CLIENT,
                        target=event['clid'],
                        msg=f'{self.config.new_user_message}',
                    )
                    return

    def process_msg_event(self, event):
        msg = event['msg']

        envoked_command = None
        for command in self.commands:
            if msg.startswith(self.command_prefix + command):
                envoked_command = self.commands[command]
                break
        if envoked_command is None:
            return  # No command envoked, nothing to do

        self.logger.info(f'Command envoked: {envoked_command}')

        if 'targetmode' not in event:
            return

        if 'response' in self.commands[command]:
            self.ts3conn.sendtextmessage(
                targetmode=event['targetmode'], target=self.channel_id, msg=self.commands[command]['response']
            )
        else:
            # Command has no response
            # Do w/e else needs to be done
            pass

    def load_config(self):
        # Load the default config
        with open('teamspeak_default_config.yaml') as default_config_file:
            self.default_config = yaml.safe_load(default_config_file)

        if self.default_config is None:
            self.logger.error('No default config found')
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

        if 'name' in self.config:
            self.name = self.config['name']
        else:
            self.name = self.default_config['name']

        if 'commands' in self.config:
            self.commands = self.config['commands']
        else:
            self.commands = self.default_config['commands']

        if 'command_prefix' in self.config:
            self.command_prefix = self.config['command_prefix']
        else:
            self.command_prefix = self.default_config['command_prefix']
