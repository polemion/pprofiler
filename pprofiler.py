# -*- coding: utf-8 -*-

# Power Profile Manager, Copyright (C) <2025~>  <Dimitrios Koukas>
# You may contact me in my web address here: https://www.dnkoukas.xyz/contact-me/

#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published
#   by the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Main

import wx
import wx.adv
import argparse
from argparse import Namespace
import sys
import os
import subprocess
import shlex
from typing import Dict, List
from subprocess import PIPE, DEVNULL, TimeoutExpired

__appname__ = 'Power Profile Manager'
__author__ = 'Dimitrios Koukas'
__website__ = 'https://github.com/polemion/pprofiler'
__version__ = '1.0'
__license__ = 'GNU Affero General Public License (GNU GPL-3.0),\n see https://www.gnu.org/licenses/'
__contact__ = 'https://www.dnkoukas.xyz/contact-me/'

if getattr(sys, 'frozen', False):
    APP_PATH = sys._MEIPASS
else:
    APP_PATH = os.path.dirname(os.path.abspath(__file__))

CONF = {
    'powerprofilesctl': '/usr/bin/powerprofilesctl',
    'powerprofilesctl.excluded.lines': (
        'CpuDriver:',
        'Degraded:',
        'PlatformDriver:'
    ),
    'powerprofilesctl.cmds': {
        'list': 'list',
        'set': 'set',
        'get': 'get'
    },

    'parser.timeout': 1,

    'systray.icon.state': {
        'performance': None,
        'power-saver': None,
        'balanced': None
    },

    'systray.mouse.reverse': False,
    'default.icon': wx.ART_INFORMATION,
    'profile.refresh.time': 3000,

    'system.theme': '',
    'system.theme.force': False
}

def parse_args() -> Namespace:
    argsin = argparse.ArgumentParser(description=f'{__appname__} v.{__version__}')
    argsin.add_argument('-m', '--mouse-reverse', action='store_true', help='Reverse systray mouse button events.')
    argsin.add_argument('-f', '--force-theme', choices=['dark', 'light'],  help='Force icon theme to dark or light.')
    argsin.add_argument('-v', '--version', action='version', version=f'{__appname__} v{__version__}', help='Show version')
    return argsin.parse_args()


def logger(msg) -> None:
    """
    Logs a message to the console.

    :param msg: Message to be logged.
    """
    print(msg)


def get_icon(image_path) -> wx.Icon:
    """
    Construct an icon for wxPython.

    :param image_path: Path to the image file to use as the icon.
    """
    bitmap = wx.Bitmap(image_path, wx.BITMAP_TYPE_ANY)
    icon = wx.Icon()
    icon.CopyFromBitmap(bitmap)
    return icon


def parser(command: str) -> Dict[str, List[str]]:
    """
    Parses the output of a shell command, and returns a
    dictionary with the error code and output lines.

    :param command: Shell command to be executed.
    :return: Dictionary containing 'error.code' and 'output'.
    """
    result = {
        'error.code': '0',
        'output': []
    }

    try:
        with subprocess.Popen(shlex.split(command), stdout=PIPE, stderr=DEVNULL, text=True) as proc:
            stdout, _ = proc.communicate(timeout=CONF['parser.timeout'])
        result['error.code'] = str(proc.returncode)
        result['output'] = [line.strip() for line in stdout.splitlines()]
    except TimeoutExpired:
        result['error.code'] = '1'
        result['output'] = []
    return result


class PowerCtl:
    """
    Interface for interacting with the 'powerprofilesctl' command.
    """

    def __init__(self) -> None:
        self.command: str = CONF['powerprofilesctl']

    def get_profiles(self) -> Dict[str, List[str]]:
        """
        Retrieves available power profiles.

        :return: Dictionary containing 'error.code' and 'profiles'.
        """
        excluded = CONF['powerprofilesctl.excluded.lines']
        parsed = parser(f'{self.command} {CONF["powerprofilesctl.cmds"]["list"]}')
        return {
            'error.code': parsed['error.code'],
            'profiles': [
                line.replace('*', '').replace(':', '').strip()
                for line in parsed['output']
                if line and not any([x in line for x in excluded])
            ]
        }

    def set_profile(self, profile: str) -> bool:
        """
        Sets the power profile.

        :param profile: Name of the power profile to set.
        :return: True if the profile was set successfully, False otherwise.
        """
        logger(f'Set profile: {profile}')
        return parser(f'{self.command} {CONF["powerprofilesctl.cmds"]["set"]} {profile}')['error.code'] == '0'

    def get_active_profile(self) -> Dict[str, str]:
        """
        Retrieves the currently active power profile.

        :return: Dictionary containing 'error.code' and 'profile' (active profile).
        """
        parsed = parser(f'{self.command} {CONF["powerprofilesctl.cmds"]["get"]}')
        return {
            'error.code': parsed['error.code'],
            'profile': next((line for line in parsed['output'] if line), '')
        }


