"""
Branch Controller
=================
Dynamically adjusts routing branch files every INTERVAL seconds based on
logistics wait-queue sizes read from InfluxDB.

Branch file reference
---------------------
branch1.txt  — Branch1: truck leaving FA
    1 = road1_go  → car_park2_in  → FB  (deliver P1 to FB)
    2 = road2_go  → car_park3_in  → FC  (deliver P1 to FC)

branch2.txt  — Branch2: truck at FB after P1 delivery
    1 = car_park2_out1 → upload_p12 → FD  (load P12, deliver to FD)
    2 = car_park2_out2 → upload_p2  → FC  (load P2,  deliver to FC)
    3 = road1_back                  → FA  (empty return)

branch3.txt  — Branch3: truck at FC
    1 = C2D        → upload_p23 → FD  (load P23, deliver to FD)
    2 = road2_back              → FA  (empty return)
    3 = road5_back              → FB  (empty return)

branch4.txt  — Branch4: truck at FD after P23 delivery
    1 = road3_back           → FB
    2 = road4_back           → FC area (car3_gate → Branch3)

Supply chain covered
---------------------
  FA → FB  (P1)   : branch1=1
  FA → FC  (P1)   : branch1=2
  FB → FC  (P2)   : branch1=1, branch2=2
  FC → FD  (P23)  : branch3=1  (needs fc_p23 queue >= 2 to pass car3_gate)
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

# ── config ────────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent.parent / ".env")

INFLUXDB_URL    = os.getenv("INFLUXDB_URL",    "http://localhost:8086")
INFLUXDB_TOKEN  = os.getenv("INFLUXDB_TOKEN",  "")
INFLUXDB_ORG    = os.getenv("INFLUXDB_ORG",    "NUS")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "factory_data")

FILES_DIR = Path(__file__).parent.parent / "simulation_files" / "files"
LOG_FILE  = Path(__file__).parent / "logistics_log.json"
LOG_MAX   = 300   # keep latest N entries
INTERVAL  = 3     # seconds between each routing update (must NOT align with journey times)

# Thresholds — tune these to match your simulation speed
P23_THRESHOLD = 2   # fc p23_wait_queue: minimum P23 at FC to justify a FD delivery run

# branch1 rotation period: every BRANCH1_PERIOD cycles, 1 cycle sends truck to FC
# With INTERVAL=3s and FA→FB journey ≈15s (5 cycles):
#   trucks return at cycle N+5 → (N+5) % BRANCH1_PERIOD determines destination.
#   BRANCH1_PERIOD=3 means 5%3=2 → consistently lands on the FC slot.
BRANCH1_PERIOD = 3   # 2 out of 3 cycles go to FB, 1 out of 3 goes to FC


# ── InfluxDB helpers ──────────────────────────────────────────────────────────
def read_queues(query_api) -> dict:
    """
    Return the latest value for each wait-queue sub_topic.
    Keys: 'p1_wait_queue', 'p2_wait_queue', 'p23_wait_queue'
    Falls back to 0 if a metric is missing or InfluxDB is unreachable.
    """
    flux = f'''
from(bucket: "{INFLUXDB_BUCKET}")
  |> range(start: -2m)
  |> filter(fn: (r) => r["_measurement"] == "factory")
  |> filter(fn: (r) => r["sub_topic"] =~ /wait_queue/)
  |> last()
'''
    queues = {"p1_wait_queue": 0, "p2_wait_queue": 0, "p23_wait_queue": 0}
    try:
        result = query_api.query(org=INFLUXDB_ORG, query=flux)
        for table in result:
            for record in table.records:
                sub = record.values.get("sub_topic", "")
                val = record.get_value()
                if sub in queues and val is not None:
                    queues[sub] = float(val)
    except Exception as e:
        print(f"  [WARN] InfluxDB unavailable: {e}")
    return queues


# ── branch file writer ────────────────────────────────────────────────────────
def write_branch(filename: str, value: int) -> str | None:
    """Write value to branch file. Returns 'old→new' string if changed, else None."""
    path = FILES_DIR / filename
    try:
        current = path.read_text().strip()
    except FileNotFoundError:
        current = ""
    if current != str(value):
        path.write_text(str(value))
        change = f"{current or '?'} → {value}"
        print(f"  {filename}: {change}")
        return change
    return None


# ── logistics log ─────────────────────────────────────────────────────────────
_ROUTE_DESC = {
    "branch1": {1: "FA → FB (P1)", 2: "FA → FC (P1)"},
    "branch2": {1: "FB → FD (P12)", 2: "FB → FC (P2)", 3: "FB → FA (empty)"},
    "branch3": {1: "FC → FD (P23)", 2: "FC → FA (empty)", 3: "FC → FB (empty)"},
    "branch4": {1: "FD → FB", 2: "FD → FC → FA"},
}

def append_log(queues: dict, routes: dict, changes: dict):
    try:
        entries = json.loads(LOG_FILE.read_text()) if LOG_FILE.exists() else []
    except Exception:
        entries = []

    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "queues": {
            "p1":  int(queues["p1_wait_queue"]),
            "p2":  int(queues["p2_wait_queue"]),
            "p23": int(queues["p23_wait_queue"]),
        },
        "routes": {
            k: {"value": v, "desc": _ROUTE_DESC.get(k, {}).get(v, str(v))}
            for k, v in routes.items()
        },
        "changes": changes,   # dict: {"branch3": "2 → 1", ...}
    }
    entries.append(entry)
    if len(entries) > LOG_MAX:
        entries = entries[-LOG_MAX:]
    try:
        LOG_FILE.write_text(json.dumps(entries, ensure_ascii=False))
    except Exception as e:
        print(f"  [WARN] Log write failed: {e}")


# ── routing logic ─────────────────────────────────────────────────────────────
def decide_routes(queues: dict, cycle: int) -> dict:
    """
    Compute branch values from current queue sizes.

    Returns dict with keys branch1 .. branch4.
    """
    p1_q  = queues["p1_wait_queue"]
    p2_q  = queues["p2_wait_queue"]
    p23_q = queues["p23_wait_queue"]

    # ── branch3: FC → FD or empty return ──────────────────────────────────────
    # car3_gate only opens when fc_p23.QueueLength >= 2 (simulation gate logic),
    # so only set branch3=1 when there is actually P23 to load.
    branch3 = 1 if p23_q >= P23_THRESHOLD else 2

    # ── branch4: after FD delivery, where to send the empty truck ─────────────
    # ALWAYS use branch4=2 (road4_back → car_park3_in_sum → car3_gate → Branch3 → FA).
    # branch4=1 goes to car_park2_in where download_p1_b waits to unload 3 items from
    # the truck — an empty truck arriving there will deadlock forever.
    branch4 = 2

    # ── branch2: truck at FB, what to load ────────────────────────────────────
    # ALWAYS pick up P2 and deliver to FC (branch2=2).
    # fb_p2_p23 is now a dedicated transport queue (split by Branch_p2 in simulation),
    # so it fills up without competition from Assemble_p12.
    branch2 = 2

    # ── branch1: which factory gets P1 from FA ────────────────────────────────
    # INTERVAL=3s + BRANCH1_PERIOD=3.
    #   FA→FB ≈15s = 5 cycles. Trucks return at cycle N+5.
    #   (N+5) % 3 = (N+2) % 3. If N%3==0 (FB departure), return at (0+5)%3=2 → FC slot.
    #   This means trucks reliably alternate: FB trip → FC trip → FB trip → FC trip...
    #   FA→FC ≈5s ≈1.7 cycles. Return at N+1.7 → (0+5+1.7)%3 = 0 → FB slot again. ✓
    branch1 = 2 if (cycle % BRANCH1_PERIOD == 2) else 1

    return {"branch1": branch1, "branch2": branch2,
            "branch3": branch3, "branch4": branch4}


# ── main loop ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("Branch Controller")
    print(f"  Files dir : {FILES_DIR}")
    print(f"  Interval  : {INTERVAL}s")
    print(f"  InfluxDB  : {INFLUXDB_URL}")
    print("=" * 50)

    client    = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()

    cycle = 0
    try:
        while True:
            print(f"\n[cycle {cycle}]")
            queues = read_queues(query_api)
            print(f"  queues → P1={queues['p1_wait_queue']:.0f}  "
                  f"P2={queues['p2_wait_queue']:.0f}  "
                  f"P23={queues['p23_wait_queue']:.0f}")

            routes = decide_routes(queues, cycle)
            print(f"  decision → branch1={routes['branch1']}(FA→{'FB' if routes['branch1']==1 else 'FC'})  "
                  f"branch2={routes['branch2']}(FB→FC P2)  "
                  f"branch3={routes['branch3']}({'FC→FD' if routes['branch3']==1 else 'FC→FA'})  "
                  f"branch4={routes['branch4']}(FD→FC→FA)")

            changes = {}
            for name, val in routes.items():
                result = write_branch(f"{name}.txt", val)
                if result:
                    changes[name] = result

            append_log(queues, routes, changes)
            cycle += 1
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\nBranch Controller stopped.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
