"""
Plugin documentation extraction utilities.

This module provides functionality to extract documentation from plugin source code,
including configuration options, integration methods, and their arguments.
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional

from docstring_parser import parse as parse_docstring


class PluginDocExtractor:
    """Extracts documentation from plugin source code."""

    def __init__(self, plugins_dir: str):
        """Initialize the documentation extractor.

        Args:
            plugins_dir: Path to the directory containing plugin modules
        """
        self.plugins_dir = Path(plugins_dir)

    def extract_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """Extract all documentation information for a plugin.

        Args:
            plugin_name: Name of the plugin to extract documentation for

        Returns:
            Dictionary containing all plugin documentation information
        """
        plugin_path = self.plugins_dir / plugin_name
        if not plugin_path.exists():
            error_msg = f"Plugin {plugin_name} not found at {plugin_path}"
            raise ValueError(error_msg)

        return {
            "name": plugin_name,
            "description": self._extract_plugin_description(plugin_path),
            "configuration": self.extract_configuration(plugin_name),
            "integration_methods": self.extract_integration_methods(plugin_name),
            "examples": self._extract_examples(plugin_path),
            "dependencies": self._extract_dependencies(plugin_path),
        }

    def extract_configuration(self, plugin_name: str) -> List[Dict[str, Any]]:
        """Extract configuration options for a plugin.

        Args:
            plugin_name: Name of the plugin to extract configuration for

        Returns:
            List of dictionaries containing configuration option details
        """
        config_path = self.plugins_dir / plugin_name / "config.py"
        if not config_path.exists():
            return []

        config_options = []
        with open(config_path) as f:
            module = ast.parse(f.read())

        for node in ast.walk(module):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        option = {
                            "name": item.target.id,
                            "type": self._get_type_hint(item.annotation),
                            "description": self._get_docstring_from_assignment(item),
                            "default": self._get_default_value(item.value) if item.value else None,
                        }
                        config_options.append(option)

        return config_options

    def extract_integration_methods(self, plugin_name: str) -> List[Dict[str, Any]]:
        """Extract integration methods and their arguments from a plugin.

        Args:
            plugin_name: Name of the plugin to extract methods from

        Returns:
            List of dictionaries containing method details
        """
        # First try ${plugin_name}.py
        plugin_file = self.plugins_dir / plugin_name / f"{plugin_name}.py"
        if not plugin_file.exists():
            # Fallback to __init__.py if the main file doesn't exist
            plugin_file = self.plugins_dir / plugin_name / "__init__.py"
            if not plugin_file.exists():
                return []

        methods = []
        with open(plugin_file) as f:
            module = ast.parse(f.read())

        for node in ast.walk(module):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        # Skip private methods (those starting with _)
                        if item.name.startswith('_'):
                            continue

                        # Check if the function is decorated with plugin_event
                        is_plugin_event = False
                        if item.decorator_list:
                            for decorator in item.decorator_list:
                                if isinstance(decorator, ast.Name) and decorator.id == 'plugin_event':
                                    is_plugin_event = True
                                    break
                                elif (isinstance(decorator, ast.Call) and
                                      isinstance(decorator.func, ast.Name) and
                                      decorator.func.id == 'plugin_event'):
                                    is_plugin_event = True
                                    break

                        docstring = ast.get_docstring(item)
                        return_type = self._get_type_hint(item.returns) if item.returns else None
                        if docstring:
                            parsed_doc = parse_docstring(docstring)
                            methods.append(
                                {
                                    "name": item.name,
                                    "description": parsed_doc.short_description,
                                    "long_description": parsed_doc.long_description,
                                    "arguments": [
                                        {
                                            "name": param.arg_name,
                                            "type": param.type_name,
                                            "description": param.description,
                                        }
                                        for param in parsed_doc.params
                                    ],
                                    "returns": {
                                        "type": return_type
                                        or (parsed_doc.returns.type_name if parsed_doc.returns else None),
                                        "description": parsed_doc.returns.description if parsed_doc.returns else None,
                                    },
                                    "is_plugin_event": is_plugin_event,
                                }
                            )

        return methods

    def _extract_plugin_description(self, plugin_path: Path) -> Optional[str]:
        """Extract the main description from a plugin's main file."""
        # First try ${plugin_name}.py
        plugin_name = plugin_path.name
        main_file = plugin_path / f"{plugin_name}.py"

        if not main_file.exists():
            # Fallback to __init__.py if the main file doesn't exist
            main_file = plugin_path / "__init__.py"
            if not main_file.exists():
                return None

        with open(main_file) as f:
            module = ast.parse(f.read())
            return ast.get_docstring(module)

    def _extract_examples(self, plugin_path: Path) -> List[Dict[str, str]]:
        """Extract usage examples from plugin documentation."""
        examples_path = plugin_path / "examples.py"
        if not examples_path.exists():
            return []

        examples = []
        with open(examples_path) as f:
            file_content = f.read()
            module = ast.parse(file_content)

        for node in ast.walk(module):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node)
                if docstring:
                    # Get the function source code from the original file content
                    start_line = node.lineno - 1  # ast line numbers are 1-based
                    end_line = node.end_lineno
                    function_lines = file_content.splitlines()[start_line:end_line]
                    function_source = "\n".join(function_lines)

                    examples.append(
                        {
                            "title": node.name.replace("_", " ").title(),
                            "description": docstring,
                            "code": function_source,
                        }
                    )

        return examples

    def _extract_dependencies(self, plugin_path: Path) -> List[str]:
        """Extract plugin dependencies from requirements.txt if it exists."""
        req_path = plugin_path / "requirements.txt"
        if not req_path.exists():
            return []

        dependencies: List[str] = []
        with open(req_path) as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    dependencies.append(stripped)
        return dependencies

    @staticmethod
    def _get_type_hint(node: ast.AST) -> str:
        """Convert AST type annotation to string representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}[{PluginDocExtractor._get_type_hint(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return "Any"

    @staticmethod
    def _get_docstring_from_assignment(node: ast.AST) -> Optional[str]:
        """Extract docstring from assignment node's parent class."""
        if hasattr(node, "parent") and isinstance(node.parent, ast.ClassDef):
            for item in node.parent.body:
                if isinstance(item, ast.Expr) and isinstance(item.value, ast.Str):
                    return item.value.s
        return None

    @staticmethod
    def _get_default_value(node: Optional[ast.AST]) -> Optional[str]:
        """Convert AST value node to string representation."""
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.List):
            values = []
            for elt in node.elts:
                val = PluginDocExtractor._get_default_value(elt)
                if val is not None:
                    values.append(val)
            return f"[{', '.join(values)}]"
        elif isinstance(node, ast.Dict):
            items = []
            for k, v in zip(node.keys, node.values):
                key = PluginDocExtractor._get_default_value(k)
                val = PluginDocExtractor._get_default_value(v)
                if key is not None and val is not None:
                    items.append(f"{key}: {val}")
            return f"{{{', '.join(items)}}}"
        return "None"
