#!/usr/bin/env bash

echo "Starting Dolphin MQTT Proxy..."

# Install Python dependencies
pip3 install --no-cache-dir paho-mqtt requests

# Run the proxy script
python3 - << 'EOF'
import time
import requests
import paho.mqtt.client as mqtt

print("Dolphin MQTT Proxy running...")

# Placeholder loop (replace with real logic later)
while True:
    time.sleep(10)
EOF
