# anomaly_detector.py

"""
anomaly_detector.py

负责检测传感器数据中的异常，包括：
  1. 单个传感器值是否超出预设的“正常范围”；
  2. 本轮所有传感器的平均值是否超出预设的“正常平均范围”。

提供函数：
    detect_anomalies(batch) -> (single_alerts, avg_alert)

    - batch: list of dict，每个 dict 示例：
        {
          "sensor_id": 1,
          "timestamp": "2025-06-05T14:22:10",
          "temperature": 24.85,
          "humidity": 58.47,
          "soil_moisture": 512,
          "is_anomaly": False
        }

    - single_alerts: list of tuples，列出所有单传感器的超限信息，示例：
        [(sensor_id, "temperature", value), (sensor_id, "humidity", value), ...]

    - avg_alert: list of tuples，列出所有平均值超限信息，示例：
        [("avg_temperature", avg_value), ("avg_humidity", avg_value), ...]
"""

# 单个传感器可接受阈值（请根据大棚实际情况自行调整）
TEMP_MIN = 15.0       # 温度最低阈值 (℃)
TEMP_MAX = 30.0       # 温度最高阈值 (℃)
HUM_MIN  = 30.0       # 湿度最低阈值 (%RH)
HUM_MAX  = 80.0       # 湿度最高阈值 (%RH)
SOIL_MIN = 100.0      # 土壤含水量最低阈值（单位自定）
SOIL_MAX = 700.0      # 土壤含水量最高阈值（单位自定）

# 平均值可接受阈值（可以与单传感器阈值相同，也可以做适度收紧或放宽）
AVG_TEMP_MIN  = 17.0  # 平均温度最低阈值 (℃)
AVG_TEMP_MAX  = 28.0  # 平均温度最高阈值 (℃)
AVG_HUM_MIN   = 40.0  # 平均湿度最低阈值 (%RH)
AVG_HUM_MAX   = 75.0  # 平均湿度最高阈值 (%RH)
AVG_SOIL_MIN  = 200.0 # 平均土壤含水量最低阈值（单位自定）
AVG_SOIL_MAX  = 600.0 # 平均土壤含水量最高阈值（单位自定）


def detect_anomalies(batch):
    """
    检测一批传感器读数中的异常，包括两个方面：
      1. 单个传感器是否超出对应的阈值范围；
      2. 本批所有传感器的平均值是否超出对应的平均阈值范围。

    参数：
        batch (list of dict): 一批传感器读数，长度通常为 30，每个元素示例：
            {
              "sensor_id": 1,
              "timestamp": "2025-06-05T14:22:10",
              "temperature": 24.85,
              "humidity": 58.47,
              "soil_moisture": 512,
              "is_anomaly": False
            }

    返回：
        single_alerts (list of tuples): 单传感器超限警告列表。
            形如 [(sensor_id, "temperature", value), (sensor_id, "humidity", value), ...]。
            如果没有任何单传感器超限，返回空列表 []。

        avg_alert (list of tuples): 平均值超限警告列表。
            形如 [("avg_temperature", avg_val), ("avg_humidity", avg_val), ...]。
            如果平均温度、湿度、土壤含水量都在阈值内，则返回空列表 []。
    """
    single_alerts = []
    temps = []
    hums  = []
    soils = []

    # 遍历所有记录，检查单个传感器值是否超出阈值
    for rec in batch:
        sid = rec.get("sensor_id")
        t   = rec.get("temperature")
        h   = rec.get("humidity")
        s   = rec.get("soil_moisture")

        # 收集到列表，稍后用于计算平均值
        temps.append(t)
        hums.append(h)
        soils.append(s)

        # 温度阈值检测
        if t < TEMP_MIN or t > TEMP_MAX:
            single_alerts.append((sid, "temperature", t))
        # 湿度阈值检测
        if h < HUM_MIN or h > HUM_MAX:
            single_alerts.append((sid, "humidity", h))
        # 土壤含水量阈值检测
        if s < SOIL_MIN or s > SOIL_MAX:
            single_alerts.append((sid, "soil_moisture", s))

    # 计算平均值
    if temps:
        avg_t = sum(temps) / len(temps)
    else:
        avg_t = None

    if hums:
        avg_h = sum(hums) / len(hums)
    else:
        avg_h = None

    if soils:
        avg_s = sum(soils) / len(soils)
    else:
        avg_s = None

    avg_alert = []
    # 平均温度阈值检测
    if avg_t is not None:
        if avg_t < AVG_TEMP_MIN or avg_t > AVG_TEMP_MAX:
            avg_alert.append(("avg_temperature", round(avg_t, 2)))
    # 平均湿度阈值检测
    if avg_h is not None:
        if avg_h < AVG_HUM_MIN or avg_h > AVG_HUM_MAX:
            avg_alert.append(("avg_humidity", round(avg_h, 2)))
    # 平均土壤含水量阈值检测
    if avg_s is not None:
        if avg_s < AVG_SOIL_MIN or avg_s > AVG_SOIL_MAX:
            avg_alert.append(("avg_soil_moisture", int(avg_s)))

    return single_alerts, avg_alert


# 如果直接运行此模块，将对一个示例 batch 进行检测并打印结果
if __name__ == "__main__":
    # 示例 batch：包含几条正常和异常数据
    example_batch = [
        {"sensor_id": 1, "timestamp": "2025-06-05T14:22:10", "temperature": 25.0, "humidity": 50.0, "soil_moisture": 500, "is_anomaly": False},
        {"sensor_id": 2, "timestamp": "2025-06-05T14:22:10", "temperature": 28.0, "humidity": 60.0, "soil_moisture": 450, "is_anomaly": False},
        {"sensor_id": 3, "timestamp": "2025-06-05T14:22:10", "temperature": 32.5, "humidity": 55.0, "soil_moisture": 480, "is_anomaly": True},  # 温度异常
        {"sensor_id": 4, "timestamp": "2025-06-05T14:22:10", "temperature": 26.0, "humidity": 20.0, "soil_moisture": 510, "is_anomaly": True},  # 湿度异常
        {"sensor_id": 5, "timestamp": "2025-06-05T14:22:10", "temperature": 24.5, "humidity": 52.0, "soil_moisture": 50,  "is_anomaly": True}   # 土壤异常
    ]

    single_alerts, avg_alerts = detect_anomalies(example_batch)

    if single_alerts:
        print("单传感器告警：")
        for sid, metric, value in single_alerts:
            print(f"  传感器 {sid} 的 {metric} = {value}，超出阈值区间！")
    else:
        print("没有任何单传感器告警。")

    if avg_alerts:
        print("平均值告警：")
        for key, avg_val in avg_alerts:
            print(f"  {key} = {avg_val}，超出平均值阈值区间！")
    else:
        print("没有平均值告警。")
