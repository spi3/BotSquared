# TeamSpeak Plugin

The TeamSpeak plugin provides comprehensive integration with TeamSpeak servers, enabling automated server management, user monitoring, and interactive features.

## Overview

This plugin connects to a TeamSpeak server using the ServerQuery interface and provides the following core functionality:

- **Server Connection Management**: Robust connection handling with automatic retry and reconnection
- **User Activity Monitoring**: Tracking user activity and automatic AFK management
- **Message Handling**: Send and receive messages, process commands
- **New User Management**: Welcome messages and admin notifications
- **Channel Management**: Modify channel names and properties
- **Event Processing**: Real-time processing of server events

## Features

### 🔗 Connection Management
- **Automatic Connection**: Connects to TeamSpeak server using ServerQuery protocol
- **Retry Mechanism**: Exponential backoff retry strategy for failed connections
- **Connection Monitoring**: Maintains persistent connection with keepalive messages
- **Error Recovery**: Automatic reconnection on connection loss

### 👥 User Activity Monitoring
- **Activity Tracking**: Monitors user activity based on messages and channel changes
- **AFK Detection**: Automatically identifies inactive users after configurable timeout
- **AFK Channel Movement**: Moves inactive users to designated AFK channel
- **Activity Notifications**: Sends notifications to users when moved for inactivity

### 💬 Messaging System
- **Send Messages**: Send private messages to specific users
- **Command Processing**: Process text commands with configurable prefix
- **Command Responses**: Automated responses to recognized commands
- **Event-based Messaging**: React to server events with appropriate messages

### 🆕 New User Management
- **Welcome Messages**: Automatically welcome new users joining the server
- **Admin Notifications**: Notify administrators when new users join
- **Guest Detection**: Identify new users based on server group membership
- **Customizable Messages**: Configure welcome messages and notification content

### 🛠️ Channel Management
- **Channel Naming**: Programmatically update channel names
- **Channel Monitoring**: Track channel-related events
- **Bot Channel Assignment**: Automatically position bot in designated channel

## Configuration

The plugin uses a YAML configuration file (`teamspeak_default_config.yaml`) with the following options:

### Connection Settings
```yaml
ts3_server_ip: "your.teamspeak.server.ip"
ts3_server_query_username: "MyTSBot"
ts3_server_query_passwd: "MyTSBotPassword"
ts3_server_id: 1  # Virtual server ID (usually 1)
bot_channel_id: 1  # Channel where the bot will reside
iteration_rate_hz: 1  # Plugin update frequency
```

### Inactivity Monitoring
```yaml
inactivity_timeout_minutes: 30  # Minutes before user considered inactive
afk_channel_id: 0  # Channel ID for inactive users
enable_inactivity_monitoring: true  # Enable/disable feature
```

### Command System
```yaml
command_prefix: '!'  # Character(s) that prefix commands
commands:
  help:
    response: "Sorry, no commands have been set up for this plugin yet!"
  # Add more commands as needed
```

### New User Settings
```yaml
new_user_message: "Welcome!"  # Message sent to new users
new_user_inform_group: "Server Admin"  # Group to notify about new users
```

### Integration Settings
```yaml
integrations:
  integration_1:
  integration_2:
  # Configure integrations with other plugins
```

## Plugin Events

The plugin exposes several methods decorated with `@plugin_event`, making them available for integration with other plugins:

### Public Methods
- `send_message(message: str, to: int)`: Send a message to a specific client
- `set_channel_name(channel_id: int, name: str)`: Update a channel's name
- `receive_message()`: Handle incoming messages (currently a placeholder)

### Activity Tracking
- `_update_user_activity(client_id: str)`: Update user activity timestamp

## Event Processing

The plugin processes various TeamSpeak events:

### Message Events
- **Text Messages**: Process incoming text messages for commands
- **Command Matching**: Match messages against configured command patterns
- **Response Generation**: Send appropriate responses based on commands

### Join Events
- **New User Detection**: Identify users joining for the first time
- **Welcome Processing**: Send welcome messages to new guests
- **Admin Notification**: Alert administrators about new user joins

### Activity Events
- **Channel Changes**: Track when users move between channels
- **Message Activity**: Update activity timestamps when users send messages
- **Inactivity Checks**: Periodic scanning for inactive users

## Technical Implementation

### Dependencies
- `ts3`: TeamSpeak 3 ServerQuery library
- `yaml`: Configuration file parsing  
- `logging`: Comprehensive logging support
- `pathlib`: File path handling

### Error Handling
- **Connection Errors**: Graceful handling of connection failures
- **Query Errors**: Proper handling of TeamSpeak ServerQuery errors
- **Timeout Management**: Configurable timeout handling for server queries
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

### Performance Features
- **Efficient Event Loop**: Optimized main loop with appropriate sleep intervals
- **Timeout Management**: Prevents blocking operations from hanging
- **Keepalive System**: Maintains connection without excessive overhead
- **Activity Batching**: Efficient processing of user activity updates

## Testing

The plugin includes comprehensive unit tests (`test_teamspeak.py`) covering:

- Connection retry mechanisms
- Message processing and command handling
- User activity tracking and AFK detection
- New user join event processing
- Error handling scenarios
- Configuration loading and validation

## Usage Examples

### Basic Plugin Initialization
```python
from bot_squared.plugins.teamspeak import create_plugin

config = {
    "ts3_server_ip": "127.0.0.1",
    "ts3_server_query_username": "serveradmin",
    "ts3_server_query_passwd": "password",
    "bot_channel_id": 1
}

teamspeak_plugin = create_plugin("TeamSpeak", config)
```

### Sending Messages
```python
# Send a message to client ID 5
teamspeak_plugin.send_message("Hello, user!", 5)
```

### Updating Channel Names
```python
# Update channel 10's name
teamspeak_plugin.set_channel_name(10, "New Channel Name")
```

## Logging

The plugin provides extensive logging at various levels:

- **DEBUG**: Detailed event processing, connection attempts, user activity
- **INFO**: Important events like connections, user joins, message sending
- **WARNING**: Connection failures, retry attempts
- **ERROR**: Critical errors, failed operations

Configure logging levels in your bot's main configuration to control verbosity.

## Integration Notes

This plugin is designed to work within the bot_squared framework and can integrate with other plugins through the event system. The `@plugin_event` decorated methods are automatically exposed for cross-plugin communication.

## Security Considerations

- Store TeamSpeak ServerQuery credentials securely
- Use dedicated ServerQuery accounts with minimal required permissions  
- Monitor log files for unauthorized access attempts
- Regularly update the ts3 library for security patches

## Troubleshooting

### Common Issues

1. **Connection Failures**: Verify server IP, credentials, and ServerQuery port
2. **Permission Errors**: Ensure ServerQuery account has necessary permissions
3. **Channel Access**: Verify bot has permission to join designated channel
4. **Command Not Working**: Check command prefix and configuration syntax

### Debug Mode

Enable debug logging to get detailed information about plugin operations:

```python
import logging
logging.getLogger('bot_squared.plugins.teamspeak').setLevel(logging.DEBUG)
```

This will provide detailed logs about connection attempts, event processing, and user activity tracking. 