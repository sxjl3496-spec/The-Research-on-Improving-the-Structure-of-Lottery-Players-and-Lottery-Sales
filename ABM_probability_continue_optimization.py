"""
概率敏感性分析 - 断点续跑脚本

基于已有的100次迭代结果，继续运行50次贝叶斯优化迭代，
寻找能同时改善彩民结构和销量的概率参数组合。
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.special import comb
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel as C
from multiprocessing import Pool
import warnings
import json
import matplotlib.pyplot as plt
import seaborn as sns

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ABM_Netlogo_analyze import LotterySensitivityAnalyzer

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# ========== 配置 ==========
EXISTING_RESULTS_DIR = r"d:\Pycharm\PycharmProjects\probability_only_sensitivity_v2\results_20260323_145413"
NETLOGO_PATH = r"D:/netlogo"
NLOGO_FILE = r"D:/BaiduSyncdisk/1DoctorStudy/1Doctor thesis/ABM-LOTTERY/normal20260203distribution.nlogo"
LOTTERY_TYPE = "DCB"
NUM_PERIODS = 1800

# 续跑配置
CONTINUE_ITERATIONS = 50      # 继续运行50次迭代
BAYES_CANDIDATES = 2          # 每轮2个候选点
REPLICATIONS = 2               # 每组参数重复2次
PROCESSES_BAYES = 4           # 4个子进程并行

PARAM_NAMES = ['R_total', 'R_pick', 'B_total', 'B_pick']

# 目标配置
SALES_TARGET_INPUT = 0.10
SALES_TARGET_OUTPUT = 0.618
STRUCTURE_TARGET_INPUT = 1.618
STRUCTURE_TARGET_OUTPUT = 0.382

BASELINE_PARAMS = {'add_cap': 0, 'R_total': 33, 'R_pick': 6, 'B_total': 16, 'B_pick': 1}

# 人口参数
POP_LOW = 9.448e8
POP_MID = 1.642e8
POP_HIGH = 0.390e8
POP_MID_HIGH = POP_MID + POP_HIGH

# 概率参数边界
PROB_PARAM_BOUNDS = {'R_total': [30, 35], 'R_pick': [6, 7], 'B_total': [10, 30], 'B_pick': [1, 2]}


def calculate_a_coefficient(target_input, target_output):
    if abs(target_output) >= 1:
        raise ValueError("target_output必须在(-1, 1)范围内")
    import math
    arctanh_value = 0.5 * math.log((1 + target_output) / (1 - target_output))
    a = arctanh_value / target_input
    return a

SALES_A_COEFFICIENT = calculate_a_coefficient(SALES_TARGET_INPUT, SALES_TARGET_OUTPUT)
STRUCTURE_A_COEFFICIENT = calculate_a_coefficient(STRUCTURE_TARGET_INPUT, STRUCTURE_TARGET_OUTPUT)


def calculate_winning_probability(R_total, R_pick, B_total, B_pick):
    red_combinations = comb(R_total, R_pick, exact=True)
    blue_combinations = comb(B_total, B_pick, exact=True) if B_total > 0 else 1
    return 1.0 / (red_combinations * blue_combinations)


def validate_lottery_rules(params):
    R_total, R_pick, B_total, B_pick = params

    if R_pick <= 0 or R_pick > R_total:
        return False, f"选红球数({R_pick})必须大于0且小于等于红球总数({R_total})"
    if B_total < 0:
        return False, f"蓝球总数({B_total})不能为负数"
    if B_pick < 0:
        return False, f"选蓝球数({B_pick})不能为负数"
    if B_pick > B_total and B_total > 0:
        return False, f"选蓝球数({B_pick})>蓝球总数({B_total})"
    if R_total <= 0:
        return False, f"红球总数({R_total})必须大于0"

    p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))
    if p > 9.24e-7:
        return False, f"中奖概率({p:.2e})过高"
    if p < 1e-12:
        return False, f"中奖概率({p:.2e})过低"

    return True, "参数有效"


def calculate_structure_improvement_index(df):
    df['structure_improvement'] = (
        (df['middle_income_lottery'] + df['high_income_lottery']) /
        df['low_income_lottery']
    )
    df['low_per_capita'] = df['low_income_lottery'] * 1e8 / POP_LOW
    df['middle_per_capita'] = df['middle_income_lottery'] * 1e8 / POP_MID
    df['high_per_capita'] = df['high_income_lottery'] * 1e8 / POP_HIGH
    df['mid_high_per_capita'] = (df['middle_income_lottery'] + df['high_income_lottery']) * 1e8 / POP_MID_HIGH
    return df


def normalize_tanh_improvement(series, baseline_value, a=1.0):
    return np.tanh(a * (series - baseline_value) / baseline_value)


def calculate_composite_score(df, baseline_sales, baseline_structure):
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

    score = 0.618 * y_structure + 0.382 * y_sales

    df['y_sales'] = y_sales
    df['y_structure'] = y_structure
    df['composite_score'] = score

    return df


def generate_mixed_lhs_samples(n, R_total=None, R_pick=None, B_total=None, B_pick=None):
    n_params = len(PARAM_NAMES)
    samples = np.zeros((n, n_params))

    for i, param_name in enumerate(PARAM_NAMES):
        if param_name == 'R_total':
            low, high = PROB_PARAM_BOUNDS['R_total']
            samples[:, i] = np.random.choice(range(int(low), int(high) + 1), size=n, replace=True)
        elif param_name == 'R_pick':
            low, high = PROB_PARAM_BOUNDS['R_pick']
            samples[:, i] = np.random.choice(range(int(low), int(high) + 1), size=n, replace=True)
        elif param_name == 'B_total':
            low, high = PROB_PARAM_BOUNDS['B_total']
            samples[:, i] = np.random.choice(range(int(low), int(high) + 1), size=n, replace=True)
        elif param_name == 'B_pick':
            low, high = PROB_PARAM_BOUNDS['B_pick']
            samples[:, i] = np.random.choice(range(int(low), int(high) + 1), size=n, replace=True)

    return samples


def run_single_combination_worker(params_with_config):
    params, config = params_with_config

    R_total, R_pick, B_total, B_pick = params
    add_cap = 0  # 概率分析中封顶额固定为0

    netlogo_path = config['netlogo_path']
    nlogo_file = config['nlogo_file']
    lottery_type = config['lottery_type']
    num_periods = config['num_periods']
    replications = config['replications']

    valid, msg = validate_lottery_rules(params)
    if not valid:
        warnings.warn(f"参数验证失败: {msg}")
        p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))
        default_result = {
            'add_cap': add_cap, 'p': p,
            'R_total': R_total, 'R_pick': R_pick,
            'B_total': B_total, 'B_pick': B_pick,
            'calculated_p': p,
            'total_tickets': 0,
            'structure_improvement': 0,
            'y_sales': 0, 'y_structure': 0,
            'composite_score': 0
        }
        return default_result

    try:
        p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))
        param_values = {
            'add_cap': add_cap, 'p': p,
            'R_total': R_total, 'R_pick': R_pick,
            'B_total': B_total, 'B_pick': B_pick,
            'calculated_p': p
        }

        analyzer = LotterySensitivityAnalyzer(
            netlogo_path=netlogo_path,
            nlogo_file=nlogo_file,
            lottery_type=lottery_type,
            processes=1
        )

        all_results = []
        for rep in range(replications):
            try:
                result = run_single_simulation(
                    analyzer, add_cap, p, num_periods, rep,
                    netlogo_path, nlogo_file
                )
                all_results.append(result)
            except Exception as e:
                warnings.warn(f"重复{rep}运行失败: {e}")

        if all_results:
            avg_result = {}
            for key in all_results[0].keys():
                if isinstance(all_results[0][key], (int, float)):
                    avg_result[key] = np.mean([r[key] for r in all_results])
                    avg_result[f'{key}_std'] = np.std([r[key] for r in all_results])
            avg_result.update(param_values)
            return avg_result
        return None
    except Exception as e:
        warnings.warn(f"参数组合{params}运行失败: {e}")
        return None


def parallel_run_simulations(param_combinations, replications, processes, param_names):
    config = {
        'netlogo_path': NETLOGO_PATH,
        'nlogo_file': NLOGO_FILE,
        'lottery_type': LOTTERY_TYPE,
        'num_periods': NUM_PERIODS,
        'replications': replications
    }
    worker_args = [(params, config) for params in param_combinations]

    with Pool(processes=processes) as pool:
        results = pool.map(run_single_combination_worker, worker_args)

    results = [r for r in results if r is not None]
    if len(results) == 0:
        raise ValueError("所有仿真都失败了")
    return pd.DataFrame(results)


def run_single_simulation(analyzer, add_cap, p, num_periods, rep_id, netlogo_path, nlogo_file):
    import pynetlogo

    temp_netlogo = pynetlogo.NetLogoLink(netlogo_home=netlogo_path, gui=False)
    temp_netlogo.load_model(nlogo_file)

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
    temp_netlogo.command(f'set add_cap {add_cap}')
    temp_netlogo.command(f'set p {p}')

    temp_netlogo.command('setup')

    period_data = []
    for period in range(num_periods):
        temp_netlogo.command('go')
        if period % 100 == 0:
            low_lottery = temp_netlogo.report('low-income-lottery') or 0
            middle_lottery = temp_netlogo.report('middle-income-lottery') or 0
            high_lottery = temp_netlogo.report('high-income-lottery') or 0
            pool_val = temp_netlogo.report('pool') or 0
            period_record = {
                'period': period,
                'low_income_lottery': low_lottery,
                'middle_income_lottery': middle_lottery,
                'high_income_lottery': high_lottery,
                'pool': pool_val
            }
            period_data.append(period_record)

    total_tickets = temp_netlogo.report('total-tickets') or 0
    low_lottery_final = temp_netlogo.report('low-income-lottery') or 0
    middle_lottery_final = temp_netlogo.report('middle-income-lottery') or 0
    high_lottery_final = temp_netlogo.report('high-income-lottery') or 0
    pool_final = temp_netlogo.report('pool') or 0

    low_participation = temp_netlogo.report('low-participation') or 0
    middle_participation = temp_netlogo.report('middle-participation') or 0
    high_participation = temp_netlogo.report('high-participation') or 0

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


def find_pareto_optimal_solutions(df):
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

    pareto_df = df.iloc[pareto_optimal].copy()
    pareto_df['pareto_optimal'] = True
    return pareto_df


def continue_optimization(existing_csv_path, baseline_sales, baseline_structure, output_dir):
    """从已有结果继续贝叶斯优化"""
    print("=" * 80)
    print(" 概率敏感性分析 - 断点续跑（继续50次迭代）")
    print("=" * 80)

    # 读取已有结果
    print(f"\n 读取已有结果: {existing_csv_path}")
    existing_df = pd.read_csv(existing_csv_path)
    print(f"   已有数据: {len(existing_df)} 行")

    # 计算结构改善和得分（如果还没有的话）
    if 'structure_improvement' not in existing_df.columns:
        existing_df = calculate_structure_improvement_index(existing_df)
    if 'y_structure' not in existing_df.columns:
        existing_df = calculate_composite_score(existing_df, baseline_sales, baseline_structure)

    # 准备训练数据（4维：R_total, R_pick, B_total, B_pick）
    X_train = existing_df[['R_total', 'R_pick', 'B_total', 'B_pick']].values
    y_train = existing_df['composite_score'].values

    print(f"   已有样本: {len(X_train)}")
    print(f"   当前最佳: 综合得分={existing_df['composite_score'].max():.4f}")
    print(f"   当前最佳: 结构得分={existing_df['y_structure'].max():.4f}")

    # 初始化高斯过程
    kernel = C(1.0) * Matern(length_scale=1.0, nu=1.5)
    gp_model = GaussianProcessRegressor(kernel=kernel, alpha=1e-3, n_restarts_optimizer=10)

    best_score = existing_df['composite_score'].max()
    best_row = existing_df.loc[existing_df['composite_score'].idxmax()]
    best_params = best_row[['R_total', 'R_pick', 'B_total', 'B_pick']].values
    best_structure = best_row['y_structure']
    best_sales = best_row['y_sales']

    print(f"\n 继续贝叶斯优化（{CONTINUE_ITERATIONS}次迭代）...")

    best_history = [{
        'iteration': 0,
        'best_score': best_score,
        'best_params': best_params.tolist(),
        'y_structure': best_structure,
        'y_sales': best_sales
    }]

    for iteration in range(CONTINUE_ITERATIONS):
        iter_start_time = datetime.now()

        print(f"\n[续跑迭代 {iteration + 1}/{CONTINUE_ITERATIONS}]")
        print(f"   训练高斯过程模型(样本数:{len(X_train)})...")
        gp_model.fit(X_train, y_train)

        # 生成候选点
        candidate_grid = generate_mixed_lhs_samples(10000)
        mean, std = gp_model.predict(candidate_grid, return_std=True)
        best_y = np.max(y_train)
        z = (mean - best_y) / (std + 1e-9)
        ei = (mean - best_y) * norm.cdf(z) + std * norm.pdf(z)

        top_indices = np.argsort(ei)[-BAYES_CANDIDATES:]
        candidates = candidate_grid[top_indices]

        print(f"   并行运行{len(candidates)}个候选点...")
        candidate_start = datetime.now()
        candidate_results = parallel_run_simulations(
            param_combinations=candidates,
            replications=REPLICATIONS,
            processes=PROCESSES_BAYES,
            param_names=PARAM_NAMES
        )
        candidate_elapsed = (datetime.now() - candidate_start).total_seconds()

        if len(candidate_results) == 0:
            print(f"   本轮所有候选点都失败，跳过更新")
            continue

        print("   计算结构改善性指标...")
        candidate_results = calculate_structure_improvement_index(candidate_results)
        print("   计算综合得分...")
        candidate_results = calculate_composite_score(candidate_results, baseline_sales, baseline_structure)

        # 添加新数据到训练集
        new_points = candidate_results[['R_total', 'R_pick', 'B_total', 'B_pick']].values
        new_scores = candidate_results['composite_score'].values

        X_train = np.vstack([X_train, new_points])
        y_train = np.hstack([y_train, new_scores])

        # 更新历史最优
        if len(new_scores) > 0:
            current_best_idx = np.argmax(new_scores)
            current_best_score = new_scores[current_best_idx]
            current_best_param = new_points[current_best_idx]

            R_total, R_pick, B_total, B_pick = current_best_param
            best_p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))

            if current_best_score > best_score:
                best_score = current_best_score
                best_params = current_best_param
                best_structure = candidate_results.iloc[current_best_idx]['y_structure']
                best_sales = candidate_results.iloc[current_best_idx]['y_sales']
                print(f"   ★ NEW BEST: 红球={int(R_total)}选{int(R_pick)}, 蓝球={int(B_total)}选{int(B_pick)}, p={best_p:.2e}, 耗时={candidate_elapsed:.1f}s, 综合={best_score:.4f}(结构{best_structure:.4f},销量{best_sales:.4f})")
            else:
                print(f"   本轮最优：得分={current_best_score:.4f}, 历史最优={best_score:.4f}")

        best_history.append({
            'iteration': iteration + 1,
            'best_score': best_score,
            'best_params': best_params.tolist(),
            'y_structure': best_structure,
            'y_sales': best_sales
        })

    # 合并所有结果
    all_results_df = pd.concat([existing_df, candidate_results], ignore_index=True)

    R_total, R_pick, B_total, B_pick = best_params
    best_p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))

    optimal_params = {
        'R_total': int(best_params[0]),
        'R_pick': int(best_params[1]),
        'B_total': int(best_params[2]),
        'B_pick': int(best_params[3]),
        'p': float(best_p),
        'score': float(best_score),
        'y_structure': float(best_structure),
        'y_sales': float(best_sales)
    }

    return optimal_params, all_results_df, best_history


def generate_visualizations(all_results_df, output_dir):
    """生成可视化图表"""
    plots_dir = os.path.join(output_dir, "plots")
    thesis_plots_dir = os.path.join(output_dir, "thesis_plots")
    os.makedirs(plots_dir, exist_ok=True)
    os.makedirs(thesis_plots_dir, exist_ok=True)

    print(f"   正在生成可视化图表...")

    # 1. 收敛曲线图
    convergence_path = os.path.join(plots_dir, "convergence_curve_continued.png")
    plt.figure(figsize=(10, 6))
    plt.xlabel('Iteration')
    plt.ylabel('Composite Score')
    plt.title('Bayesian Optimization Convergence - Probability (Continued)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(convergence_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 收敛曲线图已保存至: {convergence_path}")

    # 2. 帕累托前沿散点图
    pareto_path = os.path.join(plots_dir, "pareto_frontier_continued.png")
    plt.figure(figsize=(10, 8))

    pareto_df = find_pareto_optimal_solutions(all_results_df)

    plt.scatter(all_results_df['y_sales'], all_results_df['y_structure'],
               c=all_results_df['composite_score'], cmap='viridis', alpha=0.6, s=50, label='All Points')

    if not pareto_df.empty:
        plt.scatter(pareto_df['y_sales'], pareto_df['y_structure'],
                   c='red', s=100, edgecolors='black', linewidth=1, label='Pareto Optimal', marker='s')

    plt.xlabel('Normalized Sales Score (y_sales)')
    plt.ylabel('Normalized Structure Score (y_structure)')
    plt.title('Pareto Frontier: Sales vs Structure - Probability (Continued)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.colorbar(label='Composite Score')
    plt.legend()
    plt.tight_layout()
    plt.savefig(pareto_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 帕累托前沿图已保存至: {pareto_path}")

    # 3. 概率参数热力图
    heatmap_path = os.path.join(plots_dir, "heatmap_correlation_continued.png")
    plt.figure(figsize=(12, 8))
    numeric_cols = all_results_df.select_dtypes(include=[np.number]).columns
    correlation_matrix = all_results_df[numeric_cols].corr()
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                square=True, fmt='.2f', cbar_kws={'shrink': 0.8})
    plt.title('Correlation Heatmap - Probability (Continued)')
    plt.tight_layout()
    plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 相关性热力图已保存至: {heatmap_path}")

    return plots_dir, thesis_plots_dir


def main():
    print("\n" + "=" * 80)
    print(" 博士论文：彩票概率单一参数敏感性分析 - 断点续跑")
    print("=" * 80)

    # 基准值（使用之前运行得到的基准）
    baseline_sales = 706796.11  # 亿元
    baseline_structure = 0.8002  # 结构指数基准

    # 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(EXISTING_RESULTS_DIR, f"continued_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    # 找到最新的CSV结果
    existing_csv = os.path.join(EXISTING_RESULTS_DIR, "probability_only_results_20260323_145413.csv")

    if not os.path.exists(existing_csv):
        print(f"错误：找不到已有结果文件 {existing_csv}")
        return

    # 继续优化
    optimal_params, all_results_df, best_history = continue_optimization(
        existing_csv, baseline_sales, baseline_structure, output_dir
    )

    # 保存结果
    print(f"\n 正在保存结果到目录: {output_dir}")

    results_csv_path = os.path.join(output_dir, f"probability_results_continued_{timestamp}.csv")
    all_results_df.to_csv(results_csv_path, index=False, encoding='utf-8-sig')
    print(f" ✓ 完整结果已保存至: {results_csv_path}")

    pareto_optimal_df = find_pareto_optimal_solutions(all_results_df)
    pareto_csv_path = os.path.join(output_dir, f"pareto_optimal_continued_{timestamp}.csv")
    pareto_optimal_df.to_csv(pareto_csv_path, index=False, encoding='utf-8-sig')
    print(f" ✓ 帕累托最优解已保存至: {pareto_csv_path}")

    # 保存最优参数
    output_file = os.path.join(output_dir, f"optimal_params_continued_{timestamp}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(optimal_params, f, indent=4, ensure_ascii=False)

    p_val = optimal_params.get('p')
    p_str = f"p={p_val:.2e}" if p_val is not None else "p=N/A"
    print(f"\n续跑后最优参数：")
    print(f"  - 红球规则：{optimal_params['R_total']}选{optimal_params['R_pick']}")
    print(f"  - 蓝球规则：{optimal_params['B_total']}选{optimal_params['B_pick']}")
    print(f"  - 中奖概率：{p_str}")
    print(f"  - 综合得分：{optimal_params['score']:.4f}")
    print(f"  - 结构得分：{optimal_params['y_structure']:.4f}")
    print(f"  - 销量得分：{optimal_params['y_sales']:.4f}")

    # 检查是否找到结构为正的解
    positive_structure = all_results_df[all_results_df['y_structure'] > 0]
    if len(positive_structure) > 0:
        print(f"\n ★ 成功找到 {len(positive_structure)} 个结构改善为正的解！")
        best_positive = positive_structure.loc[positive_structure['composite_score'].idxmax()]
        print(f"   最优正值结构解：红球={int(best_positive['R_total'])}选{int(best_positive['R_pick'])}, "
              f"蓝球={int(best_positive['B_total'])}选{int(best_positive['B_pick'])}, "
              f"y_structure={best_positive['y_structure']:.4f}, "
              f"y_sales={best_positive['y_sales']:.4f}")
    else:
        print(f"\n警告：仍未找到结构改善为正的解（y_structure > 0）")

    # 生成可视化
    generate_visualizations(all_results_df, output_dir)

    print("\n 程序结束")


if __name__ == "__main__":
    main()
