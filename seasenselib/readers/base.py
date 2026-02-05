"""
Module for abstract base class for reading sensor data from various file formats.

This module defines the `AbstractReader` class, which serves as a base class for
all reader implementations in the SeaSenseLib package. Concrete reader classes should
inherit from this class and implement the methods for reading and processing data
from specific file formats (e.g., CNV, TOB, NetCDF, CSV, RBR, Nortek).
"""

from __future__ import annotations
import os
import platform
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, Optional
import re
import warnings
import xarray as xr
import gsw
import seasenselib.parameters as params

MODULE_NAME = 'seasenselib'


class AbstractReader(ABC):
    """ Abstract super class for reading sensor data. 

    Must be subclassed to implement specific file format readers.
    
    This class supports the context manager protocol for automatic resource cleanup:
    
    >>> with SomeReader('data.cnv') as reader:
    ...     ds = reader.data
    ...     # process data
    >>> # data automatically released
    
    Attributes
    ---------- 
    input_file : str (read-only property)
        The path to the input file containing sensor data.
    input_header_file : str | None (read-only property)
        The path to separate header file, or None if not applicable.
    mapping : dict (read-only property)
        A dictionary mapping names used in the input file to standard names.
    data : xr.Dataset | None (read-only property)
        The processed sensor data as a xarray Dataset, or None if not yet processed.
        This is a read-only property. Use :meth:`get_data()` for backward compatibility.
    is_loaded : bool (read-only property)
        Whether data has been loaded from the file.
    metadata : dict (read-only property)
        File metadata (size, modification time, etc.) without loading data.
    perform_default_postprocessing : bool
        Whether to perform default post-processing on the data.
    rename_variables : bool
        Whether to rename xarray variables to standard names.
    assign_metadata : bool
        Whether to assign metadata to xarray variables.
    sort_variables : bool
        Whether to sort xarray variables by name.
    
    Methods
    -------
    __init__(input_file: str, mapping: dict | None = None, 
                    perform_default_postprocessing: bool = True,
                    rename_variables: bool = True, assign_metadata: bool = True, 
                    sort_variables: bool = True)
            Initializes the reader with the input file and optional mapping.
    __enter__() -> AbstractReader
            Context manager entry point.
    __exit__(exc_type, exc_val, exc_tb) -> None
            Context manager exit - releases data from memory.
    reload() -> AbstractReader
            Force reload data from file, clearing any cached data.
    _perform_default_postprocessing(ds: xr.Dataset) -> xr.Dataset
            Performs default post-processing on the xarray Dataset.
    get_data() -> xr.Dataset | None
            Returns the processed data as an xarray Dataset (deprecated, use `data` property).
    """

    def __init__(self, input_file: str, mapping: dict | None = None,
                 input_header_file: str | None = None,
                 perform_default_postprocessing: bool = True, rename_variables: bool = True,
                 assign_metadata: bool = True, sort_variables: bool = True,
                 **kwargs):
        """Initializes the AbstractReader with the input file and optional mapping.

        This constructor sets the input file, initializes the data attribute to None,
        and sets the mapping for variable names. It also allows for configuration of
        default post-processing, renaming of variables, assignment of metadata, and 
        sorting of variables.

        Parameters
        ---------- 
        input_file : str
            The path to the input file containing sensor data.
        mapping : dict, optional
            A dictionary mapping names used in the input file to standard names.
        input_header_file : str, optional
            The path to separate header file, or None if not applicable.
        perform_default_postprocessing : bool, optional
            Whether to perform default post-processing on the data. Default is True.
        rename_variables : bool, optional
            Whether to rename xarray variables to standard names. Default is True.
        assign_metadata : bool, optional
            Whether to assign CF metadata to xarray variables. Default is True.
        sort_variables : bool, optional
            Whether to sort xarray variables by name. Default is True.
        **kwargs
            Additional reader-specific parameters. These are accepted but not used
            by the base class, allowing subclasses to define their own parameters
            without modifying the base class signature.
        """

        self._input_file = input_file
        self._input_header_file = input_header_file
        self._data = None
        self._metadata_cache: Dict[str, Any] = {}
        self._mapping = mapping if mapping is not None else {}
        self._config_perform_postprocessing = perform_default_postprocessing
        self._config_rename_variables = rename_variables
        self._config_assign_metadata = assign_metadata
        self._config_sort_variables = sort_variables
        # **kwargs is intentionally not stored - subclasses handle their own parameters

    # =========================================================================
    # File Validation Methods (Override in subclasses for format-specific validation)
    # =========================================================================

    def _validate_file(self) -> None:
        """Validate the input file before reading.
        
        This method performs basic file validation (existence, not empty).
        Subclasses can override to add format-specific validation such as
        checking file extensions or file headers.
        
        Raises
        ------
        FileNotFoundError
            If the file does not exist.
        ValueError
            If the file is not a regular file, is empty, or has an invalid
            extension (only if strict validation is enabled).
            
        Note
        ----
        This method is called automatically by subclasses that implement
        the modern reader pattern. For backward compatibility with existing
        readers that don't call this method, validation failures won't break
        the instantiation process unless explicitly called.
        
        Extension validation behavior depends on `_is_extension_validation_strict()`:
        - True (default): Invalid extension raises ValueError
        - False: Invalid extension logs a warning but continues
        
        Examples
        --------
        >>> class MyReader(AbstractReader):
        ...     def __init__(self, input_file, **kwargs):
        ...         super().__init__(input_file, **kwargs)
        ...         self._validate_file()  # Validate before loading
        ...         self._data = self._load_data()
        """
        path = Path(self._input_file)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {self._input_file}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {self._input_file}")
        
        if path.stat().st_size == 0:
            raise ValueError(f"File is empty: {self._input_file}")
        
        # Check extension if subclass specifies valid extensions
        valid_ext = self._get_valid_extensions()
        if valid_ext is not None:
            if path.suffix.lower() not in valid_ext:
                message = (
                    f"Unexpected file extension '{path.suffix}' for {self.__class__.__name__}. "
                    f"Expected one of: {', '.join(valid_ext)}"
                )
                if self._is_extension_validation_strict():
                    raise ValueError(message)
                else:
                    import logging
                    logging.getLogger(__name__).warning(message)

    @classmethod
    def _get_valid_extensions(cls) -> tuple[str, ...] | None:
        """Return valid file extensions for this reader.
        
        Subclasses should override this method to specify which file extensions
        are valid for their format. Return None to skip extension validation.
        
        Returns
        -------
        tuple[str, ...] | None
            Tuple of valid extensions (e.g., ('.cnv', '.CNV')) or None to skip validation.
            Extensions should include the leading dot and be lowercase.
            
        Examples
        --------
        >>> class MyReader(AbstractReader):
        ...     @classmethod
        ...     def _get_valid_extensions(cls) -> tuple[str, ...]:
        ...         return ('.myformat', '.myf')
        """
        return None  # Default: no extension validation

    @classmethod
    def _is_extension_validation_strict(cls) -> bool:
        """Return whether extension validation should raise an error or just warn.
        
        Override this method in subclasses to control validation behavior:
        - Return True (default): Invalid extension raises ValueError
        - Return False: Invalid extension logs a warning but continues
        
        Typically return False for ASCII/text-based formats that can have
        various extensions (.dat, .txt, .asc, etc.), and True for binary
        or proprietary formats with specific extensions (.rsk, .mat, .cnv).
        
        Returns
        -------
        bool
            True for strict validation (error), False for soft validation (warning).
            
        Examples
        --------
        >>> class AsciiReader(AbstractReader):
        ...     @classmethod
        ...     def _is_extension_validation_strict(cls) -> bool:
        ...         return False  # Warn only for ASCII formats
        """
        return True  # Default: strict validation

    # =========================================================================
    # Data Loading Methods (Override _load_data in subclasses)
    # =========================================================================

    def _load_data(self) -> xr.Dataset:
        """Load data from the input file.
        
        Subclasses SHOULD override this method to implement format-specific
        data loading logic. This method is called by the `data` property
        when lazy loading is enabled, or by `__init__` for eager loading.
        
        The default implementation raises NotImplementedError to indicate
        that subclasses using the legacy pattern (with private `__read()` methods)
        should continue working as before.
        
        Returns
        -------
        xr.Dataset
            The loaded dataset.
            
        Raises
        ------
        NotImplementedError
            If the subclass does not override this method.
            
        Note
        ----
        For backward compatibility, existing readers that use `__read()` 
        methods called from `__init__` will continue to work. New readers
        should implement `_load_data()` and call it from `__init__` or
        let the `data` property handle lazy loading.
        
        Examples
        --------
        >>> class MyReader(AbstractReader):
        ...     def _load_data(self) -> xr.Dataset:
        ...         # Read file and return Dataset
        ...         ds = xr.open_dataset(self.input_file)
        ...         return self._perform_default_postprocessing(ds)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _load_data() method. "
            "See AbstractReader documentation for the expected interface."
        )

    def _extract_metadata(self) -> None:
        """Extract format-specific metadata after loading data.
        
        Subclasses can override this method to populate `_metadata_cache`
        with format-specific metadata such as instrument information,
        data dimensions, or file format version.
        
        This method is called after `_load_data()` when the data property
        is accessed, allowing metadata extraction from the loaded dataset.
        
        The base implementation does nothing. Subclasses should call
        `super()._extract_metadata()` and then add their own metadata.
        
        Examples
        --------
        >>> class MyReader(AbstractReader):
        ...     def _extract_metadata(self) -> None:
        ...         super()._extract_metadata()
        ...         if self._data is not None:
        ...             self._metadata_cache['num_variables'] = len(self._data.data_vars)
        ...             self._metadata_cache['dimensions'] = dict(self._data.dims)
        """
        pass  # Base implementation does nothing

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def input_file(self) -> str:
        """Get the input file path (read-only).
        
        Returns
        -------
        str
            Path to the input data file
        """
        return self._input_file

    @property
    def input_header_file(self) -> str | None:
        """Get the input header file path (read-only).
        
        Returns
        -------
        str | None
            Path to the separate header file, or None if not applicable
        """
        return self._input_header_file

    @property
    def mapping(self) -> dict:
        """Get the variable name mapping (read-only).
        
        Returns
        -------
        dict
            Dictionary mapping custom variable names to standard names
        """
        return self._mapping

    @property
    def is_loaded(self) -> bool:
        """Check if data has been loaded from file.
        
        Returns
        -------
        bool
            True if data has been loaded, False otherwise.
            
        Examples
        --------
        >>> reader = SomeReader('data.cnv')
        >>> print(reader.is_loaded)  # True after __init__ loads data
        """
        return self._data is not None

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get file metadata without loading data.
        
        This property provides access to file-level metadata such as
        file size and modification time without requiring the full
        data to be loaded into memory.
        
        Returns
        -------
        Dict[str, Any]
            Dictionary containing file metadata:
            - file_path: Absolute path to the file
            - file_name: Base name of the file
            - file_size: Size in bytes
            - file_size_human: Human-readable size (e.g., "1.5 MB")
            - modified_time: Last modification timestamp (ISO format)
            - format_key: Reader format key
            - format_name: Reader format name
            
        Additionally, format-specific metadata added by `_extract_metadata()`
        will be included after the data has been loaded.
            
        Examples
        --------
        >>> reader = SomeReader('data.cnv')
        >>> print(f"File size: {reader.metadata['file_size_human']}")
        """
        path = Path(self._input_file)
        stat = path.stat()
        
        # Human-readable file size
        size_bytes = stat.st_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                size_human = f"{size_bytes:.1f} {unit}"
                break
            size_bytes /= 1024
        else:
            size_human = f"{size_bytes:.1f} PB"
        
        # Base metadata (always available)
        result = {
            'file_path': str(path.absolute()),
            'file_name': path.name,
            'file_size': stat.st_size,
            'file_size_human': size_human,
            'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'format_key': self.format_key(),
            'format_name': self.format_name(),
        }
        
        # Include format-specific metadata from cache (populated by _extract_metadata)
        result.update(self._metadata_cache)
        
        return result

    def reload(self) -> 'AbstractReader':
        """Force reload data from file.
        
        Clears any cached data (including metadata) and re-reads from the file.
        This is useful when the underlying file has been modified
        or to free memory temporarily.
        
        Returns
        -------
        AbstractReader
            Returns self for method chaining.
            
        Note
        ----
        After calling reload(), the data will be re-read when the `data`
        property is next accessed (for lazy-loading readers) or you may
        need to create a new reader instance (for eager-loading readers).
        
        Examples
        --------
        >>> reader = SomeReader('data.cnv')
        >>> reader.reload()  # Clear cached data
        >>> ds = reader.data  # Re-read from file (lazy loading)
        """
        self._data = None
        self._metadata_cache = {}
        return self

    def __enter__(self) -> 'AbstractReader':
        """Context manager entry point.
        
        Returns
        -------
        AbstractReader
            Returns self for use in with statement.
            
        Examples
        --------
        >>> with SomeReader('data.cnv') as reader:
        ...     ds = reader.data
        ...     # process data
        >>> # data automatically released
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - releases data from memory.
        
        Parameters
        ----------
        exc_type : type
            Exception type if an exception was raised.
        exc_val : BaseException
            Exception value if an exception was raised.
        exc_tb : TracebackType
            Traceback if an exception was raised.
        """
        self._data = None

    def __repr__(self) -> str:
        """String representation of the reader.
        
        Returns
        -------
        str
            Human-readable string showing class name, file, and load status.
        """
        loaded_str = "loaded" if self.is_loaded else "not loaded"
        return f"{self.__class__.__name__}('{self._input_file}', {loaded_str})"

    def _julian_to_gregorian(self, julian_days, start_date):
        full_days = int(julian_days) - 1  # Julian days start at 1, not 0
        seconds = (julian_days - int(julian_days)) * 24 * 60 * 60
        return start_date + timedelta(days=full_days, seconds=seconds)

    def _elapsed_seconds_since_jan_1970_to_datetime(self, elapsed_seconds):
        base_date = datetime(1970, 1, 1)
        time_delta = timedelta(seconds=elapsed_seconds)
        return base_date + time_delta

    def _elapsed_seconds_since_jan_2000_to_datetime(self, elapsed_seconds):
        base_date = datetime(2000, 1, 1)
        time_delta = timedelta(seconds=elapsed_seconds)
        date_value = base_date + time_delta
        return date_value

    def _elapsed_seconds_since_offset_to_datetime(self, elapsed_seconds, offset_datetime):
        base_date = offset_datetime
        time_delta = timedelta(seconds=elapsed_seconds)
        return base_date + time_delta

    def _validate_necessary_parameters(self, data, longitude, latitude, entity: str):
        if not params.TIME and not params.TIME_J and not params.TIME_Q \
                and not params.TIME_N in data:
            raise ValueError(f"Parameter '{params.TIME}' is missing in {entity}.")
        if not params.PRESSURE in data and not params.DEPTH:
            raise ValueError(f"Parameter '{params.PRESSURE}' is missing in {entity}.")

    def _get_xarray_dataset_template(self, time_array, depth_array, 
                latitude, longitude, depth_name = params.DEPTH):
        coords = dict(
            time = time_array,
            latitude = latitude,
            longitude = longitude,
        )

        # Only add depth coordinate if depth_array is not None
        if depth_array is not None:
            coords[depth_name] = ([params.TIME], depth_array)

        return xr.Dataset(
            data_vars = dict(),
            coords = coords,
            attrs = dict(
                latitude = latitude,
                longitude = longitude,
                CreateTime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                DataType = 'TimeSeries',
            )
        )

    def _assign_data_for_key_to_xarray_dataset(self, ds: xr.Dataset, key:str, data):
        ds[key] = xr.DataArray(data, dims=params.TIME)
        ds[key].attrs = {}

    def _assign_metadata_for_key_to_xarray_dataset(self, ds: xr.Dataset, key: str, 
                    label = None, unit = None):
        if not ds[key].attrs:
            ds[key].attrs = {}
        # Check for numbered standard names (e.g., temperature_1, temperature_2)
        base_key = key
        m = re.match(r"^([a-zA-Z0-9_]+?)(?:_\d{1,2})?$", key)
        if m:
            base_key = m.group(1)
        # Use metadata for base_key if available
        if base_key in params.metadata:
            for attribute, value in params.metadata[base_key].items():
                if attribute not in ds[key].attrs:
                    ds[key].attrs[attribute] = value
        if unit:
            ds[key].attrs['units'] = unit
        if label:
            if unit:
                label = label.replace(f"[{unit}]", '').strip() # Remove unit from label
            ds[key].attrs['long_name'] = label

    def _derive_oceanographic_parameters(self, ds: xr.Dataset) -> xr.Dataset:
        """Derive oceanographic parameters from temperature, pressure, and salinity.
        
        This method calculates derived parameters like density and potential temperature
        using the Gibbs SeaWater (GSW) oceanographic toolbox when temperature, pressure,
        and salinity data are available in the xarray Dataset.
        
        For multiple sensors (e.g., temperature_1, temperature_2), it will use the first
        available sensor (temperature_1) or the base parameter name if only one exists.
        
        Parameters
        ----------
        ds : xr.Dataset
            The xarray Dataset containing the sensor data and to add derived parameters to.
            
        Returns
        -------
        xr.Dataset
            The xarray Dataset with derived parameters added.
        """
        
        # Find the appropriate temperature variable
        temperature_var = None
        if params.TEMPERATURE in ds.data_vars:
            temperature_var = params.TEMPERATURE
        elif f"{params.TEMPERATURE}_1" in ds.data_vars:
            temperature_var = f"{params.TEMPERATURE}_1"
        
        # Find the appropriate salinity variable
        salinity_var = None
        if params.SALINITY in ds.data_vars:
            salinity_var = params.SALINITY
        elif f"{params.SALINITY}_1" in ds.data_vars:
            salinity_var = f"{params.SALINITY}_1"
        
        # Pressure should typically be singular, but check both possibilities
        pressure_var = None
        if params.PRESSURE in ds.data_vars:
            pressure_var = params.PRESSURE
        elif f"{params.PRESSURE}_1" in ds.data_vars:
            pressure_var = f"{params.PRESSURE}_1"
        
        # Check if we have all required parameters for oceanographic calculations
        if temperature_var and salinity_var and pressure_var:
            
            # Derive density using GSW
            ds[params.DENSITY] = ([params.TIME], gsw.density.rho(
                ds[salinity_var].values, 
                ds[temperature_var].values, 
                ds[pressure_var].values))
            
            # Derive potential temperature using GSW
            ds[params.POTENTIAL_TEMPERATURE] = ([params.TIME], gsw.pt0_from_t(
                ds[salinity_var].values, 
                ds[temperature_var].values, 
                ds[pressure_var].values))
            
            if self._config_assign_metadata:
                # Assign metadata for derived parameters
                self._assign_metadata_for_key_to_xarray_dataset(ds, params.DENSITY)
                self._assign_metadata_for_key_to_xarray_dataset(ds, params.POTENTIAL_TEMPERATURE)
                
        return ds

    def _sort_xarray_variables(self, ds: xr.Dataset) -> xr.Dataset:
        """Sorts the variables in an xarray Dataset based on their standard names.

        The sorting is done in a way that ensures that variables with the same base name
        (e.g., temperature_1, temperature_2) are grouped together.

        Parameters
        ----------
        ds : xr.Dataset
            The xarray Dataset to be sorted.

        Returns
        -------
        xr.Dataset
            The xarray Dataset with variables sorted by their names.
        """
        # Sort all variables and coordinates by name
        all_names = sorted(list(ds.data_vars) + list(ds.coords))

        # Create a new Dataset with sorted variables and coordinates
        ds_sorted = ds[all_names]

        # Ensure that the attributes are preserved
        ds_sorted.attrs = ds.attrs.copy()

        return ds_sorted

    def _rename_xarray_parameters(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Rename variables in an xarray.Dataset according to params.default_mappings.
        Handles aliases with or without trailing numbering and ensures unique standard 
        names with numbering. If a standard name only occurs once, it will not have a 
        numbering suffix.
        """

        ds_vars = list(ds.variables)
        rename_dict = {}

        # Build a reverse mapping: alias_lower -> standard_name
        alias_to_standard = {}
        for standard_name, aliases in params.default_mappings.items():
            for alias in aliases:
                alias_to_standard[alias.lower()] = standard_name

        # First, collect all matches: (standard_name, original_var, suffix)
        matches = []
        for var in ds_vars:
            if not isinstance(var, str):
                continue
            var_lower = var.lower()
            matched = False
            for alias_lower, standard_name in alias_to_standard.items():
                # Match alias with optional _<number> at the end
                m = re.match(rf"^{re.escape(alias_lower)}(_?\d{{1,2}})?$", var_lower)
                if m:
                    suffix = m.group(1) or ""
                    matches.append((standard_name, var, suffix))
                    matched = True
                    break
            if not matched:
                continue

        # Group by standard_name
        grouped = defaultdict(list)
        for standard_name, var, suffix in matches:
            grouped[standard_name].append((var, suffix))

        # Assign new names: only add numbering if there are multiple
        for standard_name, vars_with_suffixes in grouped.items():
            if len(vars_with_suffixes) == 1:
                # Only one variable: use plain standard name
                rename_dict[vars_with_suffixes[0][0]] = standard_name
            else:
                # Multiple variables: always add numbering (_1, _2, ...)
                for idx, (var, suffix) in enumerate(vars_with_suffixes, 1):
                    rename_dict[var] = f"{standard_name}_{idx}"

        return ds.rename(rename_dict)

    def _assign_default_global_attributes(self, ds: xr.Dataset) -> xr.Dataset:
        """Assigns default global attributes to the xarray Dataset.

        This method sets the global attributes for the xarray Dataset, including
        the title, institution, source, and other relevant metadata.

        Parameters
        ----------
        ds : xr.Dataset
            The xarray Dataset to which the global attributes will be assigned.
        """

        module_name = MODULE_NAME
        module_version = version(MODULE_NAME)
        module_reader_class = self.__class__.__name__
        python_version = platform.python_version()
        input_file = self._input_file
        input_file_type = self.format_name()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # assemble history entry
        history_entry = (
            f"{timestamp}: created from {input_file_type} file ({input_file}) "
            f"using {module_name} v{module_version} ({module_reader_class} class) "
            f"under Python {python_version}"
        )

        ds.attrs['history'] = history_entry
        ds.attrs['Conventions'] = 'CF-1.8'

        # Information about the processor of the xarray dataset
        ds.attrs['processor_name'] = module_name
        ds.attrs['processor_version'] = module_version
        ds.attrs['processor_reader_class'] = module_reader_class
        ds.attrs['processor_python_version'] = python_version
        ds.attrs['processor_input_filename'] = input_file
        ds.attrs['processor_input_file_type'] = input_file_type

        return ds

    def _perform_default_postprocessing(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Perform default post-processing on the xarray Dataset.
        This includes renaming variables and assigning metadata.

        Parameters
        ----------
        ds : xr.Dataset
            The xarray Dataset to be processed.

        Returns
        -------
        xr.Dataset
            The processed xarray Dataset.
        """

        # Apply custom mapping of variable names if provided
        if self._mapping is not None:
            for key, value in self._mapping.items():
                if value in ds.variables:
                    ds = ds.rename({value: key})

        # Rename variables according to default mappings
        if self._config_rename_variables:
            ds = self._rename_xarray_parameters(ds)

        # Assign metadata for all attributes of the xarray Dataset
        if self._config_assign_metadata:
            for key in (list(ds.data_vars.keys()) + list(ds.coords.keys())):
                self._assign_metadata_for_key_to_xarray_dataset(ds, key)

        # Assign default global attributes
        ds = self._assign_default_global_attributes(ds)

        # Sort variables and coordinates by name
        if self._config_sort_variables:
            ds = self._sort_xarray_variables(ds)

        return ds

    @property
    def data(self) -> xr.Dataset | None:
        """Get the processed sensor data as an xarray Dataset (lazy loading).
        
        This property provides read-only access to the data. The data is loaded
        lazily on first access - subsequent accesses return the cached dataset.
        
        Returns
        -------
        xr.Dataset | None
            The processed sensor data.
            
        Raises
        ------
        NotImplementedError
            If the subclass does not implement `_load_data()`.
        RuntimeError
            If data loading fails.
            
        Examples
        --------
        >>> reader = SomeReader('data.cnv')
        >>> print(reader.is_loaded)  # False - not loaded yet
        >>> ds = reader.data  # Triggers lazy load
        >>> print(reader.is_loaded)  # True - now loaded
        >>> ds2 = reader.data  # Returns cached data
        >>> assert ds is ds2  # Same object
        """
        if self._data is None:
            try:
                self._data = self._load_data()
            except NotImplementedError:
                # Re-raise NotImplementedError with clear message
                raise
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load data from {self._input_file}: {e}"
                ) from e
        return self._data

    def get_data(self) -> xr.Dataset | None:
        """Returns the processed data as an xarray Dataset.
        
        .. deprecated:: 1.5
            Use the :attr:`data` property instead: ``reader.data``
            This method will be removed in version 2.0.
            
        Returns
        -------
        xr.Dataset | None
            The processed sensor data, or None if not yet read.
        """
        import warnings
        warnings.warn(
            "get_data() is deprecated and will be removed in version 2.0. "
            "Use the 'data' property instead: reader.data",
            DeprecationWarning,
            stacklevel=2
        )
        return self.data

    @classmethod
    @abstractmethod
    def format_name(cls) -> str:
        """Get the format name for this reader.

        This property must be implemented by all subclasses.

        Returns:
        --------
        str
            The format (e.g., 'SeaBird CNV', 'Nortek ASCII', 'RBR RSK').

        Raises:
        -------
        NotImplementedError:
            If the subclass does not implement this property.
        """
        raise NotImplementedError("Reader classes must define a format name")

    @classmethod
    @abstractmethod
    def format_key(cls) -> str:
        """Get the format key for this reader.

        This property must be implemented by all subclasses.
        
        Returns:
        --------
        str
            The format key (e.g., 'sbe-cnv', 'nortek-ascii', 'rbr-rsk').

        Raises:
        -------
        NotImplementedError:
            If the subclass does not implement this property.
        """
        raise NotImplementedError("Writer classes must define a format key")

    @classmethod
    @abstractmethod
    def file_extension(cls) -> str | None:
        """Get the file extension for this reader.

        This property must be implemented by all subclasses.
        The extension must be unique over all registered readers.
        If a reader does not specify a unique file extension, just return `None`.

        Returns:
        --------
        str
            The file extension (e.g., '.cnv', '.tob', '.rsk').

        Raises:
        -------
        NotImplementedError:
            If the subclass does not implement this property.
        """
        raise NotImplementedError("Reader classes must define a file extension")
