#!/bin/bash

# Variable to track success
success_flag=0

# Loop through all Ethernet interfaces (eth*)
for interface in $(ip -o link show | awk -F': ' '{print $2}' | grep '^eth'); do
  # Check if the interface is up
  if ip link show "$interface" | grep -q 'state UP'; then
    echo "$interface is UP"
    
    # Check if the interface has an IP address
    if ip -4 addr show "$interface" | grep -q 'inet'; then
      echo "$interface has an IP address"
      
      # Check for Internet connectivity using the specific interface
      if ping -I "$interface" -c 1 8.8.8.8; then
        echo "$interface has Internet access"
        success_flag=1  # Set success flag if any interface has Internet
        break  # Exit the loop as soon as one connection has Internet
      else
        echo "$interface does not have Internet access"
      fi
    else
      echo "$interface does not have an IP address"
    fi
  else
    echo "$interface is DOWN"
  fi
done

# If no Ethernet interface with Internet access was found, fail th
