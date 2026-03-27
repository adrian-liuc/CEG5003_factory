import json
from influxdb_client import InfluxDBClient
from config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

class InfluxService:
    def __init__(self):
        self.client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        self.query_api = self.client.query_api()

    def get_factory_data(self, factory_id: str = None, minutes: int = 5):
        """获取指定工厂或所有工厂最近几分钟的数据"""
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
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        "time": record.get_time().strftime("%Y-%m-%d %H:%M:%S"),
                        "factory_id": record.values.get("factory_id"),
                        "metric": record.values.get("sub_topic") or record.get_field(),
                        "value": record.get_value()
                    })
            if not data:
                return f"No data found in the past {minutes} minutes."
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Error fetching factory data: {e}"

influx_service = InfluxService()
