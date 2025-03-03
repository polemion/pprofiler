# Power Profile System Tray App

A system tray (only) application for managing power profiles using `powerprofilesctl` on Linux.

I made it for Linux Mint XFCE, which I am using, since it has no widget to change the profile in the GUI as of February 2025.

## Features
- System tray icon updates based on the active power profile.
- Left-click menu to switch profiles (with active profile shown).
- It detects whether the desktop is using a light or dark theme, but it can also be forced to use light or dark themed icons, as well as overriding them in the included icon directories.

## Notes
- Should work on any Linux system using `powerprofilesctl` with a desktop environment that supports system tray icons.
- The icons used, are modified Adwaita icons (but can be overriden).

## Requirements
It was designed against the following, but lesser versions should suffice:
- Python 3.12.0
- wxPython 4.2.2 (no other external library).

It should work out of the box in Ubuntu 24.x based distros (like Linux Mint 22.x), otherwise, a virtual environment is required to run it directly by the Python source.


### Available Flags
```commandline
options:
  -h, --help            show this help message and exit
  -m, --mouse-reverse   Reverse systray mouse button events.
  -f, --force-theme     {dark,light}
                        Force icon theme to dark or light.
  -v, --version         Show version

```

## License
GPL-3.0 License
