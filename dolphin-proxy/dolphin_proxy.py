import time
import json
import logging
import threading
from typing import Optional

import httpx
import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

LOGGER = logging.getLogger("dolphin_proxy")


# ---------------------------------------------------------------------------
# MyDolphin Plus API Client (placeholder implementation)
# ---------------------------------------------------------------------------

class MyDolphinClient:
    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password
        self._token: Optional[str] = None
        self._client = httpx.Client(timeout=10.0)

    def login(self) -> None:
        """
        TODO: Implement real MyDolphin Plus login.
        """
        LOGGER.info("Logging in to MyDolphin Plus as %s", self._email)
        # Placeholder: replace with real auth call
        self._token = "dummy-token"
        LOGGER.info("MyDolphin Plus login successful (placeholder token)")

    def get_robot_state(self) -> dict:
        """
        TODO: Implement real API call to fetch robot state.
        """
        if not self._token:
            raise RuntimeError("Not authenticated to MyDolphin Plus")

        # Placeholder data
        return {
            "online": True,
            "mode": "clean",
            "status": "running",
            "battery": 100,
        }

    def send_command(self, command: str) -> None:
        """
        TODO: Implement real API call to send a command to the robot.
        """
        if not self._token:
            raise RuntimeError("Not authenticated to MyDolphin Plus")

        LOGGER.info("Sending command to robot via MyDolphin Plus: %s", command)
        # Placeholder: no-op for now


# ---------------------------------------------------------------------------
# MQTT Proxy
# ---------------------------------------------------------------------------

class DolphinMQTTProxy:
    def __init__(
        self,
        mqtt_host: str,
        mqtt_port: int,
        mqtt_topic_prefix: str,
        dolphin_email: str,
        dolphin_password: str,
        poll_interval: int = 30,
    ):
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._topic_prefix = mqtt_topic_prefix.rstrip("/")
        self._poll_interval = poll_interval

        self._dolphin = MyDolphinClient(dolphin_email, dolphin_password)

        self._mqtt = mqtt.Client()
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message

        self._stop = False

    # ---------- MQTT callbacks ----------

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            LOGGER.info("Connected to MQTT broker at %s:%s", self._mqtt_host, self._mqtt_port)
            cmd_topic = f"{self._topic_prefix}/command"
            LOGGER.info("Subscribing to command topic: %s", cmd_topic)
            client.subscribe(cmd_topic)
        else:
            LOGGER.error("Failed to connect to MQTT broker, rc=%s", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8").strip()
            LOGGER.info("Received MQTT message on %s: %s", msg.topic, payload)
            self._dolphin.send_command(payload)
        except Exception as exc:
            LOGGER.exception("Error handling MQTT message: %s", exc)

    # ---------- Main loops ----------

    def _poll_loop(self):
        while not self._stop:
            try:
                state = self._dolphin.get_robot_state()
                topic = f"{self._topic_prefix}/state"
                payload = json.dumps(state)
                LOGGER.info("Publishing robot state to %s: %s", topic, payload)
                self._mqtt.publish(topic, payload, qos=1, retain=True)
            except Exception as exc:
                LOGGER.exception("Error polling robot state: %s", exc)

            time.sleep(self._poll_interval)

    def start(self):
        LOGGER.info("Starting Dolphin MQTT Proxy")

        # Login to MyDolphin Plus
        self._dolphin.login()

        # Connect to MQTT
        LOGGER.info("Connecting to MQTT broker at %s:%s", self._mqtt_host, self._mqtt_port)
        self._mqtt.connect(self._mqtt_host, self._mqtt_port, keepalive=60)

        # Start MQTT loop in background thread
        mqtt_thread = threading.Thread(target=self._mqtt.loop_forever, daemon=True)
        mqtt_thread.start()

        # Start polling loop (blocking)
        self._poll_loop()

    def stop(self):
        self._stop = True
        try:
            self._mqtt.disconnect()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main entrypoint — loads config from /data/options.json
# ---------------------------------------------------------------------------

def main():
    # Load add-on options
    with open("/data/options.json", "r") as f:
        opts = json.load(f)

    mqtt_host = opts.get("mqtt_host", "core-mosquitto")
    mqtt_port = opts.get("mqtt_port", 1883)
    mqtt_topic_prefix = opts.get("topic_prefix", "dolphin")

    dolphin_email = opts.get("email")
    dolphin_password = opts.get("password")

    poll_interval = opts.get("poll_interval", 30)

    proxy = DolphinMQTTProxy(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic_prefix=mqtt_topic_prefix,
        dolphin_email=dolphin_email,
        dolphin_password=dolphin_password,
        poll_interval=poll_interval,
    )

    try:
        proxy.start()
    except KeyboardInterrupt:
        LOGGER.info("Stopping Dolphin MQTT Proxy")
        proxy.stop()


if __name__ == "__main__":
    main()
