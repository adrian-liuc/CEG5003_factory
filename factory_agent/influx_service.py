import json
from collections import defaultdict
from influxdb_client import InfluxDBClient
from config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

class InfluxService:
    def __init__(self):
        self.client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        self.query_api = self.client.query_api()

    def get_trend_data(self, factory_id: str = None, minutes: int = 10):
        """Per-minute production totals for trend analysis (last value per minute window)."""
        filter_str = '|> filter(fn: (r) => r["_measurement"] == "factory")'
        if factory_id and factory_id.lower() != "all":
            filter_str += f' |> filter(fn: (r) => r["factory_id"] == "{factory_id}")'

        flux_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -{minutes}m)
          {filter_str}
          |> aggregateWindow(every: 1m, fn: last, createEmpty: false)
        '''
        try:
            result = self.query_api.query(org=INFLUXDB_ORG, query=flux_query)

            PRODUCTION_METRICS = {"p1", "p2", "p3", "p4", "p12", "p13", "p23", "p234"}

            trend = defaultdict(list)
            for table in result:
                for record in table.records:
                    metric = record.values.get("sub_topic") or record.get_field()
                    if metric not in PRODUCTION_METRICS:
                        continue
                    fid = record.values.get("factory_id", "")
                    trend[(fid, metric)].append({
                        "minute": record.get_time().strftime("%H:%M"),
                        "value": record.get_value()
                    })

            if not trend:
                return f"No trend data found in the past {minutes} minutes."

            # Compute per-minute delta (produced each minute) from cumulative values
            output = {}
            for (fid, metric), points in sorted(trend.items()):
                points.sort(key=lambda x: x["minute"])
                deltas = []
                for i, p in enumerate(points):
                    if i == 0:
                        delta = 0
                    else:
                        delta = p["value"] - points[i - 1]["value"]
                        # Negative delta means counter reset — use current value as produced
                        if delta < 0:
                            delta = p["value"]
                    deltas.append({"minute": p["minute"], "produced": delta, "total": p["value"]})
                key = f"{fid.upper()}_{metric.upper()}"
                output[key] = deltas

            return json.dumps({
                "period_minutes": minutes,
                "note": "Each entry shows units produced in that 1-minute window and running total.",
                "trend": output
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"Error fetching trend data: {e}"

    def get_production_delta(self, factory_id: str = None, minutes: int = 1):
        """Units produced in the given window (last - first per metric)."""
        filter_str = '|> filter(fn: (r) => r["_measurement"] == "factory")'
        if factory_id and factory_id.lower() != "all":
            filter_str += f' |> filter(fn: (r) => r["factory_id"] == "{factory_id}")'

        flux_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -{minutes}m)
          {filter_str}
        '''
        try:
            result = self.query_api.query(org=INFLUXDB_ORG, query=flux_query)

            series = defaultdict(list)  # (factory_id, metric) -> [(time, value)]

            for table in result:
                for record in table.records:
                    fid = record.values.get("factory_id", "")
                    metric = record.values.get("sub_topic") or record.get_field()
                    val = record.get_value()
                    t = record.get_time()
                    if val is not None:
                        series[(fid, metric)].append((t, val))

            if not series:
                return f"No data found in the past {minutes} minutes."

            for key in series:
                series[key].sort(key=lambda x: x[0])

            production_delta = []

            PRODUCTION_METRICS = {"p1", "p2", "p3", "p4", "p12", "p13", "p23", "p234"}

            for (fid, metric), points in series.items():
                if metric not in PRODUCTION_METRICS:
                    continue
                first_val = points[0][1]
                last_val = points[-1][1]
                delta = last_val - first_val
                # counter reset on restart: last_val is production since reset
                produced = last_val if delta < 0 else delta
                production_delta.append({
                    "factory_id": fid,
                    "metric": metric,
                    "produced": produced,
                    "total_at_end": last_val
                })

            return json.dumps({
                "period_minutes": minutes,
                "production_delta": sorted(production_delta, key=lambda x: (x["factory_id"], x["metric"]))
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"Error fetching production delta: {e}"

    def get_current_status(self, factory_id: str = None):
        """Latest value for every metric (used for queue queries and production overview)."""
        filter_str = '|> filter(fn: (r) => r["_measurement"] == "factory")'
        if factory_id and factory_id.lower() != "all":
            filter_str += f' |> filter(fn: (r) => r["factory_id"] == "{factory_id}")'

        flux_query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: -5m)
          {filter_str}
          |> last()
        '''
        try:
            result = self.query_api.query(org=INFLUXDB_ORG, query=flux_query)
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        "factory_id": record.values.get("factory_id"),
                        "metric": record.values.get("sub_topic") or record.get_field(),
                        "value": record.get_value(),
                        "time": record.get_time().strftime("%Y-%m-%d %H:%M:%S")
                    })
            if not data:
                return "No current data available."
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Error fetching current status: {e}"

influx_service = InfluxService()
