"""
附录用图脚本

生成以下图表：
1. 帕累托前沿图
2. 参与率对比热力图
3. 人均购买量变化图
4. 参数相关性热力图
5. 销量结构分解图
6. 贝叶斯优化探索过程图（EI变化）
"""
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def plot_pareto_frontier(df, output_path=None):
    """
    帕累托前沿散点图
    销量得分 vs 结构得分散点图，标注帕累托最优解
    """
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
    non_pareto = df.drop(pareto_optimal)

    fig, ax = plt.subplots(figsize=(10, 8))

    # 所有点
    scatter = ax.scatter(non_pareto['y_sales'], non_pareto['y_structure'],
                        c=non_pareto['composite_score'], cmap='viridis',
                        alpha=0.5, s=30, label='All Points')

    # 帕累托最优解
    if len(pareto_df) > 0:
        ax.scatter(pareto_df['y_sales'], pareto_df['y_structure'],
                  c='red', s=100, marker='s', edgecolors='black',
                  linewidth=1, label='Pareto Optimal', zorder=5)

    ax.set_xlabel('销量得分 (y_sales)', fontsize=12)
    ax.set_ylabel('结构得分 (y_structure)', fontsize=12)
    ax.set_title('帕累托前沿：销量 vs 结构', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(fontsize=10)
    plt.colorbar(scatter, ax=ax, label='综合得分')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"帕累托前沿图已保存至: {output_path}")
    else:
        plt.show()

    plt.close()


def plot_participation_heatmap(df, output_path=None):
    """
    参与率对比热力图
    不同收入群体参与率随参数变化
    """
    if 'add_cap' in df.columns and 'low_participation' in df.columns:
        # 按封顶额分组的参与率
        pivot_low = df.pivot_table(values='low_participation', index='add_cap', aggfunc='mean')
        pivot_middle = df.pivot_table(values='middle_participation', index='add_cap', aggfunc='mean') if 'middle_participation' in df.columns else None
        pivot_high = df.pivot_table(values='high_participation', index='add_cap', aggfunc='mean') if 'high_participation' in df.columns else None

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        # 低收入参与率
        sns.heatmap(pivot_low, annot=True, cmap='YlOrRd', ax=axes[0], fmt='.1f')
        axes[0].set_title('低收入群体参与率')
        axes[0].set_xlabel('封顶额')
        axes[0].set_ylabel('参与率 (%)')

        # 中收入参与率
        if pivot_middle is not None:
            sns.heatmap(pivot_middle, annot=True, cmap='YlOrRd', ax=axes[1], fmt='.1f')
        axes[1].set_title('中收入群体参与率')
        axes[1].set_xlabel('封顶额')

        # 高收入参与率
        if pivot_high is not None:
            sns.heatmap(pivot_high, annot=True, cmap='YlOrRd', ax=axes[2], fmt='.1f')
        axes[2].set_title('高收入群体参与率')
        axes[2].set_xlabel('封顶额')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"参与率热力图已保存至: {output_path}")
        else:
            plt.show()
        plt.close()
    else:
        print("数据中缺少必要的列")


