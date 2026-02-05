"""
Module for reading RCM data from MATLAB .mat files.
"""

from __future__ import annotations
import pandas as pd
import xarray as xr
from seasenselib.readers.base import AbstractReader

class RcmMatlabReader(AbstractReader):
    """Reader which converts RCM data stored in MATLAB .mat files into xarray dataset."""

    def __init__(self, input_file: str,
                 mapping: dict | None = None,
                 **kwargs):
        """Initialize RcmMatlabReader.
        
        Parameters
        ----------
        input_file : str
            Path to the MAT file.
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
        self._validate_file()

    @classmethod
    def _get_valid_extensions(cls) -> tuple[str, ...] | None:
        """Return valid file extensions for MATLAB files."""
        return ('.mat',)

    def _parse_data(self, mat_file_path):
        import scipy.io

        # read adcp file 
        data = scipy.io.loadmat(mat_file_path)

        #prepare for alteration
        def mat_to_dict(data):
            return {key: data[key].flatten()
                    if hasattr(data[key], 'flatten')
                    else data[key]
                    for key in data.keys()
            }
        data = mat_to_dict(data)

        # convert julian time to datetime
        data['time'] = pd.to_datetime(data['t'] - 719529, unit='D')
        
        # remove original julian time 
        data.pop('t')

        #create pandas dataframe 
        df = pd.DataFrame(dict([(key, pd.Series(value)) for key, value in data.items()]))

        # set time as index
        df.set_index('time', inplace=True)

        return df

    def _create_xarray_dataset(self, df):
        """create xarray dataset from pandas dataframe"""

        ds = xr.Dataset.from_dataframe(df)

        # rename variables after cf convention
        ds = ds.rename_vars({
            'u': 'east_velocity', 
            'v': 'north_velocity', 
            'temp': 'temperature', 
            'cond': 'conductivity', 
            'pres': 'pressure', 
            'vdir': 'vdir', 
            'vmag': 'vmag'
        })

        #add metadata for cf compliance
        ds["east_velocity"].attrs = {
            "units": "m/s", 
            "long_name": "Eastward velocity", 
            "standard_name": "eastward_sea_water_velocity"
        }
        ds["north_velocity"].attrs = {
            "units": "m/s", 
            "long_name": "Northward velocity", 
            "standard_name": "northward_sea_water_velocity"
        }
        ds["temperature"].attrs = {
            "units": "°C", 
            "long_name": "Temperature", 
            "standard_name": "sea_water_temperature"
        }
        ds['conductivity'].attrs = {
            "units": "S/m", 
            "long_name": "Conductivity", 
            "standard_name": "sea_water_conductivity"
        }
        ds['pressure'].attrs = {
            "units": "dbar", 
            "long_name": "Pressure", 
            "standard_name": "sea_water_pressure"
        }

        ds.attrs["Conventions"] = "CF-1.8"
        ds.attrs["title"] = "RCM Data"
        ds.attrs["source"] = "Recording Current Meter - Aanderaa"

        for key in (list(ds.data_vars.keys()) + list(ds.coords.keys())):
            super()._assign_metadata_for_key_to_xarray_dataset( ds, key)
        return ds

    def _load_data(self) -> xr.Dataset:
        """Load data from the MATLAB file and return an xarray Dataset."""
        data = self._parse_data(self.input_file)
        return self._create_xarray_dataset(data)

    def _extract_metadata(self) -> None:
        """Extract RCM-specific metadata."""
        super()._extract_metadata()
        if self._data is not None:
            self._metadata_cache['dimensions'] = dict(self._data.dims)
            self._metadata_cache['variables'] = list(self._data.data_vars)
            self._metadata_cache['coordinates'] = list(self._data.coords)

    @classmethod
    def format_key(cls) -> str:
        return 'rcm-matlab'

    @classmethod
    def format_name(cls) -> str:
        return 'RCM Matlab'

    @classmethod
    def file_extension(cls) -> str | None:
        return None
