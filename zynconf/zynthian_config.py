# -*- coding: utf-8 -*-
# ********************************************************************
# ZYNTHIAN PROJECT: Zynthian Config Library
#
# Zynthian Config library and tools
#
# Copyright (C) 2015-2023 Fernando Moyano <jofemodo@zynthian.org>
#
# ********************************************************************
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
#
# ********************************************************************

import os
import re
import socket
import psutil
import logging
from time import sleep
from shutil import copyfile
from subprocess import check_output
from collections import OrderedDict

# -------------------------------------------------------------------------------
# Configure logging
# -------------------------------------------------------------------------------

#logging.getLogger(__name__).setLevel(logging.ERROR)

# -------------------------------------------------------------------------------
# UI Definitions
# -------------------------------------------------------------------------------

CustomSwitchActionType = [
	"NONE",
	"UI_ACTION_PUSH",
	"UI_ACTION_RELEASE",
	"MIDI_CC",
	"MIDI_CC_SWITCH",
	"MIDI_NOTE",
	"MIDI_PROG_CHANGE",
	"MIDI_CLOCK",
	"MIDI_TRANSPORT_START",
	"MIDI_TRANSPORT_CONTINUE",
	"MIDI_TRANSPORT_STOP",
	"CVGATE_IN",
	"CVGATE_OUT",
	"GATE_OUT"
]

ZynSensorActionType = [
	"NONE",
	"MIDI_CC",
	"MIDI_PITCH_BEND",
	"MIDI_CHAN_PRESS"
]

NoteCuiaDefault = {
	"0": "POWER_OFF",
	"2": "REBOOT",
	"4": "RESTART_UI",
	"5": "RELOAD_MIDI_CONFIG",
	"7": "RELOAD_KEY_BINDING",
	"9": "RELOAD_WIRING_LAYOUT",
	"11": "LAST_STATE_ACTION",
	"12": "ALL_NOTES_OFF",
	"14": "ALL_SOUNDS_OFF",
	"24": "TOGGLE_AUDIO_RECORD",
	"26": "START_AUDIO_RECORD",
	"28": "STOP_AUDIO_RECORD",
	"29": "TOGGLE_AUDIO_PLAY",
	"31": "START_AUDIO_PLAY",
	"33": "STOP_AUDIO_PLAY",
	"36": "TOGGLE_MIDI_RECORD",
	"38": "START_MIDI_RECORD",
	"40": "STOP_MIDI_RECORD",
	"41": "TOGGLE_MIDI_PLAY",
	"43": "START_MIDI_PLAY",
	"45": "STOP_MIDI_PLAY",
	"48": "ARROW_UP",
	"50": "ARROW_DOWN",
	"52": "ARROW_RIGHT",
	"53": "ARROW_LEFT",
	"55": "BACK",
	"57": "SELECT",
	"60": "SCREEN_MAIN_MENU",
	"62": "SCREEN_ADMIN",
	"64": "SCREEN_AUDIO_MIXER",
	"65": "SCREEN_SNAPSHOT",
	"67": "SCREEN_ALSA_MIXER",
	"69": "SCREEN_MIDI_RECORDER",
	"71": "SCREEN_ZYNPAD",
	"72": "SCREEN_PATTERN_EDITOR",
	"74": "SCREEN_BANK",
	"76": "SCREEN_PRESET",
	"77": "SCREEN_CALIBRATE",
	"79": "LAYER_CONTROL",
	"81": "LAYER_OPTIONS",
	"83": "MENU",
	"84": "PRESET",
	"86": "FAVS",
	"90": "ZYNSWITCH 0",
	"91": "ZYNSWITCH 1",
	"92": "ZYNSWITCH 2",
	"93": "ZYNSWITCH 3",
	"94": "ZYNSWITCH 4",
	"95": "ZYNSWITCH 5",
	"96": "ZYNSWITCH 6",
	"97": "ZYNSWITCH 7",
	"98": "ZYNSWITCH 8",
	"99": "ZYNSWITCH 9",
	"100": "ZYNSWITCH 10",
	"101": "ZYNSWITCH 11",
	"102": "ZYNSWITCH 12",
	"103": "ZYNSWITCH 13",
	"104": "ZYNSWITCH 14",
	"105": "ZYNSWITCH 15",
	"106": "ZYNSWITCH 16",
	"107": "ZYNSWITCH 17",
	"108": "ZYNSWITCH 18",
	"109": "ZYNSWITCH 19",
	"110": "ZYNSWITCH 20",
	"111": "ZYNSWITCH 21",
	"112": "ZYNSWITCH 22",
	"113": "ZYNSWITCH 23",
	"114": "ZYNSWITCH 24",
	"115": "ZYNSWITCH 25",
	"116": "ZYNSWITCH 26",
	"117": "ZYNSWITCH 27",
	"118": "ZYNSWITCH 28",
	"119": "ZYNSWITCH 29",
	"120": "ZYNSWITCH 30",
	"121": "ZYNSWITCH 31",
	"122": "ZYNSWITCH 32",
	"123": "ZYNSWITCH 33",
	"124": "ZYNSWITCH 34",
	"125": "ZYNSWITCH 35",
	"126": "ZYNSWITCH 36",
	"127": "ZYNSWITCH 37"
}

