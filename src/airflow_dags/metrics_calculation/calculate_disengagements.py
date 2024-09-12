from dataclasses import dataclass
from math import isnan
from pathlib import Path
import datetime
from airflow_dags.metrics_calculation.base_metrics_calculation import (
    IndividualMetricCalculation, MetricsCalculation
)
import utm
from mcap.reader import make_reader
from mcap_ros2.reader import read_ros2_messages
from tqdm import tqdm
from typing import List
from argparse import ArgumentParser


AUTONOMY_MODE : int = 4


@dataclass
class OperationalModeMessage:
    timestamp: datetime.datetime
    operational_mode: int


class CalculateDisengagements(IndividualMetricCalculation):

    def __init__(self):
        super().__init__()

        self._topics_to_parse: List[str] = ["/operational_mode"]
        self._disengagements : List[datetime.datetime] = []

        self._current_operational_mode = 0
        self._operational_mode_messages = []
    
    def _has_autonomy_disengaged(self, operational_mode: int) -> bool:
        # Check if the autonomy has been disengaged
        # Check if the autonomy has been disengaged
        if self._current_operational_mode== AUTONOMY_MODE and operational_mode != AUTONOMY_MODE:
            print(f"Mode switch from autonomy to {operational_mode}")
            self._current_operational_mode = operational_mode
            return True
        
        else:
            self._current_operational_mode = operational_mode
            return False

    def ros_message_class(self):
        return ["OperationalMode"]
    
    def collate_messages(self, operational_mode_message):
        mssg_timestamp : int =  datetime.datetime.fromtimestamp(operational_mode_message.header.stamp.sec + operational_mode_message.header.stamp.nanosec * 1e-9)
        operational_mode_message : OperationalModeMessage = OperationalModeMessage(timestamp=mssg_timestamp, operational_mode=operational_mode_message.mode)
        self._operational_mode_messages.append(operational_mode_message)
    
    def compute(self, mcap_file):
        for operational_mode_message in self._operational_mode_messages:
            if self._has_autonomy_disengaged(operational_mode_message.operational_mode):
                self._disengagements.append(operational_mode_message.timestamp)
        self._operational_mode_messages.clear()
        return { "disengagements": self._disengagements }


if __name__ == "__main__":
    parser = ArgumentParser(description="Genearate gps stats from mcap bags")
    parser.add_argument("mcap_bags", nargs="+")

    metric_class_dict = {
        "disengagements": CalculateDisengagements(),
    }
    metrics_calculation = MetricsCalculation(metric_class_dict)
    metrics = metrics_calculation.compute_metrics(parser.parse_args().mcap_bags)
    # breakpoint()
    metrics_calculation.write_metrics_to_db(metrics)
    print(metrics)
    print("Metrics written to the database.")
    print("Metrics computation complete.")