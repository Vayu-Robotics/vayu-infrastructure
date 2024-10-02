from argparse import ArgumentParser
from airflow_dags.metrics_calculation.parse_gps_data import CalculateMileage
from airflow_dags.metrics_calculation.calculate_disengagements import CalculateDisengagements
from airflow_dags.metrics_calculation.base_metrics_calculation import MetricsCalculation


if __name__ == "__main__":
    parser = ArgumentParser(description="Genearate gps stats from mcap bags")
    parser.add_argument("mcap_bags", nargs="+")


    metric_class_dict = {
        "mileage": CalculateMileage(),
        "disengagements": CalculateDisengagements(),
    }
    metrics_calculation = MetricsCalculation(metric_class_dict)
    metrics = metrics_calculation.compute_metrics(parser.parse_args().mcap_bags)
    # metrics_calculation.write_metrics_to_db(metrics)
    print(metrics)
    print("Metrics written to the database.")
    print("Metrics computation complete.")



# /data/nas0/data_collects/rosbags/djarin-4/20240903_djarin-4_3/20240903_djarin-4_3_7.mcap
# /data/nas0/data_collects/rosbags/djarin-4/20240903_djarin-4_3/20240903_djarin-4_3_8.mcap