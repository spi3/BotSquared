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
        self.logger.debug(f"Initializing TeamSpeak plugin with config: {config}")
        self.default_config = None

        # Config fields
        self.iteration_rate_hz = None

        # Connection retry settings
        self.initial_retry_delay = 5  # seconds
        self.max_retry_delay = 60  # seconds
        self.retry_backoff_factor = 2

        # Inactivity monitoring
        self.user_activity_timestamps: Dict[str, float] = {}  # Maps client IDs to last activity timestamp
        self.inactivity_timeout_minutes = 30
        self.afk_channel_id = 0
        self.enable_inactivity_monitoring = True

        self.logger.info("Teamspeak initializing...")

        self._load_config()
        self.logger.debug(
            f"TeamSpeak plugin initialized with: iteration_rate={self.iteration_rate_hz}, "
            f"server={self.ts3_server_ip}, username={self.ts3_server_query_username}, "
            f"server_id={self.ts3_server_id}, bot_channel={self.bot_channel_id}, "
            f"inactivity_timeout={self.inactivity_timeout_minutes}, afk_channel={self.afk_channel_id}"
        )

    def _connect(self):
        """
        Attempts to connect to the TeamSpeak server with retry mechanism.
        Uses exponential backoff for retries with a maximum delay cap.
        Will retry indefinitely until a successful connection is established.

        Returns:
            bool: True if connection successful (will only return on success)
        """
        attempt = 0
        current_delay = self.initial_retry_delay

        while True:  # Infinite retry loop
            try:
                attempt += 1
                self.logger.debug(f"Connection attempt {attempt} to TeamSpeak server at {self.ts3_server_ip}")

                # Connect to the server
                self.ts3conn = ts3.query.TS3Connection(self.ts3_server_ip)

                # Authenticate with the server
                self.logger.debug(f"Authenticating with username: {self.ts3_server_query_username}")
                self.ts3conn.login(
                    client_login_name=self.ts3_server_query_username, client_login_password=self.ts3_server_query_passwd
                )

                # Join the server
                self.logger.debug("Selecting server with SID: 1")
                self.ts3conn.use(sid=1)

                # get my data
                whoami_data = self.ts3conn.whoami()[0]
                self.logger.debug(f"Bot identity data: {whoami_data}")
                server_query_id = whoami_data["client_id"]

                # move the user to the channel
                self.logger.debug(f"Moving bot (ID: {server_query_id}) to channel: {self.bot_channel_id}")
                self.ts3conn.clientmove(cid=self.bot_channel_id, clid=server_query_id)

                self.logger.info(f"{self.plugin_name} - Connected to {self.bot_channel_id}@{self.ts3_server_ip}")
                return True

            except (ts3.query.TS3QueryError, Exception) as e:
                self.logger.warning(
                    f"Connection attempt {attempt} failed: {e!s}. Retrying in {current_delay} seconds..."
                )
                time.sleep(current_delay)
                # Calculate next delay with exponential backoff, capped at max_retry_delay
                current_delay = min(current_delay * self.retry_backoff_factor, self.max_retry_delay)

    @plugin_event
    def send_message(self, message: str, to: int) -> None:
        """Send a message to a target on TeamSpeak.

        Args:
            message (str): The message to send
            to (int): The target ID to send the message to
        """
        self.logger.debug(f"Attempting to send message to client {to}: {message}")
        try:
            self.ts3conn.sendtextmessage(
                targetmode=ts3.definitions.TextMessageTargetMode.CLIENT, target=to, msg=message
            )
            self.logger.info(f"Sent message to {to}: {message}")
        except ts3.query.TS3QueryError as e:
            self.logger.error(f"Failed to send message to {to}: {e}")
            self.logger.debug(f"Full error details for failed message: {e!s}")

    @plugin_event
    def receive_message(self):
        pass

    @plugin_event
    def set_channel_name(self, channel_id: int, name: str) -> None:
        self.logger.debug(f"Attempting to update channel {channel_id} name to: {name}")
        try:
            self.ts3conn.channeledit(cid=channel_id, channel_name=name)
            self.logger.info(f"Updated channel {channel_id} to '{name}'")
        except ts3.query.TS3QueryError as e:
            self.logger.error(f"Failed to update channel {channel_id}: {e}")
            self.logger.debug(f"Full error details for channel update: {e!s}")
        except KeyError as e:
            self.logger.error(f"Invalid template variable in channel {channel_id}: {e}")
            self.logger.debug(f"Template error details: {e!s}")

    def _update_user_activity(self, client_id: str):
        """Update the last activity timestamp for a user.

        Args:
            client_id (str): The client ID of the user
        """
        current_time = time.time()
        previous_time = self.user_activity_timestamps.get(client_id)
        self.user_activity_timestamps[client_id] = current_time
        self.logger.debug(f"Updated activity for client {client_id}: previous={previous_time}, new={current_time}")

    def _check_inactive_users(self):
        """Check for inactive users and move them to the AFK channel if needed."""
        if not self.enable_inactivity_monitoring:
            self.logger.debug("Inactivity monitoring is disabled, skipping check")
            return

        try:
            current_time = time.time()
            self.logger.debug("Starting inactive user check")

            # Get list of all clients
            clients = self.ts3conn.clientlist()
            self.logger.debug(f"Retrieved {len(clients)} clients from server: {clients}")

            for client in clients:
                client_id = client["clid"]
                client_type = client.get("client_type")
                client_cid = client.get("cid", -1)
                client_name = client.get("client_nickname", "Unknown")

                self.logger.debug(
                    f"Checking client: ID={client_id}, type={client_type}, channel={client_cid}, name={client_name}"
                )

                # Skip server query clients and users already in AFK channel
                if client_type == "1" or int(client_cid) == self.afk_channel_id:
                    self.logger.debug(
                        f"Skipping client {client_id}: "
                        f"{'Server query client' if client_type == '1' else 'Already in AFK channel'}"
                    )
                    continue

                # If user not in activity tracking, add them with current time
                if client_id not in self.user_activity_timestamps:
                    self.logger.debug(f"New client {client_id} detected, initializing activity timestamp")
                    self._update_user_activity(client_id)
                    continue

                # Check if user has been inactive
                last_activity = self.user_activity_timestamps[client_id]
                inactive_time = (current_time - last_activity) / 60  # Convert to minutes
                self.logger.debug(
                    f"Client {client_id} inactive time: {inactive_time:.2f} minutes "
                    f"(last active: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_activity))})"
                )

                if inactive_time >= self.inactivity_timeout_minutes:
                    try:
                        self.logger.debug(f"Moving inactive client {client_id} to AFK channel {self.afk_channel_id}")
                        # Move user to AFK channel
                        self.ts3conn.clientmove(cid=self.afk_channel_id, clid=client_id)
                        self.logger.info(f"Moved inactive user {client_name} to AFK channel")

                        # Notify the user
                        notification = (
                            f"You have been moved to the AFK channel due to "
                            f"{self.inactivity_timeout_minutes} minutes of inactivity."
                        )
                        self.logger.debug(f"Sending inactivity notification to client {client_id}: {notification}")
                        self.send_message(notification, client_id)
                    except ts3.query.TS3QueryError as e:
                        self.logger.error(f"Failed to move inactive user {client_id}: {e}")
                        self.logger.debug(f"Full error details for move operation: {e!s}")

        except ts3.query.TS3QueryError as e:
            self.logger.error(f"Error checking for inactive users: {e}")
            self.logger.debug(f"Full error details for inactive user check: {e!s}")

    def run(self):
        while True:  # Outer loop for continuous operation
            try:
                # Connect to the server with retry mechanism
                self._connect()

                # Register for events
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

                # Inner loop for normal operation
                while True:
                    self.ts3conn.send_keepalive()
                    self.handle_integration_function_queue()

                    # Check for inactive users every minute
                    current_time = time.time()
                    if current_time - last_inactivity_check >= INACTIVITY_CHECK_INTERVAL:
                        self._check_inactive_users()
                        last_inactivity_check = current_time

                    try:
                        # This method blocks, but we must sent the keepalive message at
                        # least once in 5 minutes to avoid the sever side idle client
                        # disconnect. So we set the timeout parameter simply to 1 minute.
                        events = self.ts3conn.wait_for_event(timeout=1)

                        self.logger.debug(f"{events}")
                        for event in events:
                            self.logger.debug(f"{self.plugin_name} - Event: {event}")
                            self._process_event(event)

                    except ts3.query.TS3TimeoutError:
                        timeouts += 1
                        if timeouts >= MAX_TIMEOUTS:
                            pass

            except Exception as e:
                self.logger.error(f"Connection lost or error occurred: {e!s}")
                self.logger.info("Attempting to reconnect...")
                time.sleep(self.initial_retry_delay)  # Wait before attempting to reconnect
                continue  # Restart from the beginning of the outer loop

    def _process_event(self, event):
        self.logger.debug(f"Processing event: {event}")

        # Update user activity on any event that indicates user interaction
        if "invokerid" in event:
            self.logger.debug(f"Updating activity for invoker {event['invokerid']}")
            self._update_user_activity(event["invokerid"])

        # Handle channel change events to update activity
        if "cfid" in event and "clid" in event:
            self.logger.debug(
                f"Channel change event detected for client {event['clid']}: "
                f"from={event['cfid']}, to={event.get('ctid', 'unknown')}"
            )
            self._update_user_activity(event["clid"])

        # Ignore events from the plugin
        if "invokername" in event and event["invokername"] == self.ts3_server_query_username:
            self.logger.debug("Ignoring self-generated event")
            return

        if "msg" in event:
            self.logger.debug(f"Processing message event: {event['msg']}")
            self._process_msg_event(event)
        elif "cfid" in event:
            self.logger.debug("Processing join event")
            self._process_join_event(event)
        else:
            self.logger.debug(f"Unhandled event type: {event}")

    def _process_join_event(self, event):
        """Process a user join event.

        This method:
        1. Sends a welcome message to new users (those with only the Guest group)
        2. Notifies the admin group about the new user

        Args:
            event (dict): The join event containing user information
        """
        self.logger.debug(f"Processing join event: {event}")

        joining_user_groups = None
        if "client_servergroups" in event:
            joining_user_groups = event["client_servergroups"].split(",")
            self.logger.debug(f"User groups for joining client: {joining_user_groups}")

        if joining_user_groups is not None and len(joining_user_groups) == 1:
            user_nickname = event.get("client_nickname", "Unknown User")
            self.logger.debug(f"Processing single-group user join: {user_nickname}")

            # If user only has one group upon joining, check if it's the guest group
            server_groups = self.ts3conn.servergrouplist()
            self.logger.debug(f"Server groups: {server_groups}")

            for group in server_groups:
                if group["sgid"] == joining_user_groups[0] and group["name"] == "Guest":
                    self.logger.debug(f"New guest user detected: {user_nickname}")

                    # Send welcome message to the new user
                    try:
                        self.logger.debug(f"Sending welcome message to {user_nickname}: {self.new_user_message}")
                        self.ts3conn.sendtextmessage(
                            targetmode=ts3.definitions.TextMessageTargetMode.CLIENT,
                            target=event["clid"],
                            msg=self.new_user_message,
                        )
                        self.logger.info(f"Sent welcome message to new user: {user_nickname}")
                    except ts3.query.TS3QueryError as e:
                        self.logger.error(f"Failed to send welcome message to {user_nickname}: {e}")
                        self.logger.debug(f"Full error details for welcome message: {e!s}")

                    # Find admin group and notify them about the new user
                    try:
                        for admin_group in server_groups:
                            if admin_group["name"] == self.new_user_inform_group:
                                self.logger.debug(f"Found admin group: {admin_group}")

                                # Get all clients in the admin group
                                admin_clients = self.ts3conn.servergroupclientlist(sgid=admin_group["sgid"])
                                self.logger.debug(f"Admin clients to notify: {admin_clients}")

                                # Send notification to each admin
                                for admin in admin_clients:
                                    try:
                                        admin_msg = f"New user joined: {user_nickname}"
                                        self.logger.debug(
                                            f"Sending admin notification to {admin['cldbid']}: {admin_msg}"
                                        )
                                        self.ts3conn.sendtextmessage(
                                            targetmode=ts3.definitions.TextMessageTargetMode.CLIENT,
                                            target=admin["cldbid"],
                                            msg=admin_msg,
                                        )
                                    except ts3.query.TS3QueryError as e:
                                        self.logger.error(
                                            f"Failed to notify admin {admin['cldbid']} about new user: {e}"
                                        )
                                        self.logger.debug(f"Full error details for admin notification: {e!s}")

                                self.logger.info(f"Notified admins about new user: {user_nickname}")
                                break
                    except ts3.query.TS3QueryError as e:
                        self.logger.error(f"Failed to notify admins about new user {user_nickname}: {e}")
                        self.logger.debug(f"Full error details for admin group notification: {e!s}")
                    return

    def _process_msg_event(self, event):
        msg = event["msg"]
        self.logger.debug(f"Processing message event: {msg}")

        envoked_command = None
        for command in self.commands:
            if msg.startswith(self.command_prefix + command):
                envoked_command = self.commands[command]
                self.logger.debug(f"Command matched: {command} -> {envoked_command}")
                break

        if envoked_command is None:
            self.logger.debug("No command matched in message")
            return

        self.logger.info(f"Command envoked: {envoked_command}")

        if "targetmode" not in event:
            self.logger.debug("No targetmode in event, skipping response")
            return

        if "response" in self.commands[command]:
            response = self.commands[command]["response"]
            self.logger.debug(f"Sending command response to channel {self.channel_id}: {response}")
            self.ts3conn.sendtextmessage(targetmode=event["targetmode"], target=self.channel_id, msg=response)
        else:
            self.logger.debug("Command has no response configured")

    def _load_config(self):
        # Load the default config
        with open(Path(__file__).resolve().parent / "teamspeak_default_config.yaml") as default_config_file:
            self.default_config = yaml.safe_load(default_config_file)

        if self.default_config is None:
            self.logger.error("No default config found")
            return

        # Load connection retry settings
        if "initial_retry_delay" in self.config:
            self.initial_retry_delay = self.config["initial_retry_delay"]
        else:
            self.initial_retry_delay = self.default_config.get("initial_retry_delay", 5)

        if "max_retry_delay" in self.config:
            self.max_retry_delay = self.config["max_retry_delay"]
        else:
            self.max_retry_delay = self.default_config.get("max_retry_delay", 60)

        if "retry_backoff_factor" in self.config:
            self.retry_backoff_factor = self.config["retry_backoff_factor"]
        else:
            self.retry_backoff_factor = self.default_config.get("retry_backoff_factor", 2)

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
