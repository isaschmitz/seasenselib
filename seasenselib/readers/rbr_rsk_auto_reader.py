"""
Module for reading RBR RSK data files into xarray Datasets.
"""

from __future__ import annotations
import xarray as xr
from packaging.version import Version
from .base import AbstractReader
from .rbr_rsk_reader import RbrRskReader
from .rbr_rsk_legacy_reader import RbrRskLegacyReader


class RbrRskAutoReader(AbstractReader):
    """
    Facade for reading RBR .rsk files, automatically selecting the correct reader
    based on the file's type and version.

    This class checks the type and version of the RSK file and initializes either
    the RbrRskReader for modern files or the RbrRskLegacyReader for legacy files.
    It reads the data and returns it as an xarray Dataset.      

    Attributes
    ----------
    input_file : str
        The path to the input file containing the RBR data.
    mapping : dict, optional
        A dictionary mapping names used in the input file to standard names.
    data : xr.Dataset | None
        The processed sensor data as an xarray Dataset, or None if not yet processed.

    Properties
    ----------
    data : xr.Dataset (read-only)
        Returns the xarray Dataset containing the sensor data.
        For backward compatibility, get_data() method is also available but deprecated.

    Methods
    -------
    _load_data()
        Selects the appropriate reader based on the RSK file type and version,
        and reads the data into an xarray Dataset.
    """

    def __init__(self, input_file: str,
                 mapping: dict | None = None,
                 **kwargs):
        """Initialize RbrRskAutoReader.
        
        Parameters
        ----------
        input_file : str
            Path to the RSK file.
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
        self._reader_format_name = None
        self._reader_format_key = None
        self._validate_file()
        # Store kwargs to pass to delegate reader
        self._kwargs = kwargs

    @classmethod
    def _get_valid_extensions(cls) -> tuple[str, ...]:
        """Return valid file extensions for RSK files."""
        return ('.rsk',)

    def _load_data(self) -> xr.Dataset:
        """ Selects the appropriate reader based on the RSK file type and version.

        This method connects to the SQLite database within the RSK file, checks the
        type and version of the database, and initializes either the RbrRskReader
        or the RbrRskLegacyReader accordingly.
        
        Returns
        -------
        xr.Dataset
            The loaded dataset.
        """

        import sqlite3

        # Connect to the SQLite database of the RSK file to check type and version
        con = sqlite3.connect(self.input_file)
        try:
            dbinfo = con.execute("SELECT type, version FROM dbInfo").fetchone()
            if dbinfo is None:
                raise ValueError("dbInfo table not found in RSK file.")
            db_type, db_version = dbinfo
        finally:
            con.close()

        # Check if version is >= minimum supported
        is_modern = (
            (db_type.lower() == "full" and Version(db_version) >= Version("2.0.0")) or
            (db_type.lower() == "epdesktop" and Version(db_version) >= Version("1.13.4"))
        )

        # Select the appropriate reader based on the type and version
        # Pass through all kwargs to honor configuration options
        if is_modern:
            reader = RbrRskReader(
                self.input_file,
                mapping=self.mapping,
                **self._kwargs
            )
        else:
            reader = RbrRskLegacyReader(
                self.input_file,
                mapping=self.mapping,
                **self._kwargs
            )

        # Store reader metadata
        self._reader_format_name = reader.format_name()
        self._reader_format_key = reader.format_key()
        
        return reader.data

    @classmethod
    def format_key(cls) -> str:
        return 'rbr-rsk'

    @classmethod
    def format_name(cls) -> str:
        return 'RBR RSK'

    @classmethod
    def file_extension(cls) -> str | None:
        return '.rsk'
