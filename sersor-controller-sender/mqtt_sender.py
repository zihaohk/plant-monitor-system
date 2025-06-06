# mqtt_sender.py

"""
mqtt_sender.py

原有的 publish_batch() 保留不变，我们在此新增 publish_individual() 用于逐条发送。
"""

import json
import paho.mqtt.client as mqtt
import time

def publish_batch(
    batch: list,
    broker: str = "localhost",
    port: int = 1883,
    topic: str = "greenhouse/sensors"
) -> None:
    """
    原先的一次性发布整个 batch（JSON 数组）的函数，保留不变。
    """
    client = mqtt.Client()
    try:
        client.connect(broker, port)
    except Exception as e:
        print(f"[Error] 无法连接到 MQTT Broker {broker}:{port} → {e}")
        return

    client.loop_start()
    try:
        payload = json.dumps(batch, ensure_ascii=False)
    except (TypeError, ValueError) as e:
        print(f"[Error] 序列化 batch 为 JSON 失败：{e}")
        client.loop_stop()
        client.disconnect()
        return

    result = client.publish(topic, payload)
    if result[0] != mqtt.MQTT_ERR_SUCCESS:
        print(f"[Warning] 发布整批消息到主题 '{topic}' 失败，状态码：{result[0]}")

    client.loop_stop()
    client.disconnect()


def publish_individual(
    batch: list,
    broker: str = "localhost",
    port: int = 1883,
    topic: str = "greenhouse/sensors",
    delay: float = 0.0
) -> None:
    """
    按条逐条发布 batch 中的每一条记录：
      - batch: list of dict，每个 dict 看起来像：
          {
            "sensor_id": 1,
            "timestamp": "2025-06-05T14:22:10",
            "temperature": 24.85,
            "humidity": 58.47,
            "soil_moisture": 512,
            "is_anomaly": False
          }
      - broker/port/topic: MQTT 服务配置
      - delay: 每发完一条后，等待 delay 秒再发送下一条（可设为 0.0 不延迟）

    这会用同一个连接循环发多条消息，但每条都单独序列化成 JSON。
    """
    client = mqtt.Client()
    try:
        client.connect(broker, port)
    except Exception as e:
        print(f"[Error] 无法连接到 MQTT Broker {broker}:{port} → {e}")
        return

    client.loop_start()

    for record in batch:
        try:
            payload = json.dumps(record, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            print(f"[Error] 序列化单条记录为 JSON 失败：{e}；记录内容：{record}")
            continue

        result = client.publish(topic, payload)
        if result[0] != mqtt.MQTT_ERR_SUCCESS:
            print(f"[Warning] 发布单条消息到主题 '{topic}' 失败，状态码：{result[0]}；记录：{record}")
        # 如果需要间隔，可以在这里加延时
        if delay > 0.0:
            time.sleep(delay)

    client.loop_stop()
    client.disconnect()
