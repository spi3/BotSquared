import importlib


def validate_function_integrations(function_integrations: list) -> None:
    """
    Validate the integration dictionary

    :param function_integrations: Integration dictionary
    :return: None
    """
    for integration in function_integrations:
        if not isinstance(integration, dict):
            msg = "Integration must be a dictionary"
            raise ValueError(msg)

        if "function" not in integration:
            msg = 'Integration must have a "function" key'
            raise ValueError(msg)

        if not isinstance(integration["function"], str):
            msg = 'Integration "function" must be a string'
            raise ValueError(msg)

        if "args" not in integration:
            msg = 'Integration must have an "args" key'
            raise ValueError(msg)

        if not isinstance(integration["args"], dict):
            msg = 'Integration "args" must be a dictionary'
            raise ValueError(msg)


def validate_integrations(integrations: dict) -> None:
    """
    Validate the integration dictionary

    :param integrations: Integration dictionary
    :return: None
    """
    if not isinstance(integrations, dict):
        msg = "Integrations must be a dictionary"
        raise ValueError(msg)

    for _, function_integrations in integrations.items():
        validate_function_integrations(function_integrations)


def validate_config(config: dict) -> None:
    """
    Validate the configuration dictionary

    :param config: Configuration dictionary
    :return: None
    """
    if "plugins" not in config:
        msg = 'Configuration must contain a "plugins" key'
        raise ValueError(msg)

    if not isinstance(config["plugins"], dict):
        msg = 'Configuration "plugins" must be a dictionary'
        raise ValueError(msg)

    plugins = config["plugins"]

    for plugin_name in plugins:
        plugin = plugins[plugin_name]

        if not isinstance(plugin, dict):
            msg = f"Plugin {plugin_name} must be a dictionary"
            raise ValueError(msg)

        if "plugin_type" not in plugin:
            msg = f'Plugin {plugin_name} must have a "plugin_type" key'
            raise ValueError(msg)

        # Validate if plugin_type is a valid plugin
        if not isinstance(plugin["plugin_type"], str):
            msg = f'Plugin {plugin_name} "plugin_type" must be a string'
            raise ValueError(msg)
        try:
            importlib.import_module(f"plugins.{plugin['plugin_type']}")
        except ModuleNotFoundError as e:
            msg = f"Plugin {plugin_name} plugin_type {plugin['plugin_type']} is not a valid plugin"
            raise ValueError(msg) from e

        if "integrations" in plugin:
            integrations = plugin["integrations"]

            validate_integrations(integrations)
