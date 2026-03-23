"""
收敛过程绘图脚本

根据仿真结果数据绘制贝叶斯优化的收敛曲线
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def plot_convergence_from_results(csv_path, output_path=None):
    """
    从结果CSV文件绘制收敛曲线

    参数:
        csv_path: 结果CSV文件路径
        output_path: 输出图片路径（可选）
    """
    df = pd.read_csv(csv_path)

    # 按时间顺序计算累计最优
    df_sorted = df.sort_index()
    cumulative_max = df_sorted['composite_score'].expanding().max()

    plt.figure(figsize=(10, 6))
    plt.plot(range(1, len(cumulative_max) + 1), cumulative_max, 'b-', linewidth=2, label='Best Score So Far')

    # 如果有每轮得分数据，绘制当前得分散点
    if 'y_sales' in df.columns and 'y_structure' in df.columns:
        current_scores = df_sorted['composite_score']
        plt.scatter(range(1, len(current_scores) + 1), current_scores, alpha=0.3, s=20, c='gray', label='Current Score')

    plt.xlabel('Simulation Run', fontsize=12)
    plt.ylabel('Composite Score', fontsize=12)
    plt.title('Bayesian Optimization Convergence Curve', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(fontsize=10)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"收敛曲线已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


def plot_convergence_with_history(history_path, output_path=None):
    """
    从优化历史数据绘制收敛曲线

    参数:
        history_path: 历史记录CSV文件路径（包含iteration, best_score等列）
        output_path: 输出图片路径（可选）
    """
    df = pd.read_csv(history_path)

    if 'iteration' not in df.columns or 'best_score' not in df.columns:
        print("历史文件必须包含 iteration 和 best_score 列")
        return

    plt.figure(figsize=(10, 6))

    iterations = df['iteration']
    best_scores = df['best_score']

    plt.plot(iterations, best_scores, 'b-', linewidth=2, label='Best Score So Far')
    plt.xlabel('Iteration', fontsize=12)
    plt.ylabel('Composite Score', fontsize=12)
    plt.title('Bayesian Optimization Convergence Curve', fontsize=14)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(fontsize=10)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"收敛曲线已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


def plot_multi_metric_convergence(df, output_path=None):
    """
    绘制多指标收敛曲线

    参数:
        df: 包含 composite_score, y_structure, y_sales 的DataFrame
        output_path: 输出图片路径（可选）
    """
    df_sorted = df.sort_index()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # 综合得分收敛
    cumulative_max = df_sorted['composite_score'].expanding().max()
    axes[0].plot(range(1, len(cumulative_max) + 1), cumulative_max, 'b-', linewidth=2)
    axes[0].set_xlabel('Simulation Run')
    axes[0].set_ylabel('Composite Score')
    axes[0].set_title('Composite Score Convergence')
    axes[0].grid(True, linestyle='--', alpha=0.6)

    # 结构得分收敛
    cumulative_max_structure = df_sorted['y_structure'].expanding().max()
    axes[1].plot(range(1, len(cumulative_max_structure) + 1), cumulative_max_structure, 'g-', linewidth=2)
    axes[1].set_xlabel('Simulation Run')
    axes[1].set_ylabel('Structure Score')
    axes[1].set_title('Structure Score Convergence')
    axes[1].grid(True, linestyle='--', alpha=0.6)

    # 销量得分收敛
    cumulative_max_sales = df_sorted['y_sales'].expanding().max()
    axes[2].plot(range(1, len(cumulative_max_sales) + 1), cumulative_max_sales, 'r-', linewidth=2)
    axes[2].set_xlabel('Simulation Run')
    axes[2].set_ylabel('Sales Score')
    axes[2].set_title('Sales Score Convergence')
    axes[2].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"多指标收敛曲线已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='绘制贝叶斯优化收敛曲线')
    parser.add_argument('--results', type=str, help='结果CSV文件路径')
    parser.add_argument('--output', type=str, help='输出图片路径')
    parser.add_argument('--history', type=str, help='历史记录CSV文件路径')

    args = parser.parse_args()

    if args.history:
        plot_convergence_with_history(args.history, args.output)
    elif args.results:
        plot_convergence_from_results(args.results, args.output)
    else:
        print("请提供 --results 或 --history 参数")
