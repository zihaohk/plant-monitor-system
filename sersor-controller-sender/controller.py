# controller.py

"""
controller.py

负责“根据检测结果调整基准温度/湿度/土壤含水量”的模块，带有：
  - 最大补偿能力限制（max_comp_*）
  - 当需要补偿量超过最大能力时，打印“请人工干预”警告

函数：
    update_baselines(
        base_temp, base_hum, base_soil,
        avg_alert,
        temp_step=0.1, hum_step=0.2, soil_step=2.0,
        max_temp_comp=3.0, max_hum_comp=5.0, max_soil_comp=20.0
    ) -> (new_base_temp, new_base_hum, new_base_soil)
"""

# 平均值正常阈值（保持与 anomaly_detector.py 一致）
AVG_TEMP_MIN   = 17.0   # 平均温度最低阈值 (℃)
AVG_TEMP_MAX   = 28.0   # 平均温度最高阈值 (℃)
AVG_HUM_MIN    = 40.0   # 平均湿度最低阈值 (%RH)
AVG_HUM_MAX    = 75.0   # 平均湿度最高阈值 (%RH)
AVG_SOIL_MIN   = 200.0  # 平均土壤含水量最低阈值（单位自定）
AVG_SOIL_MAX   = 600.0  # 平均土壤含水量最高阈值（单位自定）


