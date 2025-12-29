#!/usr/bin/env python3
"""
jar-inspector.py - Analyze JAR files and extract structured information

This script provides dual purpose:
1. Executable tool for JAR analysis
2. Reference documentation for understanding JAR structure

Usage:
    jar-inspector.py <jar_file> [--full] [--output json|text]

Features:
- Extract manifest information
- List all classes and packages
- Identify entry points and main classes
- Extract resources and configuration files
- Analyze dependencies (if available)
- Security: Read-only operations, no code execution

Output: JSON format by default for easy parsing
"""

import zipfile
import json
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict


class JARInspector:
    """
    JAR file analyzer that extracts metadata without executing code.

    This class demonstrates best practices:
    - Type hints for all methods
    - Comprehensive error handling
    - Read-only operations (security)
    - Structured output format
    """

    def __init__(self, jar_path: str):
        """
        Initialize JAR inspector.

        Args:
            jar_path: Path to JAR file

        Raises:
            FileNotFoundError: If JAR file doesn't exist
            zipfile.BadZipFile: If file is not a valid ZIP/JAR
        """
        self.jar_path = Path(jar_path)
        if not self.jar_path.exists():
            raise FileNotFoundError(f"JAR file not found: {jar_path}")

        self.jar = zipfile.ZipFile(str(self.jar_path), 'r')
        self.manifest = self._parse_manifest()

    def _parse_manifest(self) -> Dict[str, str]:
        """
        Parse META-INF/MANIFEST.MF file.

        Returns:
            Dictionary of manifest attributes
        """
        try:
            manifest_data = self.jar.read('META-INF/MANIFEST.MF').decode('utf-8', errors='ignore')
            manifest = {}

            # Parse manifest entries (key: value format)
            for line in manifest_data.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    manifest[key.strip()] = value.strip()

            return manifest
        except KeyError:
            # No manifest file
            return {}
        except Exception as e:
            print(f"Warning: Could not parse manifest: {e}", file=sys.stderr)
            return {}

    def list_classes(self, limit: Optional[int] = None) -> List[str]:
        """
        List all .class files in the JAR.

        Args:
            limit: Maximum number of classes to return (None for all)

        Returns:
            List of class file paths
        """
        classes = [f for f in self.jar.namelist() if f.endswith('.class')]
        return classes[:limit] if limit else classes

    def get_packages(self) -> Set[str]:
        """
        Extract unique package names from class files.

        Returns:
            Set of package names
        """
        packages = set()
        for class_file in self.list_classes():
            # Remove .class and convert path to package name
            package = class_file.replace('.class', '').replace('/', '.')
            # Get package (everything before last dot)
            if '.' in package:
                packages.add('.'.join(package.split('.')[:-1]))
        return packages

    def find_main_classes(self) -> List[str]:
        """
        Find potential entry point classes.

        Returns:
            List of classes that might be entry points
        """
        main_classes = []

        # Check manifest
        if 'Main-Class' in self.manifest:
            main_classes.append(self.manifest['Main-Class'])

        # Look for classes with 'Main' in the name
        for class_file in self.list_classes():
            if 'Main' in class_file or 'Application' in class_file:
                class_name = class_file.replace('.class', '').replace('/', '.')
                main_classes.append(class_name)

        return main_classes

    def list_resources(self) -> Dict[str, List[str]]:
        """
        List non-class resources in the JAR.

        Returns:
            Dictionary mapping resource types to file lists
        """
        resources = defaultdict(list)

        for file_path in self.jar.namelist():
            if file_path.endswith('.class'):
                continue

            # Categorize by extension
            if file_path.endswith(('.xml', '.yml', '.yaml', '.properties', '.json')):
                resources['config'].append(file_path)
            elif file_path.endswith(('.txt', '.md', '.rst')):
                resources['docs'].append(file_path)
            elif file_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                resources['images'].append(file_path)
            elif file_path.endswith(('.sql', '.ddl')):
                resources['sql'].append(file_path)
            else:
                resources['other'].append(file_path)

        return dict(resources)

    def analyze_dependencies(self) -> List[str]:
        """
        Extract dependency information from manifest.

        Returns:
            List of dependency JARs (if Class-Path is specified)
        """
        class_path = self.manifest.get('Class-Path', '')
        if not class_path:
            return []

        # Parse space-separated JAR files
        return [dep.strip() for dep in class_path.split() if dep.strip()]

    def find_api_patterns(self) -> Dict[str, List[str]]:
        """
        Find common API-related patterns in class names.

        Returns:
            Dictionary mapping pattern types to matching classes
        """
        patterns = {
            'controllers': [],
            'services': [],
            'repositories': [],
            'entities': [],
            'dtos': [],
            'endpoints': []
        }

        for class_file in self.list_classes():
            class_lower = class_file.lower()

            if 'controller' in class_lower:
                patterns['controllers'].append(class_file)
            elif 'service' in class_lower:
                patterns['services'].append(class_file)
            elif 'repository' in class_lower or 'dao' in class_lower:
                patterns['repositories'].append(class_file)
            elif 'entity' in class_lower or 'model' in class_lower:
                patterns['entities'].append(class_file)
            elif 'dto' in class_lower or 'request' in class_lower or 'response' in class_lower:
                patterns['dtos'].append(class_file)
            elif 'endpoint' in class_lower or 'resource' in class_lower:
                patterns['endpoints'].append(class_file)

        # Remove empty categories
        return {k: v for k, v in patterns.items() if v}

    def get_summary(self, full: bool = False) -> Dict:
        """
        Generate comprehensive JAR analysis summary.

        Args:
            full: Include full class listing (can be large)

        Returns:
            Dictionary with all analysis results
        """
        classes = self.list_classes()

        summary = {
            'file': str(self.jar_path),
            'size_bytes': self.jar_path.stat().st_size,
            'manifest': self.manifest,
            'statistics': {
                'total_classes': len(classes),
                'total_files': len(self.jar.namelist()),
                'packages': len(self.get_packages())
            },
            'entry_points': self.find_main_classes(),
            'dependencies': self.analyze_dependencies(),
            'api_patterns': self.find_api_patterns(),
            'resources': self.list_resources()
        }

        if full:
            summary['all_classes'] = classes
            summary['all_packages'] = sorted(self.get_packages())
        else:
            # Include sample classes (first 50)
            summary['sample_classes'] = classes[:50]
            summary['sample_packages'] = sorted(list(self.get_packages())[:20])

        return summary

    def close(self):
        """Close the JAR file."""
        if hasattr(self, 'jar'):
            self.jar.close()


