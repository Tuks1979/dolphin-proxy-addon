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
# MyDolphin Plus API Client (real implementation)
# ---------------------------------------------------------------------------

class MyDolphinClient:
    BASE_URL = "https://prod-api.maytronics.com"

    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password
        self._token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._robot_id: Optional[str] = None
        self._client = httpx.Client(timeout=10.0)

    # ---------------------------
    # Authentication
    # ---------------------------
    def login(self) -> None:
        LOGGER.info("Authenticating with MyDolphin Plus cloud...")

        resp = self._client.post(
            f"{self.BASE_URL}/auth/login",
            json={"email": self._email, "password": self._password},
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Login failed: {resp.text}")

        data = resp.json()
        self._token = data["token"]
        self._user_id = data["userId"]

        LOGGER.info("Login successful. User ID: %s", self._user_id)

        # Fetch robot list
        self._fetch_robot_id()

    # ---------------------------
    # Robot discovery
    # ---------------------------
    def _fetch_robot_id(self):
        LOGGER.info("Fetching robot list...")

        resp = self._client.get(
            f"{self.BASE_URL}/users/{self._user_id}/robots",
            headers={"Authorization": f"Bearer {self._token}"},
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch robots: {resp.text}")

        robots = resp.json()
        if not robots:
            raise RuntimeError("No robots found in your account")

        # For now, pick the first robot
        robot = robots[0]
        self._robot_id = robot["id"]

        LOGGER.info("Using robot: %s (%s)", robot["name"], self._robot_id)

    # ---------------------------
    # Robot status
    # ---------------------------
    def get_robot_state(self) -> dict:
        if not self._token or not self._robot_id:
            raise RuntimeError("Not authenticated or robot not selected")

        resp = self._client.get(
            f"{self.BASE_URL}/robots/{self._robot_id}/status",
            headers={"Authorization": f"Bearer {self._token}"},
        )

        if resp.status_code != 200:
            LOGGER.error("Error fetching robot state: %s", resp.text)
            return {"online": False}

        return resp.json()

    # ---------------------------
    # Commands
    # ---------------------------
    def send_command(self, command: str) -> None:
        if not self._token or not self._robot_id:
            raise RuntimeError("Not authenticated or robot not selected")

        LOGGER.info("Sending command to robot: %s", command)

        resp = self._client.post(
            f"{self.BASE_URL}/robots/{self._robot_id}/command",
            headers={"Authorization": f"Bearer {self._token}"},
            json={"command": command},
        )

        if resp.status_code != 200:
            LOGGER.error("Command failed: %s", resp.text)
        else:
            LOGGER.info("Command accepted by cloud")


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
