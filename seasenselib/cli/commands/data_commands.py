"""
Data processing commands (convert, show, subset, calc).
"""

import argparse
from ...core.exceptions import ValidationError
from .base import BaseCommand, CommandResult


class ConvertCommand(BaseCommand):
    """Handle file conversion with lazy loading."""

    def execute(self, args: argparse.Namespace) -> CommandResult:
        """Execute convert command."""
        try:
            # Validate parameter mapping if provided
            if args.mapping:
                import seasenselib.parameters as params
                allowed_parameters = params.allowed_parameters()

                for mapping in args.mapping:
                    if '=' not in mapping:
                        raise ValidationError(
                            f"Invalid mapping format: {mapping}. Use 'name=value'")

                    key, value = mapping.split('=', 1)
                    if key not in allowed_parameters:
                        raise ValidationError(
                            f"Unknown parameter name: {key}. "
                            f"Allowed parameters are: {', '.join(allowed_parameters)}"
                        )

            # Read data
            data = self.io.read_data(args.input, args.input_format, args.header_input, sanitize_input=not getattr(args, "no_sanitize", False), fix_missing_coords=not getattr(args, "no_fix_coords", False))

            if not data:
                raise ValidationError('No data found in file.')

            # Write data
            self.io.write_data(data, args.output, args.output_format)

            return CommandResult(success=True, 
                    message=f"Successfully converted {args.input} to {args.output}")

        except Exception as e:
            return CommandResult(success=False, message=str(e))


class ShowCommand(BaseCommand):
    """Handle data inspection with lazy loading."""

    def execute(self, args: argparse.Namespace) -> CommandResult:
        """Execute show command."""
        try:
            # Read data
            data = self.io.read_data(args.input, args.input_format, args.header_input, sanitize_input=not getattr(args, "no_sanitize", False), fix_missing_coords=not getattr(args, "no_fix_coords", False))

            if not data:
                raise ValidationError('No data found in file.')

            # Display based on schema
            if args.schema == 'summary':
                print(data)
            elif args.schema == 'info':
                data.info()
            elif args.schema == 'example':
                df = data.to_dataframe()
                print(df.head())

            return CommandResult(success=True, message="Data displayed successfully")

        except Exception as e:
            print(f"{e}")
            return CommandResult(success=False, message=str(e))


class SubsetCommand(BaseCommand):
    """Handle data subsetting with lazy loading."""

    def execute(self, args: argparse.Namespace) -> CommandResult:
        """Execute subset command."""
        try:
            # Lazy import processors
            from ...processors import SubsetProcessor

            # Read data
            data = self.io.read_data(args.input, args.input_format, args.header_input, sanitize_input=not getattr(args, "no_sanitize", False), fix_missing_coords=not getattr(args, "no_fix_coords", False))

            if not data:
                raise ValidationError('No data found in file.')

            # Create subsetter
            subsetter = SubsetProcessor(data)

            # Apply subsetting parameters
            if args.sample_min:
                subsetter.set_sample_min(args.sample_min)
            if args.sample_max:
                subsetter.set_sample_max(args.sample_max)
            if args.time_min:
                subsetter.set_time_min(args.time_min)
            if args.time_max:
                subsetter.set_time_max(args.time_max)
            if args.parameter:
                subsetter.set_parameter_name(args.parameter)
            if args.value_min:
                subsetter.set_parameter_value_min(args.value_min)
            if args.value_max:
                subsetter.set_parameter_value_max(args.value_max)

            # Get subset
            subset = subsetter.get_subset()

            # Output or write
            if args.output:
                self.io.write_data(subset, args.output, args.output_format)
                return CommandResult(success=True, message=f"Subset written to {args.output}")
            else:
                print(subset)
                return CommandResult(success=True, message="Subset displayed successfully")

        except Exception as e:
            return CommandResult(success=False, message=str(e))


class CalcCommand(BaseCommand):
    """Handle calculations with lazy loading."""
  
    def execute(self, args: argparse.Namespace) -> CommandResult:
        """Execute calc command."""
        try:
            # Lazy import processors
            from ...processors import ResampleProcessor, StatisticsProcessor
            
            # Read data
            data = self.io.read_data(args.input, args.input_format, args.header_input, sanitize_input=not getattr(args, "no_sanitize", False), fix_missing_coords=not getattr(args, "no_fix_coords", False))

            if not data:
                raise ValidationError('No data found in file.')

            # Handle resampling if requested
            if args.resample:
                if not args.time_interval:
                    raise ValidationError("Time interval is required when resampling")

                resampler = ResampleProcessor(data)
                data = resampler.resample(args.time_interval)
                
                # Process resampled data
                # pylint: disable=C0415
                import re
                import pandas as pd

                # Format datetime output based on time interval
                datetime_format_pattern = "%Y-%m-%d %H:%M:%S"
                if re.match(r"^[0-9\.]*M$", args.time_interval):
                    datetime_format_pattern = '%Y-%m'
                elif re.match(r"^[0-9\.]*Y$", args.time_interval):
                    datetime_format_pattern = '%Y'
                elif re.match(r"^[0-9\.]*D$", args.time_interval):
                    datetime_format_pattern = '%Y-%m-%d'
                elif re.match(r"^[0-9\.]*H$", args.time_interval):
                    datetime_format_pattern = '%Y-%m-%d %H:%M'
                elif re.match(r"^[0-9\.]*min$", args.time_interval):
                    datetime_format_pattern = '%Y-%m-%d %H:%M'

                # Process each time period
                for time_period, group in data:
                    result = self._run_calculation(
                        group, args.method, args.parameter, StatisticsProcessor)
                    dt_datetime = pd.to_datetime(time_period)
                    datetime_string = dt_datetime.strftime(datetime_format_pattern)
                    print(f"{datetime_string}: {result}")
            else:
                # Single calculation
                result = self._run_calculation(data, args.method, args.parameter, StatisticsProcessor)
                print(result)
            
            return CommandResult(success=True, message="Calculation completed successfully")
            
        except Exception as e:
            return CommandResult(success=False, message=str(e))
    
    def _run_calculation(self, data, method, parameter, StatisticsProcessor):
        """Run the specified calculation on the data."""
        calc = StatisticsProcessor(data, parameter)

        if method == 'max':
            return calc.max()
        elif method == 'min':
            return calc.min()
        elif method == 'mean':
            return calc.mean()
        elif method == 'median':
            return calc.median()
        elif method in ['std', 'standard_deviation']:
            return calc.std()
        elif method in ['var', 'variance']:
            return calc.var()
        else:
            raise ValidationError(f"Unknown calculation method: {method}")
