#! /usr/bin/env python3

from argparse import ArgumentParser
from dataclasses import dataclass
from math import isnan
from pathlib import Path

import numpy as np
import rdp
import utm
from mcap.reader import make_reader
from mcap_ros2.reader import read_ros2_messages
from tqdm import tqdm


@dataclass
class GpsMessage:
    timestamp: float
    latitude: float
    longitude: float
    altitude: float


def read_gps_messages(mcap_file, topic="/ublox/ublox_gps_node/fix"):
    bag_iterator = read_ros2_messages(mcap_file, topics=[topic])
    messages = []
    cov = 0
    print(f"Reading {topic} from {mcap_file}")
    for msg in tqdm(bag_iterator):
        gps_message = msg.ros_msg
        # skip large covariance values
        if gps_message.position_covariance[0] > 10.0:
            continue
        # skip NaN messages
        if isnan(gps_message.latitude) or isnan(gps_message.longitude):
            continue
        cov += gps_message.position_covariance[0]
        messages.append(
            GpsMessage(
                timestamp=gps_message.header.stamp.sec + gps_message.header.stamp.nanosec * 1e-9,
                latitude=gps_message.latitude,
                longitude=gps_message.longitude,
                altitude=gps_message.altitude,
            )
        )
    print(f"Average covariance: {cov / len(messages)}")
    return messages


def get_reduced_messages(gps_messages):
    utms = [utm.from_latlon(gps_message.latitude, gps_message.longitude) for gps_message in gps_messages]
    utm_zone = utms[0][2]
    utm_letter = utms[0][3]
    utm_points = [(utm[0], utm[1]) for utm in utms]
    # create rdp with the utm points with 50 cm tolerance
    rdp_points = rdp.rdp(utm_points, epsilon=0.5)
    print(f"Reduced {len(utm_points)} points to {len(rdp_points)} points using RDP")
    # convert utm to gps
    reduced_gps_points = [utm.to_latlon(utm_point[0], utm_point[1], utm_zone, utm_letter) for utm_point in rdp_points]
    return reduced_gps_points


def get_total_duration(gps_messages):
    return gps_messages[-1].timestamp - gps_messages[0].timestamp


def get_total_moving_duration(gps_messages):
    utms = [utm.from_latlon(gps_message.latitude, gps_message.longitude) for gps_message in gps_messages] 
    utm_points = np.array([(utm[0], utm[1]) for utm in utms])
    timestamps = np.array([gps.timestamp for gps in gps_messages])

    utm_diff = utm_points[1:] - utm_points[:-1]
    dist_diff = np.power(np.sum(utm_diff * utm_diff, axis=1), 0.5)
    time_diff = timestamps[1:] - timestamps[:-1]

    # accumulate time for which we have moved at least 5 cm
    return np.sum(time_diff[dist_diff > 0.005])


def calculate_total_distance(gps_points):
    utms = [utm.from_latlon(gps[0], gps[1]) for gps in gps_points]
    utm_points = np.array([(utm[0], utm[1]) for utm in utms])
    diff = utm_points[1:] - utm_points[:-1]
    total_distance = np.sum(np.power(np.sum(diff * diff, axis=1), 0.5))
    return total_distance



def compute_mileage(mcap_bags : str):
    """
    Compute mileage from mcap bags
    """
    stats = {}
    for mcap_bag in mcap_bags:
        try:
            gps_messages = read_gps_messages(mcap_bag)
            total_duration = get_total_moving_duration(gps_messages)
            reduced_gps_points = get_reduced_messages(gps_messages)
            total_distance = calculate_total_distance(reduced_gps_points)
            print(f"Total accumulated distance: {total_distance:.2f} m")
            print(f"Total duration: {total_duration:.2f} s")
            stats[mcap_bag] = {"total_duration": total_duration, "total_distance": total_distance}
        except Exception as e:
            print(e)

    print("Statistics:")
    print("-" * 80)
    print("{:<50} {:>10} {:>10}".format("mcap_bag", "total_duration", "total_distance"))
    for mcap_bag, stat in stats.items():
        print(f"{mcap_bag[-40:]:50}  {stat['total_duration']:>10.2f} {stat['total_distance']:>10.2f}")

    print("-" * 80)
    total_distance_m = sum([stats["total_distance"] for stats in stats.values()])
    total_distance_km = total_distance_m / 1000
    total_duration_s = sum([stats["total_duration"] for stats in stats.values()])
    total_duration_hours = total_duration_s / 3600
    print(f"Total distance: {total_distance_km:.2f} km / {total_distance_km * 0.621371:.2f} miles")
    print(f"Total duration: {total_duration_hours:.2f} hours")

    print(f"Average speed: {total_distance_km / total_duration_hours:.2f} km/h")
    print(f"Average speed: {total_distance_km * 0.621371 / total_duration_hours:.2f} miles/h")
    print("-" * 80)



if __name__ == "__main__":
    parser = ArgumentParser(description="Genearate gps stats from mcap bags")
    parser.add_argument("mcap_bags", nargs="+")
    compute_mileage(parser.mcap_bags)
    args = parser.parse_args()


