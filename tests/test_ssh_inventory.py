import subprocess
import json
import sys
import os

def test_ssh_inventory_list():
    res = subprocess.run([sys.executable, "ssh_inventory.py", "--list"], capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "_meta" in data
    assert "hostvars" in data["_meta"]

def test_ssh_inventory_host():
    res = subprocess.run([sys.executable, "ssh_inventory.py", "--host", "somehost"], capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "_meta" in data
    assert "hostvars" in data["_meta"]
