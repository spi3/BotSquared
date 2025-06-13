"""
HTML documentation generator for bot_squared plugins.

This module provides functionality to generate HTML documentation pages for plugins
using the extracted documentation information.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import jinja2
import markdown2
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer

from bot_squared.documentation.generator.doc_extractor import PluginDocExtractor


class DocumentationGenerator:
    """Generates HTML documentation for plugins."""

    def __init__(self, plugins_dir: str, output_dir: str, template_dir: Optional[str] = None):
        """Initialize the documentation generator.

        Args:
            plugins_dir: Path to the directory containing plugin modules
            output_dir: Path where generated documentation will be saved
            template_dir: Optional path to custom template directory
        """
        self.plugins_dir = Path(plugins_dir)
        self.output_dir = Path(output_dir)
        self.template_dir = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
        self.doc_extractor = PluginDocExtractor(plugins_dir)

        # Set up Jinja environment
        self.jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(self.template_dir)), autoescape=True)

        # Set up markdown converter
        self.markdown = markdown2.Markdown(extras=["fenced-code-blocks", "tables"])

        # Set up code highlighter
        self.code_formatter = HtmlFormatter(style="monokai", cssclass="highlight")
        self.code_lexer = PythonLexer()

    def generate_all_documentation(self) -> None:
        """Generate documentation for all plugins."""
        # Create output directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "plugins").mkdir(exist_ok=True)
        (self.output_dir / "static").mkdir(exist_ok=True)

        # Copy static assets
        self._copy_static_assets()

        # Generate documentation for each plugin
        plugins_info = []
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
                plugin_info = self.doc_extractor.extract_plugin_info(plugin_dir.name)
                plugins_info.append(plugin_info)
                self.generate_plugin_page(plugin_dir.name, plugin_info)

        # Generate index page
        self.generate_index_page(plugins_info)

    def generate_index_page(self, plugins_info: List[Dict[str, Any]]) -> None:
        """Generate the main index page.

        Args:
            plugins_info: List of dictionaries containing plugin information
        """
        template = self.jinja_env.get_template("index.html.j2")

        # Sort plugins by name
        plugins_info.sort(key=lambda x: x["name"])

        # Generate categories
        categories: Dict[str, List[Dict[str, Any]]] = {}
        for plugin in plugins_info:
            category = plugin.get("category", "Uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(plugin)

        html = template.render(plugins=plugins_info, categories=categories, title="Bot Squared Plugin Documentation")

        with open(self.output_dir / "index.html", "w") as f:
            f.write(html)

    def generate_plugin_page(self, plugin_name: str, plugin_info: Optional[Dict[str, Any]] = None) -> None:
        """Generate documentation page for a specific plugin.

        Args:
            plugin_name: Name of the plugin to generate documentation for
            plugin_info: Optional pre-extracted plugin information
        """
        if plugin_info is None:
            plugin_info = self.doc_extractor.extract_plugin_info(plugin_name)

        template = self.jinja_env.get_template("plugin.html.j2")

        # Convert markdown to HTML
        if plugin_info["description"]:
            plugin_info["description"] = self.markdown.convert(plugin_info["description"])

        # Highlight code examples
        for example in plugin_info["examples"]:
            example["code"] = highlight(example["code"], self.code_lexer, self.code_formatter)

        html = template.render(plugin=plugin_info, title=f"{plugin_name} - Bot Squared Plugin Documentation")

        output_path = self.output_dir / "plugins" / f"{plugin_name}.html"
        with open(output_path, "w") as f:
            f.write(html)

    def update_documentation(self, plugin_name: str) -> None:
        """Update documentation for a specific plugin.

        Args:
            plugin_name: Name of the plugin to update documentation for
        """
        plugin_info = self.doc_extractor.extract_plugin_info(plugin_name)
        self.generate_plugin_page(plugin_name, plugin_info)

        # Regenerate index page with updated information
        plugins_info = []
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
                if plugin_dir.name == plugin_name:
                    plugins_info.append(plugin_info)
                else:
                    plugins_info.append(self.doc_extractor.extract_plugin_info(plugin_dir.name))
        self.generate_index_page(plugins_info)

    def _copy_static_assets(self) -> None:
        """Copy static assets (CSS, JS) to the output directory."""
        static_dir = self.template_dir / "static"
        if static_dir.exists():
            import shutil

            shutil.copytree(static_dir, self.output_dir / "static", dirs_exist_ok=True)

        # Generate pygments CSS
        with open(self.output_dir / "static" / "pygments.css", "w") as f:
            f.write(self.code_formatter.get_style_defs())
