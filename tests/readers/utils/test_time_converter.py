"""
Unit tests for TimeConverter utility class.

Tests all static methods for time format conversions including:
- Julian day to Gregorian datetime conversion
- Elapsed seconds since various epochs (1970, 2000, custom offset)
"""

import unittest
from datetime import datetime, timezone
from seasenselib.readers.utils import TimeConverter


class TestTimeConverter(unittest.TestCase):
    """Test suite for TimeConverter utility class."""

    def test_julian_to_gregorian_basic(self):
        """Test basic Julian day to Gregorian conversion."""
        # Julian days are 1-based, day 1.0 = start_date
        start = datetime(2000, 1, 1)
        result = TimeConverter.julian_to_gregorian(1.0, start)
        self.assertEqual(result, start)

    def test_julian_to_gregorian_fractional_day(self):
        """Test Julian day conversion with fractional days."""
        # Day 1.5 = 12 hours (noon) on start date
        start = datetime(2000, 1, 1)
        result = TimeConverter.julian_to_gregorian(1.5, start)
        expected = datetime(2000, 1, 1, 12, 0, 0)
        self.assertEqual(result, expected)

    def test_julian_to_gregorian_multiple_days(self):
        """Test Julian day conversion spanning multiple days."""
        start = datetime(2000, 1, 1)
        result = TimeConverter.julian_to_gregorian(2.0, start)
        expected = datetime(2000, 1, 2, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_julian_to_gregorian_complex(self):
        """Test Julian day conversion with days and fractional parts."""
        start = datetime(2024, 1, 1)
        result = TimeConverter.julian_to_gregorian(3.25, start)
        expected = datetime(2024, 1, 3, 6, 0, 0)  # 3rd day + 6 hours (0.25 * 24)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_jan_1970_zero(self):
        """Test Unix epoch conversion with zero seconds."""
        result = TimeConverter.elapsed_seconds_since_jan_1970_to_datetime(0.0)
        expected = datetime(1970, 1, 1, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_jan_1970_positive(self):
        """Test Unix epoch conversion with positive seconds."""
        # 1 day = 86400 seconds
        result = TimeConverter.elapsed_seconds_since_jan_1970_to_datetime(86400.0)
        expected = datetime(1970, 1, 2, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_jan_1970_fractional(self):
        """Test Unix epoch conversion with fractional seconds."""
        # 1 hour = 3600 seconds
        result = TimeConverter.elapsed_seconds_since_jan_1970_to_datetime(3600.5)
        expected = datetime(1970, 1, 1, 1, 0, 0, 500000)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_jan_1970_large(self):
        """Test Unix epoch conversion with large value (year 2022)."""
        # 2022-01-01 00:00:00 UTC = 1640995200 seconds since Unix epoch
        result = TimeConverter.elapsed_seconds_since_jan_1970_to_datetime(1640995200.0)
        expected = datetime(2022, 1, 1, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_jan_2000_zero(self):
        """Test Y2K epoch conversion with zero seconds."""
        result = TimeConverter.elapsed_seconds_since_jan_2000_to_datetime(0.0)
        expected = datetime(2000, 1, 1, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_jan_2000_positive(self):
        """Test Y2K epoch conversion with positive seconds."""
        # 1 day = 86400 seconds
        result = TimeConverter.elapsed_seconds_since_jan_2000_to_datetime(86400.0)
        expected = datetime(2000, 1, 2, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_jan_2000_fractional(self):
        """Test Y2K epoch conversion with fractional seconds."""
        # 1 day + 0.5 seconds
        result = TimeConverter.elapsed_seconds_since_jan_2000_to_datetime(86400.5)
        expected = datetime(2000, 1, 2, 0, 0, 0, 500000)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_offset_zero(self):
        """Test custom offset conversion with zero seconds."""
        offset = datetime(2020, 6, 15, 12, 0, 0)
        result = TimeConverter.elapsed_seconds_since_offset_to_datetime(0.0, offset)
        self.assertEqual(result, offset)

    def test_elapsed_seconds_since_offset_positive(self):
        """Test custom offset conversion with positive seconds."""
        offset = datetime(2020, 6, 15, 12, 0, 0)
        # Add 1 hour
        result = TimeConverter.elapsed_seconds_since_offset_to_datetime(3600.0, offset)
        expected = datetime(2020, 6, 15, 13, 0, 0)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_offset_negative(self):
        """Test custom offset conversion with negative seconds."""
        offset = datetime(2020, 6, 15, 12, 0, 0)
        # Subtract 1 day
        result = TimeConverter.elapsed_seconds_since_offset_to_datetime(-86400.0, offset)
        expected = datetime(2020, 6, 14, 12, 0, 0)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_offset_fractional(self):
        """Test custom offset conversion with fractional seconds."""
        offset = datetime(2020, 6, 15, 12, 0, 0)
        # Add 1.5 seconds
        result = TimeConverter.elapsed_seconds_since_offset_to_datetime(1.5, offset)
        expected = datetime(2020, 6, 15, 12, 0, 1, 500000)
        self.assertEqual(result, expected)

    def test_elapsed_seconds_since_offset_different_epochs(self):
        """Test custom offset with various epoch dates."""
        epochs = [
            datetime(1900, 1, 1, 0, 0, 0),
            datetime(1980, 1, 1, 0, 0, 0),
            datetime(2010, 1, 1, 0, 0, 0),
        ]
        seconds = 86400.0  # 1 day
        
        for epoch in epochs:
            result = TimeConverter.elapsed_seconds_since_offset_to_datetime(seconds, epoch)
            expected = datetime(epoch.year, epoch.month, epoch.day + 1, 0, 0, 0)
            self.assertEqual(result, expected)

    def test_time_converter_methods_are_static(self):
        """Verify all TimeConverter methods are static methods."""
        import inspect
        methods = ['julian_to_gregorian', 
                   'elapsed_seconds_since_jan_1970_to_datetime',
                   'elapsed_seconds_since_jan_2000_to_datetime',
                   'elapsed_seconds_since_offset_to_datetime']
        
        for method_name in methods:
            method = getattr(TimeConverter, method_name)
            self.assertTrue(isinstance(inspect.getattr_static(TimeConverter, method_name), staticmethod),
                          f"{method_name} should be a static method")


if __name__ == '__main__':
    unittest.main()
