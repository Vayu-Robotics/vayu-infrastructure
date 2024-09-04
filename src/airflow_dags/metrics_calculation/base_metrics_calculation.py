""" Base metrics calculation class.
1. The base class sets up the files to be read.
2. Calls relevant callbacks to calculate metrics.
3. Writes the calculated metrics to the databasee

"""

from math import isnan
from pathlib import Path
from typing import List, Union
import os
from mcap.reader import make_reader
from mcap_ros2.reader import read_ros2_messages
from tqdm import tqdm
from dataclasses import dataclass
import psycopg2
import datetime

# Note all the errors which should lead to the `calculate metrics node to crash` should
# have unhandled excpetions.

class MetricsCalculationErrorException(Exception):
    def __init__(self, message="An error occured while trying to compute the metric."):
        self.message = message
        super().__init__(self.message)


class MetricsCalculationDatabaseException(Exception):
    def __init__(
        self, message="Exception occured trying to persist the metrics to the database."
    ) -> None:
        self.message = message
        super().__init__(self.message)


@dataclass
class Metric:
    metric_name: str
    value: Union[List, float]
    bag_file_name: str
    robot_name: str
    start_time: datetime = None
    end_time: datetime = None

    def __str__(self):
        return f"Metric: {self.metric_name}, Value: {self.value}, Bag: {self.bag_file_name}, Robot: {self.robot_name}, Start Time: {self.start_time}, End Time: {self.end_time}"


class MetricsCalculation:

    def __init__(self, metric_class_dict: dict):
        # Dict of {metric_name: metric_class}/
        # metric_class should be a subclass of BaseMetricCalculation
        self.metric_class_dict = metric_class_dict
        self._metric_calculation_driver = MetricCalculationDriver(metric_class_dict)
        self._init_database()
        
    
    def _get_robot_name(self, bag_file_name: str) -> str:
        """ TODO: Is there a better way to get the robot name from the bag file name? """
        return bag_file_name.split("/")[5]

    def _init_database(self):
        """Initializes connection to the database."""
        # Get environment variables for database credentials
        db_name = os.getenv("POSTGRES_DB")
        db_user = os.getenv("POSTGRES_USER")
        db_password = os.getenv("POSTGRES_PASSWORD")
        db_host = os.getenv("POSTGRES_HOST", "localhost")  # default is localhost
        self._conn_str = (
            f"dbname={db_name} user={db_user} password={db_password} host={db_host}"
        )

        create_table_query = """
        CREATE TABLE IF NOT EXISTS test_robots_ts_dis (
            uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            robot_name VARCHAR(100),
            bag_name VARCHAR(10000),
            mileage REAL,
            data_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            disengagements TIMESTAMP[] DEFAULT '{}'
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

    def write_metrics_to_db(self, metrics: List[Metric]):
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
                # cur.execute(
                #     """
                #     INSERT INTO test_robots_ts_dis (robot_name, bag_name, mileage, start_time, end_time)
                #     VALUES (%s, %s, %s, %s, %s)
                # """,
                #     (metric.robot_name, metric.bag_file_name, metric.value, metric.start_time, metric.end_time),
                # )
                query = f"""
                    INSERT INTO test_robots_ts_dis (robot_name, bag_name, {metric.metric_name}, start_time, end_time)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (bag_name) 
                    DO UPDATE SET
                        robot_name = EXCLUDED.robot_name,
                        {metric.metric_name} = EXCLUDED.{metric.metric_name},
                        start_time = EXCLUDED.start_time,
                        end_time = EXCLUDED.end_time;
                """
                cur.execute(
                    query,
                    (metric.robot_name, metric.bag_file_name, metric.value, metric.start_time, metric.end_time)
                )
                conn.commit()
                cur.close()
                conn.close()

            except Exception as e:
                print(f"Error creating table: {e}")
                raise MetricsCalculationDatabaseException()

    def compute_metrics(self, bags: List):
        metrics = []
        # Get metrics at bag level
        for bag in bags:
            robot_name = self._get_robot_name(bag)
            print(f"Computing metrics for {robot_name}")
            try:
                time_dict: dict = self._metric_calculation_driver.iterate_messages(bag)
                computed_metrics: List[dict] = self._metric_calculation_driver.compute(bag)
            except:
                raise MetricsCalculationErrorException()
            for computed_metric in computed_metrics:
                for metric_type, metric_value in computed_metric.items():
                    metric_obj: Metric = Metric(
                        metric_name=metric_type,
                        value=metric_value,
                        bag_file_name=bag,
                        robot_name=robot_name,
                        start_time=time_dict["start_time"],
                        end_time=time_dict["end_time"],
                    )
                metrics.append(metric_obj)
        return metrics


class MetricCalculationDriver:

    def __init__(self, metric_class_dict: dict):

        # Make a dictionary of class_dict value and `topic to parse`
        # Call the `topics_to_parse` method on each class and store the result in a dictionary
        self._metric_class_to_topics: dict = {
            metric_class: metric_class.topics_to_parse()
            for metric_class in metric_class_dict.values()
        }
        self._metric_class_to_ros_message_class: dict = {
            metric_class: metric_class.ros_message_class()
            for metric_class in metric_class_dict.values()
        }
        self._topics_to_parse: List = [
            topic
            for topics in self._metric_class_to_topics.values()
            for topic in topics
        ]
        self._start_time: datetime = None
        self._end_time: datetime = None

    def get_bag_iterator(self, mcap_file):
        return read_ros2_messages(mcap_file, topics=self._topics_to_parse)

    @property
    def topics_to_parse(self):
        return self._topics_to_parse

    def compute(self, mcap_file: str) -> List[dict]:
        
        computed_metrics = []
        for metric_class in self._metric_class_to_topics.keys():
            computed_metrics.append(metric_class.compute(mcap_file))
        return computed_metrics

    def iterate_messages(self, mcap_file) -> dict:

        start_time: datetime = None
        end_time: datetime = None
        bag_iterator = self.get_bag_iterator(mcap_file)
        print(f"Reading {self.topics_to_parse} from {mcap_file}")
        for msg in tqdm(bag_iterator):

            current_msg = msg.ros_msg
            if start_time is None:
                start_time = datetime.datetime.fromtimestamp(
                    current_msg.header.stamp.sec
                )
            current_time = datetime.datetime.fromtimestamp(current_msg.header.stamp.sec)

            for metric_class in self._metric_class_to_topics.keys():
                if current_msg.__class__.__name__ in self._metric_class_to_ros_message_class[metric_class]:
                    metric_class.collate_messages(current_msg)

        end_time = current_time
        return {"start_time": start_time, "end_time": end_time}


class IndividualMetricCalculation:

    def __init__(self) -> None:
        self._topics_to_parse : List = []

    def collate_messages(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def compute(self) -> dict:
        raise NotImplementedError("Subclasses must implement this method")

    def ros_message_class(self):
        raise NotImplementedError("Subclasses must implement this method")

    def topics_to_parse(self) -> List[str]:
        return self._topics_to_parse