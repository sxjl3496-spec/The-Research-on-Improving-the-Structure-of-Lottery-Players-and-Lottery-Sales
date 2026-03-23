"""
彩民结构指数计算工具

新公式：结构指数 = 中高收入人群彩票消费总量 / 低收入人群彩票消费总量
     = (middle_income_lottery + high_income_lottery) / low_income_lottery

目标最佳值：1.618（黄金分割比）
"""

import numpy as np
import pandas as pd

# 人口参数
POP_LOW = 9.448e8      # 低收入人口
POP_MID = 1.642e8      # 中收入人口
POP_HIGH = 0.390e8     # 高收入人口
POP_MID_HIGH = POP_MID + POP_HIGH  # 中高收入合计人口


def calculate_structure_index(df):
    """
    计算彩民结构指数 = 中高收入人群彩票消费总量 / 低收入人群彩票消费总量

    参数:
        df: DataFrame，必须包含 low_income_lottery, middle_income_lottery, high_income_lottery 列

    返回:
        df: 添加了 structure_improvement 列的 DataFrame
    """
    df['structure_improvement'] = (
        (df['middle_income_lottery'] + df['high_income_lottery']) /
        df['low_income_lottery']
    )
    return df


def calculate_per_capita(df):
    """
    计算各收入群体人均购买量（辅助分析用）

    参数:
        df: DataFrame，必须包含彩票消费列

    返回:
        df: 添加了各人均购买量列的 DataFrame
    """
    df['low_per_capita'] = df['low_income_lottery'] * 1e8 / POP_LOW
    df['middle_per_capita'] = df['middle_income_lottery'] * 1e8 / POP_MID
    df['high_per_capita'] = df['high_income_lottery'] * 1e8 / POP_HIGH
    df['mid_high_per_capita'] = (
        (df['middle_income_lottery'] + df['high_income_lottery']) * 1e8 / POP_MID_HIGH
    )
    return df


def calculate_share(df):
    """
    计算各收入群体彩票购买量占比

    参数:
        df: DataFrame，必须包含各收入群体彩票消费列

    返回:
        df: 添加了各占比列的 DataFrame
    """
    total = df['low_income_lottery'] + df['middle_income_lottery'] + df['high_income_lottery']
    df['low_share'] = df['low_income_lottery'] / total * 100
    df['middle_share'] = df['middle_income_lottery'] / total * 100
    df['high_share'] = df['high_income_lottery'] / total * 100
    df['mid_high_share'] = df['middle_share'] + df['high_share']
    return df


def calculate_all_metrics(df):
    """
    计算所有结构相关指标

    参数:
        df: DataFrame

    返回:
        df: 添加了所有结构指标的 DataFrame
    """
    df = calculate_structure_index(df)
    df = calculate_per_capita(df)
    df = calculate_share(df)
    return df


# ========== tanh归一化系数计算 ==========

def calculate_a_coefficient(target_input, target_output):
    """
    根据目标输入和目标输出计算系数a

    参数:
        target_input: 当(series-baseline_value)/baseline_value达到的目标值
        target_output: 希望此时tanh函数输出的目标值

    返回:
        a: 用于normalize_tanh_improvement函数的缩放系数
    """
    if abs(target_output) >= 1:
        raise ValueError("target_output必须在(-1, 1)范围内")
    import math
    arctanh_value = 0.5 * math.log((1 + target_output) / (1 - target_output))
    a = arctanh_value / target_input
    return a


def normalize_tanh_improvement(series, baseline_value, a=1.0):
    """
    使用带系数a的tanh函数对改善性指标进行归一化

    参数:
        series: 输入序列
        baseline_value: 基准值
        a: 缩放系数

    返回:
        归一化后的值
    """
    return np.tanh(a * (series - baseline_value) / baseline_value)


# 预计算的系数
SALES_TARGET_INPUT = 0.10
SALES_TARGET_OUTPUT = 0.618
STRUCTURE_TARGET_INPUT = 1.618
STRUCTURE_TARGET_OUTPUT = 0.382

SALES_A_COEFFICIENT = calculate_a_coefficient(SALES_TARGET_INPUT, SALES_TARGET_OUTPUT)
STRUCTURE_A_COEFFICIENT = calculate_a_coefficient(STRUCTURE_TARGET_INPUT, STRUCTURE_TARGET_OUTPUT)


def calculate_composite_score(df, baseline_sales, baseline_structure):
    """
    计算综合得分

    参数:
        df: DataFrame，必须包含 total_tickets 和 structure_improvement 列
        baseline_sales: 销量基准值
        baseline_structure: 结构指数基准值

    返回:
        df: 添加了 y_sales, y_structure, composite_score 列的 DataFrame
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

    # 黄金分割比例权重：结构 0.618，销量 0.382
    score = 0.618 * y_structure + 0.382 * y_sales

    df['y_sales'] = y_sales
    df['y_structure'] = y_structure
    df['composite_score'] = score

    return df
