"""
Module for reading CTD data from CSV files into xarray Datasets.
"""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime
import csv
import seasenselib.parameters as params
from .base import AbstractReader


class CsvReader(AbstractReader):
    """ Reads CTD data from a CSV file into a xarray Dataset.

    This class reads CTD data from a CSV file, processes the data into a dictionary of columns,
    and organizes it into an xarray Dataset. It handles the conversion of timestamps to 
    datetime objects and assigns metadata according to CF conventions.

    Attributes
    ----------
    data : xr.Dataset
        The xarray Dataset containing the sensor data.
    input_file : str
        The path to the input CSV file containing the CTD data.
    mapping : dict, optional
        A dictionary mapping names used in the input file to standard names.

    Methods
    -------
    __init__(input_file: str, mapping: dict | None = None)
        Initializes the CsvReader with the input file and optional mapping.
    __read()
        Reads the CSV file and processes the data into an xarray Dataset.
    
    Properties
    ----------
    data : xr.Dataset (read-only)
        Returns the xarray Dataset containing the sensor data.
        For backward compatibility, get_data() method is also available but deprecated.
    
    get_file_type()
        Returns the type of the file being read, which is 'CSV'.
    get_file_extension()
        Returns the file extension for this reader, which is '.csv'.
    """

    def __init__(self, input_file: str,
                 mapping: dict | None = None,
                 **kwargs):
        """Initialize CsvReader.
        
        Parameters
        ----------
        input_file : str
            Path to the CSV file.
        mapping : dict, optional
            Variable name mapping dictionary.
        **kwargs
            Additional base class parameters:
            
            - input_header_file : str | None
                Path to separate header file (if applicable).
            - perform_default_postprocessing : bool, default=True
                Whether to perform default post-processing.
            - rename_variables : bool, default=True
                Whether to rename variables to standard names.
            - assign_metadata : bool, default=True
                Whether to assign CF-compliant metadata.
            - sort_variables : bool, default=True
                Whether to sort variables alphabetically.
        """
        super().__init__(input_file, mapping, **kwargs)
        self.__read()

    def __read(self):
        # Read the CSV into a dictionary of columns
        with open(self.input_file, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Initialize a defaultdict of lists
            data = defaultdict(list)
            for row in reader:
                for key, value in row.items():
                    # Append the value from the row to the right list in data
                    data[key].append(value)

            # Convert defaultdict to dict
            data = dict(data)

            # Validation
            super()._validate_necessary_parameters(data, None, None, 'CSV file')

            # Convert 'time' values to datetime objects
            data[params.TIME] = [
                datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f') \
                    for timestamp in data[params.TIME]
            ]

            # Convert all other columns to floats
            for key in data.keys():
                if key != params.TIME and key in params.default_mappings: 
                    data[key] = [float(value) for value in data[key]]

            # Create xarray Dataset
            ds = self._get_xarray_dataset_template( 
                data[params.TIME],data[params.DEPTH],
                data[params.LATITUDE][0], data[params.LONGITUDE][0]
            )

            # Assign parameter values and meta information for each parameter to xarray Dataset
            for key in data.keys():
                super()._assign_data_for_key_to_xarray_dataset(ds, key, data[key])
                super()._assign_metadata_for_key_to_xarray_dataset( ds, key )
    
            # Store processed data
            self._data = ds

    @classmethod
    def format_key(cls) -> str:
        return 'csv'
    
    @classmethod
    def format_name(cls) -> str:
        return 'CSV'

    @classmethod
    def file_extension(cls) -> str | None:
        return '.csv'
