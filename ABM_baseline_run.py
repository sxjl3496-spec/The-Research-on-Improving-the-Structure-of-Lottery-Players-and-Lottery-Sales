"""
基准参数运行脚本 - 双色球当前规则
运行基准政策仿真，输出完整统计数据

基准参数：
- add_cap: 0 (封顶额增加幅度)
- R_total: 33 (红球总数)
- R_pick: 6 (选红球数)
- B_total: 16 (蓝球总数)
- B_pick: 1 (选蓝球数)
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.special import comb

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import warnings

plt = None  # 延迟导入，避免baseline脚本不需要画图

# 配置
NETLOGO_PATH = r"D:/netlogo"
NLOGO_FILE = r"D:/BaiduSyncdisk/1DoctorStudy/1Doctor thesis/ABM-LOTTERY/normal20260203distribution.nlogo"
LOTTERY_TYPE = "DCB"
NUM_PERIODS = 1800
REPLICATIONS = 9  # 基准运行使用9次重复

# 基准参数
BASELINE_PARAMS = {
    'add_cap': 0,
    'R_total': 33,
    'R_pick': 6,
    'B_total': 16,
    'B_pick': 1
}

# tanh归一化系数计算
def calculate_a_coefficient(target_input, target_output):
    """根据目标输入和目标输出计算系数a"""
    if abs(target_output) >= 1:
        raise ValueError("target_output必须在(-1, 1)范围内")
    import math
    arctanh_value = 0.5 * math.log((1 + target_output) / (1 - target_output))
    a = arctanh_value / target_input
    return a

# 目标配置
SALES_TARGET_INPUT = 0.10
SALES_TARGET_OUTPUT = 0.618
STRUCTURE_TARGET_INPUT = 1.618
STRUCTURE_TARGET_OUTPUT = 0.382

SALES_A_COEFFICIENT = calculate_a_coefficient(SALES_TARGET_INPUT, SALES_TARGET_OUTPUT)
STRUCTURE_A_COEFFICIENT = calculate_a_coefficient(STRUCTURE_TARGET_INPUT, STRUCTURE_TARGET_OUTPUT)


def calculate_winning_probability(R_total, R_pick, B_total, B_pick):
    """计算中奖概率"""
    red_combinations = comb(R_total, R_pick, exact=True)
    blue_combinations = comb(B_total, B_pick, exact=True)
    return 1.0 / (red_combinations * blue_combinations)


def normalize_tanh_improvement(series, baseline_value, a=1.0):
    """使用带系数a的tanh函数对改善性指标进行归一化"""
    return np.tanh(a * (series - baseline_value) / baseline_value)


def calculate_structure_improvement_index(df):
    """
    计算彩民结构指数 = 中高收入人群彩票消费总量 / 低收入人群彩票消费总量
    """
    # 中高收入消费总量 / 低收入消费总量
    df['structure_improvement'] = (
        (df['middle_income_lottery'] + df['high_income_lottery']) /
        df['low_income_lottery']
    )

    # 人均购买量（辅助分析）
    POP_LOW = 9.448e8
    POP_MID = 1.642e8
    POP_HIGH = 0.390e8
    POP_MID_HIGH = POP_MID + POP_HIGH

    df['low_per_capita'] = df['low_income_lottery'] * 1e8 / POP_LOW
    df['middle_per_capita'] = df['middle_income_lottery'] * 1e8 / POP_MID
    df['high_per_capita'] = df['high_income_lottery'] * 1e8 / POP_HIGH
    df['mid_high_per_capita'] = (df['middle_income_lottery'] + df['high_income_lottery']) * 1e8 / POP_MID_HIGH

    return df


def calculate_composite_score(df, baseline_sales, baseline_structure):
    """
    计算综合得分
    - y_structure: 结构指数的tanh归一化得分
    - y_sales: 销量的tanh归一化得分
    - composite_score = 0.618 * y_structure + 0.382 * y_sales
    """
    valid_rows = (df['total_tickets'] != 0) | (df['structure_improvement'] != 0)

    y_sales = pd.Series(index=df.index, dtype=float)
    y_structure = pd.Series(index=df.index, dtype=float)

    if valid_rows.any():
        y_sales.loc[valid_rows] = normalize_tanh_improvement(
            df.loc[valid_rows, 'total_tickets'], baseline_sales, SALES_A_COEFFICIENT
        )
        y_structure.loc[valid_rows] = normalize_tanh_improvement(
            df.loc[valid_rows, 'structure_improvement'], baseline_structure, STRUCTURE_A_COEFFICIENT
        )

    invalid_rows = ~valid_rows
    if invalid_rows.any():
        y_sales.loc[invalid_rows] = 0.0
        y_structure.loc[invalid_rows] = 0.0

    # 黄金分割比例权重
    score = 0.618 * y_structure + 0.382 * y_sales

    df['y_sales'] = y_sales
    df['y_structure'] = y_structure
    df['composite_score'] = score

    return df


def run_single_simulation(add_cap, p, num_periods, rep_id, netlogo_path, nlogo_file):
    """运行单次仿真"""
    import pynetlogo

    temp_netlogo = pynetlogo.NetLogoLink(netlogo_home=netlogo_path, gui=False)
    temp_netlogo.load_model(nlogo_file)

    # 设置校准参数
    calibrated_params = {
        'u_con': 0.0568,
        'u_sr': 355.16,
        'sd_con': 2.7e-05,
        'sd_sr': 0.729
    }

    temp_netlogo.command(f'set u-con {calibrated_params["u_con"]}')
    temp_netlogo.command(f'set u-sr {calibrated_params["u_sr"]}')
    temp_netlogo.command(f'set sd-con {calibrated_params["sd_con"]}')
    temp_netlogo.command(f'set sd-sr {calibrated_params["sd_sr"]}')

    # 设置政策参数
    temp_netlogo.command(f'set add_cap {add_cap}')
    temp_netlogo.command(f'set p {p}')

    # 运行仿真
    temp_netlogo.command('setup')

    # 收集时间序列数据
    period_data = []
    for period in range(num_periods):
        temp_netlogo.command('go')
        if period % 100 == 0:
            low_lottery = temp_netlogo.report('low-income-lottery') or 0
            middle_lottery = temp_netlogo.report('middle-income-lottery') or 0
            high_lottery = temp_netlogo.report('high-income-lottery') or 0
            pool = temp_netlogo.report('pool') or 0

            period_record = {
                'period': period,
                'low_income_lottery': low_lottery,
                'middle_income_lottery': middle_lottery,
                'high_income_lottery': high_lottery,
                'pool': pool
            }
            period_data.append(period_record)

    # 收集最终结果
    total_tickets = temp_netlogo.report('total-tickets') or 0
    low_lottery_final = temp_netlogo.report('low-income-lottery') or 0
    middle_lottery_final = temp_netlogo.report('middle-income-lottery') or 0
    high_lottery_final = temp_netlogo.report('high-income-lottery') or 0
    pool_final = temp_netlogo.report('pool') or 0

    # 参与率
    low_participation = temp_netlogo.report('low-participation') or 0
    middle_participation = temp_netlogo.report('middle-participation') or 0
    high_participation = temp_netlogo.report('high-participation') or 0

    # 关闭NetLogo实例
    temp_netlogo.kill_workspace()

    result = {
        'rep_id': rep_id,
        'add_cap': add_cap,
        'p': p,
        'total_tickets': total_tickets,
        'low_income_lottery': low_lottery_final,
        'middle_income_lottery': middle_lottery_final,
        'high_income_lottery': high_lottery_final,
        'pool': pool_final,
        'low_participation': low_participation,
        'middle_participation': middle_participation,
        'high_participation': high_participation,
        'time_series_data': period_data
    }

    return result


def run_baseline_simulation():
    """运行基准仿真"""
    print("=" * 80)
    print("基准参数仿真 - 双色球当前规则")
    print("=" * 80)

    add_cap = BASELINE_PARAMS['add_cap']
    R_total = BASELINE_PARAMS['R_total']
    R_pick = BASELINE_PARAMS['R_pick']
    B_total = BASELINE_PARAMS['B_total']
    B_pick = BASELINE_PARAMS['B_pick']

    p = calculate_winning_probability(R_total, R_pick, B_total, B_pick)

    print(f"\n基准参数：")
    print(f"  封顶额增加幅度: {add_cap} 万元")
    print(f"  红球规则: {R_total}选{R_pick}")
    print(f"  蓝球规则: {B_total}选{B_pick}")
    print(f"  中奖概率: p = {p:.6e}")
    print(f"  仿真期数: {NUM_PERIODS}")
    print(f"  重复次数: {REPLICATIONS}")
    print()

    print("开始仿真...")
    start_time = datetime.now()

    results = []
    for rep in range(REPLICATIONS):
        print(f"  运行重复 {rep + 1}/{REPLICATIONS}...")
        result = run_single_simulation(
            add_cap, p, NUM_PERIODS, rep,
            NETLOGO_PATH, NLOGO_FILE
        )
        results.append(result)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n仿真完成，耗时: {elapsed:.1f} 秒")

    # 计算平均值
    avg_result = {}
    for key in results[0].keys():
        if isinstance(results[0][key], (int, float)):
            avg_result[key] = np.mean([r[key] for r in results])
            # 同时计算标准差
            avg_result[f'{key}_std'] = np.std([r[key] for r in results])

    avg_result.update({
        'add_cap': add_cap,
        'R_total': R_total,
        'R_pick': R_pick,
        'B_total': B_total,
        'B_pick': B_pick,
        'p': p
    })

    return avg_result, results


def generate_statistics_report(avg_result, output_dir):
    """生成统计报告"""
    report_path = os.path.join(output_dir, "baseline_statistics_report.txt")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("基准参数仿真统计报告\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("【参数设置】\n")
        f.write(f"  封顶额增加幅度: {avg_result['add_cap']:.1f} 万元\n")
        f.write(f"  红球规则: {avg_result['R_total']:.0f}选{avg_result['R_pick']:.0f}\n")
        f.write(f"  蓝球规则: {avg_result['B_total']:.0f}选{avg_result['B_pick']:.0f}\n")
        f.write(f"  中奖概率: {avg_result['p']:.6e}\n\n")

        f.write("【销量指标】\n")
        f.write(f"  总销量: {avg_result['total_tickets']:.2f} 亿元\n")
        f.write(f"    - 低收入人群购买量: {avg_result['low_income_lottery']:.2f} 亿元\n")
        f.write(f"    - 中收入人群购买量: {avg_result['middle_income_lottery']:.2f} 亿元\n")
        f.write(f"    - 高收入人群购买量: {avg_result['high_income_lottery']:.2f} 亿元\n")
        f.write(f"  奖池金额: {avg_result['pool']:.2f} 亿元\n\n")

        f.write("【彩民结构指数】\n")
        f.write(f"  结构指数 = (中高收入消费总量) / (低收入消费总量)\n")
        structure_idx = (avg_result['middle_income_lottery'] + avg_result['high_income_lottery']) / avg_result['low_income_lottery']
        f.write(f"  结构指数 = ({avg_result['middle_income_lottery']:.2f} + {avg_result['high_income_lottery']:.2f}) / {avg_result['low_income_lottery']:.2f}\n")
        f.write(f"  结构指数值: {structure_idx:.4f}\n\n")

        f.write("【人均购买量】\n")
        POP_LOW = 9.448e8
        POP_MID = 1.642e8
        POP_HIGH = 0.390e8
        POP_MID_HIGH = POP_MID + POP_HIGH

        low_pc = avg_result['low_income_lottery'] * 1e8 / POP_LOW
        mid_pc = avg_result['middle_income_lottery'] * 1e8 / POP_MID
        high_pc = avg_result['high_income_lottery'] * 1e8 / POP_HIGH
        mid_high_pc = (avg_result['middle_income_lottery'] + avg_result['high_income_lottery']) * 1e8 / POP_MID_HIGH

        f.write(f"  低收入人均购买量: {low_pc:.2f} 元\n")
        f.write(f"  中收入人均购买量: {mid_pc:.2f} 元\n")
        f.write(f"  高收入人均购买量: {high_pc:.2f} 元\n")
        f.write(f"  中高收入综合人均: {mid_high_pc:.2f} 元\n\n")

        f.write("【参与率】\n")
        f.write(f"  低收入人群参与率: {avg_result['low_participation']:.2f}%\n")
        f.write(f"  中收入人群参与率: {avg_result['middle_participation']:.2f}%\n")
        f.write(f"  高收入人群参与率: {avg_result['high_participation']:.2f}%\n\n")

        f.write("【综合得分】\n")
        # 这里只输出结构指数值，得分需要相对基准计算
        f.write(f"  结构指数: {structure_idx:.4f}\n")
        f.write(f"  (得分需在敏感性分析中相对基准计算)\n\n")

        f.write("=" * 70 + "\n")

    return report_path


def main():
    print("\n" + "=" * 80)
    print("博士论文敏感性分析 - 基准参数运行脚本")
    print("=" * 80)

    # 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join("baseline_results", f"results_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n输出目录: {output_dir}")

    # 运行基准仿真
    avg_result, all_results = run_baseline_simulation()

    # 创建DataFrame
    df = pd.DataFrame([avg_result])

    # 计算结构指数和人均
    df = calculate_structure_improvement_index(df)

    # 打印统计表
    print("\n" + "=" * 80)
    print("基准参数统计结果")
    print("=" * 80)

    print(f"\n【参数】")
    print(f"  add_cap = {avg_result['add_cap']:.1f}")
    print(f"  R_total = {avg_result['R_total']:.0f}, R_pick = {avg_result['R_pick']:.0f}")
    print(f"  B_total = {avg_result['B_total']:.0f}, B_pick = {avg_result['B_pick']:.0f}")
    print(f"  p = {avg_result['p']:.6e}")

    print(f"\n【销量】")
    print(f"  总销量 = {avg_result['total_tickets']:.2f} 亿元")
    print(f"  低收入 = {avg_result['low_income_lottery']:.2f} 亿元")
    print(f"  中收入 = {avg_result['middle_income_lottery']:.2f} 亿元")
    print(f"  高收入 = {avg_result['high_income_lottery']:.2f} 亿元")

    structure_idx = (avg_result['middle_income_lottery'] + avg_result['high_income_lottery']) / avg_result['low_income_lottery']
    print(f"\n【彩民结构指数】")
    print(f"  (中收入 + 高收入) / 低收入 = {structure_idx:.4f}")

    print(f"\n【参与率】")
    print(f"  低收入参与率 = {avg_result['low_participation']:.2f}%")
    print(f"  中收入参与率 = {avg_result['middle_participation']:.2f}%")
    print(f"  高收入参与率 = {avg_result['high_participation']:.2f}%")

    POP_LOW = 9.448e8
    POP_MID = 1.642e8
    POP_HIGH = 0.390e8
    POP_MID_HIGH = POP_MID + POP_HIGH

    low_pc = avg_result['low_income_lottery'] * 1e8 / POP_LOW
    mid_pc = avg_result['middle_income_lottery'] * 1e8 / POP_MID
    high_pc = avg_result['high_income_lottery'] * 1e8 / POP_HIGH
    mid_high_pc = (avg_result['middle_income_lottery'] + avg_result['high_income_lottery']) * 1e8 / POP_MID_HIGH

    print(f"\n【人均购买量】")
    print(f"  低收入人均 = {low_pc:.2f} 元")
    print(f"  中收入人均 = {mid_pc:.2f} 元")
    print(f"  高收入人均 = {high_pc:.2f} 元")
    print(f"  中高收入综合人均 = {mid_high_pc:.2f} 元")

    print("=" * 80)

    # 保存CSV
    csv_path = os.path.join(output_dir, f"baseline_results_{timestamp}.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n结果已保存至: {csv_path}")

    # 保存JSON
    json_data = {k: v for k, v in avg_result.items() if not k.endswith('_std')}
    # 移除time_series_data
    json_data.pop('time_series_data', None)
    json_path = os.path.join(output_dir, f"baseline_params_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)
    print(f"参数已保存至: {json_path}")

    # 生成统计报告
    report_path = generate_statistics_report(avg_result, output_dir)
    print(f"统计报告已保存至: {report_path}")

    print("\n程序结束")


if __name__ == "__main__":
    main()
