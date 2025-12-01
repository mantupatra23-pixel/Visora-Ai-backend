# services/node_monitor.py
"""
Very small node register and heartbeat store.
Workers must call /farm/node/heartbeat to register.
"""
from pathlib import Path, json
import time
ROOT = Path(".").resolve()
NODES_DIR = ROOT / "runtime" / "nodes"
NODES_DIR.mkdir(parents=True, exist_ok=True)

def heartbeat(node_id: str, info: dict):
    nf = NODES_DIR / f"{node_id}.json"
    info['last_seen'] = time.time()
    nf.write_text(json.dumps(info, indent=2))
    return {"ok": True}

def list_nodes():
    nodes = []
    for nf in NODES_DIR.glob("*.json"):
        nodes.append(json.loads(nf.read_text()))
    return nodes

def prune_dead(threshold_sec: int = 60*5):
    import time
    now = time.time()
    removed = []
    for nf in NODES_DIR.glob("*.json"):
        info = json.loads(nf.read_text())
        if now - info.get('last_seen',0) > threshold_sec:
            nf.unlink()
            removed.append(info.get('node_id'))
    return removed
