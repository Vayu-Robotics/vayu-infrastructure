""" Base metrics calculation class.
1. The base class sets up the files to be read.
2. Calls relevant callbacks to calculate metrics.
3. Writes the calculated metrics to the databasee

"""

from math import isnan
from pathlib import Path
from typing import List
import numpy as np
import rdp
import utm
from mcap.reader import make_reader
from mcap_ros2.reader import read_ros2_messages
from tqdm import tqdm
from dataclasses import dataclass
# import psychopg2
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
                # Insert initial records (if needed)
                cur.execute(f"""
                INSERT INTO robots (robot_name, bag_name, mileage) 
                VALUES ({metric.robot_name}, {metric.bag_file_name}, {metric.value})
                ON CONFLICT DO NOTHING;
                """)
                conn.commit()
                cur.close()
                conn.close()

            except Exception as e:
                print(f"Error creating table: {e}")

    def compute_metrics(self, bags : List):
        metrics = []
        for bag in bags:
            for metric_name, metric_class in self.metric_class_dict.items():
                metric = metric_class.compute(bag)
                metric_obj = Metric(metric_name=metric_name, value=metric["value"], bag_file_name=bag, robot_name="test_robot")
                # TODO: Add robot name to the metric object
                metrics.append(metric)
        return metrics


class BaseMetricCalculation:

    def __init__(self, topics_to_parse: List[str]):
        self.topics_to_parse = topics_to_parse

    def get_bag_iterator(self, mcap_file):
        return read_ros2_messages(mcap_file, topics=self.topics_to_parse)
    
    def compute(self, mcap_file : str) -> dict:
        raise NotImplementedError("Subclasses must implement this method")