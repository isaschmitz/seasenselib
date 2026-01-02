"""
Facade for reading RBR MATLAB .mat files, automatically selecting the correct reader
based on the root variable in the MATLAB structure.

If the root variable is "RBR", delegates to RbrMatlabLegacyReader.
If the root variable is "rsk", delegates to RbrMatlabRsktoolsReader.
Otherwise, raises an error.
"""

from __future__ import annotations
from .base import AbstractReader
from .rbr_matlab_legacy_reader import RbrMatlabLegacyReader
from .rbr_matlab_rsktools_reader import RbrMatlabRsktoolsReader

class RbrMatlabReader(AbstractReader):
    """
    Facade for reading RBR Matlab .mat files, automatically selecting the correct reader
    based on the root variable in the MATLAB structure.
    """
    def __init__(self, input_file: str,
                 mapping: dict | None = None,
                 **kwargs):
        """Initialize RbrMatlabReader.
        
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
        self._reader_format_name = None
        self._reader_format_key = None
        self._select_and_read()

    def _select_and_read(self):
        """
        Selects the appropriate reader based on the root variable in the MATLAB file.
        """

        import scipy.io

        # Load Matlab file to inspect root variable
        mat = scipy.io.loadmat(self.input_file, squeeze_me=True, struct_as_record=False)

        # Select the appropriate reader based on root variable
        if "RBR" in mat:
            reader = RbrMatlabLegacyReader(self.input_file, mapping=self.mapping)
        elif "rsk" in mat:
            reader = RbrMatlabRsktoolsReader(self.input_file, mapping=self.mapping)
        else:
            raise ValueError("Neither 'RBR' nor 'rsk' struct found in .mat file.")

        # Read the data using the selected reader
        self._data = reader.data
        self._reader_format_name = reader.format_name()
        self._reader_format_key = reader.format_key()

    @classmethod
    def format_key(cls) -> str:
        return 'rbr-matlab'

    @classmethod
    def format_name(cls) -> str:
        return 'RBR Matlab'

    @classmethod
    def file_extension(cls) -> str | None:
        return None
