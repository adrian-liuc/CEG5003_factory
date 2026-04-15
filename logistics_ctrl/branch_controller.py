# Branch Controller
# Reads wait-queue sizes from InfluxDB every INTERVAL seconds and writes
# branch routing files accordingly.
#
# branch1.txt  — truck leaving FA
#   1 = road1_go  → car_park2_in  → FB  (P1 to FB)
#   2 = road2_go  → car_park3_in  → FC  (P1 to FC)
#
# branch2.txt  — truck at FB after P1 delivery
#   1 = car_park2_out1 → upload_p12 → FD  (P12 to FD)
#   2 = car_park2_out2 → upload_p2  → FC  (P2 to FC)
#   3 = road1_back                  → FA  (empty return)
#
# branch3.txt  — truck at FC
#   1 = C2D        → upload_p23 → FD  (P23 to FD)
#   2 = road2_back              → FA  (empty return)
#   3 = road5_back              → FB  (empty return)
#
# branch4.txt  — truck at FD after P23 delivery
#   1 = road3_back  → FB
#   2 = road4_back  → FC area (car3_gate → Branch3)
#
# Supply chain: FA→FB (P1): b1=1 | FA→FC (P1): b1=2 | FB→FC (P2): b1=1,b2=2 | FC→FD (P23): b3=1

import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

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

BRANCH1_PERIOD = 3   # 2/3 cycles → FB, 1/3 → FC


def read_queues(query_api) -> dict:
    """Latest value for each wait-queue metric. Returns 0 on missing/error."""
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


def decide_routes(queues: dict, cycle: int) -> dict:
    p1_q  = queues["p1_wait_queue"]
    p2_q  = queues["p2_wait_queue"]
    p23_q = queues["p23_wait_queue"]

    # car3_gate only opens when fc_p23.QueueLength >= 2, so don't set branch3=1 with empty queue
    branch3 = 1 if p23_q >= P23_THRESHOLD else 2

    # branch4=1 sends truck to car_park2_in where download_p1_b tries to unload 3 items — deadlocks on empty
    branch4 = 2

    # fb_p2_p23 is a dedicated transport queue (split by Branch_p2), no competition with Assemble_p12
    branch2 = 2

    # INTERVAL=3s, FA→FB≈15s (5 cycles): trucks back at N+5. With BRANCH1_PERIOD=3, (N+5)%3
    # reliably puts FB departures into the FC slot → alternates FB/FC as intended
    branch1 = 2 if (cycle % BRANCH1_PERIOD == 2) else 1

    return {"branch1": branch1, "branch2": branch2,
            "branch3": branch3, "branch4": branch4}


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
