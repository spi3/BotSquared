from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class InactivityMonitoringConfig:
    """Configuration for inactivity monitoring settings."""
    enabled: bool = True
    afk_channel_id: int = 0
    inactivity_timeout_minutes: int = 30


@dataclass
class ChatConfig:
    """Configuration for chat functionality."""
    enabled: bool = True
    command_prefix: str = "!"
    commands: Dict[str, Dict] = None

    def __post_init__(self):
        if self.commands is None:
            self.commands = {}


@dataclass
class NewUserAlertingConfig:
    """Configuration for new user alerting settings."""
    new_user_message: str = "Welcome to the server!"
    new_user_inform_group: str = "Server Admin"


@dataclass
class TeamspeakConfig:
    """Main configuration dataclass for the TeamSpeak plugin.
    
    This dataclass defines the complete configuration structure for the TeamSpeak plugin,
    including server connection details, monitoring settings, and chat functionality.
    """
    # Server connection details
    ts3_server_ip: str
    ts3_server_query_username: str
    ts3_server_query_passwd: str
    ts3_server_id: int
    bot_channel_id: int
    iteration_rate_hz: float
    
    # Optional configuration sections
    inactivity_monitoring: Optional[InactivityMonitoringConfig] = None
    chat: Optional[ChatConfig] = None
    new_user_alerting: Optional[NewUserAlertingConfig] = None

    def __post_init__(self):
        """Initialize optional configuration sections with defaults if not provided."""
        if self.inactivity_monitoring is None:
            self.inactivity_monitoring = InactivityMonitoringConfig()
        
        if self.chat is None:
            self.chat = ChatConfig()
            
        if self.new_user_alerting is None:
            self.new_user_alerting = NewUserAlertingConfig()

    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'TeamspeakConfig':
        """Create a TeamspeakConfig instance from a dictionary.
        
        Args:
            config_dict: Dictionary containing configuration values
            
        Returns:
            TeamspeakConfig instance with values from the dictionary
        """
        # Extract main configuration values
        main_config = {
            'ts3_server_ip': config_dict['ts3_server_ip'],
            'ts3_server_query_username': config_dict['ts3_server_query_username'],
            'ts3_server_query_passwd': config_dict['ts3_server_query_passwd'],
            'ts3_server_id': config_dict['ts3_server_id'],
            'bot_channel_id': config_dict['bot_channel_id'],
            'iteration_rate_hz': config_dict['iteration_rate_hz'],
        }
        
        # Extract optional configuration sections
        inactivity_config = config_dict.get('inactivity_monitoring', {})
        if inactivity_config:
            main_config['inactivity_monitoring'] = InactivityMonitoringConfig(
                enabled=inactivity_config.get('enabled', True),
                afk_channel_id=inactivity_config.get('afk_channel_id', 0),
                inactivity_timeout_minutes=inactivity_config.get('inactivity_timeout_minutes', 30)
            )
        
        chat_config = config_dict.get('chat', {})
        if chat_config:
            main_config['chat'] = ChatConfig(
                enabled=chat_config.get('enabled', True),
                command_prefix=chat_config.get('command_prefix', '!'),
                commands=chat_config.get('commands', {})
            )
        
        new_user_config = config_dict.get('new_user_alerting', {})
        if new_user_config:
            main_config['new_user_alerting'] = NewUserAlertingConfig(
                new_user_message=new_user_config.get('new_user_message', 'Welcome to the server!'),
                new_user_inform_group=new_user_config.get('new_user_inform_group', 'Server Admin')
            )
        
        return cls(**main_config)
