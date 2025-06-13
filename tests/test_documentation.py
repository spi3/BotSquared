"""Tests for the documentation generator."""

import os
import tempfile
from pathlib import Path

import pytest

from bot_squared.documentation import DocumentationGenerator, PluginDocExtractor

# Constants for test assertions
NUM_CONFIG_OPTIONS = 2
NUM_METHOD_ARGS = 2
RATE_LIMIT_THRESHOLD = 0.1


@pytest.fixture
def temp_plugin_dir():
    """Create a temporary plugin directory with a test plugin."""
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "test_plugin"
        plugin_dir.mkdir()

        # Create __init__.py with a test class
        with open(plugin_dir / "__init__.py", "w") as f:
            f.write('''"""Test plugin for documentation generation."""

class TestPlugin:
    """A test plugin class."""
    def test_method(self, arg1: str, arg2: int = 42) -> bool:
        """Test method with arguments.
        Args:
            arg1: First argument description
            arg2: Second argument description
        Returns:
            True if successful
        """
        return True
''')

        # Create config.py with configuration options
        with open(plugin_dir / "config.py", "w") as f:
            f.write('''"""Configuration for test plugin."""

class Config:
    """Configuration options."""
    option1: str = "default"  # First option description
    option2: int = 123  # Second option description
''')

        # Create examples.py with usage examples
        with open(plugin_dir / "examples.py", "w") as f:
            f.write('''"""Usage examples for test plugin."""

def basic_usage():
    """Basic usage example."""
    plugin = TestPlugin()
    result = plugin.test_method("test", 42)
    print(f"Result: {result}")
''')

        # Create requirements.txt
        with open(plugin_dir / "requirements.txt", "w") as f:
            f.write("test-dependency==1.0.0\n")

        yield temp_dir


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_plugin_doc_extractor(temp_plugin_dir):
    """Test the PluginDocExtractor class."""
    extractor = PluginDocExtractor(temp_plugin_dir)
    plugin_info = extractor.extract_plugin_info("test_plugin")

    assert plugin_info["name"] == "test_plugin"
    assert "Test plugin for documentation generation" in plugin_info["description"]

    # Test configuration extraction
    assert len(plugin_info["configuration"]) == NUM_CONFIG_OPTIONS
    assert plugin_info["configuration"][0]["name"] == "option1"
    assert plugin_info["configuration"][0]["type"] == "str"
    assert plugin_info["configuration"][0]["default"] == "'default'"

    # Test method extraction
    assert len(plugin_info["integration_methods"]) == 1
    method = plugin_info["integration_methods"][0]
    assert method["name"] == "test_method"
    assert len(method["arguments"]) == NUM_METHOD_ARGS
    assert method["returns"]["type"] == "bool"

    # Test example extraction
    assert len(plugin_info["examples"]) == 1
    assert plugin_info["examples"][0]["title"] == "Basic Usage"

    # Test dependency extraction
    assert len(plugin_info["dependencies"]) == 1
    assert plugin_info["dependencies"][0] == "test-dependency==1.0.0"


def test_documentation_generator(temp_plugin_dir, temp_output_dir):
    """Test the DocumentationGenerator class."""
    generator = DocumentationGenerator(temp_plugin_dir, temp_output_dir)
    generator.generate_all_documentation()

    # Check that output files were created
    assert os.path.exists(os.path.join(temp_output_dir, "index.html"))
    assert os.path.exists(os.path.join(temp_output_dir, "plugins", "test_plugin.html"))
    assert os.path.exists(os.path.join(temp_output_dir, "static", "pygments.css"))

    # Check index.html content
    with open(os.path.join(temp_output_dir, "index.html")) as f:
        index_content = f.read()
        assert "Bot Squared Plugin Documentation" in index_content
        assert "test_plugin" in index_content

    # Check plugin page content
    with open(os.path.join(temp_output_dir, "plugins", "test_plugin.html")) as f:
        plugin_content = f.read()
        assert "test_plugin" in plugin_content
        assert "Test plugin for documentation generation" in plugin_content
        assert "test_method" in plugin_content
        assert "option1" in plugin_content
        assert "Basic Usage" in plugin_content
