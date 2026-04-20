# Constants for the integration
DOMAIN = "growatt_modbus"
PLATFORMS = ["sensor"]

DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
DEFAULT_REGISTERS = [3, 4]  # [voltage_reg, current_reg]
DEFAULT_MONITOR_INTERVAL = 5  # seconds
DEFAULT_TIMEOUT = 5  # seconds
