import logging
import threading
from functools import wraps

from bot_squared.plugins.plugin import Plugin

_loaded_plugins: dict[str, Plugin] = {}
_integrations: dict = {}
_integrations_lock = threading.Lock()
_logger = logging.getLogger(__name__)


def add_integration(plugin_name: str, integration: dict):
    _integrations_lock.acquire()
    if plugin_name not in _integrations:
        _integrations[plugin_name] = {}

    _integrations[plugin_name] = integration
    _integrations_lock.release()


def add_loaded_plugins(plugin_name: str, plugin: Plugin):
    _integrations_lock.acquire()
    _loaded_plugins[plugin_name] = plugin
    _integrations_lock.release()


def integrates(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 'self' is the instance of the calling object

        _integrations_lock.acquire()

        # Call the function
        func_ret = func(self, *args, **kwargs)

        # Get the function name
        func_name = func.__name__

        # Get the integrations for the plugin
        integrations = _integrations.get(self.plugin_name, None)

        if integrations is None:
            _logger.debug(f"No integrations found for {self.plugin_name}")
        elif func_name not in integrations:
            _logger.debug(f"No integrations found for {self.plugin_name} - {func_name}")
        else:
            integration = integrations[func_name]

            # Run the integrations
            for function_integration in integration:
                integration_plugin = function_integration["plugin_name"]

                if integration_plugin not in _loaded_plugins:
                    _logger.error(f"Integration invalid - Plugin {integration_plugin} not loaded")
                    continue

                if "function" not in function_integration:
                    _logger.error(f"Integration invalid - Plugin {integration_plugin} missing function")
                    continue

                integration_plugin_function = function_integration["function"]
                integration_plugin_function_args = {}

                if "args" in function_integration:
                    for arg in function_integration["args"]:
                        if isinstance(function_integration["args"][arg], str):
                            integration_plugin_function_args[arg] = function_integration["args"][arg].format(
                                **func_ret if isinstance(func_ret, dict) else {"return_val": func_ret}
                            )
                        else:
                            integration_plugin_function_args[arg] = function_integration["args"][arg]
                try:
                    # integration_function = getattr(
                    #     _loaded_plugins[integration_plugin].instance, integration_plugin_function
                    # )
                    # threading.Thread(target=integration_function(integration_plugin_function_args)).start()
                    _loaded_plugins[integration_plugin].instance.add_to_queue(
                        integration_plugin_function, integration_plugin_function_args
                    )
                    _logger.debug(
                        f"Integration {integration_plugin} called - "
                        f"function: {integration_plugin_function} with args:"
                        f"{integration_plugin_function_args}"
                    )

                except Exception as e:
                    _logger.error(
                        f"Error in integration {integration_plugin}calling function: {integration_plugin_function}- {e}"
                    )

        _integrations_lock.release()
        return func_ret

    return wrapper