# -------------------------------------------------------------------------------
# Global variables
# -------------------------------------------------------------------------------

sys_dir = os.environ.get('ZYNTHIAN_SYS_DIR', "/zynthian/zynthian-sys")
config_dir = os.environ.get('ZYNTHIAN_CONFIG_DIR', '/zynthian/config')
config_fpath = config_dir + "/zynthian_envars.sh"

# -------------------------------------------------------------------------------
# Config management
# -------------------------------------------------------------------------------


def get_midi_config_fpath(fpath=None):
	if not fpath:
		fpath = os.environ.get("ZYNTHIAN_SCRIPT_MIDI_PROFILE",
			os.environ.get("ZYNTHIAN_MY_DATA_DIR", "/zynthian/zynthian-my-data") + "/midi-profiles/default.sh")
	if not os.path.isfile(fpath):
		#Try to copy from default template
		default_src = "%s/config/default_midi_profile.sh" % os.getenv('ZYNTHIAN_SYS_DIR', "/zynthian/zynthian-sys")
		copyfile(default_src, fpath)

	return fpath


def load_config(set_env=True, fpath=None):
	global config_fpath
	if not fpath:
		fpath = config_fpath

	# Get config file content
	with open(fpath) as f:
		lines = f.readlines()

	# Load config varnames
	varnames = []
	pattern = re.compile("^export ([^\s]*?)=")
	for line in lines:
		res = pattern.match(line)
		if res:
			varnames.append(res.group(1))
			#logging.debug("CONFIG VARNAME: %s" % res.group(1))

	# Execute config script and dump environment
	env = check_output("source \"{}\";env".format(fpath), shell=True, universal_newlines=True, executable="/bin/bash")

	# Parse environment dump
	config = {}
	pattern = re.compile("^([^=]*)=(.*)$")
	lines = env.split("\n")
	for line in lines:
		res = pattern.match(line)
		if res:
			vn = res.group(1)
			if vn in varnames:
				val = res.group(2)
				config[vn] = val
				#logging.debug("CONFIG VAR: %s=%s" % (vn,val))
				# Set local environment
				if set_env:
					os.environ[vn] = val

	return config


def save_config(config, updsys=False, fpath=None):
	global config_fpath
	if not fpath:
		fpath = config_fpath

	# Get config file content
	with open(fpath) as f:
		lines = f.readlines()

	# Find and replace lines to update
	updated = []
	add_row = 0
	pattern = re.compile("^export ([^\s]*?)=")
	for i, line in enumerate(lines):
		res = pattern.match(line)
		if res:
			varname = res.group(1)
			if varname in config:
				value = config[varname].replace("\n", "\\n")
				value = value.replace("\r", "")
				os.environ[varname] = value
				lines[i] = "export %s=\"%s\"\n" % (varname, value)
				updated.append(varname)
				#logging.debug(lines[i])

		if line.startswith("# Directory Paths"):
			add_row = i-1

	if add_row == 0:
		add_row = len(lines)

	# Add the rest
	vars_to_add = set(config.keys())-set(updated)
	for varname in vars_to_add:
		value = config[varname].replace("\n", "\\n")
		value = value.replace("\r", "")
		os.environ[varname] = value
		lines.insert(add_row, "export %s=\"%s\"\n" % (varname, value))
		#logging.info(lines[add_row])

	# Write updated config file
	with open(fpath, 'w') as f:
		f.writelines(lines)
		f.flush()
		os.fsync(f.fileno())

	# Update System Configuration
	if updsys:
		update_sys()


def update_sys():
	try:
		os.environ['ZYNTHIAN_FLAG_MASTER'] = "NONE"
		check_output(os.environ.get('ZYNTHIAN_SYS_DIR') + "/scripts/update_zynthian_sys.sh", shell=True)
	except Exception as e:
		logging.error("Updating Sytem Config: %s" % e)

# -------------------------------------------------------------------------------
# MIDI Config
# -------------------------------------------------------------------------------


def load_midi_config(set_env=True, fpath=None):
	return load_config(set_env, get_midi_config_fpath(fpath))


def update_midi_profile(params, fpath=None):
	if not fpath:
		fpath = get_midi_config_fpath()

	midi_params = OrderedDict()
	for k, v in params.items():
		if k.startswith('ZYNTHIAN_MIDI'):
			if isinstance(v, list):
				midi_params[k] = v[0]
			else:
				midi_params[k] = v

	save_config(midi_params, False, fpath)

	for k in midi_params:
		del params[k]


# -------------------------------------------------------------------------------
# Network Info
# -------------------------------------------------------------------------------

