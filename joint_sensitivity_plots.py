"""
联合敏感性分析绘图脚本（正文用3D图）

生成三维图：
- X轴：封顶额
- Y轴：中奖概率（对数刻度）
- Z轴：综合得分/销量/彩民结构指数
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def plot_joint_sensitivity_3d(df, output_path=None):
    """
    绘制联合敏感性分析3D图（三视图）

    参数:
        df: 包含 add_cap, p, composite_score, total_tickets, structure_improvement 的DataFrame
        output_path: 输出图片路径（可选）
    """
    fig = plt.figure(figsize=(18, 6))

    # 综合得分3D图
    ax1 = fig.add_subplot(131, projection='3d')
    scatter1 = ax1.scatter(df['add_cap'], np.log10(df['p']),
                           df['composite_score'],
                           c=df['composite_score'], cmap='viridis', s=30, alpha=0.7)
    ax1.set_xlabel('封顶额 (万元)', fontsize=10)
    ax1.set_ylabel('Log10(p)', fontsize=10)
    ax1.set_zlabel('综合得分', fontsize=10)
    ax1.set_title('(a) 综合得分', fontsize=12)
    fig.colorbar(scatter1, ax=ax1, shrink=0.5, label='综合得分')

    # 销量3D图
    ax2 = fig.add_subplot(132, projection='3d')
    scatter2 = ax2.scatter(df['add_cap'], np.log10(df['p']),
                           df['total_tickets'],
                           c=df['total_tickets'], cmap='viridis', s=30, alpha=0.7)
    ax2.set_xlabel('封顶额 (万元)', fontsize=10)
    ax2.set_ylabel('Log10(p)', fontsize=10)
    ax2.set_zlabel('销量 (亿元)', fontsize=10)
    ax2.set_title('(b) 销量', fontsize=12)
    fig.colorbar(scatter2, ax=ax2, shrink=0.5, label='销量')

    # 结构指数3D图
    ax3 = fig.add_subplot(133, projection='3d')
    scatter3 = ax3.scatter(df['add_cap'], np.log10(df['p']),
                           df['structure_improvement'],
                           c=df['structure_improvement'], cmap='viridis', s=30, alpha=0.7)
    ax3.set_xlabel('封顶额 (万元)', fontsize=10)
    ax3.set_ylabel('Log10(p)', fontsize=10)
    ax3.set_zlabel('彩民结构指数', fontsize=10)
    ax3.set_title('(c) 彩民结构指数', fontsize=12)
    ax3.axhline(y=np.log10(1.618), color='purple', linestyle='--', alpha=0.7)
    fig.colorbar(scatter3, ax=ax3, shrink=0.5, label='结构指数')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"联合敏感性3D图已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


def plot_joint_sensitivity_contour(df, output_path=None):
    """
    绘制联合敏感性分析等高线图

    参数:
        df: DataFrame
        output_path: 输出图片路径（可选）
    """
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 综合得分等高线
    ax1 = axes[0]
    scatter1 = ax1.scatter(df['add_cap'], np.log10(df['p']),
                           c=df['composite_score'], cmap='viridis', s=30, alpha=0.7)
    ax1.set_xlabel('封顶额 (万元)')
    ax1.set_ylabel('Log10(p)')
    ax1.set_title('(a) 综合得分')
    plt.colorbar(scatter1, ax=ax1, label='综合得分')

    # 销量等高线
    ax2 = axes[1]
    scatter2 = ax2.scatter(df['add_cap'], np.log10(df['p']),
                           c=df['total_tickets'], cmap='viridis', s=30, alpha=0.7)
    ax2.set_xlabel('封顶额 (万元)')
    ax2.set_ylabel('Log10(p)')
    ax2.set_title('(b) 销量')
    plt.colorbar(scatter2, ax=ax2, label='销量')

    # 结构指数等高线
    ax3 = axes[2]
    scatter3 = ax3.scatter(df['add_cap'], np.log10(df['p']),
                           c=df['structure_improvement'], cmap='viridis', s=30, alpha=0.7)
    ax3.set_xlabel('封顶额 (万元)')
    ax3.set_ylabel('Log10(p)')
    ax3.set_title('(c) 彩民结构指数')
    plt.colorbar(scatter3, ax=ax3, label='结构指数')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"等高线图已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


def plot_parameter_tradeoff(df, output_path=None):
    """
    绘制参数权衡分析图

    参数:
        df: DataFrame
        output_path: 输出图片路径（可选）
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # 封顶额 vs 销量（按结构指数着色）
    ax1 = axes[0, 0]
    scatter1 = ax1.scatter(df['add_cap'], df['total_tickets'],
                          c=df['structure_improvement'], cmap='RdYlGn', s=30, alpha=0.7)
    ax1.set_xlabel('封顶额 (万元)')
    ax1.set_ylabel('销量 (亿元)')
    ax1.set_title('封顶额 vs 销量')
    plt.colorbar(scatter1, ax=ax1, label='结构指数')
    ax1.grid(True, linestyle='--', alpha=0.6)

    # 封顶额 vs 结构指数（按销量着色）
    ax2 = axes[0, 1]
    scatter2 = ax2.scatter(df['add_cap'], df['structure_improvement'],
                           c=df['total_tickets'], cmap='RdYlGn', s=30, alpha=0.7)
    ax2.set_xlabel('封顶额 (万元)')
    ax2.set_ylabel('结构指数')
    ax2.set_title('封顶额 vs 结构指数')
    ax2.axhline(y=1.618, color='purple', linestyle='--', alpha=0.7, label='目标值')
    plt.colorbar(scatter2, ax=ax2, label='销量')
    ax2.grid(True, linestyle='--', alpha=0.6)

    # 中奖概率 vs 销量（按结构指数着色）
    ax3 = axes[1, 0]
    scatter3 = ax3.scatter(np.log10(df['p']), df['total_tickets'],
                           c=df['structure_improvement'], cmap='RdYlGn', s=30, alpha=0.7)
    ax3.set_xlabel('Log10(p)')
    ax3.set_ylabel('销量 (亿元)')
    ax3.set_title('中奖概率 vs 销量')
    plt.colorbar(scatter3, ax=ax3, label='结构指数')
    ax3.grid(True, linestyle='--', alpha=0.6)

    # 中奖概率 vs 结构指数（按销量着色）
    ax4 = axes[1, 1]
    scatter4 = ax4.scatter(np.log10(df['p']), df['structure_improvement'],
                           c=df['total_tickets'], cmap='RdYlGn', s=30, alpha=0.7)
    ax4.set_xlabel('Log10(p)')
    ax4.set_ylabel('结构指数')
    ax4.set_title('中奖概率 vs 结构指数')
    ax4.axhline(y=1.618, color='purple', linestyle='--', alpha=0.7, label='目标值')
    plt.colorbar(scatter4, ax=ax4, label='销量')
    ax4.grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"参数权衡分析图已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


