# from interfaces.chat_bot import ChatBot
import logging
import time
from pathlib import Path
from typing import Dict

import ts3
import ts3.definitions
import yaml

# from bot_squared.integrator import plugin_event
from bot_squared.integrator import plugin_event
from bot_squared.plugins.plugin_base import PluginBase

MAX_TIMEOUTS: int = 5
INACTIVITY_CHECK_INTERVAL: int = 60  # seconds


class Teamspeak(PluginBase):
    """Teamspeak plugin"""

    def __init__(self, plugin_name: str, config: dict):
        super().__init__()

        self.plugin_name = plugin_name
        self.config = config

        self.logger = logging.getLogger(__name__)
        self.default_config = None

        # Config fields
        self.iteration_rate_hz = None

        # Inactivity monitoring
        self.user_activity_timestamps: Dict[str, float] = {}  # Maps client IDs to last activity timestamp
        self.inactivity_timeout_minutes = 30
        self.afk_channel_id = 0
        self.enable_inactivity_monitoring = True

        self.logger.info("Teamspeak initializing...")

        self.load_config()

    def _connect(self):
        # Connect to the server
        self.ts3conn = ts3.query.TS3Connection(self.ts3_server_ip)

        # Authenticate with the server
        self.ts3conn.login(
            client_login_name=self.ts3_server_query_username, client_login_password=self.ts3_server_query_passwd
        )

        # Join the server
        self.ts3conn.use(sid=1)

        # get my data
        # serverQueryName = self.ts3conn.whoami()[0]['client_nickname']
        server_query_id = self.ts3conn.whoami()[0]["client_id"]

        # move the user to the channel
        self.ts3conn.clientmove(cid=self.bot_channel_id, clid=server_query_id)

        self.logger.info(f"{self.plugin_name} - Connected to {self.bot_channel_id}@{self.ts3_server_ip}")

    @plugin_event
    def send_message(self, message: str, to: int) -> None:
        """Send a message to a target on TeamSpeak.

        Args:
            message (str): The message to send
            to (int): The target ID to send the message to
        """
        try:
            self.ts3conn.sendtextmessage(
                targetmode=ts3.definitions.TextMessageTargetMode.CLIENT, target=to, msg=message
            )
            self.logger.info(f"Sent message to {to}: {message}")
        except ts3.query.TS3QueryError as e:
            self.logger.error(f"Failed to send message to {to}: {e}")

    def receive_message(self):
        pass

    def set_channel_name(self, channel_id: int, name: str) -> None:
        try:
            self.ts3conn.channeledit(cid=channel_id, channel_name=name)
            self.logger.info(f"Updated channel {channel_id} to '{name}'")
        except ts3.query.TS3QueryError as e:
            self.logger.error(f"Failed to update channel {channel_id}: {e}")
        except KeyError as e:
            self.logger.error(f"Invalid template variable in channel {channel_id}: {e}")

    def update_user_activity(self, client_id: str):
        """Update the last activity timestamp for a user.

        Args:
            client_id (str): The client ID of the user
        """
        self.user_activity_timestamps[client_id] = time.time()

    def check_inactive_users(self):
        """Check for inactive users and move them to the AFK channel if needed."""
        if not self.enable_inactivity_monitoring:
            return

        try:
            # Get current time
            current_time = time.time()

            # Get list of all clients
            clients = self.ts3conn.clientlist()

            for client in clients:
                client_id = client["clid"]

                # Skip server query clients and users already in AFK channel
                if (
                    client.get("client_type") == "1"  # Server query client
                    or int(client.get("cid", -1)) == self.afk_channel_id
                ):  # Already in AFK channel
                    continue

                # If user not in activity tracking, add them with current time
                if client_id not in self.user_activity_timestamps:
                    self.update_user_activity(client_id)
                    continue

                # Check if user has been inactive
                inactive_time = (current_time - self.user_activity_timestamps[client_id]) / 60  # Convert to minutes
                if inactive_time >= self.inactivity_timeout_minutes:
                    try:
                        # Move user to AFK channel
                        self.ts3conn.clientmove(cid=self.afk_channel_id, clid=client_id)
                        self.logger.info(
                            f"Moved inactive user {client.get('client_nickname', 'Unknown')} to AFK channel"
                        )

                        # Notify the user
                        self.send_message(
                            "You have been moved to the AFK channel due to "
                            f"{self.inactivity_timeout_minutes} minutes of inactivity.",
                            client_id,
                        )
                    except ts3.query.TS3QueryError as e:
                        self.logger.error(f"Failed to move inactive user {client_id}: {e}")

        except ts3.query.TS3QueryError as e:
            self.logger.error(f"Error checking for inactive users: {e}")

    def run(self):
        # Connect to the server
        try:
            self._connect()
        except Exception as e:
            self.logger.error(f"{self.plugin_name} - Failed to connect to server: {e}")
            return

        # Register for the event.
        self.ts3conn.servernotifyregister(event="server")
        self.ts3conn.servernotifyregister(event="channel", id_=self.bot_channel_id)

        # If all events are registered at the same time the client
        # gets flagged for flooding, therefore sleep between calls
        time.sleep(1)
        self.ts3conn.servernotifyregister(event="textchannel")
        self.ts3conn.servernotifyregister(event="textprivate")
        self.ts3conn.servernotifyregister(event="textserver")

        timeouts = 0
        last_inactivity_check = time.time()

        while True:
            self.ts3conn.send_keepalive()

            self.handle_integration_function_queue()

            # Check for inactive users every minute
            current_time = time.time()
            if current_time - last_inactivity_check >= INACTIVITY_CHECK_INTERVAL:
                self.check_inactive_users()
                last_inactivity_check = current_time

            try:
                # This method blocks, but we must sent the keepalive message at
                # least once in 5 minutes to avoid the sever side idle client
                # disconnect. So we set the timeout parameter simply to 1 minute.
                events = self.ts3conn.wait_for_event(timeout=1)

                self.logger.debug(f"{events}")
                for event in events:
                    self.logger.debug(f"{self.plugin_name} - Event: {event}")
                    self.process_event(event)

            except ts3.query.TS3TimeoutError:
                timeouts += 1
                if timeouts >= MAX_TIMEOUTS:
                    pass

    def process_event(self, event):
        # Update user activity on any event that indicates user interaction
        if "invokerid" in event:
            self.update_user_activity(event["invokerid"])

        # Handle channel change events to update activity
        if "cfid" in event and "clid" in event:
            self.update_user_activity(event["clid"])

        # Ignore events from the plugin
        if "invokername" in event and event["invokername"] == self.ts3_server_query_username:
            return

        if "msg" in event:
            self.process_msg_event(event)
        elif "cfid" in event:
            self.process_join_event(event)
        else:
            pass

    def process_join_event(self, event):
        """Process a user join event.

        This method:
        1. Sends a welcome message to new users (those with only the Guest group)
        2. Notifies the admin group about the new user

        Args:
            event (dict): The join event containing user information
        """
        joining_user_groups = None
        if "client_servergroups" in event:
            joining_user_groups = event["client_servergroups"]
            joining_user_groups = joining_user_groups.split(",")

        if joining_user_groups is not None and len(joining_user_groups) == 1:
            # Get the user's nickname
            user_nickname = event.get("client_nickname", "Unknown User")

            # If user only has one group upon joining, check if it's the guest group
            for group in self.ts3conn.servergrouplist():
                if group["sgid"] == joining_user_groups[0] and group["name"] == "Guest":
                    # Send welcome message to the new user
                    try:
                        self.ts3conn.sendtextmessage(
                            targetmode=ts3.definitions.TextMessageTargetMode.CLIENT,
                            target=event["clid"],
                            msg=self.new_user_message,
                        )
                        self.logger.info(f"Sent welcome message to new user: {user_nickname}")
                    except ts3.query.TS3QueryError as e:
                        self.logger.error(f"Failed to send welcome message to {user_nickname}: {e}")

                    # Find admin group and notify them about the new user
                    try:
                        for admin_group in self.ts3conn.servergrouplist():
                            if admin_group["name"] == self.new_user_inform_group:
                                # Get all clients in the admin group
                                admin_clients = self.ts3conn.servergroupclientlist(sgid=admin_group["sgid"])

                                # Send notification to each admin
                                for admin in admin_clients:
                                    try:
                                        self.ts3conn.sendtextmessage(
                                            targetmode=ts3.definitions.TextMessageTargetMode.CLIENT,
                                            target=admin["cldbid"],  # Use database ID for the admin
                                            msg=f"New user joined: {user_nickname}",
                                        )
                                    except ts3.query.TS3QueryError as e:
                                        self.logger.error(
                                            f"Failed to notify admin {admin['cldbid']} about new user: {e}"
                                        )

                                self.logger.info(f"Notified admins about new user: {user_nickname}")
                                break
                    except ts3.query.TS3QueryError as e:
                        self.logger.error(f"Failed to notify admins about new user {user_nickname}: {e}")

                    return

    def process_msg_event(self, event):
        msg = event["msg"]

        envoked_command = None
        for command in self.commands:
            if msg.startswith(self.command_prefix + command):
                envoked_command = self.commands[command]
                break
        if envoked_command is None:
            return  # No command envoked, nothing to do

        self.logger.info(f"Command envoked: {envoked_command}")

        if "targetmode" not in event:
            return

        if "response" in self.commands[command]:
            self.ts3conn.sendtextmessage(
                targetmode=event["targetmode"], target=self.channel_id, msg=self.commands[command]["response"]
            )
        else:
            # Command has no response
            # Do w/e else needs to be done
            pass

    def load_config(self):
        # Load the default config
        with open(Path(__file__).resolve().parent / "teamspeak_default_config.yaml") as default_config_file:
            self.default_config = yaml.safe_load(default_config_file)

        if self.default_config is None:
            self.logger.error("No default config found")
            return

        # Load existing config fields
        if "iteration_rate_hz" in self.config:
            self.iteration_rate_hz = self.config["iteration_rate_hz"]
        else:
            self.iteration_rate_hz = self.default_config["iteration_rate_hz"]

        if "ts3_server_ip" in self.config:
            self.ts3_server_ip = self.config["ts3_server_ip"]
        else:
            self.ts3_server_ip = self.default_config["ts3_server_ip"]

        if "ts3_server_query_username" in self.config:
            self.ts3_server_query_username = self.config["ts3_server_query_username"]
        else:
            self.ts3_server_query_username = self.default_config["ts3_server_query_username"]

        if "ts3_server_query_passwd" in self.config:
            self.ts3_server_query_passwd = self.config["ts3_server_query_passwd"]
        else:
            self.ts3_server_query_passwd = self.default_config["ts3_server_query_passwd"]

        if "ts3_server_id" in self.config:
            self.ts3_server_id = self.config["ts3_server_id"]
        else:
            self.ts3_server_id = self.default_config["ts3_server_id"]

        if "bot_channel_id" in self.config:
            self.bot_channel_id = self.config["bot_channel_id"]
        else:
            self.bot_channel_id = self.default_config["bot_channel_id"]

        # Load inactivity monitoring settings
        if "inactivity_timeout_minutes" in self.config:
            self.inactivity_timeout_minutes = self.config["inactivity_timeout_minutes"]
        else:
            self.inactivity_timeout_minutes = self.default_config.get("inactivity_timeout_minutes", 30)

        if "afk_channel_id" in self.config:
            self.afk_channel_id = self.config["afk_channel_id"]
        else:
            self.afk_channel_id = self.default_config.get("afk_channel_id", 0)

        if "enable_inactivity_monitoring" in self.config:
            self.enable_inactivity_monitoring = self.config["enable_inactivity_monitoring"]
        else:
            self.enable_inactivity_monitoring = self.default_config.get("enable_inactivity_monitoring", True)

        if "commands" in self.config:
            self.commands = self.config["commands"]
        else:
            self.commands = self.default_config["commands"]

        if "command_prefix" in self.config:
            self.command_prefix = self.config["command_prefix"]
        else:
            self.command_prefix = self.default_config["command_prefix"]

        # Load new user settings
        if "new_user_message" in self.config:
            self.new_user_message = self.config["new_user_message"]
        else:
            self.new_user_message = self.default_config.get("new_user_message", "Welcome!")

        if "new_user_inform_group" in self.config:
            self.new_user_inform_group = self.config["new_user_inform_group"]
        else:
            self.new_user_inform_group = self.default_config.get("new_user_inform_group", "Server Admin")
