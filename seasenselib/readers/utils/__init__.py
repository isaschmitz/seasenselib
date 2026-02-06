"""
Utility classes for reader operations.

This module provides reusable utility classes extracted from AbstractReader
for better testability, maintainability, and separation of concerns.

Classes
-------
TimeConverter
    Static methods for time format conversions (Julian days, elapsed seconds, etc.)
DatasetProcessor
    Static methods for xarray Dataset transformations (sorting, renaming, attributes)
DatasetBuilder
    Static methods for creating and populating xarray Datasets
"""

from seasenselib.readers.utils.time_converter import TimeConverter
from seasenselib.readers.utils.dataset_processor import DatasetProcessor
from seasenselib.readers.utils.dataset_builder import DatasetBuilder

__all__ = [
    'TimeConverter',
    'DatasetProcessor', 
    'DatasetBuilder',
]
