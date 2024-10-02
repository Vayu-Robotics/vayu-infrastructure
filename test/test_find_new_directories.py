import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import pytz
import os

from src.airflow_dags.metrics_dag.metrics_dag import get_new_directories, read_last_synced_time

class TestFindNewDirectories(unittest.TestCase):

    @patch('src.airflow_dags.metrics_dag.metrics_dag.read_last_synced_time')
    @patch('os.path.isdir')
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.path.getmtime')
    def test_find_new_directories_newer_than_last_sync(self, mock_getmtime, mock_listdir, mock_exists, mock_isdir, mock_read_last_synced_time):
        # Set up the mock values
        base_paths = ['/test/path1', '/test/path2']
        mock_read_last_synced_time.return_value = datetime(2023, 8, 1, tzinfo=pytz.UTC)
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.return_value = ['dir1', 'dir2']
        
        # Mock modification times for directories
        mod_time_new = datetime(2023, 8, 2, tzinfo=pytz.UTC).timestamp()  # Newer than last sync
        mod_time_old = datetime(2023, 7, 30, tzinfo=pytz.UTC).timestamp()  # Older than last sync
        mock_getmtime.side_effect = [mod_time_new, mod_time_old, mod_time_new, mod_time_old]

        # Call the function to test
        new_directories = get_new_directories(base_paths, sync_file='sync_data.yaml')

        # Check if the function identified the new directories correctly
        expected_directories = [
            '/test/path1/dir1',  # new directory
            '/test/path2/dir1'   # new directory
        ]
        self.assertEqual(new_directories, expected_directories)

    @patch('src.airflow_dags.metrics_dag.metrics_dag.read_last_synced_time')
    @patch('os.path.exists')
    def test_find_new_directories_base_path_not_exists(self, mock_exists, mock_read_last_synced_time):
        # Set up the mock values
        base_paths = ['/invalid/path']
        mock_exists.return_value = False
        mock_read_last_synced_time.return_value = datetime(2023, 8, 1, tzinfo=pytz.UTC)

        # Call the function to test
        new_directories = get_new_directories(base_paths, sync_file='sync_data.yaml')

        # Check if the function handled the invalid path correctly
        self.assertEqual(new_directories, [])

    # Test case for the scenario where no directories are found in the base path
    @patch('src.airflow_dags.metrics_dag.metrics_dag.read_last_synced_time')
    @patch('os.path.isdir')
    @patch('os.path.exists')
    def test_find_new_directories_no_directories_in_path(self, mock_exists, mock_isdir, mock_read_last_synced_time):
        # Set up the mock values
        base_paths = ['/test/path1']
        mock_exists.return_value = True
        mock_isdir.side_effect = [False]  # No directories found
        mock_read_last_synced_time.return_value = datetime(2023, 8, 1, tzinfo=pytz.UTC)

        # Call the function to test
        new_directories = get_new_directories(base_paths, sync_file='sync_data.yaml')

        # Check if the function handled the case correctly
        self.assertEqual(new_directories, [])

    @patch('src.airflow_dags.metrics_dag.metrics_dag.yaml.safe_load')
    @patch('builtins.open', new_callable=mock_open, read_data="last_synced_time: '2023-08-01T00:00:00+00:00'")
    def test_read_last_synced_time(self, mock_open_file, mock_yaml_load):
        # Mock YAML safe_load
        mock_yaml_load.return_value = {'last_synced_time': '2023-08-01T00:00:00+00:00'}

        # Call the function to test
        last_synced_time = read_last_synced_time(file_path='sync_data.yaml')

        # Expected time in UTC
        expected_time = datetime(2023, 8, 1, tzinfo=pytz.UTC)

        # Check if the function returns the correct datetime object
        self.assertEqual(last_synced_time, expected_time)

if __name__ == '__main__':
    unittest.main()
