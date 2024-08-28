from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Define your DAG's default arguments
# default_args = {
#     'depends_on_past': False,
#     'start_date': datetime(2024, 8, 20),
#     'retries': 1,
#     'retry_delay': timedelta(minutes=5),
# }


# Default arguments for the DAG
default_args = {
    'depends_on_past': False,  # DAG tasks don't depend on previous runs
    'start_date': datetime(2023, 1, 1),  # Fixed start date in the past
    'retries': 1,  # Number of retries in case of failure
    'retry_delay': timedelta(minutes=5),  # Time between retries
}

# Define your DAG
with DAG(
    'upload_sync_dag',
    default_args=default_args,
    schedule_interval=None,  # No automatic scheduling, trigger manually for debugging
    catchup=False,  # Avoid backfilling previous runs
) as dag:

    # Task 1: Check for wired Ethernet connection
    check_wired_connection = BashOperator(
        task_id='check_wired_connection',
        bash_command='./check_wired_connection.sh',
    )

    # Task 2: Rsync between local folder and NAS
    rsync_to_nas = BashOperator(
        task_id='rsync_to_nas',
        bash_command="""
        rsync -avz --no-perms --no-owner --no-group /data/collects/artifacts nas0:/data_collects/testing
        """,
    )

    # Task 3: Delete local folder after sync
    delete_local_folder = BashOperator(
        task_id='delete_local_folder',
        bash_command='rm -rf /data/collects/dummy',
    )

    # Define the order of execution
    check_wired_connection >> rsync_to_nas >> delete_local_folder


# vayu-infrastructure  | standalone | Login with username: admin  password: vdtN5C6DqTvkXPYX