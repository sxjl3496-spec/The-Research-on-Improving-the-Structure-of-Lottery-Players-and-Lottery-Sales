"""
彩票规则单一参数敏感性分析 - 概率优化（贝叶斯优化）

中奖概率敏感性分析：优化 R_total, R_pick, B_total, B_pick
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

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ABM_Netlogo_analyze import LotterySensitivityAnalyzer

import json
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# ========== 配置 ==========
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "probability_only_sensitivity_v2")
NETLOGO_PATH = r"D:/netlogo"
NLOGO_FILE = r"D:/BaiduSyncdisk/1DoctorStudy/1Doctor thesis/ABM-LOTTERY/normal20260203distribution.nlogo"
LOTTERY_TYPE = "DCB"
NUM_PERIODS = 1800

# 优化参数配置
LHS_SAMPLES = 5           # 5个LHS采样点
PROCESSES_LHS = 5         # 5个子进程并行
BAYES_ITERATIONS = 300   # 300轮贝叶斯迭代
BAYES_CANDIDATES = 4      # 每轮4个候选点
REPLICATIONS = 1          # 每组参数重复1次
PROCESSES_BAYES = 4      # 4个子进程并行

PARAM_NAMES = ['R_total', 'R_pick', 'B_total', 'B_pick']
PARAM_BOUNDS = {'R_total': [30, 50], 'R_pick': [6, 9], 'B_total': [5, 40], 'B_pick': [1, 3]}
BASELINE_PARAMS = {'add_cap': 0, 'R_total': 33, 'R_pick': 6, 'B_total': 16, 'B_pick': 1}
OPTIMAL_STRUCTURE_INDEX = 1.618

# 人口参数
POP_LOW = 9.448e8
POP_MID = 1.642e8
POP_HIGH = 0.390e8
POP_MID_HIGH = POP_MID + POP_HIGH

# ========== tanh归一化系数 ==========
def calculate_a_coefficient(target_input, target_output):
    if abs(target_output) >= 1:
        raise ValueError("target_output必须在(-1, 1)范围内")
    import math
    arctanh_value = 0.5 * math.log((1 + target_output) / (1 - target_output))
    a = arctanh_value / target_input
    return a

SALES_TARGET_INPUT = 0.1
SALES_TARGET_OUTPUT = 0.9
STRUCTURE_TARGET_INPUT = 0.382
STRUCTURE_TARGET_OUTPUT = 0.618

SALES_A_COEFFICIENT = calculate_a_coefficient(SALES_TARGET_INPUT, SALES_TARGET_OUTPUT)
STRUCTURE_A_COEFFICIENT = calculate_a_coefficient(STRUCTURE_TARGET_INPUT, STRUCTURE_TARGET_OUTPUT)


def calculate_winning_probability(R_total, R_pick, B_total, B_pick):
    """计算中奖概率"""
    red_combinations = comb(R_total, R_pick, exact=True)
    blue_combinations = comb(B_total, B_pick, exact=True)
    return 1.0 / (red_combinations * blue_combinations)


def validate_lottery_rules(params):
    """验证彩票规则参数"""
    add_cap, R_total, R_pick, B_total, B_pick = params

    if not (PARAM_BOUNDS['R_total'][0] <= R_total <= PARAM_BOUNDS['R_total'][1]):
        return False, f"R_total({R_total})不在允许范围内"
    if not (PARAM_BOUNDS['R_pick'][0] <= R_pick <= PARAM_BOUNDS['R_pick'][1]):
        return False, f"R_pick({R_pick})不在允许范围内"
    if not (PARAM_BOUNDS['B_total'][0] <= B_total <= PARAM_BOUNDS['B_total'][1]):
        return False, f"B_total({B_total})不在允许范围内"
    if not (PARAM_BOUNDS['B_pick'][0] <= B_pick <= PARAM_BOUNDS['B_pick'][1]):
        return False, f"B_pick({B_pick})不在允许范围内"

    if R_pick <= 0 or R_pick > R_total:
        return False, f"选红球数({R_pick})必须大于0且小于等于红球总数({R_total})"
    if B_total < 0:
        return False, f"蓝球总数({B_total})不能为负数"
    if B_pick < 0:
        return False, f"选蓝球数({B_pick})不能为负数"
    if B_pick > B_total and B_total > 0:
        return False, f"选蓝球数({B_pick})>蓝球总数({B_total})"
    if B_pick > 0 and B_total == 0:
        return False, f"选蓝球数({B_pick})>0但蓝球总数为0"
    if R_total <= 0:
        return False, f"红球总数({R_total})必须大于0"

    p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))
    if p > 9.24e-7:
        return False, f"中奖概率({p:.2e})过高"
    if p < 1e-15:
        return False, f"中奖概率({p:.2e})过低"

    return True, "参数有效"


def calculate_structure_improvement_index(df):
    """
    计算彩民结构指数 = 中高收入人群彩票消费总量 / 低收入人群彩票消费总量
    """
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
    """使用tanh函数计算复合得分"""
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


def generate_lhs_samples(n, param_info):
    """生成LHS采样（离散参数）"""
    n_params = len(PARAM_NAMES)
    samples = np.zeros((n, n_params))
    for i, param_name in enumerate(PARAM_NAMES):
        low, high = param_info[param_name]
        values = np.random.choice(range(int(low), int(high) + 1), size=n, replace=True)
        samples[:, i] = values
    return samples


def run_single_combination_worker(params_with_config):
    """并行运行单个参数组合"""
    params, config = params_with_config

    R_total, R_pick, B_total, B_pick = params
    add_cap = BASELINE_PARAMS['add_cap']

    netlogo_path = config['netlogo_path']
    nlogo_file = config['nlogo_file']
    lottery_type = config['lottery_type']
    num_periods = config['num_periods']
    replications = config['replications']

    valid, msg = validate_lottery_rules([add_cap, R_total, R_pick, B_total, B_pick])
    if not valid:
        warnings.warn(f"参数验证失败: {msg}")
        return None

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
    """并行运行仿真"""
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
    """运行单次仿真"""
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
            pool = temp_netlogo.report('pool') or 0

            period_record = {
                'period': period,
                'low_income_lottery': low_lottery,
                'middle_income_lottery': middle_lottery,
                'high_income_lottery': high_lottery,
                'pool': pool
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


def probability_only_bayesian_optimization(baseline_sales, baseline_structure):
    """中奖概率贝叶斯优化"""
    print("=" * 80)
    print(" 彩票概率单一参数敏感性分析 - 贝叶斯优化")
    print("=" * 80)
    print(f"\n 优化配置:")
    print(f"   优化参数: {PARAM_NAMES}")
    print(f"   LHS采样点数: {LHS_SAMPLES}")
    print(f"   LHS并行进程: {PROCESSES_LHS}")
    print(f"   贝叶斯迭代轮数: {BAYES_ITERATIONS}")
    print(f"   每轮候选点数: {BAYES_CANDIDATES}")
    print(f"   贝叶斯并行进程: {PROCESSES_BAYES}")
    print(f"   重复次数: {REPLICATIONS}")
    print("=" * 80)

    print("\n 第一阶段：拉丁超立方采样（5个点）")
    lhs_points = generate_lhs_samples(n=LHS_SAMPLES, param_info=PARAM_BOUNDS)
    print(f"   生成{len(lhs_points)}个采样点")

    print("   验证并修正参数约束...")
    for i in range(len(lhs_points)):
        base_add_cap = BASELINE_PARAMS['add_cap']
        params_with_base = [base_add_cap] + list(lhs_points[i])
        valid, _ = validate_lottery_rules(params_with_base)
        if not valid:
            _, R_total, R_pick, B_total, B_pick = params_with_base
            R_pick = min(R_pick, R_total)
            B_pick = min(B_pick, max(0, B_total)) if B_total > 0 else 0
            lhs_points[i] = [R_total, R_pick, B_total, B_pick]

    print("   并行运行仿真...")
    start_time = datetime.now()
    lhs_results = parallel_run_simulations(
        param_combinations=lhs_points,
        replications=REPLICATIONS,
        processes=PROCESSES_LHS,
        param_names=PARAM_NAMES
    )
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"   完成，耗时{elapsed:.1f}秒")

    if len(lhs_results) == 0:
        raise ValueError("LHS阶段所有仿真都失败")

    print("   计算结构改善性指标...")
    lhs_results = calculate_structure_improvement_index(lhs_results)
    print("   计算综合得分...")
    lhs_results = calculate_composite_score(lhs_results, baseline_sales, baseline_structure)

    successful_points = []
    successful_scores = []
    for idx in range(len(lhs_results)):
        row = lhs_results.iloc[idx]
        successful_points.append([row['R_total'], row['R_pick'], row['B_total'], row['B_pick']])
        successful_scores.append(row['composite_score'])

    X_train = np.array(successful_points)
    y_train = np.array(successful_scores)

    print(f"   初步结果：找到{len(lhs_results)}个有效点")
    best_lhs = lhs_results.nlargest(1, 'composite_score').iloc[0]
    print(f"   LHS最优：得分={best_lhs['composite_score']:.4f}")

    print("\n 第二阶段：贝叶斯优化（100轮序贯搜索）")
    kernel = C(1.0) * Matern(length_scale=1.0, nu=1.5)
    gp_model = GaussianProcessRegressor(kernel=kernel, alpha=1e-3, n_restarts_optimizer=10)
    print(f"\n   初始化训练集：{len(X_train)}个样本")

    best_score = -np.inf
    best_params = None
    best_structure = None
    best_sales = None

    all_results_df = lhs_results.copy()
    best_history = []

    for iteration in range(BAYES_ITERATIONS):
        iter_start_time = datetime.now()

        print(f"\n[迭代 {iteration + 1}/{BAYES_ITERATIONS}]")
        print(f"   训练高斯过程模型(样本数:{len(X_train)})...")
        gp_model.fit(X_train, y_train)

        candidate_grid = generate_lhs_samples(n=10000, param_info=PARAM_BOUNDS)

        # 验证候选点
        valid_count = 0
        for i in range(len(candidate_grid)):
            base_add_cap = BASELINE_PARAMS['add_cap']
            params_with_base = [base_add_cap] + list(candidate_grid[i])
            valid, _ = validate_lottery_rules(params_with_base)
            if valid:
                valid_count += 1

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

        successful_candidate_points = []
        successful_candidate_scores = []
        for idx in range(len(candidate_results)):
            row = candidate_results.iloc[idx]
            successful_candidate_points.append([row['R_total'], row['R_pick'], row['B_total'], row['B_pick']])
            successful_candidate_scores.append(row['composite_score'])

        candidate_points_synced = np.array(successful_candidate_points)
        candidate_scores_synced = np.array(successful_candidate_scores)

        X_train = np.vstack([X_train, candidate_points_synced])
        y_train = np.hstack([y_train, candidate_scores_synced])

        all_results_df = pd.concat([all_results_df, candidate_results], ignore_index=True)

        if len(candidate_scores_synced) > 0:
            current_best_idx = np.argmax(candidate_scores_synced)
            current_best_score = candidate_scores_synced[current_best_idx]
            current_best_param = candidate_points_synced[current_best_idx]

            R_total, R_pick, B_total, B_pick = current_best_param
            best_p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))

            if current_best_score > best_score:
                best_score = current_best_score
                best_params = current_best_param
                best_structure = candidate_results.iloc[current_best_idx]['y_structure']
                best_sales = candidate_results.iloc[current_best_idx]['y_sales']
                print(f"   ★ NEW BEST: 红球={int(R_total)}选{int(R_pick)}, 蓝球={int(B_total)}选{int(B_pick)}, p={best_p:.2e}, 耗时={candidate_elapsed:.1f}s, 历史最优={best_score:.4f}, 本轮得分=综合{current_best_score:.4f}(结构{best_structure:.4f},销量{best_sales:.4f})")
            else:
                print(f"   本轮最优：得分={current_best_score:.4f}, 历史最优={best_score:.4f}")
        else:
            print(f"   本轮所有候选点都失败，跳过更新")

        best_history.append({
            'iteration': iteration + 1,
            'best_score': best_score,
            'best_params': best_params.tolist() if best_params is not None else None,
            'best_p': calculate_winning_probability(int(best_params[0]), int(best_params[1]), int(best_params[2]), int(best_params[3])) if best_params is not None else None,
            'y_structure': best_structure,
            'y_sales': best_sales
        })

    print("\n" + "=" * 80)
    print(" 贝叶斯优化完成！")
    print("=" * 80)

    best_p = calculate_winning_probability(
        int(best_params[0]), int(best_params[1]),
        int(best_params[2]), int(best_params[3])
    )
    optimal_params = {
        'R_total': int(best_params[0]),
        'R_pick': int(best_params[1]),
        'B_total': int(best_params[2]),
        'B_pick': int(best_params[3]),
        'p': best_p,
        'score': best_score,
        'y_structure': best_structure,
        'y_sales': best_sales
    }

    return optimal_params, all_results_df, best_history


def run_baseline_simulation():
    """运行基准仿真"""
    print("\n 运行基准政策仿真（当前双色球规则）...")
    print(f"   参数：{BASELINE_PARAMS}")

    baseline_p = calculate_winning_probability(
        BASELINE_PARAMS['R_total'], BASELINE_PARAMS['R_pick'],
        BASELINE_PARAMS['B_total'], BASELINE_PARAMS['B_pick']
    )
    print(f"   中奖概率：p={baseline_p:.2e}")

    analyzer = LotterySensitivityAnalyzer(
        netlogo_path=NETLOGO_PATH,
        nlogo_file=NLOGO_FILE,
        lottery_type=LOTTERY_TYPE,
        processes=1
    )

    results = []
    for rep in range(REPLICATIONS):
        result = run_single_simulation(
            analyzer, BASELINE_PARAMS['add_cap'], baseline_p,
            NUM_PERIODS, rep, NETLOGO_PATH, NLOGO_FILE
        )
        results.append(result)

    avg_result = {}
    for key in results[0].keys():
        if isinstance(results[0][key], (int, float)):
            avg_result[key] = np.mean([r[key] for r in results])

    df_baseline = pd.DataFrame([avg_result])
    df_baseline = calculate_structure_improvement_index(df_baseline)

    baseline_sales = df_baseline['total_tickets'].values[0]
    baseline_structure = df_baseline['structure_improvement'].values[0]

    print(f"   基准销量：{baseline_sales:.2e}亿元")
    print(f"   基准结构改善性：{baseline_structure:.4f}")

    return baseline_sales, baseline_structure


def find_pareto_optimal_solutions(df):
    """找出帕累托最优解"""
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


def generate_visualizations(all_results_df, output_subdir, best_history):
    """生成可视化图表"""
    plots_dir = os.path.join(output_subdir, "plots")
    thesis_plots_dir = os.path.join(output_subdir, "thesis_plots")
    os.makedirs(plots_dir, exist_ok=True)
    os.makedirs(thesis_plots_dir, exist_ok=True)

    print(f"   正在生成可视化图表...")

    # 1. 收敛曲线图
    if best_history:
        convergence_path = os.path.join(plots_dir, "convergence_curve.png")
        plt.figure(figsize=(10, 6))

        iterations = [h['iteration'] for h in best_history]
        best_scores = [h['best_score'] for h in best_history]

        plt.plot(iterations, best_scores, 'b-', linewidth=2, label='Best Score So Far')
        plt.xlabel('Iteration')
        plt.ylabel('Composite Score')
        plt.title('Bayesian Optimization Convergence Curve - Probability Only')
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.tight_layout()
        plt.savefig(convergence_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"   ✓ 收敛曲线图已保存至: {convergence_path}")

    # 2. 帕累托前沿散点图
    pareto_path = os.path.join(plots_dir, "pareto_frontier.png")
    plt.figure(figsize=(10, 8))

    pareto_df = find_pareto_optimal_solutions(all_results_df)

    plt.scatter(all_results_df['y_sales'], all_results_df['y_structure'],
               c=all_results_df['composite_score'], cmap='viridis', alpha=0.6, s=50, label='All Points')

    if not pareto_df.empty:
        plt.scatter(pareto_df['y_sales'], pareto_df['y_structure'],
                   c='red', s=100, edgecolors='black', linewidth=1, label='Pareto Optimal', marker='s')

    plt.xlabel('Normalized Sales Score (y_sales)')
    plt.ylabel('Normalized Structure Score (y_structure)')
    plt.title('Pareto Frontier: Sales vs Structure - Probability Only')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.colorbar(label='Composite Score')
    plt.legend()
    plt.tight_layout()
    plt.savefig(pareto_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 帕累托前沿图已保存至: {pareto_path}")

    # 3. 概率与各项指标的关系图
    prob_vs_metrics_path = os.path.join(plots_dir, "prob_vs_metrics.png")
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    axes[0, 0].scatter(all_results_df['p'], all_results_df['composite_score'], alpha=0.6)
    axes[0, 0].set_xlabel('Winning Probability')
    axes[0, 0].set_ylabel('Composite Score')
    axes[0, 0].set_title('Winning Probability vs Composite Score')
    axes[0, 0].set_xscale('log')
    axes[0, 0].grid(True, linestyle='--', alpha=0.6)

    axes[0, 1].scatter(all_results_df['p'], all_results_df['total_tickets'], alpha=0.6)
    axes[0, 1].set_xlabel('Winning Probability')
    axes[0, 1].set_ylabel('Total Tickets (亿元)')
    axes[0, 1].set_title('Winning Probability vs Total Sales')
    axes[0, 1].set_xscale('log')
    axes[0, 1].grid(True, linestyle='--', alpha=0.6)

    axes[1, 0].scatter(all_results_df['p'], all_results_df['structure_improvement'], alpha=0.6)
    axes[1, 0].set_xlabel('Winning Probability')
    axes[1, 0].set_ylabel('Structure Improvement Index')
    axes[1, 0].set_title('Winning Probability vs Structure Improvement')
    axes[1, 0].set_xscale('log')
    axes[1, 0].grid(True, linestyle='--', alpha=0.6)

    axes[1, 1].scatter(all_results_df['p'], all_results_df['y_sales'], alpha=0.6)
    axes[1, 1].set_xlabel('Winning Probability')
    axes[1, 1].set_ylabel('Normalized Sales Score')
    axes[1, 1].set_title('Winning Probability vs Sales Score')
    axes[1, 1].set_xscale('log')
    axes[1, 1].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig(prob_vs_metrics_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 概率与指标关系图已保存至: {prob_vs_metrics_path}")

    # 4. 论文用图 - 正文三子图（使用对数坐标）
    thesis_fig_path = os.path.join(thesis_plots_dir, "fig_prob_sensitivity_main.png")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # (a) 综合得分
    axes[0].scatter(all_results_df['p'], all_results_df['composite_score'], alpha=0.6, s=30)
    axes[0].set_xlabel('中奖概率')
    axes[0].set_ylabel('综合得分')
    axes[0].set_title('(a) 中奖概率 vs 综合得分')
    axes[0].set_xscale('log')
    axes[0].grid(True, linestyle='--', alpha=0.6)

    # (b) 销量
    axes[1].scatter(all_results_df['p'], all_results_df['total_tickets'], alpha=0.6, s=30)
    axes[1].set_xlabel('中奖概率')
    axes[1].set_ylabel('销量 (亿元)')
    axes[1].set_title('(b) 中奖概率 vs 销量')
    axes[1].set_xscale('log')
    axes[1].grid(True, linestyle='--', alpha=0.6)

    # (c) 结构指数
    axes[2].scatter(all_results_df['p'], all_results_df['structure_improvement'], alpha=0.6, s=30)
    axes[2].set_xlabel('中奖概率')
    axes[2].set_ylabel('彩民结构指数')
    axes[2].set_title('(c) 中奖概率 vs 彩民结构指数')
    axes[2].set_xscale('log')
    axes[2].grid(True, linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.savefig(thesis_fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 正文用图已保存至: {thesis_fig_path}")

    return plots_dir, thesis_plots_dir


def main():
    print("\n" + "=" * 80)
    print(" 博士论文：彩票概率单一参数敏感性分析")
    print("=" * 80)

    print("\n本脚本用于分析彩票概率变化对不同收入人群购彩行为的影响")
    print("优化参数：R_total, R_pick, B_total, B_pick")
    print("目标：同时优化消费结构改善性和销量")

    # 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_subdir = os.path.join(OUTPUT_DIR, f"results_{timestamp}")
    summary_dir = os.path.join(output_subdir, "summary")
    os.makedirs(output_subdir, exist_ok=True)
    os.makedirs(summary_dir, exist_ok=True)

    baseline_sales, baseline_structure = run_baseline_simulation()
    optimal_params, all_results_df, best_history = probability_only_bayesian_optimization(
        baseline_sales, baseline_structure
    )

    # 保存结果
    print(f"\n 正在生成输出文件到目录: {output_subdir}")

    results_csv_path = os.path.join(output_subdir, f"probability_only_results_{timestamp}.csv")
    all_results_df.to_csv(results_csv_path, index=False, encoding='utf-8-sig')
    print(f" ✓ 完整结果已保存至: {results_csv_path}")

    pareto_optimal_df = find_pareto_optimal_solutions(all_results_df)
    pareto_csv_path = os.path.join(output_subdir, f"pareto_optimal_{timestamp}.csv")
    pareto_optimal_df.to_csv(pareto_csv_path, index=False, encoding='utf-8-sig')
    print(f" ✓ 帕累托最优解已保存至: {pareto_csv_path}")

    # 保存最优参数
    output_file = os.path.join(output_subdir, f"optimal_params_{timestamp}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(optimal_params, f, indent=4, ensure_ascii=False)
    print(f"\n最优参数：")
    print(f"  - 红球规则：{optimal_params['R_total']}选{optimal_params['R_pick']}")
    print(f"  - 蓝球规则：{optimal_params['B_total']}选{optimal_params['B_pick']}")
    p_val = optimal_params.get('p')
    p_str = f"p={p_val:.2e}" if p_val is not None else "p=N/A"
    print(f"  - 中奖概率：{p_str}")
    print(f"  - 综合得分：{optimal_params['score']:.4f}")
    print(f"  - 结构得分：{optimal_params['y_structure']:.4f}")
    print(f"  - 销量得分：{optimal_params['y_sales']:.4f}")

    # 生成可视化
    generate_visualizations(all_results_df, output_subdir, best_history)

    print("\n 程序结束")


if __name__ == "__main__":
    main()
