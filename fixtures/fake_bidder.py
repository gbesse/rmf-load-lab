"""Deterministic protocol example; this does not run Open-RMF."""

import json
from pathlib import Path
import sys
import time


scenario = json.loads(Path(sys.argv[1]).read_text())
time.sleep(0.15 + scenario["queue_depth"] * 0.002)
print(json.dumps({"accepted": True}))
