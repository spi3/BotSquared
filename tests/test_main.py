import argparse
import logging
import os
import tempfile
from unittest import mock

import pytest
import yaml

from bot_squared.b2 import convert_log_level, main


@pytest.fixture
def valid_config():
    return {
        "log_level": "DEBUG",
        "log_file": "test.log",
        "plugins": {"test_plugin": {"plugin_type": "template", "integrations": {}}},
    }


@pytest.fixture
def default_config():
    return {"log_level": "INFO", "log_file": "bot.log"}


@pytest.fixture
def temp_config_file(valid_config):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(valid_config, f)
        config_path = f.name
    yield config_path
    os.unlink(config_path)


def test_main_with_valid_config(temp_config_file, valid_config, default_config):
    args = argparse.Namespace(config=temp_config_file)
    mock_open = mock.mock_open()
    mock_open.side_effect = [
        mock.mock_open(read_data=yaml.dump(valid_config)).return_value,
        mock.mock_open(read_data=yaml.dump(default_config)).return_value,
    ]
    with mock.patch("builtins.open", mock_open), mock.patch("bot_squared.b2.Plugin") as mock_plugin, mock.patch(
        "bot_squared.b2.integrator"
    ) as mock_integrator, mock.patch("bot_squared.b2.validate_config") as mock_validate:
        mock_plugin_instance = mock.MagicMock()
        mock_plugin_instance.is_alive.side_effect = [True, False]
        mock_plugin.return_value = mock_plugin_instance
        main(args)
        mock_validate.assert_called_once()
        mock_plugin.assert_called_once()
        mock_integrator.register_integrations.assert_called_once()
        mock_integrator.add_loaded_plugins.assert_called_once()


def test_main_with_missing_config():
    args = argparse.Namespace(config="nonexistent.yaml")
    with pytest.raises(FileNotFoundError):
        main(args)


def test_main_with_empty_config(temp_config_file):
    with open(temp_config_file, "w") as f:
        f.write("")
    args = argparse.Namespace(config=temp_config_file)
    mock_open = mock.mock_open()
    mock_open.side_effect = [
        mock.mock_open(read_data="").return_value,
        mock.mock_open(read_data=yaml.dump({"log_level": "INFO", "log_file": "bot.log"})).return_value,
    ]
    with mock.patch("builtins.open", mock_open), mock.patch("logging.getLogger") as mock_logger:
        main(args)
        mock_logger.return_value.error.assert_called_with("No config found")


def test_convert_log_level():
    assert convert_log_level("DEBUG") == logging.DEBUG
    assert convert_log_level("INFO") == logging.INFO
    assert convert_log_level("WARNING") == logging.WARNING
    assert convert_log_level("ERROR") == logging.ERROR
    assert convert_log_level("CRITICAL") == logging.CRITICAL
    assert convert_log_level("FATAL") == logging.FATAL
    assert convert_log_level("INVALID") is None


def test_main_without_plugins(temp_config_file, default_config):
    config = {"log_level": "DEBUG", "log_file": "test.log", "plugins": {}}
    mock_open = mock.mock_open()
    mock_open.side_effect = [
        mock.mock_open(read_data=yaml.dump(config)).return_value,
        mock.mock_open(read_data=yaml.dump(default_config)).return_value,
    ]
    args = argparse.Namespace(config=temp_config_file)
    with mock.patch("builtins.open", mock_open), mock.patch("logging.getLogger") as mock_logger:
        main(args)
        mock_logger.return_value.error.assert_called_with(
            "No plugins found in config. Please update your config to include the plugins you want to run. Thank you."
        )
