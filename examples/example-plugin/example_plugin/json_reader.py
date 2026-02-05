"""
Example JSON Reader Plugin for SeaSenseLib.

This reader demonstrates how to create a custom reader plugin that extends
SeaSenseLib with support for reading oceanographic data from JSON files.

The modern reader design pattern includes:
1. Call _validate_file() in __init__ for fail-fast validation
2. Implement _load_data() method that returns xr.Dataset (called lazily by data property)
3. Implement _get_valid_extensions() class method for extension validation

IMPORTANT: Do NOT call _load_data() in __init__! The base class data property 
handles lazy loading automatically.
"""

from pathlib import Path
import xarray as xr
from seasenselib.readers.base import AbstractReader


class JsonReader(AbstractReader):
    """
    Reader for oceanographic data in JSON format.
    
    This is an example plugin that reads a simple JSON structure:
    
    {
        "time": ["2024-01-01T00:00:00", ...],
        "temperature": [15.2, 15.4, ...],
        "salinity": [35.1, 35.2, ...],
        "metadata": {
            "instrument": "...",
            "location": "..."
        }
    }
    
    This reader follows the modern reader design pattern:
    - Uses _validate_file() for fail-fast validation
    - Implements _load_data() for data loading
    - Implements _get_valid_extensions() for extension checking
    """

    def __init__(self, input_file: str, **kwargs):
        """
        Initialize the JSON reader.
        
        Parameters:
        -----------
        input_file : str
            Path to the JSON data file
        **kwargs
            Additional base class parameters (mapping, perform_default_postprocessing, etc.)
        """
        super().__init__(input_file, **kwargs)
        self._validate_file()
        # Data is loaded lazily via the data property - no _load_data() call here!

    @classmethod
    def _get_valid_extensions(cls) -> tuple[str, ...]:
        """Return valid file extensions for JSON files."""
        return ('.json',)

    @classmethod
    def format_key(cls) -> str:
        """Return the unique format identifier."""
        return "example-json"

    @classmethod
    def format_name(cls) -> str:
        """Return the human-readable format name."""
        return "Example JSON Format"

    @classmethod
    def file_extension(cls) -> str:
        """Return the file extension for this format."""
        return ".json"

    def _load_data(self) -> xr.Dataset:
        """
        Read JSON data and return as xarray Dataset.
        
        Returns:
        --------
        xr.Dataset
            Dataset containing the oceanographic data
            
        Raises:
        -------
        ValueError
            If the JSON structure is invalid
        """

        # Lazy imports
        import json
        from datetime import datetime
        import pandas as pd
        import numpy as np

        # Read JSON file
        with open(self.input_file, 'r') as f:
            data = json.load(f)

        # Validate structure
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")

        # Extract time coordinate
        if 'time' not in data:
            raise ValueError("JSON must contain 'time' field")

        times = pd.to_datetime(data['time'])

        # Extract data variables
        data_vars = {}
        self._json_metadata = data.pop('metadata', {})

        for key, values in data.items():
            if key == 'time':
                continue

            if not isinstance(values, list):
                continue

            # Convert to numpy array
            arr = np.array(values)

            # Create DataArray
            data_vars[key] = xr.DataArray(
                arr,
                coords={'time': times},
                dims=['time']
            )

        # Create Dataset
        ds = xr.Dataset(data_vars)

        # Add global attributes
        ds.attrs['source_file'] = str(self.input_file)
        ds.attrs['reader'] = self.format_name()
        ds.attrs['reader_version'] = '0.1.0'
        ds.attrs['date_created'] = datetime.now().isoformat()

        # Add metadata from JSON
        for key, value in self._json_metadata.items():
            ds.attrs[key] = value

        # Add time coordinate attributes
        ds['time'].attrs['standard_name'] = 'time'
        ds['time'].attrs['long_name'] = 'Time'
        ds['time'].attrs['axis'] = 'T'

        # Perform default post-processing
        ds = self._perform_default_postprocessing(ds)

        return ds
