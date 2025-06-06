# main.py

"""
main.py

主流程：生成 → 检测 → 自动控制 → 逐条发送 → 打印摘要
（已将“原来一次性发送整批”改为“一个一个发送”）
"""

import time
import threading
import argparse
import os

from data_generator import generate_batch
from anomaly_detector import detect_anomalies
from controller import update_baselines
from mqtt_sender import publish_individual  # 这里改成逐条发送

# ─── 全局基准值与每轮增量 ───────────────────────────────────────────────────
base_temp = 25.0   # 温度基准 (℃)
base_hum  = 60.0   # 湿度基准 (%RH)
base_soil = 500.0  # 土壤含水基准（单位自定）

temp_step = 0.0    # 每轮温度增量 (℃)
hum_step  = 0.0    # 每轮湿度增量 (%RH)
soil_step = 0.0    # 每轮土壤含水增量 (单位)
# ────────────────────────────────────────────────────────────────────────────


def key_listener_loop():
    """
    按键监听线程：
      温度：
        t → temp_step += 0.1℃
        T → temp_step -= 0.1℃
        r → temp_step = 0
      湿度：
        h → hum_step += 0.2%RH
        H → hum_step -= 0.2%RH
        u → hum_step = 0
      土壤含水：
        s → soil_step += 2
        S → soil_step -= 2
        l → soil_step = 0
      q → 退出程序
    每次按下后立即清空输入缓冲，避免长按持续触发。
    """
    global temp_step, hum_step, soil_step

    try:
        import msvcrt
    except ImportError:
        print("[Warning] 当前系统不支持 msvcrt，按键调整功能不可用。")
        return

    print("按键操作提示：")
    print("  温度增量调整： t → +0.1℃ ， T → -0.1℃ ， r → 重置为 0")
    print("  湿度增量调整： h → +0.2%RH， H → -0.2%RH， u → 重置为 0")
    print("  土壤含水：     s → +2     ， S → -2     ， l → 重置为 0")
    print("  q → 退出程序\n")

    while True:
        if msvcrt.kbhit():
            ch = msvcrt.getch().decode("utf-8", errors="ignore")

            # 温度增量
            if ch == "t":
                temp_step = round(temp_step + 0.1, 2)
                print(f"🌡 按键 t → temp_step = {temp_step:+.2f} ℃/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            elif ch == "T":
                temp_step = round(temp_step - 0.1, 2)
                print(f"🌡 按键 T → temp_step = {temp_step:+.2f} ℃/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            elif ch == "r":
                temp_step = 0.0
                print("🌡 按键 r → temp_step 已重置为 0.00 ℃/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            # 湿度增量
            elif ch == "h":
                hum_step = round(hum_step + 0.2, 2)
                print(f"💧 按键 h → hum_step = {hum_step:+.2f}%RH/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            elif ch == "H":
                hum_step = round(hum_step - 0.2, 2)
                print(f"💧 按键 H → hum_step = {hum_step:+.2f}%RH/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            elif ch == "u":
                hum_step = 0.0
                print("💧 按键 u → hum_step 已重置为 0.00%RH/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            # 土壤含水增量
            elif ch == "s":
                soil_step = round(soil_step + 2.0, 2)
                print(f"🌱 按键 s → soil_step = {soil_step:+.2f}/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            elif ch == "S":
                soil_step = round(soil_step - 2.0, 2)
                print(f"🌱 按键 S → soil_step = {soil_step:+.2f}/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            elif ch == "l":
                soil_step = 0.0
                print("🌱 按键 l → soil_step 已重置为 0.00/轮")
                while msvcrt.kbhit():
                    msvcrt.getch()

            # 退出
            elif ch.lower() == "q":
                print("检测到 'q'，程序退出。")
                os._exit(0)

        time.sleep(0.1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="主流程：按键调整温/湿/土 每轮增量，逐条发送"
    )
    parser.add_argument("--broker", "-b", type=str, default="test.mosquitto.org",
                        help="MQTT Broker 地址（默认 localhost）")
    parser.add_argument("--port", "-p", type=int, default=1883,
                        help="MQTT Broker 端口（默认 1883）")
    parser.add_argument("--topic", "-t", type=str, default="greenhouse/sensors",
                        help="MQTT 发布主题（默认 greenhouse/sensors）")
    parser.add_argument("--interval", "-i", type=int, default=10,
                        help="循环间隔（秒）（默认 10 秒）")
    parser.add_argument("--num-sensors", "-n", type=int, default=30,
                        help="每批传感器数量（默认 30）")
    parser.add_argument("--anomaly-rate", "-r", type=float, default=0.01,
                        help="小概率异常注入率（0~1，默认 0.05）")
    return parser.parse_args()


def main():
    args = parse_args()
    broker       = args.broker
    port         = args.port
    topic        = args.topic
    interval_sec = args.interval
    num_sensors  = args.num_sensors
    anomaly_rate = args.anomaly_rate

    global base_temp, base_hum, base_soil, temp_step, hum_step, soil_step

    # 启动按键监听线程
    listener_thread = threading.Thread(target=key_listener_loop, daemon=True)
    listener_thread.start()

    print(f"[Info] 主循环启动：每 {interval_sec} 秒生成→检测→控制→逐条发送\n")

    try:
        while True:
            # ─── 1. 手动增量先行 ────────────────────────────────────────────
            if temp_step != 0.0:
                before_t = base_temp
                base_temp = round(base_temp + temp_step, 2)
                print(f"🖥️ 手动增量：温度基准 {before_t:.2f} ℃ → {base_temp:.2f} ℃ (step={temp_step:+.2f})")

            if hum_step != 0.0:
                before_h = base_hum
                base_hum = round(base_hum + hum_step, 2)
                print(f"🖥️ 手动增量：湿度基准 {before_h:.2f}%RH → {base_hum:.2f}%RH (step={hum_step:+.2f})")

            if soil_step != 0.0:
                before_s = base_soil
                base_soil = round(base_soil + soil_step, 2)
                print(f"🖥️ 手动增量：土壤含水基准 {before_s:.2f} → {base_soil:.2f} (step={soil_step:+.2f})")

            # ─── 2. 生成数据 & 检测异常 ────────────────────────────────────────
            batch = generate_batch(
                base_temp=base_temp,
                base_hum=base_hum,
                base_soil=base_soil,
                num_sensors=num_sensors,
                anomaly_rate=anomaly_rate
            )
            single_alerts, avg_alert = detect_anomalies(batch)

            # ─── 3. 自动控制 + 最大补偿 & 是否告警 ─────────────────────────────
            base_temp, base_hum, base_soil = update_baselines(
                base_temp, base_hum, base_soil,
                avg_alert,
                temp_step=0.1,    # 自动补偿最小步长
                hum_step=0.2,
                soil_step=2.0,
                max_temp_comp=3.0,   # 最大补偿能力
                max_hum_comp=5.0,
                max_soil_comp=20.0
            )

            # ─── 4. 逐条发送到 MQTT ──────────────────────────────────────────
            #    将 batch 中的每条记录单独作为 JSON 发布
            publish_individual(
                batch,
                broker=broker,
                port=port,
                topic=topic,
                delay=0.0   # 如果想每条之间加个短延时，可设置为 0.05 / 0.1 等
            )

            # ─── 5. 控制台输出本轮摘要 ───────────────────────────────────────
            timestamp = batch[0]["timestamp"] if batch else "N/A"
            print(f"[{timestamp}] 逐条发布 {len(batch)} 条数据 | "
                  f"基准 → 温度: {base_temp:.2f} ℃, 湿度: {base_hum:.2f}%RH, 土壤: {base_soil:.2f}")
            if single_alerts:
                print("  单传感器告警（示例前3条）：", single_alerts[:3])
            if avg_alert:
                print("  平均值告警：", avg_alert)
            print()  # 空行分隔

            # ─── 6. 等待下一轮 ─────────────────────────────────────────────
            time.sleep(interval_sec)

    except KeyboardInterrupt:
        print("\n[Info] 收到 Ctrl+C，程序退出。")
    finally:
        print("[Info] 退出完成。")


if __name__ == "__main__":
    main()
