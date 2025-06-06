# data_generator.py

"""
data_generator.py

负责“虚拟生成传感器读数”模块。每次调用 generate_batch() 时，会生成一批指定数量的
传感器读数，其中包含随机噪声、小概率注入的异常，以及时间戳。

现在每条记录在 "sensor_id" 前增加一个 "id" 字段，数值与 sensor_id 相同。
"""

import datetime
import numpy as np

def generate_batch(
    base_temp: float,
    base_hum: float,
    base_soil: float,
    num_sensors: int = 30,
    anomaly_rate: float = 0.05
) -> list:
    """
    生成一批虚拟传感器数据。

    参数：
        base_temp   (float): 生成温度时的基准值（℃）。
        base_hum    (float): 生成湿度时的基准值（%RH）。
        base_soil   (float): 生成土壤含水量时的基准值（任意单位）。
        num_sensors (int)  : 本次要生成的传感器数量，默认 30。
        anomaly_rate(float): 注入异常的概率（0~1），默认 5%。

    返回：
        list: 包含 num_sensors 个字典的列表，每个字典示例：
            {
                "id": 1,
                "sensor_id": 1,
                "timestamp": "2025-06-05T14:22:10",
                "temperature": 24.85,
                "humidity": 58.47,
                "soil_moisture": 512,
                "is_anomaly": False
            }
    """
    # 获取当前时间，精确到秒
    timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    batch = []

    for sid in range(1, num_sensors + 1):
        # 基础随机噪声
        t = base_temp + np.random.normal(0, 1.5)     # 温度 ±1.5℃
        h = base_hum  + np.random.normal(0, 5)        # 湿度 ±5%RH
        s = base_soil + np.random.normal(0, 30)       # 土壤含水量 ±30 单位

        is_anom = False

        # 小概率注入异常
        if np.random.rand() < anomaly_rate:
            is_anom = True
            typ = np.random.choice(["temp_high", "humidity_low", "soil_dry"])
            if typ == "temp_high":
                # 异常高温：再加 10~15℃
                t += np.random.uniform(10, 15)
            elif typ == "humidity_low":
                # 异常低湿：再减 30~50%RH
                h -= np.random.uniform(30, 50)
            else:  # "soil_dry"
                # 异常干燥：再减 200~300 单位
                s -= np.random.uniform(200, 300)
                s = max(s, 0)  # 保证不为负

        record = {
            "id": sid,
            "sensor_id": sid,
            "timestamp": timestamp,
            "temperature": round(t, 2),
            "humidity":    round(h, 2),
            "soil_moisture": int(s),
            "is_anomaly":  is_anom
        }
        batch.append(record)

    return batch


# 如果直接运行此模块，会演示生成一次并打印结果
if __name__ == "__main__":
    sample_batch = generate_batch(
        base_temp=25.0,
        base_hum=60.0,
        base_soil=500.0,
        num_sensors=30,
        anomaly_rate=0.05
    )
    import json
    print(json.dumps(sample_batch, indent=2, ensure_ascii=False))
