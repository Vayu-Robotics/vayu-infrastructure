""" Base metrics calculation class.
1. The base class sets up the files to be read.
2. Calls relevant callbacks to calculate metrics.
3. Writes the calculated metrics to the databasee

"""

from math import isnan
from pathlib import Path
from typing import List
import os
from mcap.reader import make_reader
from mcap_ros2.reader import read_ros2_messages
from tqdm import tqdm
from dataclasses import dataclass
import psycopg2

# Note all the errors which should lead to the `calculate metrics node to crash` should
# have unhandled excpetions.

class MetricsCalculationErrorException(Exception):
    def __init__(self, message="An error occured while trying to compute the metric."):
        self.message = message
        super().__init__(self.message)

class MetricsCalculationDatabaseException(Exception):
    def __init__(self, message="Exception occured trying to persist the metrics to the database.") -> None:
        self.message = message
        super().__init__(self.message)

@dataclass
class Metric:
    metric_name: str
    value: float
    bag_file_name: str
    robot_name: str

    def __str__(self):
        return f"Metric: {self.metric_name}, Value: {self.value}, Bag: {self.bag_file_name}, Robot: {self.robot_name}"


class MetricsCalculation:

    def __init__(self, metric_class_dict : dict):
        # Dict of {metric_name: metric_class}/
        # metric_class should be a subclass of BaseMetricCalculation
        self.metric_class_dict = metric_class_dict

        self._init_database()

    
    def _init_database(self):
        """ Initializes connection to the database. """
        # Get environment variables for database credentials
        db_name = os.getenv("POSTGRES_DB")
        db_user = os.getenv("POSTGRES_USER")
        db_password = os.getenv("POSTGRES_PASSWORD")
        db_host = os.getenv("POSTGRES_HOST", "localhost")  # default is localhost
        self._conn_str = f"dbname={db_name} user={db_user} password={db_password} host={db_host}"

        create_table_query = """
        CREATE TABLE IF NOT EXISTS test_robots (
            uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            robot_name VARCHAR(100),
            bag_name VARCHAR(10000),
            mileage REAL,
            data_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(self._conn_str)
            cur = conn.cursor()

            # Execute the table creation query
            cur.execute(create_table_query)
            conn.commit()
        except:
            raise MetricsCalculationDatabaseException()
        finally:
            cur.close()
            conn.close()
    
    def write_metrics_to_db(self, metrics : List[Metric]):
        # Use psychopg2 to write metrics to the database
        # Write the metric to the database
        # Schema
        '''
        cur.execute("""
        INSERT INTO robots (robot_name, bag_name, mileage) 
        VALUES ('robot1', 'bag1', 100)
        ON CONFLICT DO NOTHING;
        """)
        '''

        for metric in metrics:
            try:
                # Connect to PostgreSQL
                conn = psycopg2.connect(self._conn_str)
                cur = conn.cursor()

                # Insert initial records (if needed)
                cur.execute("""
                    INSERT INTO test_robots (robot_name, bag_name, mileage)
                    VALUES (%s, %s, %s)
                """, (metric.robot_name, metric.bag_file_name, metric.value))
                
                conn.commit()
                cur.close()
                conn.close()

            except Exception as e:
                print(f"Error creating table: {e}")
                raise MetricsCalculationDatabaseException()

    def compute_metrics(self, bags : List):
        metrics = []
        for bag in bags:
            for metric_name, metric_class in self.metric_class_dict.items():
                try:
                    metric = metric_class.compute(bag)
                except:
                    raise MetricsCalculationErrorException()
                metric_obj : Metric = Metric(metric_name=metric_name, value=metric["value"], bag_file_name=bag, robot_name="test_robot")
                # TODO: Add robot name to the metric object
                metrics.append(metric_obj)
        return metrics


class BaseMetricCalculation:

    def __init__(self, topics_to_parse: List[str]):
        self.topics_to_parse = topics_to_parse

    def get_bag_iterator(self, mcap_file):
        return read_ros2_messages(mcap_file, topics=self.topics_to_parse)
    
    def compute(self, mcap_file : str) -> dict:
        raise NotImplementedError("Subclasses must implement this method")