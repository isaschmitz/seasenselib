"""
SeaSenseLib Readers Module with Autodiscovery

This module provides various reader classes for importing CTD sensor data
from different file formats into xarray Datasets. It uses an autodiscovery
mechanism to automatically find and register all available reader classes.

Available Readers:
-----------------
All reader classes are automatically discovered from the readers directory.
Common readers include:
- SbeCnvReader: Read SeaBird CNV files
- NetCdfReader: Read NetCDF files
- CsvReader: Read CSV files
- RbrRskReader: Read RBR RSK files
- And many more...

Example Usage:
--------------
from seasenselib.readers import SbeCnvReader, NetCdfReader

# Read a CNV file
reader = SbeCnvReader("data.cnv")
data = reader.data

# Read a NetCDF file  
nc_reader = NetCdfReader("data.nc")
nc_data = nc_reader.data
"""

# Import the base class
from .base import AbstractReader

# Import autodiscovery functionality (lazy to avoid circular imports)
def _get_reader_discovery():
    """Get reader discovery instance lazily."""
    from ..core.autodiscovery import ReaderDiscovery
    return ReaderDiscovery()

# Discover all available reader classes
_all_readers = {}
_discovery_done = False

def _ensure_readers_discovered():
    """Ensure readers are discovered and loaded into module namespace."""
    global _all_readers, _discovery_done
    if not _discovery_done:
        discovery = _get_reader_discovery()
        _all_readers = discovery.discover_classes()

        # Import all discovered reader classes into this module's namespace
        for class_name, class_obj in _all_readers.items():
            globals()[class_name] = class_obj

        _discovery_done = True

# Trigger discovery on import
_ensure_readers_discovered()

# Build __all__ from discovered classes
__all__ = ['AbstractReader'] + list(_all_readers.keys())

# Legacy compatibility functions for registry-like access
def get_reader_by_format_key(format_key: str):
    """Get reader class by format key."""
    discovery = _get_reader_discovery()
    return discovery.get_reader_by_format_key(format_key)

def get_readers_by_extension(extension: str):
    """Get reader classes that can handle a specific file extension."""
    discovery = _get_reader_discovery()
    return discovery.get_readers_by_extension(extension)

def get_all_reader_classes():
    """Get list of all reader class names."""
    discovery = _get_reader_discovery()
    return discovery.get_all_class_names()

def get_format_info():
    """Get format information for all readers."""
    discovery = _get_reader_discovery()
    return discovery.get_format_info()
