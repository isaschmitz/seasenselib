"""
Module for reading CTD data from SBE CNV files.
"""

from __future__ import annotations
import re
from datetime import datetime
import pandas as pd
import numpy as np

from seasenselib.readers.base import AbstractReader
import seasenselib.parameters as params


class SbeCnvReader(AbstractReader):
    """ Reads sensor data from a SeaBird CNV file into a xarray Dataset. 

    This class is used to read SeaBird CNV files, which are commonly used for storing
    sensor data. The provided data is expected to be in a CNV format, and this reader
    is designed to parse that format correctly.

    The reader includes automatic fixing capabilities for common issues:
    - File sanitization: Fixes trailing whitespace and malformed lines that cause pycnv errors
    - Coordinate defaults: Uses 45° latitude when missing (common for moored instruments)
    
    These behaviors can be controlled via the sanitize_input and fix_missing_coords parameters.

    Attributes
    ----------
    data : xr.Dataset
        The xarray Dataset containing the sensor data to be read from the CNV file.
    input_file : str
        The path to the input CNV file containing the sensor data.
    mapping : dict
        A mapping dictionary for renaming variables or attributes in the dataset.
    sanitize_input : bool
        Whether to automatically fix file format issues (default: True).
    fix_missing_coords : bool
        Whether to use default values for missing coordinates (default: True).

    Methods
    -------
    __init__(input_file, sanitize_input=True, fix_missing_coords=True, mapping=None, **kwargs):
        Initializes the CnvReader with the input file and configuration options.
    data():
        Returns the xarray Dataset containing the sensor data.
    format_name():
        Returns the format of the file being read, which is 'SBE CNV'.
    file_extension():
        Returns the file extension for this reader, which is '.cnv'.
    
    Examples
    --------
    >>> # Default behavior (auto-fix enabled)
    >>> reader = SbeCnvReader('mooring_data.cnv')
    >>> ds = reader.data
    
    >>> # Disable automatic coordinate fixing
    >>> reader = SbeCnvReader('mooring_data.cnv', fix_missing_coords=False)
    
    >>> # Disable file sanitization (stricter parsing)
    >>> reader = SbeCnvReader('data.cnv', sanitize_input=False)
    """

    def __init__(self, input_file: str,
                 sanitize_input: bool = True,
                 fix_missing_coords: bool = True,
                 mapping: dict | None = None,
                 **kwargs):
        """Initialize SbeCnvReader with configuration options.
        
        Parameters
        ----------
        input_file : str
            Path to the CNV file.
        sanitize_input : bool, default=True
            Whether to automatically fix known file format issues (e.g., trailing
            whitespace in start_time lines). When False, files with format issues
            may fail to load. CLI flag: --no-sanitize
        fix_missing_coords : bool, default=True
            Whether to automatically use default values for missing coordinates
            (e.g., 45° latitude for depth calculation). When False, missing
            coordinates will result in NaN values. CLI flag: --no-fix-coords
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
        self._sanitize_input = sanitize_input
        self._fix_missing_coords = fix_missing_coords
        self.__read()

    def __get_scan_interval_in_seconds(self, string):
        pattern = r'^# interval = seconds: ([\d.]+)$'
        match = re.search(pattern, string, re.MULTILINE)
        if match:
            seconds = float(match.group(1))
            return seconds
        return None

    def __get_bad_flag(self, string):
        pattern = r'^# bad_flag = (.+)$'
        match = re.search(pattern, string, re.MULTILINE)
        if match:
            bad_flag = match.group(1)
            return bad_flag
        return None

    def __get_start_time_from_header(self, header_string: str) -> pd.Timestamp | None:
        """Extract start_time from CNV header.
        
        Parameters
        ----------
        header_string : str
            The header string from the CNV file.

        Returns
        -------
        pd.Timestamp | None
            The extracted start time or None if not found.
        """

        pattern = r'^# start_time = ([A-Za-z]{3} \d{1,2} \d{4} \d{2}:\d{2}:\d{2})'
        match = re.search(pattern, header_string, re.MULTILINE)
        if match:
            time_str = match.group(1)
            try:
                # Parse the time string like "Aug 01 2025 10:10:08"
                return pd.to_datetime(time_str, format='%b %d %Y %H:%M:%S')
            except ValueError:
                return None
        return None

    def __normalize_time_coords(self, time_coords):
        """Normalize time coordinates to ensure consistent format."""
        if time_coords is None or len(time_coords) == 0:
            return time_coords
        
        # Convert to pandas datetime if it's not already
        try:
            time_coords_normalized = pd.to_datetime(time_coords)
            #print(f"Normalized time_coords type: {type(time_coords_normalized)}")
            #print(f"Normalized time_coords dtype: {time_coords_normalized.dtype}")
            #if len(time_coords_normalized) > 0:
                #print(f"Normalized time_coords[0]: {time_coords_normalized[0]}")
            
            # Convert DatetimeIndex to numpy array for xarray compatibility
            if isinstance(time_coords_normalized, pd.DatetimeIndex):
                time_coords_normalized = time_coords_normalized.to_numpy()
                #print(f"Converted to numpy array: {type(time_coords_normalized)}")
                #print(f"Numpy array dtype: {time_coords_normalized.dtype}")
            
            return time_coords_normalized
        except Exception as e:
            print(f"Error normalizing time_coords: {e}")
            return time_coords

    def __calculate_time_coordinates(self, xarray_data: dict, cnv: pycnv.pycnv, max_count: int) -> np.ndarray | None:
        """Calculate time coordinates from various time formats in CNV data.

        Parameters
        ----------
        xarray_data : dict
            Dictionary containing sensor data.
        cnv : pycnv.pycnv
            CNV object containing metadata.
        max_count : int
            Maximum number of data points.

        Returns
        -------
        numpy.ndarray | None
            Time coordinates as datetime values.
        """
        
        # Try to extract start_time from header instead of using cnv.date
        start_time_from_header = self.__get_start_time_from_header(cnv.header)
        if start_time_from_header:
            offset_datetime = start_time_from_header
            #print(f"Using header start_time: {offset_datetime}")
        else:
            # Fallback to cnv.date
            if cnv.date is not None:
                offset_datetime = pd.to_datetime(cnv.date.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                # Final fallback - use January 1st of current year
                current_year = datetime.now().year
                offset_datetime = pd.to_datetime(f"{current_year}-01-01 00:00:00")
            #print(f"Using cnv.date fallback: {offset_datetime}")

        # Define the time coordinates as an array of datetime values
        time_coords = None  # Initialize to avoid unbound variable error
        
        # Check for time variables (params match raw CNV names after mapping)
        if params.TIME_S in xarray_data:
            time_coords = np.array([self._elapsed_seconds_since_offset_to_datetime(elapsed_seconds, offset_datetime) \
                                   for elapsed_seconds in xarray_data[params.TIME_S]])
        elif params.TIME_J in xarray_data:
            year_startdate = datetime(year=offset_datetime.year, month=1, day=1)
            time_coords = np.array([self._julian_to_gregorian(jday, year_startdate) \
                                    for jday in xarray_data[params.TIME_J]])
        elif params.TIME_Q in xarray_data:
            time_coords = np.array([self._elapsed_seconds_since_jan_2000_to_datetime(elapsed_seconds) \
                                    for elapsed_seconds in xarray_data[params.TIME_Q]])
        elif params.TIME_N in xarray_data:
            time_coords = np.array([self._elapsed_seconds_since_jan_1970_to_datetime(elapsed_seconds) \
                                    for elapsed_seconds in xarray_data[params.TIME_N]])
        else:
            timedelta = self.__get_scan_interval_in_seconds(cnv.header)
            if timedelta:
                time_coords = [offset_datetime + pd.Timedelta(seconds=i*timedelta) for i in range(max_count)][:]

        # Normalize time coordinates to ensure consistent format
        return self.__normalize_time_coords(time_coords)

    def __assign_cnv_metadata(self, ds, xarray_labels, xarray_units, channel_names, cnv):
        """Assign CNV-specific metadata while preserving CF-compliant units when CNV units are missing.
        
        Parameters
        ----------
        ds
            xarray Dataset to add metadata to.
        xarray_labels
            Dictionary containing CNV channel labels/names.
        xarray_units
            Dictionary containing CNV channel units.
        channel_names
            List of original channel names from CNV.
        cnv
            CNV object containing header information.
            
        Returns
        -------
        xarray.Dataset 
            Dataset with CNV metadata assigned.
        """
        
        for var_name in ds.data_vars:
            # Find the original CNV channel name that corresponds to this variable
            original_channel = None
            
            # Check if this variable name directly matches a channel name
            if var_name in channel_names:
                original_channel = var_name
            else:
                # For renamed variables, try to find the original channel
                # This is a bit tricky after postprocessing, so we check both directions
                for channel in channel_names:
                    if channel.lower() == var_name.lower():
                        original_channel = channel
                        break
            
            if original_channel:
                # Store original CNV name and label
                if original_channel in xarray_labels:
                    ds[var_name].attrs['cnv_original_name'] = original_channel
                    ds[var_name].attrs['cnv_original_label'] = xarray_labels[original_channel]
                    ds[var_name].attrs['cnv_original_unit'] = xarray_units[original_channel]

                # Handle units: CNV units take precedence if they exist
                if original_channel in xarray_units and xarray_units[original_channel]:
                    cnv_unit = xarray_units[original_channel].strip()
                    if cnv_unit:  # Only use non-empty units
                        ds[var_name].attrs['units'] = cnv_unit
        
        return ds

    def __assign_cnv_global_attributes(self, ds, cnv):
        """Assign CNV-specific global attributes to the xarray Dataset.
        
        Parameters
        ----------
        ds
            xarray Dataset to add global attributes to.
        cnv
            CNV object containing metadata from pycnv.

        Returns
        -------
        xarray.Dataset
            Dataset with CNV global attributes assigned.
        """

        # Extract metadata from CNV header if available
        if cnv.header:
            # Extract SBE model via regex. Example: "* Sea-Bird SBE 9plus Data File:"
            sbe_model_match = re.search(r"\* Sea-Bird SBE *(?P<value>\d.*?) +Data File:", 
                                      cnv.header, re.IGNORECASE)
            if sbe_model_match:
                ds.attrs['cnv_sbe_model'] = "SBE " + sbe_model_match.group("value")
            
            # Extract software version via regex. Example: "* Software Version Seasave V 7.26.7.121"
            software_version_match = re.search(r"\* Software Version (?P<value>.+?)(?:\s*$)", 
                                             cnv.header, re.MULTILINE | re.IGNORECASE)
            if software_version_match:
                ds.attrs['cnv_software_version'] = software_version_match.group("value").strip()
        
        # Assign date/time attributes
        if cnv.date:
            ds.attrs['cnv_start_date'] = cnv.date.strftime("%Y-%m-%d %H:%M:%S")
        
        if cnv.upload_date:
            ds.attrs['cnv_upload_date'] = cnv.upload_date.strftime("%Y-%m-%d %H:%M:%S")
        
        if cnv.nmea_date:
            ds.attrs['cnv_nmea_date'] = cnv.nmea_date.strftime("%Y-%m-%d %H:%M:%S")
        
        # Assign scan interval if available
        if hasattr(cnv, 'interval_s') and cnv.interval_s:
            ds.attrs['cnv_interval_seconds'] = cnv.interval_s
        else:
            # Fallback: try to extract from header
            interval_from_header = self.__get_scan_interval_in_seconds(cnv.header)
            if interval_from_header:
                ds.attrs['cnv_interval_seconds'] = interval_from_header
        
        # Assign list of sensor information
        sensor_metadata = self.__extract_sensor_metadata_from_xml(cnv.header)
        for channel_num, metadata in sensor_metadata.items():
            entry_name = f'cnv_sensor_{channel_num}'
            # Create list of sensor information for a sensor without empty entries
            combined_sensor_metadata = {k: v for k, v in metadata.items() if v is not None}
            ds.attrs[entry_name] = combined_sensor_metadata

        return ds

    def __extract_sensor_metadata_from_xml(self, cnv_header):
        """Extract sensor metadata from XML-style sensor entries in CNV header.

        Parameters
        ----------
        cnv_header
            CNV header string containing XML sensor information.

        Returns
        -------
        dict
            Dictionary mapping channel numbers to sensor metadata.
        """

        import xml.etree.ElementTree as ET
        
        sensor_metadata: dict[int, dict[str, str | int]] = {}
        
        try:
            # Extract the XML sensor block from the CNV header
            xml_start = cnv_header.find('# <Sensors count=')
            if xml_start == -1:
                return sensor_metadata
            
            # Find the end of the XML block (look for closing </Sensors>)
            xml_end = cnv_header.find('# </Sensors>', xml_start)
            if xml_end == -1:
                # If no closing tag found, try to find where XML ends
                lines = cnv_header[xml_start:].split('\n')
                xml_lines = []
                for line in lines:
                    if line.startswith('#') and ('<' in line or '>' in line):
                        xml_lines.append(line[1:].strip())  # Remove '# ' prefix
                    else:
                        break
                xml_content = '\n'.join(xml_lines)
            else:
                xml_block = cnv_header[xml_start:xml_end + len('# </Sensors>')]
                # Remove '# ' prefix from each line
                xml_lines = []
                for line in xml_block.split('\n'):
                    if line.startswith('# '):
                        xml_lines.append(line[2:])
                xml_content = '\n'.join(xml_lines)
            
            # Parse the XML
            root = ET.fromstring(xml_content)
            
            # Extract sensor information
            for sensor in root.findall('sensor'):
                channel_attr = sensor.get('Channel')
                if channel_attr:
                    channel_num = int(channel_attr)
                    metadata: dict[str, str | int] = {'channel': channel_num}
                    
                    # Find sensor type and extract information
                    for sensor_element in sensor:
                        if sensor_element.tag.endswith('Sensor'):
                            sensor_type = sensor_element.tag
                            metadata['sensor_type'] = sensor_type
                            
                            # Extract SerialNumber
                            serial_elem = sensor_element.find('SerialNumber')
                            if serial_elem is not None and serial_elem.text:
                                metadata['serial_number'] = serial_elem.text
                            
                            # Extract CalibrationDate
                            cal_date_elem = sensor_element.find('CalibrationDate')
                            if cal_date_elem is not None and cal_date_elem.text:
                                metadata['calibration_date'] = cal_date_elem.text
                            
                            # Extract SensorID if available
                            sensor_id = sensor_element.get('SensorID')
                            if sensor_id:
                                metadata['sensor_id'] = sensor_id
                    
                    sensor_metadata[channel_num] = metadata
        
        except Exception as e:
            # If XML parsing fails, fall back to regex extraction
            print(f"XML parsing failed, trying regex fallback: {e}")
            return self.__extract_sensor_metadata_from_regex(cnv_header)
        
        return sensor_metadata

    def __extract_sensor_metadata_from_regex(self, cnv_header):
        """Fallback method to extract sensor metadata using regex when XML parsing fails.

        Parameters
        ----------
        cnv_header
            CNV header string.
            
        Returns
        -------
        dict
            Dictionary mapping channel numbers to sensor metadata.
        """

        sensor_metadata: dict[int, dict[str, str | int]] = {}
        
        # Look for sensor channel patterns
        sensor_pattern = r'#\s*<sensor Channel="(\d+)"\s*>'
        sensor_matches = re.finditer(sensor_pattern, cnv_header)
        
        for match in sensor_matches:
            channel_num = int(match.group(1))
            metadata: dict[str, str | int] = {'channel': channel_num}
            
            # Find the content for this sensor (until next sensor or end)
            start_pos = match.end()
            next_sensor = re.search(r'#\s*<sensor Channel="(\d+)"\s*>', cnv_header[start_pos:])
            if next_sensor:
                end_pos = start_pos + next_sensor.start()
                sensor_content = cnv_header[start_pos:end_pos]
            else:
                # Look for closing sensor tag or end of sensors block
                end_match = re.search(r'#\s*</sensor>|#\s*</Sensors>', cnv_header[start_pos:])
                if end_match:
                    end_pos = start_pos + end_match.end()
                    sensor_content = cnv_header[start_pos:end_pos]
                else:
                    sensor_content = cnv_header[start_pos:]
            
            # Extract comment information
            comment_match = re.search(r'#\s*<!--\s*([^>]+?)\s*-->', sensor_content)
            if comment_match:
                comment_text = comment_match.group(1).strip()
                metadata['sensor_comment'] = comment_text
                
                # Parse frequency and parameter info from comment
                freq_match = re.search(r'Frequency\s+(\d+)', comment_text, re.IGNORECASE)
                if freq_match:
                    metadata['frequency_channel'] = int(freq_match.group(1))
                
                # Extract parameter type from comment (Temperature, Conductivity, etc.)
                param_match = re.search(r'Frequency\s+\d+,\s*(.+)', comment_text, re.IGNORECASE)
                if param_match:
                    metadata['parameter_type'] = param_match.group(1).strip()
            
            # Extract SerialNumber
            serial_match = re.search(r'#\s*<SerialNumber>([^<]+)</SerialNumber>', sensor_content)
            if serial_match:
                metadata['serial_number'] = serial_match.group(1)
            
            # Extract CalibrationDate
            cal_date_match = re.search(r'#\s*<CalibrationDate>([^<]+)</CalibrationDate>', sensor_content)
            if cal_date_match:
                metadata['calibration_date'] = cal_date_match.group(1)
            
            # Extract sensor type
            sensor_type_match = re.search(r'#\s*<(\w+Sensor)\s+SensorID="([^"]*)"', sensor_content)
            if sensor_type_match:
                metadata['sensor_type'] = sensor_type_match.group(1)
                metadata['sensor_id'] = sensor_type_match.group(2)
            
            sensor_metadata[channel_num] = metadata
        
        return sensor_metadata
    
    def __calculate_depth_from_pressure(self, xarray_data, xarray_labels, xarray_units, cnv):
        """Calculate depth from pressure data using GSW library.

        Parameters
        ----------
        xarray_data
            Dictionary containing sensor data.
        xarray_labels
            Dictionary containing data labels.
        xarray_units
            Dictionary containing data units.
        cnv
            CNV object containing metadata.

        Returns
        -------
        numpy.ndarray | None 
            Depth values in meters, or None if pressure not available.
            
        Notes
        -----
        If latitude is not available from CNV metadata or data columns, a default
        value of 45° is used. This is standard practice in oceanography for cases
        like moored instruments. The depth error from using 45° instead of actual
        latitude is typically < 0.3m at typical CTD depths (< 0.5m at 100 dbar).
        """

        import gsw

        depth = None

        for alias in params.default_mappings[params.PRESSURE]:
            if alias in xarray_data:
                # rename key
                xarray_data[params.PRESSURE] = xarray_data[alias]
                xarray_labels[params.PRESSURE] = xarray_labels[alias]
                xarray_units[params.PRESSURE] = xarray_units[alias]
                break
        
        if params.PRESSURE in xarray_data:
            lat = cnv.lat
            
            # Check if lat is None or NaN
            if lat is None or (isinstance(lat, float) and np.isnan(lat)):
                if params.LATITUDE in xarray_data:
                    lat = xarray_data[params.LATITUDE][0]
                else:
                    lat = None
            
            # Use default latitude if not available and fix_missing_coords is enabled
            if lat is None or (isinstance(lat, float) and np.isnan(lat)):
                if self._fix_missing_coords:
                    lat = 45.0
                    print(f"Warning: Latitude not found in CNV file '{self.input_file}'. "
                          f"Using default latitude of {lat}° for depth calculation. "
                          f"This is common for moored instruments and typically introduces < 0.3m error. "
                          f"Set fix_missing_coords=False to disable this behavior.")
                else:
                    # If fix_missing_coords is disabled, lat remains None and will produce NaN depths
                    print(f"Warning: Latitude not found in CNV file '{self.input_file}'. "
                          f"Depth values will be NaN. Set fix_missing_coords=True to use default latitude.")
            
            depth = gsw.conversions.z_from_p(xarray_data[params.PRESSURE], lat)

        return depth

    def _sanitize_cnv_file(self, file):
        """ Sanitizes a CNV file to fix known issues that pycnv cannot handle.
        
        This function creates a temporary sanitized version of the CNV file,
        fixing common issues like trailing whitespace in start_time lines.
        
        Parameters
        ----------
        file : str
            Path to the CNV file to sanitize.

        Returns
        -------
        str
            Path to the sanitized file (may be a temporary file or the original).
        bool
            True if sanitization was needed, False if file was already clean.
        """
        import tempfile
        import os
        
        needs_sanitization = False
        sanitized_lines = []
        
        # Read file and check/fix problematic patterns
        with open(file, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                # Fix 1: Remove trailing whitespace from start_time lines
                if re.match(r'^# start_time \= [A-Za-z]{3} \d{1,2} \d{4} \d{2}:\d{2}:\d{2}\s+$', line):
                    line = line.rstrip() + '\n'
                    needs_sanitization = True
                    print(f"Warning: Fixed trailing whitespace in start_time at line {line_num}")
                
                # Fix 2: Skip lines starting with multiple asterisks (malformed)
                if re.match(r'^\* \*', line):
                    print(f"Warning: Skipping malformed line {line_num}: {line.strip()}")
                    needs_sanitization = True
                    continue
                
                sanitized_lines.append(line)
        
        # If sanitization was needed, create a temporary file
        if needs_sanitization:
            # Create temporary file in the same directory to preserve relative paths
            temp_fd, temp_path = tempfile.mkstemp(suffix='.cnv', prefix='sanitized_', 
                                                   dir=os.path.dirname(file) or '.')
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.writelines(sanitized_lines)
                print(f"Info: Created sanitized temporary file for pycnv processing")
                return temp_path, True
            except Exception as e:
                # Clean up temp file if writing fails
                try:
                    os.unlink(temp_path)
                except Exception:
                    # Ignore errors during cleanup - the original exception is more important
                    pass
                raise e
        
        return file, False

    def __read(self):
        """ Reads a CNV file and converts it to a xarray Dataset. """

        import pycnv
        import os

        # Sanitize the file if sanitize_input is enabled (fixes pycnv incompatibilities)
        if self._sanitize_input:
            file_to_read, was_sanitized = self._sanitize_cnv_file(self.input_file)
        else:
            file_to_read = self.input_file
            was_sanitized = False
        
        try:
            # Read CNV file with pycnv reader
            cnv = pycnv.pycnv(file_to_read)
        except Exception as e:
            # Clean up temp file before re-raising
            if was_sanitized and os.path.exists(file_to_read):
                try:
                    os.unlink(file_to_read)
                except Exception:
                    # Ignore errors during cleanup - the original exception is more important
                    pass
            
            # Provide helpful error message
            error_msg = str(e)
            if "dimension 'time' already exists" in error_msg:
                raise ValueError(
                    f"pycnv failed to parse CNV file: {error_msg}\n"
                    f"This is a known pycnv issue with certain CNV file formats. "
                    f"The file may have incompatible time variables or header formatting."
                ) from e
            else:
                raise ValueError(f"pycnv failed to parse CNV file: {error_msg}") from e

        # Map column names ('channel names') to standard names
        channel_names = [d['name'] for d in cnv.channels if 'name' in d]

        # Validate required parameters
        #super()._validate_necessary_parameters(self.mapping, cnv.lat, cnv.lon, 'mapping data')

        # Create dictionaries with data, names, and labels
        xarray_data = dict()
        xarray_labels = dict()
        xarray_units = dict()
        max_count = 0

        for channel_name in channel_names:
            # Map channel names to standard names
            if cnv.data is not None and channel_name in cnv.data:
                xarray_data[channel_name] = cnv.data[channel_name][:]
                xarray_labels[channel_name] = cnv.names[channel_name]
                xarray_units[channel_name] = cnv.units[channel_name]
                max_count = max(max_count, len(cnv.data[channel_name]))

        # Calculate time coordinates
        time_coords = self.__calculate_time_coordinates(xarray_data, cnv, max_count)

        # Create xarray Dataset
        ds = self._get_xarray_dataset_template(time_coords, None, cnv.lat, cnv.lon)

        # Assign data to xarray Dataset
        for key in xarray_data.keys():
            ds[key] = ([params.TIME], xarray_data[key])

        # Assign CNV-specific global attributes
        ds = self.__assign_cnv_global_attributes(ds, cnv)

        # Assign CNV-specific metadata (preserves CNV units, adds original names/labels)
        ds = self.__assign_cnv_metadata(ds, xarray_labels, xarray_units, channel_names, cnv)

        # Rename to standard names
        ds = self._perform_default_postprocessing(ds)

        # If "depth" not in ds, create depth variable
        if params.DEPTH not in ds:
            depth_data = self.__calculate_depth_from_pressure(xarray_data, xarray_labels, xarray_units, cnv)
            if depth_data is not None:
                ds[params.DEPTH] = (["time"], depth_data)
                if self._config_assign_metadata:
                    self._assign_metadata_for_key_to_xarray_dataset(ds, params.DEPTH)

        # Derive oceanographic parameters (density, potential temperature)
        ds = self._derive_oceanographic_parameters(ds)

        # Check for bad flag
        bad_flag = self.__get_bad_flag(cnv.header)
        if bad_flag is not None:
            for var in ds:
                ds[var] = ds[var].where(ds[var] != bad_flag, np.nan)

        # Store processed data
        self._data = ds

        # Clean up temporary sanitized file after all processing is complete
        if was_sanitized and os.path.exists(file_to_read):
            try:
                os.unlink(file_to_read)
            except Exception as e:
                print(f"Warning: Could not delete temporary file {file_to_read}: {e}")

    @classmethod
    def format_key(cls) -> str:
        return 'sbe-cnv'

    @classmethod
    def format_name(cls) -> str:
        return 'SeaBird CNV'

    @classmethod
    def file_extension(cls) -> str | None:
        return '.cnv'
