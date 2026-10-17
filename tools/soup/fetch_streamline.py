"""Fetch NVIDIA Streamline's signed runtime DLLs for the DLSS path.

Downloads the pinned Streamline SDK release, checks its SHA-256, and extracts
only the four production DLLs DLSS Super Resolution needs (plus licences) into
third_party/streamline/bin/ (git-ignored; the build copies them next to the
exe). The headers are already vendored in third_party/streamline/include/.

usage: python tools/soup/fetch_streamline.py
"""
import hashlib
import os
import sys
import tempfile
import urllib.request
import zipfile

VERSION = "v2.14.1"
URL = ("https://github.com/NVIDIA-RTX/Streamline/releases/download/"
       f"{VERSION}/streamline-sdk-{VERSION}.zip")
SHA256 = "92c4d954631a1710da86ca3fa8d5034f2b9503838c95fc4ae977ae149319781b"
FILES = ["bin/x64/sl.interposer.dll", "bin/x64/sl.common.dll", "bin/x64/sl.dlss.dll",
         "bin/x64/nvngx_dlss.dll", "bin/x64/nvngx_dlss.license.txt", "license.txt"]

def main():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = os.path.join(root, "third_party", "streamline", "bin")
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        zpath = os.path.join(tmp, "sl.zip")
        print("downloading", URL)
        urllib.request.urlretrieve(URL, zpath)
        h = hashlib.sha256()
        with open(zpath, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != SHA256:
            sys.exit("SHA-256 mismatch: got %s, expected %s" % (h.hexdigest(), SHA256))
        with zipfile.ZipFile(zpath) as z:
            for name in FILES:
                data = z.read(name)
                with open(os.path.join(out, os.path.basename(name)), "wb") as f:
                    f.write(data)
                print("  ", os.path.basename(name), len(data))
    print("Streamline", VERSION, "runtime ->", out)

if __name__ == "__main__":
    main()