class SystrayIcon(wx.adv.TaskBarIcon):
    """Systray functions."""

    def __init__(self, icon: wx.Icon, powerctl: PowerCtl) -> None:
        super().__init__()
        self.icon = icon
        self.powerctl = powerctl
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_click if not CONF['systray.mouse.reverse'] else self.on_right_click)
        self.Bind(wx.adv.EVT_TASKBAR_RIGHT_DOWN, self.on_right_click if not CONF['systray.mouse.reverse'] else self.on_left_click)
        self.current_profile = ''
        self.update_icon()

    def update_icon(self) -> None:
        active_profile = self.powerctl.get_active_profile()['profile']
        if active_profile != self.current_profile:
            self.current_profile = active_profile
            icon = CONF['systray.icon.state'].get(active_profile, CONF['systray.icon.state']['balanced'])
            self.SetIcon(icon, 'Active Profile: ' + active_profile)

    def create_left_click_menu(self) -> wx.Menu:
        menu = wx.Menu()
        profiles = self.powerctl.get_profiles()['profiles']
        active_profile = self.powerctl.get_active_profile()['profile']
        local_vars = {}
        for n, profile in enumerate(profiles):
            local_vars[f'item{n}'] = menu.AppendRadioItem(wx.ID_ANY, profile)
            if profile == active_profile:
                local_vars[f'item{n}'].Check()
            self.Bind(wx.EVT_MENU, lambda event, p=profile: self.powerctl.set_profile(p), local_vars[f'item{n}'])
        return menu

    def create_right_click_menu(self) -> wx.Menu:
        menu = wx.Menu()
        about_item = menu.Append(wx.ID_ANY, 'About')
        menu.AppendSeparator()
        quit_item = menu.Append(wx.ID_EXIT, 'Exit')
        self.Bind(wx.EVT_MENU, self.on_about, about_item)
        self.Bind(wx.EVT_MENU, self.on_quit, quit_item)
        return menu

    def on_left_click(self, event: wx.adv.TaskBarIconEvent) -> None:
        self.PopupMenu(self.create_left_click_menu())

    def on_right_click(self, event: wx.adv.TaskBarIconEvent) -> None:
        self.PopupMenu(self.create_right_click_menu())

    def on_about(self, event: wx.Event) -> None:
        about_info = wx.adv.AboutDialogInfo()
        about_info.SetName(__appname__)
        about_info.SetVersion(f'Version: {__version__}')
        about_info.SetCopyright(f'Copyright (c) 2025~ {__author__}')
        about_info.SetLicense(f'\n{__license__}\n\nContact: {__contact__}')
        about_info.SetWebSite(__website__)
        about_info.SetIcon(self.icon)
        wx.adv.AboutBox(about_info)

    def on_quit(self, event: wx.Event) -> None:
        self.RemoveIcon()
        self.Destroy()
        wx.GetApp().on_exit(event)
        logger('Exited.')


class MainApp(wx.App):
    """Main."""

    def __init__(self, redirect: bool) -> None:
        super().__init__(redirect)

    def OnInit(self) -> bool:
        self.frame = wx.Frame(None, -1)
        self.SetTopWindow(self.frame)
        self.set_theme_style()
        self.set_icons()
        self.systray = SystrayIcon(CONF['systray.icon.state']['balanced'], PowerCtl())
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(CONF['profile.refresh.time'])
        return True

    def set_theme_style(self) -> None:
        if not CONF['system.theme.force']:
            CONF['system.theme'] = 'dark' if wx.SystemSettings.GetAppearance().IsDark() else 'light'

    def os_theme_style_changed(self) -> bool:
        """
        Checks if the current OS theme style has changed.

        :return: True if the current OS theme matches the stored theme in the configuration,
                 False otherwise.
        """
        cur_theme = 'dark' if wx.SystemSettings.GetAppearance().IsDark() else 'light'
        return CONF['system.theme'] == cur_theme

    def set_icons(self) -> None:
        """Parse images in App's current directory to use, otherwise revert to default."""
        cur_image_files = [x for x in os.listdir(os.path.join(APP_PATH, CONF['system.theme'])) if x.lower().endswith('.png')]
        for image_file in cur_image_files:
            img_tmp = image_file.split('.')[0]
            if img_tmp in CONF['systray.icon.state']:
                CONF['systray.icon.state'][img_tmp] = get_icon(os.path.join(APP_PATH, CONF['system.theme'], image_file))
        for profile_status in CONF['systray.icon.state']:
            if CONF['systray.icon.state'][profile_status] is None:
                CONF['systray.icon.state'][profile_status] = wx.ArtProvider.GetIcon(CONF['default.icon'])

    def on_timer(self, event: wx.TimerEvent) -> None:
        if self.os_theme_style_changed():
            self.set_theme_style()
            self.set_icons()
        self.systray.update_icon()

    def on_exit(self, event: wx.CloseEvent) -> None:
        self.timer.Stop()
        self.frame.Destroy()
        self.ExitMainLoop()


if __name__ == '__main__':
    args = parse_args()
    if args.mouse_reverse:
        CONF['systray.mouse.reverse'] = True
        logger('Info: Mouse buttons reversed.')
    if args.force_theme:
        CONF['system.theme.force'] = True
        CONF['system.theme'] = args.force_theme
        logger(f'Forcing icon theme: {args.force_theme}')
    app = MainApp(False)
    app.MainLoop()
