import argparse
import logging
import sys
import time
from typing import Optional

import yaml

from bot_squared.plugins.plugin import Plugin


def main(args: Optional[argparse.Namespace] = None):
    default_config_path = 'config.yaml'
    log_level: str = 'DEBUG'
    log_file = 'bot.log'
    config: dict = {}
    default_config: dict = {}
    config_file_path = default_config_path
    logger = logging.getLogger(__name__)

    if args is not None and args.config is not None:
        config_file_path = args.config

    # Load the config file
    with open(config_file_path) as config_file:
        config = yaml.safe_load(config_file)

    # Load the default config file
    with open('default_config.yaml') as default_config_file:
        default_config = yaml.safe_load(default_config_file)

    if config is None:
        logger.error('No config found')
        return

    if default_config is None:
        logger.error('No default config found')
        return

    log_level = config['log_level'] if 'log_level' in config else default_config['log_level']
    log_file = config['log_file'] if 'log_file' in config else default_config['log_file']

    # Configure logging
    log_level = convert_log_level(log_level)
    logging.basicConfig(filename=log_file, level=log_level)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # Get the plugins from config
    if config['plugins'] is None:
        logger.error(
            'No plugins found in config. Please update your config to include the plugins you want to run. Thank you.'
        )
        return
    plugins = config['plugins']
    logger.debug(f'Plugins - {plugins}')

    # Load the plugins
    loaded_plugins: dict = {}
    for plugin_name in plugins:
        logger.info(f'Loading: {plugin_name}')

        if 'plugin_type' not in plugins[plugin_name]:
            logger.error(f'No plugin specified in configuration for: {plugin_name}')

        plugin_type = plugins[plugin_name]['plugin_type']

        logger.info(f'Loading: {plugin_name}: {plugins[plugin_name][plugin_type]}')

        # Load the plugin
        loaded_plugins[plugin_name] = Plugin(
            plugin_name=plugin_name, plugin_type=plugin_type, plugin_conf=plugins[plugin_name]
        )

    plugin_active = True
    while plugin_active:
        plugin_active = False

        # Check if the plugins are still running
        for plugin in loaded_plugins.items():
            if loaded_plugins[plugin].is_alive():
                plugin_active = True
                break

        time.sleep(1)

    logging.info('No plugins running. Exiting...')


def convert_log_level(level: str):
    """
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    NOTSET = 0
    """
    logging_level = None
    if level == 'DEBUG':
        logging_level = logging.DEBUG
    elif level == 'INFO':
        logging_level = logging.INFO
    elif level == 'WARNING':
        logging_level = logging.WARNING
    elif level == 'WARN':
        logging_level = logging.WARN
    elif level == 'ERROR':
        logging_level = logging.ERROR
    elif level == 'CRITICAL':
        logging_level = logging.CRITICAL
    elif level == 'FATAL':
        logging_level = logging.FATAL

    return logging_level


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Bot Squared')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the config file')
    args = parser.parse_args()

    main(args)