def plot_per_capita_purchase(df, output_path=None):
    """
    人均购买量变化图
    各收入群体人均购买量随参数变化
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 低收入人均
    if 'low_per_capita' in df.columns:
        axes[0, 0].scatter(df['add_cap'] if 'add_cap' in df.columns else range(len(df)),
                          df['low_per_capita'], alpha=0.6, s=30)
        axes[0, 0].set_xlabel('样本')
        axes[0, 0].set_ylabel('人均购买量 (元)')
        axes[0, 0].set_title('低收入群体人均购买量')
        axes[0, 0].grid(True, linestyle='--', alpha=0.6)

    # 中收入人均
    if 'middle_per_capita' in df.columns:
        axes[0, 1].scatter(df['add_cap'] if 'add_cap' in df.columns else range(len(df)),
                          df['middle_per_capita'], alpha=0.6, s=30)
        axes[0, 1].set_xlabel('样本')
        axes[0, 1].set_ylabel('人均购买量 (元)')
        axes[0, 1].set_title('中收入群体人均购买量')
        axes[0, 1].grid(True, linestyle='--', alpha=0.6)

    # 高收入人均
    if 'high_per_capita' in df.columns:
        axes[1, 0].scatter(df['add_cap'] if 'add_cap' in df.columns else range(len(df)),
                          df['high_per_capita'], alpha=0.6, s=30)
        axes[1, 0].set_xlabel('样本')
        axes[1, 0].set_ylabel('人均购买量 (元)')
        axes[1, 0].set_title('高收入群体人均购买量')
        axes[1, 0].grid(True, linestyle='--', alpha=0.6)

    # 中高收入综合人均
    if 'mid_high_per_capita' in df.columns:
        axes[1, 1].scatter(df['add_cap'] if 'add_cap' in df.columns else range(len(df)),
                          df['mid_high_per_capita'], alpha=0.6, s=30)
        axes[1, 1].set_xlabel('样本')
        axes[1, 1].set_ylabel('人均购买量 (元)')
        axes[1, 1].set_title('中高收入综合人均购买量')
        axes[1, 1].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"人均购买量图已保存至: {output_path}")
    else:
        plt.show()
    plt.close()


def plot_correlation_heatmap(df, output_path=None):
    """
    参数相关性热力图
    参数与输出指标的相关性
    """
    # 选择数值列
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df_numeric = df[numeric_cols]

    # 计算相关性矩阵
    corr_matrix = df_numeric.corr()

    fig, ax = plt.subplots(figsize=(14, 12))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0,
                square=True, fmt='.2f', cbar_kws={'shrink': 0.8}, ax=ax)
    ax.set_title('参数与输出指标相关性热力图', fontsize=14)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"相关性热力图已保存至: {output_path}")
    else:
        plt.show()
    plt.close()


def plot_sales_structure_stacked(df, output_path=None):
    """
    销量结构分解图
    堆叠柱状图显示各收入群体对总销量的贡献
    """
    if 'low_income_lottery' not in df.columns:
        print("数据中缺少必要的列")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # 按综合得分排序取前20个点
    df_sorted = df.nlargest(20, 'composite_score')

    # 堆叠柱状图
    x = range(len(df_sorted))
    width = 0.8

    axes[0].bar(x, df_sorted['low_income_lottery'], width, label='低收入', color='#ff9999')
    axes[0].bar(x, df_sorted['middle_income_lottery'], width,
                bottom=df_sorted['low_income_lottery'], label='中收入', color='#66b3ff')
    axes[0].bar(x, df_sorted['high_income_lottery'], width,
                bottom=df_sorted['low_income_lottery'] + df_sorted['middle_income_lottery'],
                label='高收入', color='#99ff99')

    axes[0].set_xlabel('参数组合（按综合得分排序）')
    axes[0].set_ylabel('销量 (亿元)')
    axes[0].set_title('各收入群体销量贡献（前20个最优组合）')
    axes[0].legend()
    axes[0].grid(True, linestyle='--', alpha=0.6)

    # 百分比堆叠图
    total = df_sorted['low_income_lottery'] + df_sorted['middle_income_lottery'] + df_sorted['high_income_lottery']
    low_pct = df_sorted['low_income_lottery'] / total * 100
    middle_pct = df_sorted['middle_income_lottery'] / total * 100
    high_pct = df_sorted['high_income_lottery'] / total * 100

    axes[1].bar(x, low_pct, width, label='低收入', color='#ff9999')
    axes[1].bar(x, middle_pct, width, bottom=low_pct, label='中收入', color='#66b3ff')
    axes[1].bar(x, high_pct, width, bottom=low_pct + middle_pct, label='高收入', color='#99ff99')

    axes[1].set_xlabel('参数组合（按综合得分排序）')
    axes[1].set_ylabel('占比 (%)')
    axes[1].set_title('各收入群体销量占比（前20个最优组合）')
    axes[1].legend()
    axes[1].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"销量结构分解图已保存至: {output_path}")
    else:
        plt.show()
    plt.close()


def plot_expected_improvement(df, output_path=None):
    """
    贝叶斯优化探索过程图
    显示期望改进(EI)的变化（如果有相关数据）
    """
    # 这个图需要从优化历史中获取EI数据
    # 如果结果中有ei列可以使用
    if 'ei' not in df.columns:
        print("数据中缺少 EI (期望改进) 列，跳过此图")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # EI分布随迭代变化
    if 'iteration' in df.columns:
        iterations = df.groupby('iteration')['ei'].mean()

        axes[0, 0].plot(iterations.index, iterations.values, 'b-', linewidth=2)
        axes[0, 0].set_xlabel('迭代轮次')
        axes[0, 0].set_ylabel('平均EI')
        axes[0, 0].set_title('期望改进随迭代变化')
        axes[0, 0].grid(True, linestyle='--', alpha=0.6)

        # EI的最大值
        ei_max = df.groupby('iteration')['ei'].max()
        axes[0, 1].plot(ei_max.index, ei_max.values, 'r-', linewidth=2)
        axes[0, 1].set_xlabel('迭代轮次')
        axes[0, 1].set_ylabel('最大EI')
        axes[0, 1].set_title('最大期望改进随迭代变化')
        axes[0, 1].grid(True, linestyle='--', alpha=0.6)

        # 累计最优得分
        if 'composite_score' in df.columns:
            cumulative_max = df.groupby('iteration')['composite_score'].max().expanding().max()
            axes[1, 0].plot(cumulative_max.index, cumulative_max.values, 'g-', linewidth=2)
            axes[1, 0].set_xlabel('迭代轮次')
            axes[1, 0].set_ylabel('累计最优得分')
            axes[1, 0].set_title('累计最优得分收敛')
            axes[1, 0].grid(True, linestyle='--', alpha=0.6)

            # 样本数随迭代变化
            sample_count = df.groupby('iteration').size().cumsum()
            axes[1, 1].plot(sample_count.index, sample_count.values, 'm-', linewidth=2)
            axes[1, 1].set_xlabel('迭代轮次')
            axes[1, 1].set_ylabel('累计样本数')
            axes[1, 1].set_title('训练集样本增长')
            axes[1, 1].grid(True, linestyle='--', alpha=0.6)
    else:
        print("数据中缺少 iteration 列")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"期望改进图已保存至: {output_path}")
    else:
        plt.show()
    plt.close()


def generate_all_appendix_plots(df, output_dir):
    """
    生成所有附录用图

    参数:
        df: DataFrame
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    print("生成附录用图...")

    # 1. 帕累托前沿图
    plot_pareto_frontier(df, os.path.join(output_dir, "appendix_pareto_frontier.png"))

    # 2. 参与率热力图
    plot_participation_heatmap(df, os.path.join(output_dir, "appendix_participation_heatmap.png"))

    # 3. 人均购买量变化图
    plot_per_capita_purchase(df, os.path.join(output_dir, "appendix_per_capita.png"))

    # 4. 相关性热力图
    plot_correlation_heatmap(df, os.path.join(output_dir, "appendix_correlation_heatmap.png"))

    # 5. 销量结构分解图
    plot_sales_structure_stacked(df, os.path.join(output_dir, "appendix_sales_structure.png"))

    # 6. 期望改进图（如果数据中有EI）
    if 'ei' in df.columns:
        plot_expected_improvement(df, os.path.join(output_dir, "appendix_expected_improvement.png"))

    print(f"所有附录用图已保存至: {output_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='生成附录用图')
    parser.add_argument('--results', type=str, required=True, help='结果CSV文件路径')
    parser.add_argument('--output-dir', type=str, required=True, help='输出目录')
    parser.add_argument('--type', type=str,
                       choices=['pareto', 'participation', 'percapita', 'correlation', 'structure', 'ei', 'all'],
                       default='all', help='图表类型')

    args = parser.parse_args()

    df = pd.read_csv(args.results)
    os.makedirs(args.output_dir, exist_ok=True)

    if args.type == 'pareto':
        plot_pareto_frontier(df, os.path.join(args.output_dir, "appendix_pareto_frontier.png"))
    elif args.type == 'participation':
        plot_participation_heatmap(df, os.path.join(args.output_dir, "appendix_participation_heatmap.png"))
    elif args.type == 'percapita':
        plot_per_capita_purchase(df, os.path.join(args.output_dir, "appendix_per_capita.png"))
    elif args.type == 'correlation':
        plot_correlation_heatmap(df, os.path.join(args.output_dir, "appendix_correlation_heatmap.png"))
    elif args.type == 'structure':
        plot_sales_structure_stacked(df, os.path.join(args.output_dir, "appendix_sales_structure.png"))
    elif args.type == 'ei':
        plot_expected_improvement(df, os.path.join(args.output_dir, "appendix_expected_improvement.png"))
    elif args.type == 'all':
        generate_all_appendix_plots(df, args.output_dir)
