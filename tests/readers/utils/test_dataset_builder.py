"""
Unit tests for DatasetBuilder utility class.

Tests static methods for creating and populating xarray Datasets:
- Creating Dataset templates with time coordinate and optional depth
- Assigning data arrays to Datasets
"""

import unittest
import numpy as np
import xarray as xr
from datetime import datetime
from seasenselib.readers.utils import DatasetBuilder
import seasenselib.parameters as params


class TestDatasetBuilder(unittest.TestCase):
    """Test suite for DatasetBuilder utility class."""

    def setUp(self):
        """Set up test fixtures."""
        self.time_array = np.array([
            datetime(2023, 1, 1, 12, 0, 0),
            datetime(2023, 1, 1, 12, 1, 0),
            datetime(2023, 1, 1, 12, 2, 0),
        ], dtype='datetime64[ns]')
        self.depth_array = np.array([0.0, 1.0, 2.0])
        self.latitude = 54.0
        self.longitude = 10.0

    def test_create_template_basic(self):
        """Test creating a basic Dataset template."""
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=self.depth_array,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        self.assertIsInstance(ds, xr.Dataset)
        self.assertIn('time', ds.coords)
        self.assertIn('latitude', ds.coords)
        self.assertIn('longitude', ds.coords)
        self.assertIn(params.DEPTH, ds.coords)

    def test_create_template_without_depth(self):
        """Test creating template without depth coordinate."""
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=None,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        self.assertIn('time', ds.coords)
        self.assertIn('latitude', ds.coords)
        self.assertIn('longitude', ds.coords)
        self.assertNotIn(params.DEPTH, ds.coords)

    def test_create_template_coordinate_values(self):
        """Test that coordinate values are correctly assigned."""
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=self.depth_array,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        np.testing.assert_array_equal(ds.time.values, self.time_array)
        self.assertEqual(float(ds.latitude.values), self.latitude)
        self.assertEqual(float(ds.longitude.values), self.longitude)
        np.testing.assert_array_almost_equal(ds[params.DEPTH].values, self.depth_array)

    def test_create_template_has_attributes(self):
        """Test that Dataset has proper global attributes."""
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=self.depth_array,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        self.assertIn('latitude', ds.attrs)
        self.assertIn('longitude', ds.attrs)
        self.assertIn('DataType', ds.attrs)
        self.assertEqual(ds.attrs['DataType'], 'TimeSeries')

    def test_assign_data_basic(self):
        """Test assigning data to a Dataset."""
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=self.depth_array,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        data = np.array([15.5, 16.0, 16.5])
        DatasetBuilder.assign_data(ds, 'temperature', data)
        
        self.assertIn('temperature', ds.data_vars)
        np.testing.assert_array_almost_equal(ds['temperature'].values, data)

    def test_assign_data_multiple_variables(self):
        """Test assigning multiple variables to a Dataset."""
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=self.depth_array,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        temp_data = np.array([15.5, 16.0, 16.5])
        sal_data = np.array([35.0, 35.1, 35.2])
        
        DatasetBuilder.assign_data(ds, 'temperature', temp_data)
        DatasetBuilder.assign_data(ds, 'salinity', sal_data)
        
        self.assertIn('temperature', ds.data_vars)
        self.assertIn('salinity', ds.data_vars)
        np.testing.assert_array_almost_equal(ds['temperature'].values, temp_data)
        np.testing.assert_array_almost_equal(ds['salinity'].values, sal_data)

    def test_assign_data_dimensions(self):
        """Test that assigned data has correct dimensions."""
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=self.depth_array,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        data = np.array([15.5, 16.0, 16.5])
        DatasetBuilder.assign_data(ds, 'temperature', data)
        
        self.assertEqual(ds['temperature'].dims, ('time',))
        self.assertEqual(len(ds['temperature']), 3)

    def test_assign_data_preserves_existing_variables(self):
        """Test that assigning new data preserves existing variables."""
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=self.depth_array,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        temp_data = np.array([15.5, 16.0, 16.5])
        sal_data = np.array([35.0, 35.1, 35.2])
        
        DatasetBuilder.assign_data(ds, 'temperature', temp_data)
        original_temp = ds['temperature'].values.copy()
        
        DatasetBuilder.assign_data(ds, 'salinity', sal_data)
        
        # Check temperature is still there and unchanged
        self.assertIn('temperature', ds.data_vars)
        np.testing.assert_array_almost_equal(ds['temperature'].values, original_temp)

    def test_create_template_and_assign_data_workflow(self):
        """Test typical workflow of creating template and assigning data."""
        # Create template
        ds = DatasetBuilder.create_template(
            time_array=self.time_array,
            depth_array=self.depth_array,
            latitude=self.latitude,
            longitude=self.longitude
        )
        
        # Add multiple variables
        DatasetBuilder.assign_data(ds, 'temperature', np.array([15.5, 16.0, 16.5]))
        DatasetBuilder.assign_data(ds, 'salinity', np.array([35.0, 35.1, 35.2]))
        DatasetBuilder.assign_data(ds, 'pressure', np.array([10.0, 20.0, 30.0]))
        
        # Verify all variables are present (depth is coordinate, not data_var)
        self.assertIn('temperature', ds.data_vars)
        self.assertIn('salinity', ds.data_vars)
        self.assertIn('pressure', ds.data_vars)
        self.assertIn(params.DEPTH, ds.coords)

    def test_dataset_builder_methods_are_static(self):
        """Verify all DatasetBuilder methods are static methods."""
        import inspect
        methods = ['create_template', 'assign_data']
        
        for method_name in methods:
            method = getattr(DatasetBuilder, method_name)
            self.assertTrue(isinstance(inspect.getattr_static(DatasetBuilder, method_name), staticmethod),
                          f"{method_name} should be a static method")


if __name__ == '__main__':
    unittest.main()
