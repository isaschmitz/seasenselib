"""
Information commands (list, formats).
"""

import argparse
import csv
import json
from io import StringIO
from .base import BaseCommand, CommandResult


class ListCommand(BaseCommand):
    """Handle listing of readers, writers, and plotters with minimal dependencies."""

    def execute(self, args: argparse.Namespace) -> CommandResult:
        """Execute list command."""
        try:
            # Use autodiscovery to get format information
            # pylint: disable=C0415
            from ...core.autodiscovery import ReaderDiscovery, WriterDiscovery, PlotterDiscovery

            resource_type = args.resource_type
            all_data = []

            # Collect data based on resource type
            if resource_type in ['all', 'readers']:
                discovery = ReaderDiscovery()
                readers = self._convert_format_info(discovery.get_format_info(), 'reader')
                all_data.extend(readers)

            if resource_type in ['all', 'writers']:
                discovery = WriterDiscovery()
                writers = self._convert_format_info(discovery.get_format_info(), 'writer')
                all_data.extend(writers)

            if resource_type in ['all', 'plotters']:
                discovery = PlotterDiscovery()
                plotters = self._convert_format_info(discovery.get_format_info(), 'plotter')
                all_data.extend(plotters)

            # Apply filtering if specified
            if args.filter:
                filter_term = args.filter.lower()
                all_data = [
                    item for item in all_data
                    if filter_term in item['name'].lower() or 
                       filter_term in item.get('extension', '').lower() or
                       filter_term in item['key'].lower() or
                       filter_term in item['type'].lower()
                ]

            # Sort data
            sort_key = args.sort
            if sort_key == 'name':
                all_data.sort(key=lambda x: x['name'].lower(), reverse=args.reverse)
            elif sort_key == 'key':
                all_data.sort(key=lambda x: x['key'].lower(), reverse=args.reverse)
            elif sort_key == 'extension':
                all_data.sort(key=lambda x: x.get('extension', '').lower(), reverse=args.reverse)
            elif sort_key == 'type':
                all_data.sort(key=lambda x: x['type'].lower(), reverse=args.reverse)

            # Output based on selected format
            self._output_list(all_data, args)

            return CommandResult(success=True, message="List displayed successfully")

        except Exception as e:
            return CommandResult(success=False, message=str(e))

    def _convert_format_info(self, format_info_list, resource_type):
        """Convert format info to unified structure with type."""
        result = []
        for format_info in format_info_list:
            item = {
                'name': format_info.get('name', 'Unknown'),
                'key': format_info['key'],
                'extension': format_info.get('extension') or '',
                'class': format_info['class_name'],
                'type': resource_type,
                'is_plugin': format_info.get('is_plugin', False)
            }
            result.append(item)
        return result

    def _output_list(self, data, args):
        """Output list in the requested format."""
        output_format = args.output

        if output_format == 'json':
            print(json.dumps(data, indent=2))
        elif output_format == 'yaml':
            try:
                # pylint: disable=C0415
                import yaml
                print(yaml.dump(data, default_flow_style=False))
            except ImportError:
                print("Error: PyYAML not installed. Install with: pip install PyYAML")
                print("Falling back to JSON format:")
                print(json.dumps(data, indent=2))
        elif output_format == 'csv':
            self._output_csv(data, args)
        else:  # table format (default)
            self._output_table(data, args)

    def _output_csv(self, data, args):
        """Output data as CSV."""
        output = StringIO()
        fieldnames = ['name', 'key', 'type', 'extension']
        if args.verbose:
            fieldnames.extend(['class', 'is_plugin'])

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        if not args.no_header:
            writer.writeheader()

        for item in data:
            row = {k: item.get(k, '') for k in fieldnames}
            writer.writerow(row)

        print(output.getvalue().rstrip())

    def _output_table(self, data, args):
        """Output data as a formatted table."""
        if not data:
            print("No resources found matching the criteria.")
            return

        # Determine if we're showing a single resource type
        resource_type = args.resource_type
        single_type = resource_type in ['readers', 'writers', 'plotters']
        
        # Determine columns to show
        columns = [
            ('Name', 'name'),
            ('Key', 'key'),
        ]
        
        # Only show Type column if showing multiple types (all)
        if not single_type:
            columns.append(('Type', 'type'))
        
        # Only show Extension column for readers/writers (not for plotters)
        if resource_type != 'plotters':
            # Check if any item has an extension
            has_extensions = any(item.get('extension') for item in data)
            if has_extensions:
                columns.append(('Extension', 'extension'))
        
        # Add Plugin column
        columns.append(('Plugin', 'is_plugin'))
        
        if args.verbose:
            columns.append(('Class', 'class'))

        # Calculate column widths
        col_widths = []
        for header, field in columns:
            max_width = len(header)
            for item in data:
                value = str(item.get(field, ''))
                # Format plugin column as Yes/No
                if field == 'is_plugin':
                    value = 'Yes' if item.get('is_plugin', False) else 'No'
                max_width = max(max_width, len(value))
            col_widths.append(max_width + 2)  # Add padding

        # Create table border
        border = "+" + "+".join("-" * width for width in col_widths) + "+"

        # Print table
        if not args.no_header:
            print(border)
            header_row = "|"
            for i, (header, _) in enumerate(columns):
                header_row += f" {header:<{col_widths[i]-2}} |"
            print(header_row)
            print(border)

        for item in data:
            row = "|"
            for i, (_, field) in enumerate(columns):
                value = str(item.get(field, ''))
                # Format plugin column as Yes/No
                if field == 'is_plugin':
                    value = 'Yes' if item.get('is_plugin', False) else 'No'
                row += f" {value:<{col_widths[i]-2}} |"
            print(row)

        if not args.no_header:
            print(border)

        # Show summary
        if not args.no_header:
            total = len(data)
            plugins = sum(1 for item in data if item.get('is_plugin', False))
            print(f"\nTotal: {total} resource(s)", end='')
            if plugins > 0:
                print(f" ({plugins} plugin(s))")
            else:
                print()
            if args.filter:
                print(f"Filtered by: '{args.filter}'")
            
            # Show usage hint if showing all resources (no specific type selected)
            if args.resource_type == 'all' and not args.filter:
                print("\nTip: Use 'seasenselib list readers', 'list writers', or 'list plotters'")
                print("     to show only specific resource types.")
                print("     Use --help for more options (filtering, sorting, output formats).")


class FormatsCommand(BaseCommand):
    """
    Legacy formats command - redirects to ListCommand with 'readers' resource type.
    Maintained for backward compatibility.
    """

    def execute(self, args: argparse.Namespace) -> CommandResult:
        """
        Execute formats command by delegating to ListCommand.
        
        This maintains backward compatibility by treating 'formats' as 
        an alias for 'list readers'.
        """
        # Create a modified args namespace that forces resource_type to 'readers'
        # This ensures 'formats' only shows readers (original behavior)
        list_args = argparse.Namespace(**vars(args))
        list_args.resource_type = 'readers'
        
        # Delegate to ListCommand
        list_command = ListCommand(self.io)
        return list_command.execute(list_args)
