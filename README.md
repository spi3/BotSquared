Bot Squared
===================

A python bot of bots. Integrate all your bots together with infinite configurability. 


Configuration
===================

- ```log_level```: Sets the global log level for the application. Possible values are ```DEBUG```, ```INFO```, ```WARNING```, ```ERROR```, ```CRITICAL```.
- ```plugins```: A dictionary containing configurations for each plugin. Each plugin configuration includes:
  - ```plugin_type```: The type of the plugin (e.g., ```teamspeak```, ```discord```, ```steam```).
- Plugin-specific configuration options (e.g., ```ts3_server_ip```, ```ts3_server_query_username```, ```bot_channel_id``` for Teamspeak).
- ```integrations```: A dictionary defining integrations with other plugins (optional). Each integration includes:
  - The event that triggers the integration (e.g., ```receive_message```).
  - The target plugin and function to call, along with any arguments to pass.

Developing
===================

Prerequisites: 
```
pipx install hatch
```

Test & Build:
```
hatch run check:all
hatch test
hatch build
```