def get_wifi_list():
	# Get list of configured networks
	configured_wifi = []
	rows = check_output(["nmcli", "--terse", "con", "show"], encoding='utf-8').split("\n")
	for row in rows:
		parts = row.split(":")
		if len(parts) > 3:
			nw_type = parts[-2]
			name = parts[-4]
			if nw_type == "802-11-wireless":
				configured_wifi.append(name)

	# Check if access point connection does exist,
	# and create it if needed
	if "zynthian-ap" not in configured_wifi:
		logging.info("Creating Wi-Fi Access Point connection 'zynthian'...")
		check_output(f"{self.sys_dir}/sbin/create_wifi_access_point.sh", encoding='utf-8')

	# Get list of available networks
	wifi_data = []
	ap_enabled = False
	rows = check_output(["nmcli", "--terse", "dev", "wifi", "list"], encoding='utf-8').split("\n")
	for row in rows:
		parts = row.split(":")
		if len(parts) > 8:
			signal = parts[-3]
			bars = parts[-2]
			ssid = parts[-7]
			if signal == "0":
				ap_enabled = True
				continue
			if ssid in configured_wifi:
				configured = True
			else:
				configured = False
			rate = parts[-4].replace("Mbit/s", "Mbs")
			if parts[0] == "*":
				enabled = True
				bullet = "\u2612"
			else:
				enabled = False
				bullet = "\u2610"
			title = f"{bullet} {bars} {ssid} ({rate})"
			wifi_data.append((ssid, 0, title, configured, enabled))

	# Add Access Point
	if ap_enabled:
		bullet = "\u2612"
	else:
		bullet = "\u2610"
	title = f"{bullet} Wi-Fi Access Point zynthian"
	wifi_data.append(("zynthian-ap", 0, title, True, ap_enabled))

	return wifi_data


def get_nwdev_all_status(devname):
	status = {}
	try:
		rows = check_output(["nmcli", "--terse", "dev", "show", devname], encoding='utf-8').split("\n")
		for row in rows:
			parts = row.split(":", 2)
			if len(parts) > 1:
				status[parts[0]] = parts[1]
	except Exception as e:
		logging.error(f"Can't get status for '{devname}': {e}")
	return status


def get_nwdev_status_code(devname):
	try:
		return int(get_nwdev_all_status(devname)["GENERAL.STATE"].split(" ")[0])
	except:
		return -1


def get_nwdev_status_string(devname):
	try:
		status = get_nwdev_all_status(devname)
		code = int(status["GENERAL.STATE"].split(" ")[0])
		if code == 20:
			return "OFF"
		elif code == 30:
			return "ON"
		elif code == 50:
			return "Connecting"
		elif code == 100:
			return status['GENERAL.CONNECTION']
		else:
			return status["GENERAL.STATE"]
	except:
		return "ERR"


def get_netinfo(exclude_down=True):
	netinfo = {}
	snic = None
	for ifc, snics in psutil.net_if_addrs().items():
		if ifc == "lo":
			continue
		for snic in snics:
			if snic.family == socket.AF_INET:
				netinfo[ifc] = snic
		if ifc not in netinfo:
			c = 0
			for snic in snics:
				if snic.family == socket.AF_INET6:
					c += 1
			if c >= 2:
				netinfo[ifc] = snic
		if ifc not in netinfo and not exclude_down:
			netinfo[ifc] = None
	return netinfo


def network_info():
	logging.info("NETWORK INFO")
	res = {
		"Link-Local Name": ["{}.local".format(os.uname().nodename), "SUCCESS"]
	}
	for ifc, snic in get_netinfo().items():
		if snic.family == socket.AF_INET and snic.address:
			res[ifc] = [str(snic.address), "SUCCESS"]
		else:
			res[ifc] = ["connecting...", "WARNING"]
	return res


# ------------------------------------------------------------------------------
# External storage (removable disks)
# ------------------------------------------------------------------------------

def get_external_storage_dirs(exdpath):
	exdirs = []
	if os.path.isdir(exdpath):
		for dname in sorted(os.listdir(exdpath)):
			dpath = os.path.join(exdpath, dname)
			if os.path.isdir(dpath) and os.path.ismount(dpath):
				exdirs.append(dpath)
	return exdirs


# -------------------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------------------

def is_process_running(procname):
	cmd="ps -e | grep %s" % procname
	try:
		result = check_output(cmd, shell=True).decode('utf-8', 'ignore')
		if len(result) > 3:
			return True
		else:
			return False
	except Exception as e:
		return False


def is_service_active(service):
	cmd = "systemctl is-active %s" % service
	try:
		result = check_output(cmd, shell=True).decode('utf-8', 'ignore')
	except Exception as e:
		result = "ERROR: %s" % e
	#loggin.debug("Is service "+str(service)+" active? => "+str(result))
	if result.strip() == 'active':
		return True
	else:
		return False

# ------------------------------------------------------------------------------
# Jackd configuration
# ------------------------------------------------------------------------------


def get_jackd_options():
	jackd_options = {}
	for item in os.environ.get('JACKD_OPTIONS', "").strip().split('-'):
		try:
			parts = item.split(' ', 1)
			jackd_options[parts[0]] = parts[1].strip()
		except:
			pass

	return jackd_options

# ------------------------------------------------------------------------------