def plot_pareto_frontier_joint(df, output_path=None):
    """
    绘制联合分析帕累托前沿

    参数:
        df: DataFrame
        output_path: 输出图片路径（可选）
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # 找到帕累托最优解
    pareto_optimal = []
    for i, row in df.iterrows():
        is_pareto = True
        for j, other_row in df.iterrows():
            if i == j:
                continue
            if (other_row['y_structure'] >= row['y_structure'] and
                other_row['y_sales'] >= row['y_sales'] and
                (other_row['y_structure'] > row['y_structure'] or other_row['y_sales'] > row['y_sales'])):
                is_pareto = False
                break
        if is_pareto:
            pareto_optimal.append(i)

    pareto_df = df.iloc[pareto_optimal]

    # 绘制所有点
    non_pareto = df.drop(pareto_optimal)
    ax.scatter(non_pareto['y_sales'], non_pareto['y_structure'], non_pareto['composite_score'],
              c='gray', alpha=0.3, s=20, label='All Points')

    # 绘制帕累托最优解
    ax.scatter(pareto_df['y_sales'], pareto_df['y_structure'], pareto_df['composite_score'],
              c='red', s=100, marker='s', edgecolors='black', linewidth=1, label='Pareto Optimal')

    ax.set_xlabel('销量得分 (y_sales)')
    ax.set_ylabel('结构得分 (y_structure)')
    ax.set_zlabel('综合得分')
    ax.set_title('联合敏感性分析帕累托前沿')
    ax.legend()

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"帕累托前沿图已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='绘制联合敏感性分析图')
    parser.add_argument('--results', type=str, required=True, help='结果CSV文件路径')
    parser.add_argument('--output', type=str, help='输出图片路径')
    parser.add_argument('--type', type=str, choices=['3d', 'contour', 'tradeoff', 'pareto'],
                       default='3d', help='图表类型')
    parser.add_argument('--output-dir', type=str, help='输出目录')

    args = parser.parse_args()

    df = pd.read_csv(args.results)

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    if args.type == '3d':
        output_path = args.output or os.path.join(args.output_dir, "joint_sensitivity_3d.png") if args.output_dir else None
        plot_joint_sensitivity_3d(df, output_path)
    elif args.type == 'contour':
        output_path = args.output or os.path.join(args.output_dir, "joint_sensitivity_contour.png") if args.output_dir else None
        plot_joint_sensitivity_contour(df, output_path)
    elif args.type == 'tradeoff':
        output_path = args.output or os.path.join(args.output_dir, "parameter_tradeoff.png") if args.output_dir else None
        plot_parameter_tradeoff(df, output_path)
    elif args.type == 'pareto':
        output_path = args.output or os.path.join(args.output_dir, "pareto_frontier_joint.png") if args.output_dir else None
        plot_pareto_frontier_joint(df, output_path)
