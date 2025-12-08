"""
Reader and Writer factories for clean instantiation.

Modern factory pattern with Protocol-based type hints for extensibility.
All format handling is now dynamic via autodiscovery - no hardcoded formats!
"""

from typing import Protocol, Optional, Any, List
from .autodiscovery import ReaderDiscovery, WriterDiscovery
from .exceptions import ReaderError, WriterError


class AbstractReader(Protocol):
    """Protocol for reader classes."""

    def get_data(self) -> Any:
        """Get data from the reader."""
        ...

    @staticmethod
    def format_key() -> str:
        """Return the format key for this reader."""
        ...


class AbstractWriter(Protocol):
    """Protocol for writer classes."""

    def write(self, output_file: str) -> None:
        """Write data to file."""
        ...

    @staticmethod
    def file_extension() -> str:
        """Return the file extension for this writer."""
        ...


class ReaderFactory:
    """Factory for creating reader instances with autodiscovery."""

    def __init__(self):
        self._discovery = ReaderDiscovery()

    def create_reader(self, format_key: str, input_file: str, 
                     header_file: Optional[str] = None,
                     sanitize_input: bool = True,
                     fix_missing_coords: bool = True) -> AbstractReader:
        """
        Create a reader instance for the given format.
        
        Parameters:
        -----------
        format_key : str
            The format key (e.g., 'sbe-cnv', 'rbr-rsk')
        input_file : str
            Path to the input file
        header_file : str, optional
            Path to header file (required for some formats like Nortek ASCII)
        sanitize_input : bool, default=True
            Whether to automatically fix known file format issues (for CNV readers)
        fix_missing_coords : bool, default=True
            Whether to use default values for missing coordinates (for CNV readers)
            
        Returns:
        --------
        AbstractReader
            Reader instance ready to use
            
        Raises:
        -------
        ReaderError
            If reader cannot be created
        """
        # Find the reader class
        reader_class = self._discovery.get_reader_by_format_key(format_key)
        if not reader_class:
            raise ReaderError(f"No reader found for format: {format_key}")

        # Check if reader needs special parameters
        return self._instantiate_reader(reader_class, format_key, input_file, header_file,
                                       sanitize_input, fix_missing_coords)

    def _instantiate_reader(self, reader_class: type, format_key: str,
                          input_file: str, header_file: Optional[str],
                          sanitize_input: bool = True,
                          fix_missing_coords: bool = True) -> AbstractReader:
        """
        Instantiate reader with appropriate parameters.
        
        This method handles special cases where readers need different parameters.
        Ideally, readers would declare their parameter requirements themselves.
        """
        # Special case: Nortek ASCII requires header file
        if format_key == "nortek-ascii":
            if not header_file:
                raise ReaderError(
                    "Nortek ASCII format requires a header file. "
                    "Use --header-input to specify the header file."
                )
            return reader_class(input_file, header_file)

        # Special case: SeaBird CNV reader supports configuration flags
        if format_key == "sbe-cnv":
            return reader_class(input_file, 
                              sanitize_input=sanitize_input,
                              fix_missing_coords=fix_missing_coords)

        # Standard case: most readers just need the input file
        return reader_class(input_file)


class WriterFactory:
    """Factory for creating writer instances with dynamic autodiscovery."""

    def __init__(self):
        self._discovery = WriterDiscovery()

    def create_writer(self, format_key: str, data: Any) -> AbstractWriter:
        """
        Create a writer instance for the given format.
        
        Parameters:
        -----------
        format_key : str
            The format key (e.g., 'netcdf', 'csv', 'excel')
        data : Any
            The data to write (typically xarray.Dataset)
            
        Returns:
        --------
        AbstractWriter
            Writer instance ready to use
            
        Raises:
        -------
        WriterError
            If writer cannot be created
        """
        # Find the writer class by format key
        writer_class = self._discovery.get_writer_by_format_key(format_key)
        if not writer_class:
            available_formats = self.get_supported_formats()
            raise WriterError(
                f"No writer found for format: {format_key}. "
                f"Available formats: {', '.join(available_formats)}"
            )

        # Create writer instance with data
        return writer_class(data)

    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported output format keys.
        
        Returns:
        --------
        List[str]
            List of format keys (e.g., ['netcdf', 'csv', 'excel'])
        """
        format_info = self._discovery.get_format_info()
        return [info['key'] for info in format_info]

    def get_format_info(self) -> List[dict]:
        """
        Get detailed format information for all writers.
        
        Returns:
        --------
        List[dict]
            List of format info dicts with keys: 'key', 'format', 'extension', 'class_name'
        """
        return self._discovery.get_format_info()
