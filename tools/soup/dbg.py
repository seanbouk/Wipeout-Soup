"""Wipeout Soup: helpers for the dev build's debug server (127.0.0.1:4370, one command
per connection). Needs a -DPSX_DEBUG_TOOLS=ON build; race() needs the save
states in build-dev/saves-dev (see docs/soup/motion-vectors-phase0.md)."""
import json, socket, subprocess, time, os

def cmd(obj, timeout=30):
    s = socket.create_connection(("127.0.0.1", 4370), timeout=timeout)
    s.sendall((json.dumps(obj) + "\n").encode())
    b = b""
    while not b.endswith(b"\n"):
        c = s.recv(1 << 22)
        if not c:
            break
        b += c
    s.close()
    return json.loads(b.decode())

def launch(exe):
    p = subprocess.Popen([exe, "--no-launcher"], cwd=os.path.dirname(exe))
    for _ in range(200):          # wait for the debug server
        try:
            cmd({"cmd": "ping"}, timeout=2)
            return p
        except OSError:
            time.sleep(0.1)
    return p

def shot(path, depth=0):
    seq = cmd({"cmd": "present_shot_seq"})["seq"]
    cmd({"cmd": "present_shot", "path": path, "depth": depth})
    for _ in range(100):
        r = cmd({"cmd": "present_shot_seq"})
        if r["seq"] != seq:
            return r.get("wrote")
        time.sleep(0.05)
    return None

RACE_SLOT = 8   # build-dev/saves-dev: chase-cam, mid-race (slot 9: trackside cam, race start)

def race(exe, slot=RACE_SLOT):
    """Launch and jump straight to the saved attract-mode race."""
    p = launch(exe)
    time.sleep(3)                      # let the runtime finish booting
    gen = cmd({"cmd": "savestate_status"})["generation"]
    r = cmd({"cmd": "savestate", "op": "load", "slot": slot})
    if not r.get("ok"):
        raise RuntimeError(r)
    for _ in range(100):
        s = cmd({"cmd": "savestate_status"})
        if s["generation"] != gen:
            if not s["last_ok"]:
                raise RuntimeError(s)
            time.sleep(1)              # a few frames past the load
            return p
        time.sleep(0.1)
    raise RuntimeError("load never completed")
