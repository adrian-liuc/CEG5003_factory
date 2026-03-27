import os

class FactoryService:
    def __init__(self, factory_files_dir=r"C:\Users\97350\project2026\CEG5003_factory\simulation_files\factory_files"):
        self.factory_files_dir = factory_files_dir
        self.factories = ["fa_p1", "fb_p2", "fc_p3", "fd_p4"]

        self.maxnum_dir = os.path.join(self.factory_files_dir, "MaxNum")
        self.inter_arrival_dir = os.path.join(self.factory_files_dir, "InterArrivalTime")

        os.makedirs(self.maxnum_dir, exist_ok=True)
        os.makedirs(self.inter_arrival_dir, exist_ok=True)

    def set_plan_quantity(self, factory_id, quantity):
        """设置工厂计划生产数量（maxnum）"""
        targets = self.factories if factory_id.lower() == "all" else [factory_id.lower()]
        for t in targets:
            if t not in self.factories:
                return f"Error: Invalid factory id '{t}'. Available: {', '.join(self.factories)}, or 'all'."
        try:
            quantity_int = int(quantity)
        except ValueError:
            return "Error: Quantity must be a valid integer."
        try:
            for t in targets:
                file_path = os.path.join(self.maxnum_dir, f"{t}_maxnum.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(quantity_int))
            return f"Success: Plan quantity for {factory_id} has been set to {quantity_int}"
        except Exception as e:
            return f"Fail: Write error - {e}"

    def set_production_speed(self, factory_id, speed_interval):
        """设置工厂生产速度（InterArrival time）"""
        targets = self.factories if factory_id.lower() == "all" else [factory_id.lower()]
        for t in targets:
            if t not in self.factories:
                return f"Error: Invalid factory id '{t}'. Available: {', '.join(self.factories)}, or 'all'."
        try:
            float(speed_interval)
        except ValueError:
            return "Error: Speed interval must be a valid number (e.g., 4 or 4.5)."
        try:
            for t in targets:
                file_path = os.path.join(self.inter_arrival_dir, f"{t}_InterArrival_time.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(speed_interval).strip())
            return f"Success: Production speed (InterArrival time) for {factory_id} has been set to '{speed_interval}'"
        except Exception as e:
            return f"Fail: Write error - {e}"

    def emergency_shutdown(self, factory_id):
        """紧急停产检修：将指定工厂的 maxnum 设置为 0"""
        targets = self.factories if factory_id.lower() == "all" else [factory_id.lower()]
        for t in targets:
            if t not in self.factories:
                return f"Error: Invalid factory id '{t}'. Available: {', '.join(self.factories)}, or 'all'."
        res = self.set_plan_quantity(factory_id, 0)
        if "Success" in res:
            return f"Success: EMERGENCY SHUTDOWN activated for {factory_id}. MaxNum set to 0."
        return res

    def get_status(self):
        """获取所有工厂当前状态"""
        status = {}
        for f in self.factories:
            try:
                path = os.path.join(self.maxnum_dir, f"{f}_maxnum.txt")
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as file:
                        val = file.read().strip()
                        status[f] = {"maxnum": val, "running": val != "0"}
                else:
                    status[f] = {"maxnum": "Unknown", "running": True}
            except:
                status[f] = {"maxnum": "Error", "running": True}
        return status

factory_service = FactoryService()
