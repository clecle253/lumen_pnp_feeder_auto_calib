# LumenPnP Plugin for OpenPnP

A comprehensive Python-based GUI plugin for OpenPnP, designed specifically for LumenPnP machines.

## Features

### 1. Feeder Calibration
- **Slot Calibration**: Automatically calibrate fiducial positions for all feeders
- **Pocket Calibration** (Coming Soon): Detect and calibrate component pocket positions
- Pre-calibration feeder scanning
- Retry logic for failed detections
- Real-time progress tracking

### 2. KiCad Import (Coming Soon)
- Import KiCad PCB files
- Parse BOM CSV files
- Automatic component mapping
- Board configuration generation

### 3. Fast Travel Navigation (Coming Soon)
- Visual machine workspace map
- Click-to-move functionality
- Feeder position visualization
- Component ID labels

## Installation

1. Copy the `LumenPnP` folder and `LumenPnP_Plugin.py` to your OpenPnP scripts directory
2. In OpenPnP, go to `Scripts` menu
3. Run `LumenPnP_Plugin.py`

## Usage

The plugin opens in a separate window with three tabs:

### Feeder Calibration Tab
1. Click "Scan Feeders" to check for issues
2. Select feeders from the list (or leave all selected)
3. Click "Calibrate Slots" to start calibration
4. Monitor progress in the log panel

## Requirements

- OpenPnP 2023-04-05 or later
- Python/Jython with Tkinter support
- LumenPnP machine with configured feeders

## Development

### Project Structure
```
LumenPnP/
├── __init__.py
├── gui/
│   ├── __init__.py
│   └── main_window.py      # Main GUI window
└── core/
    ├── __init__.py
    ├── calibration.py      # Calibration logic (future)
    ├── kicad_parser.py     # KiCad import (future)
    └── navigation.py       # Fast travel (future)
```

## Version

0.1.0 - Initial release with basic GUI framework

## License

MIT License
