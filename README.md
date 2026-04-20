# Growatt Modbus Integration

A Home Assistant custom integration for reading real-time PV1 data from Growatt solar inverters (tested with Growatt 2000 TTLX with a ShineWiLan-X2 Wifi dongle) via Modbus TCP at a frequency of between 5 seconds and any value you want.

This is an alternative to getting these values from the default "Growatt Server" integration available in Home Assistant since this integration defaults to a minimum of 5 minute update interval via the Growatt API (this is a limitation of the Growatt API server).

## Features

- **Real-time monitoring** of voltage, current, and power from your Growatt inverter
- **Configurable update interval** — adjust how often data is fetched (default: 5 seconds)
- **Last-known values** — sensors display the most recent successful reading even if the inverter is temporarily unavailable
- **Automatic retry** — connection failures trigger automatic reconnection attempts
- **Multiple inverter support** — add multiple inverters with different configurations
- **Debug sensor** — view raw data and diagnostics

## Requirements

- Home Assistant 2026.1 or later (tested with 2026.4.x) 
- Growatt inverter with Modbus TCP enabled
- Network connectivity between Home Assistant and the inverter

## Installation

### Manual Installation

1. download the files from https://github.com/tgip/hass_growatt_modbus
2. Copy the `growatt_modbus` folder to your `custom_components` directory:

```~/.homeassistant/custom_components/growatt_modbus/```

3. Restart Home Assistant:

```Settings → System → Restart```

4. Add the integration:

```Settings → Devices & Services → Add integration → Growatt Modbus```

## Configuration

### Basic Setup

1. Go to **Settings → Devices & Services**
2. Search for **Growatt Modbus**
3. Click **Add entry**
4. Enter the following information:
- **Device Name**: A friendly name for your inverter (e.g., `Growatt`)
- **Host**: IP address of your Growatt inverter (e.g., `192.168.1.100`)
- **Port**: Modbus TCP port (default: `502`)
- **Unit ID**: Modbus unit ID (default: `1`)

### Advanced Configuration

You can optionally override default settings:

| Option | Default | Description |
|--------|---------|-------------|
| **Registers** | [3, 4] | Modbus register addresses for voltage (3) and current (4) |
| **Monitor Interval** | minimum default 5 seconds | How often to fetch data from the inverter |
| **Timeout** | default 5 seconds | Modbus connection timeout |

### Finding Your Inverter's IP Address

1. Log in to your router's admin interface
2. Check the connected devices list
3. Look for your Growatt inverter's hostname (usually contains "Growatt")
4. Note the IP address

### Enabling Modbus TCP on Your Inverter

1. Access your inverter's web interface (usually at `http://<inverter_ip>`)
2. Log in with your credentials
3. Navigate to **Settings → Communication → Modbus TCP**
4. Enable Modbus TCP
5. Note the port (usually `502` or `8899`)
6. Restart the inverter

## Sensors

Once configured, the following sensors are automatically created:

| Sensor | Unit | Description |
|--------|------|-------------|
| `sensor.growatt_voltage` | V | PV1 input voltage |
| `sensor.growatt_current` | A | PV1 input current |
| `sensor.growatt_power` | W | PV1 input power (calculated as voltage × current) |
| `sensor.growatt_debug_data` | — | Debug sensor with raw register data |

### Example Automation

Monitor when power drops below 100W:

```yaml
automation:
- alias: "Growatt Power Low"
 trigger:
   platform: numeric_state
   entity_id: sensor.growatt_power
   below: 100
 action:
   service: notify.notify
   data:
     message: "PV power is below 100W"
```

Example Template Sensor

Create daily energy totals in configuration.yaml:
```yaml
template:
  - sensor:
      - name: "Growatt Daily Energy"
        unique_id: growatt_daily_energy
        unit_of_measurement: "kWh"
        icon: mdi:solar-power
        state: "{{ states('sensor.growatt_power') | float(0) / 1000 }}"
```

Troubleshooting
Integration Won't Set Up

Error: "Could not connect to inverter"

    Verify the inverter's IP address is correct
    Confirm Modbus TCP is enabled on the inverter
    Check that the port number is correct (default: 502)
    Verify network connectivity between Home Assistant and the inverter:
    bash

    ping <inverter_ip>

    Check Home Assistant logs for more details:

    Settings → System → Logs

No Data / Sensors Show Unknown

Error: "Modbus error ... Using last known values"

    Verify the Modbus register addresses are correct for your inverter model
    Check that the Unit ID matches your inverter configuration (usually 1)
    Increase the Timeout value if you have a slow network
    View the debug sensor to see raw register values:
        Go to Developer Tools → States
        Search for sensor.growatt_debug_data

Connection Drops Frequently

    Increase the Timeout value (try 10 seconds)
    Check network stability between Home Assistant and the inverter
    Verify the inverter isn't overheating (check inverter logs)
    Move Home Assistant closer to the inverter or improve network connectivity

Debug Sensor Shows No Data

The debug sensor displays OK when readings are successful and stores raw data in extra_state_attributes. To view:

    Go to Developer Tools → States
    Click on sensor.growatt_debug_data
    Expand the attributes section to see voltage, current, and power values

Register Reference

By default, the integration reads from:

    Register 3: PV1 voltage (0.1 V scaling)
    Register 4: PV1 current (0.1 A scaling)

For other Growatt models, consult your inverter's Modbus documentation to find the correct register addresses.
Common Register Addresses

| Data          | Typical Register | Scaling |
|---------------|------------------|---------|
| PV Voltage    | 3                | 0.1 V   |
| PV Current    | 4                | 0.1 A   |
| PV Power      | 5                | 1 W     |
| Grid Voltage  | 35               | 0.1 V   |  
| Grid Frequency| 37               | 0.01 Hz | 

### Performance Notes

    Update interval is set to 5 seconds by default — reduce this if you need faster updates, but be aware this increases network traffic
    The integration retains last-known values if the inverter is temporarily unavailable, preventing sensor gaps
    Connection failures trigger automatic retry with exponential backoff
    All Modbus reads use short timeouts (default 5 seconds) to prevent Home Assistant from hanging

### Contributing

Found a bug or want to improve the integration? Feel free to open an issue or submit a pull request.

### License
APACHE 2.0

## This integration is provided as-is for use with Home Assistant.

### Support

For issues specific to this integration, check the Home Assistant Community Forums.

For Growatt inverter support, consult your inverter's manual or visit the Growatt website.
