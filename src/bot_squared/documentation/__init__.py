"""
Documentation generation system for bot_squared plugins.

This package provides functionality to generate HTML documentation for all plugins
in the bot_squared project, including configuration options, integration methods,
and usage examples.
"""

from bot_squared.documentation.generator.doc_extractor import PluginDocExtractor
from bot_squared.documentation.generator.html_generator import DocumentationGenerator

__all__ = ['DocumentationGenerator', 'PluginDocExtractor']