def format_text(summary: Dict) -> str:
    """
    Format summary as human-readable text.

    Args:
        summary: Analysis results dictionary

    Returns:
        Formatted text string
    """
    output = []
    output.append(f"JAR Analysis: {summary['file']}")
    output.append(f"Size: {summary['size_bytes']:,} bytes")
    output.append("")

    # Statistics
    stats = summary['statistics']
    output.append("Statistics:")
    output.append(f"  Classes: {stats['total_classes']}")
    output.append(f"  Total Files: {stats['total_files']}")
    output.append(f"  Packages: {stats['packages']}")
    output.append("")

    # Entry points
    if summary['entry_points']:
        output.append("Entry Points:")
        for entry in summary['entry_points']:
            output.append(f"  - {entry}")
        output.append("")

    # Dependencies
    if summary['dependencies']:
        output.append("Dependencies:")
        for dep in summary['dependencies']:
            output.append(f"  - {dep}")
        output.append("")

    # API patterns
    if summary['api_patterns']:
        output.append("API Patterns Found:")
        for pattern, classes in summary['api_patterns'].items():
            output.append(f"  {pattern}: {len(classes)} classes")
        output.append("")

    return '\n'.join(output)


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Analyze JAR files and extract structured information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  %(prog)s application.jar

  # Full analysis with all classes
  %(prog)s application.jar --full

  # Text output format
  %(prog)s application.jar --output text

  # Pipe to jq for filtering
  %(prog)s application.jar | jq '.api_patterns'
        """
    )

    parser.add_argument('jar_file', help='Path to JAR file')
    parser.add_argument('--full', action='store_true',
                        help='Include full class and package listings')
    parser.add_argument('--output', choices=['json', 'text'], default='json',
                        help='Output format (default: json)')

    args = parser.parse_args()

    try:
        inspector = JARInspector(args.jar_file)
        summary = inspector.get_summary(full=args.full)

        if args.output == 'json':
            print(json.dumps(summary, indent=2))
        else:
            print(format_text(summary))

        inspector.close()
        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except zipfile.BadZipFile:
        print(f"Error: {args.jar_file} is not a valid JAR/ZIP file", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
