"""
Data I/O management.

This module provides a lightweight coordinator for data reading and writing operations.
The actual work is delegated to specialized factories and autodiscovery.
"""

import os
from typing import Optional, Any
from .autodiscovery import FormatDetector
from .factories import ReaderFactory, WriterFactory
from .exceptions import ReaderError


class DataIOManager:
    """Lightweight coordinator for data reading and writing operations.
    
    This class delegates the actual work to specialized factories while
    providing a simple unified interface for CLI and API consumers.
    
    Architecture:
    - FormatDetector: Detects file formats from extensions/hints
    - ReaderFactory: Creates appropriate reader instances
    - WriterFactory: Creates appropriate writer instances
    - DataIOManager: Orchestrates the above components
    
    Attributes:
    ----------
    format_detector : FormatDetector
        Detects file formats
    reader_factory : ReaderFactory
        Creates reader instances
    writer_factory : WriterFactory
        Creates writer instances
    """

    def __init__(self):
        """Initialize the I/O manager with its dependencies."""
        self.format_detector = FormatDetector()
        self.reader_factory = ReaderFactory()
        self.writer_factory = WriterFactory()

    def read_data(self, input_file: str, format_hint: Optional[str] = None,
                  header_input_file: Optional[str] = None,
                  sanitize_input: bool = True,
                  fix_missing_coords: bool = True) -> Any:
        """
        Read data from input file.
        
        Parameters:
        ----------
        input_file : str
            Path to the input file
        format_hint : str, optional
            Format hint to override auto-detection
        header_input_file : str, optional
            Path to header file (required for some formats like Nortek ASCII)
        sanitize_input : bool, default=True
            Whether to automatically fix known file format issues (for CNV files)
        fix_missing_coords : bool, default=True
            Whether to use default values for missing coordinates (for CNV files)
            
        Returns:
        --------
        xarray.Dataset
            The loaded data
            
        Raises:
        -------
        ReaderError
            If reading fails
        """
        # Validate input file
        if not os.path.exists(input_file):
            raise ReaderError(f"Input file does not exist: {input_file}")

        # Detect format
        format_key = self.format_detector.detect_format(input_file, format_hint)

        # Create reader and get data
        reader = self.reader_factory.create_reader(
            format_key, input_file, header_input_file,
            sanitize_input=sanitize_input,
            fix_missing_coords=fix_missing_coords
        )
        return reader.get_data()

    def write_data(self, data: Any, output_file: str, format_hint: Optional[str] = None) -> None:
        """
        Write data to output file.
        
        Parameters:
        -----------
        data : xarray.Dataset
            The data to write
        output_file : str
            Path to the output file
        format_hint : str, optional
            Format hint to override auto-detection (e.g., 'netcdf', 'csv', 'excel')
            
        Raises:
        -------
        WriterError
            If writing fails
        """
        # Detect and validate output format (returns format_key like 'netcdf')
        format_key = self.format_detector.validate_output_format(output_file, format_hint)

        # Create output directory if needed
        self._ensure_output_directory(output_file)

        # Create writer and write data
        writer = self.writer_factory.create_writer(format_key, data)
        writer.write(output_file)

    def _ensure_output_directory(self, output_file: str) -> None:
        """Create output directory if it doesn't exist."""
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
