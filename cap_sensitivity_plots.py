"""
封顶额敏感性分析绘图脚本（正文用图）

生成三张子图：
(a) 封顶额 vs 综合得分
(b) 封顶额 vs 销量
(c) 封顶额 vs 彩民结构指数
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


def plot_cap_sensitivity_main(df, output_path=None, title_prefix=""):
    """
    绘制封顶额敏感性分析正文用图（三子图）

    参数:
        df: 包含 add_cap, composite_score, total_tickets, structure_improvement 的DataFrame
        output_path: 输出图片路径（可选）
        title_prefix: 标题前缀（如"封顶额"）
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # (a) 综合得分
    axes[0].scatter(df['add_cap'], df['composite_score'], alpha=0.6, s=30, c='blue')
    axes[0].set_xlabel('封顶额 (万元)', fontsize=11)
    axes[0].set_ylabel('综合得分', fontsize=11)
    axes[0].set_title(f'(a) {title_prefix} vs 综合得分', fontsize=12)
    axes[0].grid(True, linestyle='--', alpha=0.6)

    # 标注最优点
    if len(df) > 0:
        best_idx = df['composite_score'].idxmax()
        best_row = df.loc[best_idx]
        axes[0].scatter([best_row['add_cap']], [best_row['composite_score']],
                       color='red', s=100, marker='*', zorder=5, label=f"最优点: {best_row['add_cap']:.1f}")
        axes[0].legend()

    # (b) 销量
    axes[1].scatter(df['add_cap'], df['total_tickets'], alpha=0.6, s=30, c='green')
    axes[1].set_xlabel('封顶额 (万元)', fontsize=11)
    axes[1].set_ylabel('销量 (亿元)', fontsize=11)
    axes[1].set_title(f'(b) {title_prefix} vs 销量', fontsize=12)
    axes[1].grid(True, linestyle='--', alpha=0.6)

    # 标注最优点
    if len(df) > 0:
        best_idx = df['total_tickets'].idxmax()
        best_row = df.loc[best_idx]
        axes[1].scatter([best_row['add_cap']], [best_row['total_tickets']],
                       color='red', s=100, marker='*', zorder=5)

    # (c) 结构指数
    axes[2].scatter(df['add_cap'], df['structure_improvement'], alpha=0.6, s=30, c='orange')
    axes[2].set_xlabel('封顶额 (万元)', fontsize=11)
    axes[2].set_ylabel('彩民结构指数', fontsize=11)
    axes[2].set_title(f'(c) {title_prefix} vs 彩民结构指数', fontsize=12)
    axes[2].grid(True, linestyle='--', alpha=0.6)

    # 标注最优点和目标线
    if len(df) > 0:
        best_idx = df['structure_improvement'].idxmax()
        best_row = df.loc[best_idx]
        axes[2].scatter([best_row['add_cap']], [best_row['structure_improvement']],
                       color='red', s=100, marker='*', zorder=5)
        # 添加目标值参考线
        axes[2].axhline(y=1.618, color='purple', linestyle='--', alpha=0.7, label='目标值 1.618')
        axes[2].legend()

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"封顶额敏感性正文图已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


def plot_cap_sensitivity_detailed(df, output_dir=None):
    """
    绘制封顶额敏感性分析详细图（包含更多子图）

    参数:
        df: DataFrame
        output_dir: 输出目录（可选）
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    # (a) 综合得分
    axes[0, 0].scatter(df['add_cap'], df['composite_score'], alpha=0.6, s=30)
    axes[0, 0].set_xlabel('封顶额 (万元)')
    axes[0, 0].set_ylabel('综合得分')
    axes[0, 0].set_title('(a) 综合得分')
    axes[0, 0].grid(True, linestyle='--', alpha=0.6)

    # (b) 销量
    axes[0, 1].scatter(df['add_cap'], df['total_tickets'], alpha=0.6, s=30)
    axes[0, 1].set_xlabel('封顶额 (万元)')
    axes[0, 1].set_ylabel('销量 (亿元)')
    axes[0, 1].set_title('(b) 销量')
    axes[0, 1].grid(True, linestyle='--', alpha=0.6)

    # (c) 结构指数
    axes[0, 2].scatter(df['add_cap'], df['structure_improvement'], alpha=0.6, s=30)
    axes[0, 2].set_xlabel('封顶额 (万元)')
    axes[0, 2].set_ylabel('彩民结构指数')
    axes[0, 2].set_title('(c) 彩民结构指数')
    axes[0, 2].axhline(y=1.618, color='purple', linestyle='--', alpha=0.7)
    axes[0, 2].grid(True, linestyle='--', alpha=0.6)

    # (d) 归一化销量得分
    axes[1, 0].scatter(df['add_cap'], df['y_sales'], alpha=0.6, s=30)
    axes[1, 0].set_xlabel('封顶额 (万元)')
    axes[1, 0].set_ylabel('销量得分')
    axes[1, 0].set_title('(d) 归一化销量得分')
    axes[1, 0].grid(True, linestyle='--', alpha=0.6)

    # (e) 归一化结构得分
    axes[1, 1].scatter(df['add_cap'], df['y_structure'], alpha=0.6, s=30)
    axes[1, 1].set_xlabel('封顶额 (万元)')
    axes[1, 1].set_ylabel('结构得分')
    axes[1, 1].set_title('(e) 归一化结构得分')
    axes[1, 1].grid(True, linestyle='--', alpha=0.6)

    # (f) 销量 vs 结构指数散点图
    axes[1, 2].scatter(df['total_tickets'], df['structure_improvement'],
                       c=df['composite_score'], cmap='viridis', alpha=0.6, s=30)
    axes[1, 2].set_xlabel('销量 (亿元)')
    axes[1, 2].set_ylabel('彩民结构指数')
    axes[1, 2].set_title('(f) 销量 vs 结构指数')
    axes[1, 2].grid(True, linestyle='--', alpha=0.6)
    plt.colorbar(axes[1, 2].collections[0], ax=axes[1, 2], label='综合得分')

    plt.tight_layout()

    if output_dir:
        output_path = os.path.join(output_dir, "cap_sensitivity_detailed.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"详细图已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='绘制封顶额敏感性分析图')
    parser.add_argument('--results', type=str, required=True, help='结果CSV文件路径')
    parser.add_argument('--output', type=str, help='输出图片路径')
    parser.add_argument('--detailed', action='store_true', help='生成详细版本')
    parser.add_argument('--output-dir', type=str, help='输出目录')

    args = parser.parse_args()

    df = pd.read_csv(args.results)

    if args.detailed:
        plot_cap_sensitivity_detailed(df, args.output_dir)
    else:
        plot_cap_sensitivity_main(df, args.output)
