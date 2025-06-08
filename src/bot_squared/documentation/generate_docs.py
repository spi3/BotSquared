#!/usr/bin/env python3
"""Script to generate plugin documentation."""

import argparse
import logging
import os
import sys

from bot_squared.documentation import DocumentationGenerator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Generate documentation for all plugins."""
    parser = argparse.ArgumentParser(description="Generate plugin documentation")
    parser.add_argument(
        "--plugins-dir",
        type=str,
        default=os.path.join("src", "bot_squared", "plugins"),
        help="Path to the plugins directory",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join("documentation", "plugins"),
        help="Path where documentation will be generated",
    )
    parser.add_argument(
        "--template-dir",
        type=str,
        help="Optional path to custom template directory",
    )
    args = parser.parse_args()

    try:
        generator = DocumentationGenerator(
            args.plugins_dir,
            args.output_dir,
            args.template_dir,
        )
        generator.generate_all_documentation()
        logger.info("Documentation generated successfully in %s", args.output_dir)
        return 0
    except Exception as e:
        logger.error("Error generating documentation: %s", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
