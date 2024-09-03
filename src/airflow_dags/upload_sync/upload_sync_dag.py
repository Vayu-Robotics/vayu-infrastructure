import subprocess
import socket
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
# Define your DAG's default arguments
# default_args = {
#     'depends_on_past': False,
#     'start_date': datetime(2024, 8, 20),
#     'retries': 1,
#     'retry_delay': timedelta(minutes=5),
# }


def check_wifi_connection():
    result = subprocess.run(['python3', '/src/airflow_dags/upload_sync/check_wifi_connection.py'], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        raise Exception(f"WiFi connection check failed: {result.stderr}")

# Default arguments for the DAG
default_args = {
    'depends_on_past': False,
    'start_date': datetime(2024, 9, 4),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define your DAG
with DAG(
    'upload_sync_dag',
    default_args=default_args,
    schedule_interval='0 0 * * *',  # No automatic scheduling, trigger manually for debugging
    catchup=False,  # Avoid backfilling previous runs
) as dag:

    # Task 1: Check WiFi connection using a Python script
    check_wifi_connection_task = PythonOperator(
        task_id='check_wifi_connection',
        python_callable=check_wifi_connection,
    )

    hostname : str = socket.gethostname()
    # Task 2: Rsync between local folder and NAS
    rsync_to_nas = BashOperator(
        task_id='rsync_to_nas',
        bash_command=f"""
        rsync -P -rltv --no-o --no-g /data/collects/ rsync://100.108.48.87:30026/robot_rosbags/{hostname}
        """,
    )

    # Task 3: Delete local folder after sync
    delete_local_folder = BashOperator(
        task_id='delete_local_folder',
        bash_command='rm -rf /data/collects/dummy',
    )

    # Define the order of execution
    check_wifi_connection_task >> rsync_to_nas >> delete_local_folder


# vayu-infrastructure  | standalone | Login with username: admin  password: vdtN5C6DqTvkXPYX