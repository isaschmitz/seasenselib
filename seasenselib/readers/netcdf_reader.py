"""
Module for reading sensor data from netCDF files into xarray Datasets.
"""

from __future__ import annotations
import xarray as xr
from .base import AbstractReader


class NetCdfReader(AbstractReader):
    """ Reads sensor data from a netCDF file into a xarray Dataset. 

    This class is used to read netCDF files, which are commonly used for storing
    multidimensional scientific data. The provided data is expected to be in a
    netCDF format, and this reader is designed to parse that format correctly.

    Attributes:
    ---------- 
    data : xr.Dataset
        The xarray Dataset containing the sensor data to be read from the netCDF file.
    input_file : str
        The path to the input netCDF file containing the sensor data.
    
    Methods:
    -------
    __init__(input_file):
        Initializes the NetCdfReader with the input file.
    _load_data():
        Reads the netCDF file and processes the data into an xarray Dataset.
    
    Properties
    ----------
    data : xr.Dataset (read-only)
        Returns the xarray Dataset containing the sensor data.
        For backward compatibility, get_data() method is also available but deprecated.
    
    format_name():
        Returns the type of the file being read, which is 'netCDF'.
    file_extension():
        Returns the file extension for this reader, which is '.nc'.
    """

    def __init__(self, input_file: str,
                 mapping: dict | None = None,
                 **kwargs):
        """Initialize NetCdfReader.
        
        Parameters
        ----------
        input_file : str
            The path to the input netCDF file.
        mapping : dict | None, optional
            A mapping dictionary for renaming variables or attributes in the dataset.
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
        self._validate_file()

    @classmethod
    def _get_valid_extensions(cls) -> tuple[str, ...]:
        """Return valid file extensions for netCDF files."""
        return ('.nc', '.nc4', '.netcdf')

    def _load_data(self) -> xr.Dataset:
        """Load the netCDF file and return an xarray Dataset.
        
        Returns
        -------
        xr.Dataset
            The loaded dataset.
        """
        # Read from netCDF file
        ds = xr.open_dataset(self.input_file)

        # Validation
        super()._validate_necessary_parameters(ds, None, None, 'netCDF file')
        
        return ds

    @classmethod
    def format_key(cls) -> str:
        return 'netcdf'

    @classmethod
    def format_name(cls) -> str:
        return 'netCDF'

    @classmethod
    def file_extension(cls) -> str | None:
        return '.nc'
