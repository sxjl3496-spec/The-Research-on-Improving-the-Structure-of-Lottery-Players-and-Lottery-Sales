"""
彩票规则联合敏感性分析 - 多目标优化（贝叶斯优化）

联合敏感性分析：同时优化 add_cap, R_total, R_pick, B_total, B_pick
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
import logging

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

# ========== 日志配置 ==========
log_dir = "joint_sensitivity_v2/logs"
os.makedirs(log_dir, exist_ok=True)
timestamp_log = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(log_dir, f'run_{timestamp_log}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========== 配置 ==========
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "joint_sensitivity_v2")
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

PARAM_NAMES = ['add_cap', 'R_total', 'R_pick', 'B_total', 'B_pick']

# 目标配置
SALES_TARGET_INPUT = 0.10
SALES_TARGET_OUTPUT = 0.9
STRUCTURE_TARGET_INPUT = 0.382
STRUCTURE_TARGET_OUTPUT = 0.618

BASELINE_PARAMS = {'add_cap': 0, 'R_total': 33, 'R_pick': 6, 'B_total': 16, 'B_pick': 1}
OPTIMAL_STRUCTURE_INDEX = 1.618

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


def calculate_dynamic_bounds(R_total, R_pick, B_total, B_pick):
    """根据彩票规则参数动态计算add_cap参数的边界"""
    if R_pick <= 0 or R_pick > R_total or R_total <= 0:
        return [-500, 50000]
    if B_total < 0 or B_pick < 0:
        return [-500, 50000]
    if B_pick > B_total and B_total > 0:
        return [-500, 50000]
    if B_pick > 0 and B_total == 0:
        return [-500, 50000]

    try:
        p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))
    except:
        return [-500, 50000]

    if p <= 0 or p < 1e-15:
        return [-500, 50000]

    c = 0.0002
    add_cap_upper_bound = c / p - 500
    add_cap_upper_bound = min(add_cap_upper_bound, 50000000)
    add_cap_lower_bound = -500

    return [add_cap_lower_bound, add_cap_upper_bound]


def calculate_winning_probability(R_total, R_pick, B_total, B_pick):
    """计算中奖概率"""
    red_combinations = comb(R_total, R_pick, exact=True)
    blue_combinations = comb(B_total, B_pick, exact=True) if B_total > 0 else 1
    return 1.0 / (red_combinations * blue_combinations)


def validate_lottery_rules(params):
    """验证彩票规则参数"""
    add_cap, R_total, R_pick, B_total, B_pick = params

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
    if p < 1e-12:
        return False, f"中奖概率({p:.2e})过低"

    c = 0.0002
    K_upper_limit = c / p
    max_reasonable_add_cap = K_upper_limit - 500
    if add_cap > max_reasonable_add_cap:
        return False, f"add_cap值({add_cap})超过经济合理性上限({max_reasonable_add_cap:.2f})"

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


def generate_mixed_lhs_samples(n, R_total=None, R_pick=None, B_total=None, B_pick=None):
    """生成混合拉丁超立方样本（add_cap为连续，概率参数为离散）"""
    n_params = len(PARAM_NAMES)
    samples = np.zeros((n, n_params))

    for i, param_name in enumerate(PARAM_NAMES):
        if param_name == 'add_cap':
            if all(x is not None for x in [R_total, R_pick, B_total, B_pick]):
                low, high = calculate_dynamic_bounds(R_total, R_pick, B_total, B_pick)
            else:
                low, high = -500, 50000
            samples[:, i] = np.random.uniform(low, high, n)
        elif param_name == 'R_total':
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
    """并行运行单个参数组合"""
    params, config = params_with_config

    add_cap, R_total, R_pick, B_total, B_pick = params

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


def joint_parameter_bayesian_optimization(baseline_sales, baseline_structure):
    """联合参数贝叶斯优化"""
    print("=" * 80)
    print(" 彩票规则联合敏感性分析 - 贝叶斯优化")
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

    print("\n 第一阶段：混合拉丁超立方采样（5个点）")

    lhs_points_list = []
    for _ in range(LHS_SAMPLES):
        R_total_cand = np.random.randint(PROB_PARAM_BOUNDS['R_total'][0], PROB_PARAM_BOUNDS['R_total'][1] + 1)
        R_pick_cand = np.random.randint(PROB_PARAM_BOUNDS['R_pick'][0], min(PROB_PARAM_BOUNDS['R_pick'][1], R_total_cand) + 1)
        B_total_cand = np.random.randint(PROB_PARAM_BOUNDS['B_total'][0], PROB_PARAM_BOUNDS['B_total'][1] + 1)
        B_pick_cand = np.random.randint(PROB_PARAM_BOUNDS['B_pick'][0], min(PROB_PARAM_BOUNDS['B_pick'][1], max(1, B_total_cand)) + 1)

        dynamic_add_cap_bounds = calculate_dynamic_bounds(R_total_cand, R_pick_cand, B_total_cand, B_pick_cand)
        add_cap_cand = np.random.uniform(
            max(-500, dynamic_add_cap_bounds[0]),
            min(50000, dynamic_add_cap_bounds[1])
        )

        lhs_points_list.append([add_cap_cand, R_total_cand, R_pick_cand, B_total_cand, B_pick_cand])

    lhs_points = np.array(lhs_points_list)
    print(f"   生成{len(lhs_points)}个采样点")

    print("   验证并修正参数约束...")
    for i in range(len(lhs_points)):
        valid, _ = validate_lottery_rules(lhs_points[i])
        if not valid:
            add_cap, R_total, R_pick, B_total, B_pick = lhs_points[i]
            R_pick = min(R_pick, R_total)
            B_pick = min(B_pick, max(0, B_total)) if B_total > 0 else 0
            lhs_points[i] = [add_cap, R_total, R_pick, B_total, B_pick]

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
        successful_points.append([row['add_cap'], row['R_total'], row['R_pick'], row['B_total'], row['B_pick']])
        successful_scores.append(row['composite_score'])

    X_train = np.array(successful_points)
    y_train = np.array(successful_scores)

    print(f"   初始训练集：{len(X_train)}个样本")
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
        print(f"\n[迭代 {iteration + 1}/{BAYES_ITERATIONS}]")
        print(f"   训练高斯过程模型(样本数:{len(X_train)})...")
        gp_model.fit(X_train, y_train)

        candidate_grid = []
        for _ in range(10000):
            R_total_cand = np.random.randint(PROB_PARAM_BOUNDS['R_total'][0], PROB_PARAM_BOUNDS['R_total'][1] + 1)
            R_pick_cand = np.random.randint(PROB_PARAM_BOUNDS['R_pick'][0], min(PROB_PARAM_BOUNDS['R_pick'][1], R_total_cand) + 1)
            B_total_cand = np.random.randint(PROB_PARAM_BOUNDS['B_total'][0], PROB_PARAM_BOUNDS['B_total'][1] + 1)
            B_pick_cand = np.random.randint(PROB_PARAM_BOUNDS['B_pick'][0], min(PROB_PARAM_BOUNDS['B_pick'][1], max(1, B_total_cand)) + 1)

            dynamic_add_cap_bounds = calculate_dynamic_bounds(R_total_cand, R_pick_cand, B_total_cand, B_pick_cand)
            add_cap_cand = np.random.uniform(
                max(-500, dynamic_add_cap_bounds[0]),
                min(50000, dynamic_add_cap_bounds[1])
            )

            candidate_grid.append([add_cap_cand, R_total_cand, R_pick_cand, B_total_cand, B_pick_cand])

        candidate_grid = np.array(candidate_grid)

        mean, std = gp_model.predict(candidate_grid, return_std=True)
        best_y = np.max(y_train)
        z = (mean - best_y) / (std + 1e-9)
        ei = (mean - best_y) * norm.cdf(z) + std * norm.pdf(z)

        top_indices = np.argsort(ei)[-BAYES_CANDIDATES:]
        candidates = candidate_grid[top_indices]

        print("   验证并修正候选点...")
        for i in range(len(candidates)):
            valid, _ = validate_lottery_rules(candidates[i])
            if not valid:
                add_cap, R_total, R_pick, B_total, B_pick = candidates[i]
                R_pick = min(R_pick, R_total)
                B_pick = min(B_pick, max(0, B_total)) if B_total > 0 else 0
                candidates[i] = [add_cap, R_total, R_pick, B_total, B_pick]

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
            successful_candidate_points.append([row['add_cap'], row['R_total'], row['R_pick'], row['B_total'], row['B_pick']])
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

            add_cap, R_total, R_pick, B_total, B_pick = current_best_param
            best_p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))

            if current_best_score > best_score:
                best_score = current_best_score
                best_params = current_best_param
                best_structure = candidate_results.iloc[current_best_idx]['y_structure']
                best_sales = candidate_results.iloc[current_best_idx]['y_sales']
                print(f"   ★ NEW BEST: add_cap={add_cap:.1f}, 红球={int(R_total)}选{int(R_pick)}, 蓝球={int(B_total)}选{int(B_pick)}, p={best_p:.2e}, 耗时={candidate_elapsed:.1f}s, 历史最优={best_score:.4f}, 本轮得分=综合{current_best_score:.4f}(结构{best_structure:.4f},销量{best_sales:.4f})")
            else:
                print(f"   本轮最优：得分={current_best_score:.4f}, 历史最优={best_score:.4f}")
        else:
            print(f"   本轮所有候选点都失败，跳过更新")

        best_history.append({
            'iteration': iteration + 1,
            'best_score': best_score,
            'best_params': best_params.tolist() if best_params is not None else None,
            'best_p': calculate_winning_probability(int(best_params[1]), int(best_params[2]), int(best_params[3]), int(best_params[4])) if best_params is not None else None,
            'y_structure': best_structure,
            'y_sales': best_sales
        })

    print("\n" + "=" * 80)
    print(" 贝叶斯优化完成！")
    print("=" * 80)

    add_cap, R_total, R_pick, B_total, B_pick = best_params
    best_p = calculate_winning_probability(int(R_total), int(R_pick), int(B_total), int(B_pick))

    optimal_params = {
        'add_cap': best_params[0],
        'R_total': int(best_params[1]),
        'R_pick': int(best_params[2]),
        'B_total': int(best_params[3]),
        'B_pick': int(best_params[4]),
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
        plt.title('Bayesian Optimization Convergence Curve - Joint Sensitivity')
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
    plt.title('Pareto Frontier: Sales vs Structure - Joint Sensitivity')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.colorbar(label='Composite Score')
    plt.legend()
    plt.tight_layout()
    plt.savefig(pareto_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 帕累托前沿图已保存至: {pareto_path}")

    # 3. 参数相关性热力图
    heatmap_path = os.path.join(plots_dir, "heatmap_correlation.png")
    plt.figure(figsize=(12, 8))

    numeric_cols = all_results_df.select_dtypes(include=[np.number]).columns
    correlation_matrix = all_results_df[numeric_cols].corr()

    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                square=True, fmt='.2f', cbar_kws={'shrink': 0.8})
    plt.title('Correlation Heatmap - Joint Sensitivity')
    plt.tight_layout()
    plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 相关性热力图已保存至: {heatmap_path}")

    # 4. 联合敏感性的3D图
    try:
        from mpl_toolkits.mplot3d import Axes3D

        thesis_3d_path = os.path.join(thesis_plots_dir, "fig_joint_sensitivity_3d.png")
        fig = plt.figure(figsize=(18, 6))

        # 综合得分3D图
        ax1 = fig.add_subplot(131, projection='3d')
        scatter1 = ax1.scatter(all_results_df['add_cap'], np.log10(all_results_df['p']),
                               all_results_df['composite_score'],
                               c=all_results_df['composite_score'], cmap='viridis', s=30)
        ax1.set_xlabel('Add Cap (万元)')
        ax1.set_ylabel('Log10(p)')
        ax1.set_zlabel('Composite Score')
        ax1.set_title('(a) 综合得分')
        fig.colorbar(scatter1, ax=ax1, shrink=0.5)

        # 销量3D图
        ax2 = fig.add_subplot(132, projection='3d')
        scatter2 = ax2.scatter(all_results_df['add_cap'], np.log10(all_results_df['p']),
                               all_results_df['total_tickets'],
                               c=all_results_df['total_tickets'], cmap='viridis', s=30)
        ax2.set_xlabel('Add Cap (万元)')
        ax2.set_ylabel('Log10(p)')
        ax2.set_zlabel('Total Tickets (亿元)')
        ax2.set_title('(b) 销量')
        fig.colorbar(scatter2, ax=ax2, shrink=0.5)

        # 结构指数3D图
        ax3 = fig.add_subplot(133, projection='3d')
        scatter3 = ax3.scatter(all_results_df['add_cap'], np.log10(all_results_df['p']),
                               all_results_df['structure_improvement'],
                               c=all_results_df['structure_improvement'], cmap='viridis', s=30)
        ax3.set_xlabel('Add Cap (万元)')
        ax3.set_ylabel('Log10(p)')
        ax3.set_zlabel('Structure Index')
        ax3.set_title('(c) 彩民结构指数')
        fig.colorbar(scatter3, ax=ax3, shrink=0.5)

        plt.tight_layout()
        plt.savefig(thesis_3d_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"   ✓ 联合敏感性3D图已保存至: {thesis_3d_path}")
    except Exception as e:
        print(f"   ⚠ 3D图生成失败: {e}")

    return plots_dir, thesis_plots_dir


def main():
    print("\n" + "=" * 80)
    print(" 博士论文：彩票规则联合敏感性分析")
    print("=" * 80)

    print("\n本脚本用于分析彩票规则参数变化对不同收入人群购彩行为的影响")
    print("优化参数：封顶额 + 彩票规则参数（红球数、选红球数、蓝球数、选蓝球数）")
    print("目标：同时优化消费结构改善性和销量")

    # 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_subdir = os.path.join(OUTPUT_DIR, f"results_{timestamp}")
    summary_dir = os.path.join(output_subdir, "summary")
    os.makedirs(output_subdir, exist_ok=True)
    os.makedirs(summary_dir, exist_ok=True)

    baseline_sales, baseline_structure = run_baseline_simulation()
    optimal_params, all_results_df, best_history = joint_parameter_bayesian_optimization(
        baseline_sales, baseline_structure
    )

    # 保存结果
    print(f"\n 正在生成输出文件到目录: {output_subdir}")

    results_csv_path = os.path.join(output_subdir, f"joint_results_{timestamp}.csv")
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
    print(f"  - 封顶额增加幅度：{optimal_params['add_cap']:.1f} 万元")
    print(f"  - 红球规则：{optimal_params['R_total']}选{optimal_params['R_pick']}")
    print(f"  - 蓝球规则：{optimal_params['B_total']}选{optimal_params['B_pick']}")
    print(f"  - 中奖概率：{optimal_params['p']:.2e}")
    print(f"  - 综合得分：{optimal_params['score']:.4f}")
    print(f"  - 结构得分：{optimal_params['y_structure']:.4f}")
    print(f"  - 销量得分：{optimal_params['y_sales']:.4f}")

    # 生成可视化
    generate_visualizations(all_results_df, output_subdir, best_history)

    print("\n 程序结束")


if __name__ == "__main__":
    main()