def update_baselines(
    base_temp: float,
    base_hum: float,
    base_soil: float,
    avg_alert: list,
    temp_step: float = 0.1,
    hum_step: float = 0.2,
    soil_step: float = 2.0,
    max_temp_comp: float = 3.0,
    max_hum_comp: float = 5.0,
    max_soil_comp: float = 20.0
) -> tuple:
    """
    根据平均值告警调整基准，并在“需要补偿量 > 最大可补偿量”时打印人工干预告警。

    参数：
        base_temp      (float): 当前基准温度 (℃)。
        base_hum       (float): 当前基准湿度 (%RH)。
        base_soil      (float): 当前基准土壤含水量（单位自定）。
        avg_alert      (list) : 平均值告警列表，形如 [("avg_temperature", val), ...]。
        temp_step      (float): 温度单次补偿步长（单位℃），默认 0.1℃。
        hum_step       (float): 湿度单次补偿步长（单位%RH），默认 0.2%RH。
        soil_step      (float): 土壤含水量单次补偿步长（单位自定），默认 2 单位。
        max_temp_comp  (float): 温度每轮最大补偿能力（单位℃），默认 3.0℃。
        max_hum_comp   (float): 湿度每轮最大补偿能力（单位%RH），默认 5.0%RH。
        max_soil_comp  (float): 土壤含水量每轮最大补偿能力（单位自定），默认 20 单位。

    返回：
        (new_base_temp, new_base_hum, new_base_soil)
    """

    # 记录当前值以便后面对比
    old_temp, old_hum, old_soil = base_temp, base_hum, base_soil

    # 遍历 avg_alert，针对每一类平均值超限做“所需补偿”与“最大补偿”比较
    for (key, val) in avg_alert:

        if key == "avg_temperature":
            # 计算“实际所需补偿量”：
            # 若 avg 温度 > 上限，要降低： required = avg - AVG_TEMP_MAX；
            # 若 avg 温度 < 下限，要提高： required = AVG_TEMP_MIN - avg
            if val > AVG_TEMP_MAX:
                required = val - AVG_TEMP_MAX
                # 真正要补偿的量是 min(required, max_temp_comp)
                to_comp = min(required, max_temp_comp)
                base_temp -= to_comp
                if required > max_temp_comp:
                    print(f"⚠️ 平均温度 = {val:.2f} ℃， 超出上限 {AVG_TEMP_MAX} ℃，"
                          f"所需补偿 {required:.2f} ℃ ＞ 最大可补偿 {max_temp_comp:.2f} ℃；"
                          f"已补偿 {to_comp:.2f} ℃，剩余 {required - to_comp:.2f} ℃ 无法自动消解，请人工干预！")
                else:
                    print(f"🔧 平均温度 = {val:.2f} ℃ ＞ {AVG_TEMP_MAX} ℃，"
                          f"已补偿 {to_comp:.2f} ℃，新基准温度 {old_temp:.2f} ℃ → {base_temp:.2f} ℃")
            elif val < AVG_TEMP_MIN:
                required = AVG_TEMP_MIN - val
                to_comp = min(required, max_temp_comp)
                base_temp += to_comp
                if required > max_temp_comp:
                    print(f"⚠️ 平均温度 = {val:.2f} ℃， 低于下限 {AVG_TEMP_MIN} ℃，"
                          f"所需补偿 {required:.2f} ℃ ＞ 最大可补偿 {max_temp_comp:.2f} ℃；"
                          f"已补偿 {to_comp:.2f} ℃，剩余 {required - to_comp:.2f} ℃ 无法自动消解，请人工干预！")
                else:
                    print(f"🔧 平均温度 = {val:.2f} ℃ ＜ {AVG_TEMP_MIN} ℃，"
                          f"已补偿 {to_comp:.2f} ℃，新基准温度 {old_temp:.2f} ℃ → {base_temp:.2f} ℃")

            # 更新 old_temp，以免下一次打印时显示错误的“旧值”
            old_temp = base_temp

        elif key == "avg_humidity":
            if val > AVG_HUM_MAX:
                required = val - AVG_HUM_MAX
                to_comp = min(required, max_hum_comp)
                base_hum -= to_comp
                if required > max_hum_comp:
                    print(f"⚠️ 平均湿度 = {val:.2f}%RH， 超出上限 {AVG_HUM_MAX}%RH，"
                          f"所需补偿 {required:.2f}%RH ＞ 最大可补偿 {max_hum_comp:.2f}%RH；"
                          f"已补偿 {to_comp:.2f}%RH，剩余 {required - to_comp:.2f}%RH 无法自动消解，请人工干预！")
                else:
                    print(f"🔧 平均湿度 = {val:.2f}%RH ＞ {AVG_HUM_MAX}%RH，"
                          f"已补偿 {to_comp:.2f}%RH，新基准湿度 {old_hum:.2f}%RH → {base_hum:.2f}%RH")
            elif val < AVG_HUM_MIN:
                required = AVG_HUM_MIN - val
                to_comp = min(required, max_hum_comp)
                base_hum += to_comp
                if required > max_hum_comp:
                    print(f"⚠️ 平均湿度 = {val:.2f}%RH， 低于下限 {AVG_HUM_MIN}%RH，"
                          f"所需补偿 {required:.2f}%RH ＞ 最大可补偿 {max_hum_comp:.2f}%RH；"
                          f"已补偿 {to_comp:.2f}%RH，剩余 {required - to_comp:.2f}%RH 无法自动消解，请人工干预！")
                else:
                    print(f"🔧 平均湿度 = {val:.2f}%RH ＜ {AVG_HUM_MIN}%RH，"
                          f"已补偿 {to_comp:.2f}%RH，新基准湿度 {old_hum:.2f}%RH → {base_hum:.2f}%RH")

            old_hum = base_hum

        elif key == "avg_soil_moisture":
            if val > AVG_SOIL_MAX:
                required = val - AVG_SOIL_MAX
                to_comp = min(required, max_soil_comp)
                base_soil -= to_comp
                if required > max_soil_comp:
                    print(f"⚠️ 平均土壤含水量 = {val:.2f}， 超出上限 {AVG_SOIL_MAX}，"
                          f"所需补偿 {required:.2f} ＞ 最大可补偿 {max_soil_comp:.2f}；"
                          f"已补偿 {to_comp:.2f}，剩余 {required - to_comp:.2f} 无法自动消解，请人工干预！")
                else:
                    print(f"🔧 平均土壤含水量 = {val:.2f} ＞ {AVG_SOIL_MAX}，"
                          f"已补偿 {to_comp:.2f}，新基准土壤含水量 {old_soil:.2f} → {base_soil:.2f}")
            elif val < AVG_SOIL_MIN:
                required = AVG_SOIL_MIN - val
                to_comp = min(required, max_soil_comp)
                base_soil += to_comp
                if required > max_soil_comp:
                    print(f"⚠️ 平均土壤含水量 = {val:.2f}， 低于下限 {AVG_SOIL_MIN}，"
                          f"所需补偿 {required:.2f} ＞ 最大可补偿 {max_soil_comp:.2f}；"
                          f"已补偿 {to_comp:.2f}，剩余 {required - to_comp:.2f} 无法自动消解，请人工干预！")
                else:
                    print(f"🔧 平均土壤含水量 = {val:.2f} ＜ {AVG_SOIL_MIN}，"
                          f"已补偿 {to_comp:.2f}，新基准土壤含水量 {old_soil:.2f} → {base_soil:.2f}")

            old_soil = base_soil

    # 完成所有平均值告警的补偿与提示后，返回新基准
    return base_temp, base_hum, base_soil


# 如果直接运行此模块，将演示 update_baselines() 的效果
if __name__ == "__main__":
    # 初始基准值示例
    base_temp = 25.0
    base_hum  = 60.0
    base_soil = 500.0

    # 假设 avg_alert 告警示例
    avg_alert_examples = [
        [("avg_temperature", 30.5)],                        # 平均温度过高
        [("avg_humidity", 35.0), ("avg_soil_moisture", 650)],# 平均湿度过低，土壤过高
        []                                                  # 无告警
    ]

    for idx, alerts in enumerate(avg_alert_examples, start=1):
        print(f"\n示例 {idx}: avg_alert = {alerts}")
        new_t, new_h, new_s = update_baselines(
            base_temp, base_hum, base_soil,
            avg_alert=alerts,
            temp_step=0.1,
            hum_step=0.2,
            soil_step=2.0,
            max_temp_comp=3.0,
            max_hum_comp=5.0,
            max_soil_comp=20.0
        )
        print(f"    旧基准：T={base_temp}, H={base_hum}, S={base_soil}")
        print(f"    新基准：T={new_t}, H={new_h}, S={new_s}")

        # 更新为新的基准值供下一轮演示
        base_temp, base_hum, base_soil = new_t, new_h, new_s
