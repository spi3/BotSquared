import importlib
import logging

logger = logging.getLogger(__name__)


def validate_function_integrations(function_integrations: list) -> None:
    """
    Validate the integration dictionary

    :param function_integrations: Integration dictionary
    :return: None
    """
    logger.debug(f"Validating function integrations: {function_integrations}")

    for integration in function_integrations:
        logger.debug(f"Validating integration: {integration}")

        if not isinstance(integration, dict):
            msg = "Integration must be a dictionary"
            logger.error(msg)
            raise ValueError(msg)

        if "function" not in integration:
            msg = 'Integration must have a "function" key'
            logger.error(msg)
            raise ValueError(msg)

        if not isinstance(integration["function"], str):
            msg = 'Integration "function" must be a string'
            logger.error(msg)
            raise ValueError(msg)

        if "args" not in integration:
            msg = 'Integration must have an "args" key'
            logger.error(msg)
            raise ValueError(msg)

        if not isinstance(integration["args"], dict):
            msg = 'Integration "args" must be a dictionary'
            logger.error(msg)
            raise ValueError(msg)

        logger.debug(f"Integration validation successful: {integration}")


def validate_integrations(integrations: dict) -> None:
    """
    Validate the integration dictionary

    :param integrations: Integration dictionary
    :return: None
    """
    logger.debug(f"Validating integrations: {integrations}")

    if not isinstance(integrations, dict):
        msg = "Integrations must be a dictionary"
        logger.error(msg)
        raise ValueError(msg)

    for function_name, function_integrations in integrations.items():
        logger.debug(f"Validating integrations for function: {function_name}")
        validate_function_integrations(function_integrations)
        logger.debug(f"Function integrations validation successful: {function_name}")


def validate_config(config: dict) -> None:
    """
    Validate the configuration dictionary

    :param config: Configuration dictionary
    :return: None
    """
    logger.debug(f"Validating configuration: {config}")

    if "plugins" not in config:
        msg = 'Configuration must contain a "plugins" key'
        logger.error(msg)
        raise ValueError(msg)

    if not isinstance(config["plugins"], dict):
        msg = 'Configuration "plugins" must be a dictionary'
        logger.error(msg)
        raise ValueError(msg)

    plugins = config["plugins"]
    logger.debug(f"Validating plugins: {plugins}")

    for plugin_name in plugins:
        logger.debug(f"Validating plugin: {plugin_name}")
        plugin = plugins[plugin_name]

        if not isinstance(plugin, dict):
            msg = f"Plugin {plugin_name} must be a dictionary"
            logger.error(msg)
            raise ValueError(msg)

        if "plugin_type" not in plugin:
            msg = f'Plugin {plugin_name} must have a "plugin_type" key'
            logger.error(msg)
            raise ValueError(msg)

        # Validate if plugin_type is a valid plugin
        if not isinstance(plugin["plugin_type"], str):
            msg = f'Plugin {plugin_name} "plugin_type" must be a string'
            logger.error(msg)
            raise ValueError(msg)

        logger.debug(f"Attempting to import plugin module: plugins.{plugin['plugin_type']}")
        try:
            importlib.import_module(f"plugins.{plugin['plugin_type']}")
            logger.debug(f"Successfully imported plugin module: plugins.{plugin['plugin_type']}")
        except ModuleNotFoundError as e:
            msg = f"Plugin {plugin_name} plugin_type {plugin['plugin_type']} is not a valid plugin"
            logger.error(msg)
            raise ValueError(msg) from e

        if "integrations" in plugin:
            logger.debug(f"Validating integrations for plugin: {plugin_name}")
            integrations = plugin["integrations"]
            validate_integrations(integrations)
            logger.debug(f"Plugin integrations validation successful: {plugin_name}")

        logger.debug(f"Plugin validation successful: {plugin_name}")

    logger.debug("Configuration validation completed successfully")
