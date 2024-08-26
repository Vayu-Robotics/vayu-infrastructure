import os
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import yaml
import pytz

# Default arguments for the DAG
default_args = {
    'depends_on_past': False,  # DAG tasks don't depend on previous runs
    'start_date': datetime(2023, 1, 1),  # Fixed start date in the past
    'retries': 1,  # Number of retries in case of failure
    'retry_delay': timedelta(minutes=5),  # Time between retries
}

BASE_BAG_DIR = "/data/nas0/data_collects/rosbags"
PRODUCTION_BAG_DIRS = [os.path.join(BASE_BAG_DIR, "djarin-4")]
SYNC_DATA_FILE = "/home/arul/code/vayu-infrastructure/sync_data.yaml"

# Function to read the last synced time from a YAML file
def read_last_synced_time(file_path='sync_data.yaml'):
    try:
        with open(file_path, 'r') as file:
            data = yaml.safe_load(file)
            last_synced_time_str = data.get('last_synced_time')
            if last_synced_time_str:
                # Parse the time string and convert it to a UTC datetime object
                return datetime.fromisoformat(last_synced_time_str).astimezone(pytz.UTC)
    except FileNotFoundError:
        print("Sync data file not found. Assuming this is the first sync.")
    return None

# Function to get all directories newer than the last synced time from multiple base paths
def get_new_directories(base_paths, sync_file='sync_data.yaml'):
    last_synced_time = read_last_synced_time(sync_file)
    new_directories = []
    current_time = datetime.now(pytz.UTC)

    if not last_synced_time:
        # TODO(arul): Make this error out if no last_synced_time is found
        print("No last synced time found. Checking all directories.")
        last_synced_time = datetime.min.replace(tzinfo=pytz.UTC)

    # Iterate over each base path
    for base_path in base_paths:
        # Check if the base path exists and is a directory
        if os.path.exists(base_path) and os.path.isdir(base_path):
            for dir_name in os.listdir(base_path):
                dir_path = os.path.join(base_path, dir_name)
                if os.path.isdir(dir_path):
                    # Get the modification time of the directory and convert to UTC
                    mod_time = datetime.fromtimestamp(os.path.getmtime(dir_path), pytz.UTC)
                    if mod_time > last_synced_time:
                        print(f"New directory found: {dir_path}")
                        new_directories.append(dir_path)
        else:
            print(f"Base path '{base_path}' does not exist or is not a directory.")

    # Return the list of new directories
    print(f"New directories found: {new_directories}")
    return new_directories

def update_last_synced_time(new_time, file_path='sync_data.yaml'):
    with open(file_path, 'w') as file:
        yaml.dump({'last_synced_time': new_time.isoformat()}, file)

# Define your DAG
with DAG(
    'metrics_dag',
    default_args=default_args,
    schedule_interval=None,  # No automatic scheduling, trigger manually for debugging
    catchup=False,  # Avoid backfilling previous runs
) as dag:

    # Task 1: Check for new directories in the production bag directories
    # Read last_sync_time from metadata.yaml file
    # Check for new bags in the production bag directories that are added newer than last_sync_time
    # currently using modified time, we can also use created time instead.
    find_new_directories = PythonOperator(
        task_id='find_new_directories',
        python_callable=get_new_directories,
        op_kwargs={
            'base_paths': PRODUCTION_BAG_DIRS,
            'sync_file': SYNC_DATA_FILE
        },
        provide_context=True
    )

    new_time = datetime.now()
    # Task 2: Run a metrics with the new directories as input
    # TODO(suyash): Replace the placeholder script with the actual script
    def run_script_with_directories(**kwargs):
        # Get the directories from XCom
        new_directories = kwargs['ti'].xcom_pull(task_ids='find_new_directories')
        if new_directories:
            # Join the directories into a single string separated by spaces
            directories_str = ' '.join(new_directories)
            # Example: replace 'your_script.sh' with the path to your script
            os.system(f'bash your_script.sh {directories_str}')
        else:
            print("No new directories found.")

    run_script = PythonOperator(
        task_id='run_script',
        python_callable=run_script_with_directories,
        provide_context=True
    )


    # Task 3: Update the last synced time in the sync_data.yaml file
    update_sync_time = PythonOperator(
        task_id='update_sync_time',
        python_callable=update_last_synced_time,
        op_kwargs={
            'new_time': new_time,
            'file_path': 'sync_data.yaml'
        }
    )

    # Define the order of execution
    find_new_directories >> run_script >> update_sync_time

# vayu-infrastructure  | standalone | Login with username: admin  password: vdtN5C6DqTvkXPYX