#! /usr/bin/env python3

from dataclasses import dataclass
from math import isnan
from pathlib import Path
import rdp
import datetime
import numpy as np
from airflow_dags.metrics_calculation.base_metrics_calculation import (
    IndividualMetricCalculation, MetricsCalculation
)
import utm
from mcap.reader import make_reader
from mcap_ros2.reader import read_ros2_messages
from tqdm import tqdm
from typing import List


VELOCITY_FILTER_THRESH : float = 0.1
AUTONOMY_MODE : int = 4
M_TO_MILES_FACTOR : float = 0.000621371

@dataclass
class GpsMessage:
    timestamp: float
    latitude: float
    longitude: float
    altitude: float


class CalculateMileage(IndividualMetricCalculation):

    def __init__(self):
        super().__init__()

        self._topics_to_parse: List[str] = ["/ublox/ublox_gps_node/fix", "/vayu/odom", "/operational_mode"]

        self._gps_messages = []
        self._autonomy_gps_messages = []
        
        self._current_speed : float = 0.0
        
        self._current_gps_message_window = []
        self._current_auto_gps_message_window = []
        
        self._current_operational_mode = 0

    def _get_reduced_messages(self, gps_message_group : List) -> List:
        reduced_gps_points = []
        for gps_message_window in gps_message_group:
            utms = [
                utm.from_latlon(gps_message.latitude, gps_message.longitude)
                for gps_message in gps_message_window
            ]
            utm_zone = utms[0][2]
            utm_letter = utms[0][3]
            utm_points = [(utm[0], utm[1]) for utm in utms]
            # create rdp with the utm points with 50 cm tolerance
            rdp_points = rdp.rdp(utm_points, epsilon=0.5)
            print(f"Reduced {len(utm_points)} points to {len(rdp_points)} points using RDP")
            # convert utm to gps
            reduced_gps_points.append([
                utm.to_latlon(utm_point[0], utm_point[1], utm_zone, utm_letter)
                for utm_point in rdp_points
            ])
        return reduced_gps_points

    def _calculate_total_distance(self, gps_points) -> float:
        total_distance : float = 0.0
        for gps_points_window in gps_points:
            total_distance += self._calculate_distance_for_window(gps_points_window)
        return total_distance * M_TO_MILES_FACTOR

    def _calculate_distance_for_window(self, gps_points_window) -> float:
        utms = [utm.from_latlon(gps[0], gps[1]) for gps in gps_points_window]
        utm_points = np.array([(utm[0], utm[1]) for utm in utms])
        diff = utm_points[1:] - utm_points[:-1]
        total_distance = np.sum(np.power(np.sum(diff * diff, axis=1), 0.5))
        return total_distance


    def ros_message_class(self):
        return ["NavSatFix", "nav_msgs/msg/NavSatFix", "Odometry", "OperationalMode"]

    def collate_messages(self, message):
        """
        Collate gps messages
        """
        
        if message.__class__.__name__ == "Odometry":
            self._current_speed = message.twist.twist.linear.x
            return
    
        if message.__class__.__name__ == "OperationalMode":
            self._current_operational_mode = message.mode
            return
    
        # Do not apeend messages with speed less than threshold
        if self._current_speed < VELOCITY_FILTER_THRESH:
            # Append the current window to the list of gps messages
            # if the window is not empty
            if len(self._current_gps_message_window) > 0:
                self._gps_messages.append(self._current_gps_message_window)
                self._current_gps_message_window = []
            
            if len(self._current_auto_gps_message_window) > 0:
                self._autonomy_gps_messages.append(self._current_auto_gps_message_window)
                self._current_auto_gps_message_window = []
            return

        
        # skip large covariance values
        if message.position_covariance[0] > 10.0:
            return

        # skip NaN messages
        if isnan(message.latitude) or isnan(message.longitude):
            return

        self._current_gps_message_window.append(
            GpsMessage(
                timestamp=message.header.stamp.sec
                + message.header.stamp.nanosec * 1e-9,
                latitude=message.latitude,
                longitude=message.longitude,
                altitude=message.altitude,
            )
        )
        
        if self._current_operational_mode != AUTONOMY_MODE:
            # If the autonomy is not engaged close the window
            if len(self._current_auto_gps_message_window) > 0:
                self._autonomy_gps_messages.append(self._current_auto_gps_message_window)
                self._current_auto_gps_message_window = []
            return
        
        self._current_auto_gps_message_window.append(
            GpsMessage(
                timestamp=message.header.stamp.sec
                + message.header.stamp.nanosec * 1e-9,
                latitude=message.latitude,
                longitude=message.longitude,
                altitude=message.altitude,
            )
        )
        
    def compute(self, mcap_file: str):
        """
        Compute mileage from mcap bags
        """
        stats = {}
        metric_raw_data_hashmap : dict = {
            "mileage": self._gps_messages,
            "autonomy_mileage": self._autonomy_gps_messages
        }
        try:
            for metric, gps_message_group in metric_raw_data_hashmap.items():
                reduced_gps_points = self._get_reduced_messages(gps_message_group)
                total_distance = self._calculate_total_distance(reduced_gps_points)
                print(f"Total accumulated distance for : {metric} : {total_distance:.2f} m")
                stats[metric] = float(total_distance)
        except Exception as e:
            print(e)
            return {
                "mileage": 0.0,
                "autonomy_mileage": 0.0
            }

        print("Statistics:")
        print("-" * 80)
        return stats
