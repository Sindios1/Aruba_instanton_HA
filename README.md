# Aruba Instant On Home Assistant Integration

This is a custom integration for Home Assistant to monitor HPE Aruba Instant On products.

## Features
- **Site Health**: Overall status of the site.
- **Client Counts**: Wired and wireless client counts.
- **Device Status**: Inventory tracking for APs and Switches.
- **Alerts**: Binary sensor for site alerts.

## Installation

### Via HACS (Recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed.
2. In HACS, go to **Integrations**.
3. Click the three dots in the top right corner and select **Custom repositories**.
4. Add `https://github.com/Sindios1/Aruba_instanton_HA` with category `Integration`.
5. Click **Add** and then install the **Aruba Instant On** integration.
6. Restart Home Assistant.

### Manual Installation
Copy the `custom_components/aruba_instant_on` directory to your Home Assistant `custom_components` folder and restart HA.

## Disclaimer
This integration uses an unofficial API and is not supported by HPE/Aruba. Use at your own risk.
