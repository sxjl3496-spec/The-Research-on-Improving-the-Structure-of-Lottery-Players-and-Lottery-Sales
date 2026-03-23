"""
统计数据收集工具

用于收集和汇总各敏感性分析中的统计数据
"""

import pandas as pd
import numpy as np


def collect_summary_statistics(df):
    """
    收集汇总统计信息

    参数:
        df: 包含所有仿真结果的DataFrame

    返回:
        dict: 汇总统计信息
    """
    summary = {
        'total_simulations': len(df),
        'valid_simulations': len(df[df['composite_score'] > 0]),
        'best_score': df['composite_score'].max() if 'composite_score' in df else None,
        'best_add_cap': df.loc[df['composite_score'].idxmax(), 'add_cap'] if 'composite_score' in df else None,
        'mean_score': df['composite_score'].mean() if 'composite_score' in df else None,
        'std_score': df['composite_score'].std() if 'composite_score' in df else None,
    }
    return summary


def collect_income_group_statistics(df):
    """
    收集各收入群体统计信息

    参数:
        df: DataFrame

    返回:
        dict: 各收入群体统计
    """
    stats = {
        'low_income': {
            'mean_lottery': df['low_income_lottery'].mean(),
            'std_lottery': df['low_income_lottery'].std(),
            'mean_participation': df['low_participation'].mean() if 'low_participation' in df else None,
            'mean_per_capita': df['low_per_capita'].mean() if 'low_per_capita' in df else None,
        },
        'middle_income': {
            'mean_lottery': df['middle_income_lottery'].mean(),
            'std_lottery': df['middle_income_lottery'].std(),
            'mean_participation': df['middle_participation'].mean() if 'middle_participation' in df else None,
            'mean_per_capita': df['middle_per_capita'].mean() if 'middle_per_capita' in df else None,
        },
        'high_income': {
            'mean_lottery': df['high_income_lottery'].mean(),
            'std_lottery': df['high_income_lottery'].std(),
            'mean_participation': df['high_participation'].mean() if 'high_participation' in df else None,
            'mean_per_capita': df['high_per_capita'].mean() if 'high_per_capita' in df else None,
        },
    }
    return stats


def collect_parameter_statistics(df):
    """
    收集参数相关统计信息

    参数:
        df: DataFrame

    返回:
        dict: 参数统计信息
    """
    stats = {}

    if 'add_cap' in df.columns:
        stats['add_cap'] = {
            'min': df['add_cap'].min(),
            'max': df['add_cap'].max(),
            'mean': df['add_cap'].mean(),
            'std': df['add_cap'].std(),
        }

    if 'p' in df.columns:
        stats['p'] = {
            'min': df['p'].min(),
            'max': df['p'].max(),
            'mean': df['p'].mean(),
            'std': df['p'].std(),
        }

    if 'R_total' in df.columns:
        stats['R_total'] = {
            'min': df['R_total'].min(),
            'max': df['R_total'].max(),
            'unique': df['R_total'].unique().tolist(),
        }

    if 'B_total' in df.columns:
        stats['B_total'] = {
            'min': df['B_total'].min(),
            'max': df['B_total'].max(),
            'unique': df['B_total'].unique().tolist(),
        }

    return stats


def generate_summary_table(df):
    """
    生成汇总表格

    参数:
        df: DataFrame

    返回:
        DataFrame: 汇总表格
    """
    summary_data = []

    for idx, row in df.iterrows():
        entry = {
            'add_cap': row.get('add_cap', None),
            'p': row.get('p', None),
            'R_total': row.get('R_total', None),
            'R_pick': row.get('R_pick', None),
            'B_total': row.get('B_total', None),
            'B_pick': row.get('B_pick', None),
            'total_tickets': row.get('total_tickets', None),
            'structure_improvement': row.get('structure_improvement', None),
            'composite_score': row.get('composite_score', None),
            'y_sales': row.get('y_sales', None),
            'y_structure': row.get('y_structure', None),
        }
        summary_data.append(entry)

    return pd.DataFrame(summary_data)


def collect_all_statistics(df):
    """
    收集所有统计信息

    参数:
        df: DataFrame

    返回:
        dict: 所有统计信息的字典
    """
    return {
        'summary': collect_summary_statistics(df),
        'income_group': collect_income_group_statistics(df),
        'parameters': collect_parameter_statistics(df),
    }
