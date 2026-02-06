"""
Time conversion utilities for sensor data readers.

This module provides static methods for converting various time formats
commonly used in oceanographic sensor data files.
"""

from datetime import datetime, timedelta


class TimeConverter:
    """
    Utility class for time format conversions.
    
    All methods are static and stateless - they perform pure transformations
    from one time representation to another.
    
    Examples
    --------
    >>> from seasenselib.readers.utils import TimeConverter
    >>> 
    >>> # Convert Julian days to datetime
    >>> start = datetime(2024, 1, 1)
    >>> dt = TimeConverter.julian_to_gregorian(1.5, start)
    >>> 
    >>> # Convert elapsed seconds since epoch
    >>> dt = TimeConverter.elapsed_seconds_since_jan_1970_to_datetime(1704067200)
    """
    
    @staticmethod
    def julian_to_gregorian(julian_days: float, start_date: datetime) -> datetime:
        """
        Convert Julian days to Gregorian datetime.
        
        Julian days count from 1 (not 0), so day 1.0 is the start_date itself.
        Fractional days are converted to seconds.
        
        Parameters
        ----------
        julian_days : float
            Julian day number (1-based). For example, 1.5 means noon on start_date.
        start_date : datetime
            The reference date (Julian day 1).
            
        Returns
        -------
        datetime
            The calculated Gregorian datetime.
            
        Examples
        --------
        >>> start = datetime(2024, 1, 1)
        >>> TimeConverter.julian_to_gregorian(1.0, start)
        datetime.datetime(2024, 1, 1, 0, 0)
        >>> TimeConverter.julian_to_gregorian(1.5, start)
        datetime.datetime(2024, 1, 1, 12, 0)
        >>> TimeConverter.julian_to_gregorian(2.0, start)
        datetime.datetime(2024, 1, 2, 0, 0)
        """
        full_days = int(julian_days) - 1  # Julian days start at 1, not 0
        seconds = (julian_days - int(julian_days)) * 24 * 60 * 60
        return start_date + timedelta(days=full_days, seconds=seconds)

    @staticmethod
    def elapsed_seconds_since_jan_1970_to_datetime(elapsed_seconds: float) -> datetime:
        """
        Convert elapsed seconds since January 1, 1970 (Unix epoch) to datetime.
        
        Parameters
        ----------
        elapsed_seconds : float
            Number of seconds since 1970-01-01 00:00:00.
            
        Returns
        -------
        datetime
            The calculated datetime.
            
        Examples
        --------
        >>> TimeConverter.elapsed_seconds_since_jan_1970_to_datetime(0)
        datetime.datetime(1970, 1, 1, 0, 0)
        >>> TimeConverter.elapsed_seconds_since_jan_1970_to_datetime(86400)
        datetime.datetime(1970, 1, 2, 0, 0)
        """
        base_date = datetime(1970, 1, 1)
        time_delta = timedelta(seconds=elapsed_seconds)
        return base_date + time_delta

    @staticmethod
    def elapsed_seconds_since_jan_2000_to_datetime(elapsed_seconds: float) -> datetime:
        """
        Convert elapsed seconds since January 1, 2000 to datetime.
        
        This is commonly used in Sea-Bird instruments (timeQ format).
        
        Parameters
        ----------
        elapsed_seconds : float
            Number of seconds since 2000-01-01 00:00:00.
            
        Returns
        -------
        datetime
            The calculated datetime.
            
        Examples
        --------
        >>> TimeConverter.elapsed_seconds_since_jan_2000_to_datetime(0)
        datetime.datetime(2000, 1, 1, 0, 0)
        >>> TimeConverter.elapsed_seconds_since_jan_2000_to_datetime(86400)
        datetime.datetime(2000, 1, 2, 0, 0)
        """
        base_date = datetime(2000, 1, 1)
        time_delta = timedelta(seconds=elapsed_seconds)
        return base_date + time_delta

    @staticmethod
    def elapsed_seconds_since_offset_to_datetime(
        elapsed_seconds: float, 
        offset_datetime: datetime
    ) -> datetime:
        """
        Convert elapsed seconds since a custom offset datetime.
        
        This is commonly used in Sea-Bird instruments (timeS format).
        
        Parameters
        ----------
        elapsed_seconds : float
            Number of seconds since the offset datetime.
        offset_datetime : datetime
            The reference datetime (epoch).
            
        Returns
        -------
        datetime
            The calculated datetime.
            
        Examples
        --------
        >>> offset = datetime(2024, 6, 15, 12, 0, 0)
        >>> TimeConverter.elapsed_seconds_since_offset_to_datetime(3600, offset)
        datetime.datetime(2024, 6, 15, 13, 0)
        """
        time_delta = timedelta(seconds=elapsed_seconds)
        return offset_datetime + time_delta
