"""Wipeout Soup test driving on top of dbg.py: load a save state, unpause if
needed and hold full thrust (NeGcon I) with no steering.

The debug server's digital button word is active-low (a 0 bit = pressed), and
its NeGcon axis override only applies while a button override is active, so
thrust is a persistent all-released override plus the analog I pressure."""
import time
from dbg import race, cmd

START = 0xFFFF & ~0x0008

def drive(exe, slot, unpause=True, thrust=32767):
    p = race(exe, slot)
    if unpause:
        cmd({"cmd": "press", "buttons": START, "frames": 6})
        time.sleep(0.4)
    cmd({"cmd": "set_input", "buttons": "FFFF"})
    cmd({"cmd": "controller_input", "mode": "negcon", "i": thrust})
    return p

def fire(frames=6):
    """NeGcon II (fire weapon) as a full press for a few frames."""
    cmd({"cmd": "controller_input", "mode": "negcon", "i": 32767, "ii": 32767})
    time.sleep(frames / 60.0)
    cmd({"cmd": "controller_input", "mode": "negcon", "i": 32767, "ii": 0})
