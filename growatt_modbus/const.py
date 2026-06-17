# Constants for the integration
from homeassistant.components.sensor import SensorDeviceClass

DOMAIN = "growatt_modbus"
PLATFORMS = ["sensor"]

DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
DEFAULT_REGISTERS = [3, 4]  # [voltage_reg, current_reg]
DEFAULT_MONITOR_INTERVAL = 5  # seconds
DEFAULT_TIMEOUT = 5  # seconds

SENSORS = {
    "sensor_1": {
        "register_address": 3, "name": "Voltage", "key": "voltage", "friendly_name": "Voltage",
        "scaling_factor": 0.1, "unit": "V", "device_class": SensorDeviceClass.VOLTAGE,
    },
    "sensor_2": {
        # Make this a proper current sensor (was inconsistent before)
        "register_address": 4, "name": "Current", "key": "current", "friendly_name": "Current", "scaling_factor": 0.1,
        "unit": "A", "device_class": SensorDeviceClass.CURRENT,
    },
    # Add more sensors here as needed.
}

DEFAULT_SENSOR_KEYS = list(SENSORS.keys())  # For default initialization.
