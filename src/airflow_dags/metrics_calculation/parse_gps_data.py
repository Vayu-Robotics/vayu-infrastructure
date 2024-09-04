#! /usr/bin/env python3

from argparse import ArgumentParser
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


@dataclass
class GpsMessage:
    timestamp: float
    latitude: float
    longitude: float
    altitude: float


class CalculateMileage(IndividualMetricCalculation):

    def __init__(self):
        super().__init__()

        self._topics_to_parse: List[str] = ["/ublox/ublox_gps_node/fix"]

        self._gps_messages = []

    def _get_reduced_messages(self):
        utms = [
            utm.from_latlon(gps_message.latitude, gps_message.longitude)
            for gps_message in self._gps_messages
        ]
        utm_zone = utms[0][2]
        utm_letter = utms[0][3]
        utm_points = [(utm[0], utm[1]) for utm in utms]
        # create rdp with the utm points with 50 cm tolerance
        rdp_points = rdp.rdp(utm_points, epsilon=0.5)
        print(f"Reduced {len(utm_points)} points to {len(rdp_points)} points using RDP")
        # convert utm to gps
        reduced_gps_points = [
            utm.to_latlon(utm_point[0], utm_point[1], utm_zone, utm_letter)
            for utm_point in rdp_points
        ]
        return reduced_gps_points

    def _get_total_moving_duration(self):
        utms = [
            utm.from_latlon(gps_message.latitude, gps_message.longitude)
            for gps_message in self._gps_messages
        ]
        utm_points = np.array([(utm[0], utm[1]) for utm in utms])
        timestamps = np.array([gps.timestamp for gps in self._gps_messages])

        utm_diff = utm_points[1:] - utm_points[:-1]
        dist_diff = np.power(np.sum(utm_diff * utm_diff, axis=1), 0.5)
        time_diff = timestamps[1:] - timestamps[:-1]

        # accumulate time for which we have moved at least 5 cm
        return np.sum(time_diff[dist_diff > 0.005])

    def _calculate_total_distance(self, gps_points):
        utms = [utm.from_latlon(gps[0], gps[1]) for gps in gps_points]
        utm_points = np.array([(utm[0], utm[1]) for utm in utms])
        diff = utm_points[1:] - utm_points[:-1]
        total_distance = np.sum(np.power(np.sum(diff * diff, axis=1), 0.5))
        return total_distance



    def ros_message_class(self):
        return ["NavSatFix", "nav_msgs/msg/NavSatFix"]

    def collate_messages(self, gps_message):
        """
        Collate gps messages
        """
        # skip large covariance values
        if gps_message.position_covariance[0] > 10.0:
            return
        # skip NaN messages
        if isnan(gps_message.latitude) or isnan(gps_message.longitude):
            return
        self._gps_messages.append(
            GpsMessage(
                timestamp=gps_message.header.stamp.sec
                + gps_message.header.stamp.nanosec * 1e-9,
                latitude=gps_message.latitude,
                longitude=gps_message.longitude,
                altitude=gps_message.altitude,
            )
        )

    def compute(self, mcap_file: str):
        """
        Compute mileage from mcap bags
        """
        stats = {}
        try:
            total_duration = self._get_total_moving_duration()
            reduced_gps_points = self._get_reduced_messages()
            total_distance = self._calculate_total_distance(reduced_gps_points)
            print(f"Total accumulated distance: {total_distance:.2f} m")
            print(f"Total duration: {total_duration:.2f} s")
            stats["mileage"] = float(total_distance)
        except Exception as e:
            print(e)

        print("Statistics:")
        print("-" * 80)

        return stats


if __name__ == "__main__":
    parser = ArgumentParser(description="Genearate gps stats from mcap bags")
    parser.add_argument("mcap_bags", nargs="+")

    # mileage_calculator = CalculateMileage()
    # for bag in parser.parse_args().mcap_bags:
    #     mileage_calculator.compute(bag)
    # args = parser.parse_args()

    metric_class_dict = {
        "mileage": CalculateMileage(),
    }
    metrics_calculation = MetricsCalculation(metric_class_dict)
    metrics = metrics_calculation.compute_metrics(parser.parse_args().mcap_bags)
    # breakpoint()
    metrics_calculation.write_metrics_to_db(metrics)
    print(metrics)
    print("Metrics written to the database.")
    print("Metrics computation complete.")
