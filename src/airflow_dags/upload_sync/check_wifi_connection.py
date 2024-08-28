import subprocess
import os

STABLE_WIFI_SSID = os.getenv("STABLE_WIFI_SSID")

def check_wifi_connection(ssid : str = STABLE_WIFI_SSID):
    try:
        # Run the iwgetid command to get the current connected Wi-Fi SSID
        result = subprocess.run(['iwgetid', '--raw'], stdout=subprocess.PIPE, text=True)

        # Get the output from iwgetid (the current connected SSID)
        current_ssid = result.stdout.strip()

        # Check if the current SSID matches the one we are looking for
        if current_ssid == ssid:
            return True
        else:
            print(f"Currently connected with this {STABLE_WIFI_SSID}")
        return False
    except Exception as e:
        print(f"Error checking Wi-Fi connection: {e}")
        return False

if __name__ == "__main__":
    ssid_to_check = STABLE_WIFI_SSID  # Replace with your Wi-Fi SSID
    if check_wifi_connection(ssid_to_check):
        print(f"Connected to {ssid_to_check}")
    else:
        print(f"Not connected to {ssid_to_check}")