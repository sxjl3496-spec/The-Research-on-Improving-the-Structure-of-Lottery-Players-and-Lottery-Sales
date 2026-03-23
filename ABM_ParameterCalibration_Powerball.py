# Powerball参数优化脚本
# 参数定义说明：
# u_con: 消费效用参数，影响代理人对一般消费品的效用评估
# u_sr: 主观阻力参数(subjective resistance)，代表代理人购买彩票时的主观阻力水平
# sd_con: 消费效用的标准差参数，反映消费效用的波动性
# sd_sr: 主观阻力的标准差参数，反映主观阻力的波动性

# =============================================================================
# 【配置参数】- 修改这里以调整优化设置
# =============================================================================
CONFIG = {
    # --- 文件路径 ---
    'netlogo_path': r"D:/netlogo",
    'nlogo_file': r"D:/BaiduSyncdisk/1DoctorStudy/1Doctor thesis/ABM-LOTTERY/normal20260203distribution.nlogo",

    # --- 彩票类型 ("PB"=Powerball, "DCB"=双色球) ---
    'lottery_type': "PB",

    # --- 并行核心数 ---
    'max_cores_allowed': 12,
    'n_cores_lhs': 12,              # LHS阶段并行核心数
    'n_cores_bayes': 10,            # 贝叶斯优化阶段并行核心数

    # --- 贝叶斯优化参数 ---
    'n_lhs_points': 12,             # LHS 初始打点数
    'n_iterations': 50,             # 贝叶斯迭代次数
    'n_runs_per_point': 10,         # 每个参数点重复仿真次数

    # --- 损失函数权重 (total_sales, std_dev, skewness, kurtosis) ---
    'weights': {
        'total_sales': 0.4,
        'std_dev': 0.3,
        'skewness': 0.15,
        'kurtosis': 0.15
    },

    # --- 输出目录 ---
    'output_dir': r"D:\Pycharm\PycharmProjects\byes_optim_date"
}
# =============================================================================

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import qmc
import os
import pynetlogo
import time
from datetime import datetime
from skopt import gp_minimize
from skopt.space import Real
from skopt.learning import GaussianProcessRegressor
from skopt.learning.gaussian_process.kernels import Matern
from skopt import Optimizer
from joblib import Parallel, delayed  # 引入并行库
import psutil  # 用于查询CPU核心数
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pickle  # 导入pickle用于保存/加载历史数据


# ===== 辅助函数：用于在子进程中运行单次仿真 =====
def _run_simulation_worker(args):
    """
    用于并行执行的辅助函数
    args: 包含 (u_con, u_sr, sd_con, sd_sr, netlogo_path, nlogo_file, lottery_type, num_periods) 的元组
    """
    u_con, u_sr, sd_con, sd_sr, netlogo_path, nlogo_file, lottery_type, num_periods = args

    print(
        f"   -> [{datetime.now().strftime('%H:%M:%S')}] 子进程仿真 (u_con={u_con:.3f}, u_sr={u_sr:.0f}, sd_con={sd_con:.3f}, sd_sr={sd_sr:.0f})")

    netlogo_link = None
    try:
        # 初始化 NetLogo - 传递 netlogo_home
        netlogo_link = pynetlogo.NetLogoLink(netlogo_home=netlogo_path, gui=False)
        netlogo_link.load_model(nlogo_file)

        # 设置参数
        netlogo_link.command(f'set u-con {u_con}')
        netlogo_link.command(f'set u-sr {u_sr}')
        netlogo_link.command(f'set sd-con {sd_con}')
        netlogo_link.command(f'set sd-sr {sd_sr}')

        if lottery_type == "DCB":
            netlogo_link.command('set lottery_types 1')
            netlogo_link.command('set country 1')
        else:
            netlogo_link.command('set lottery_types 0')
            netlogo_link.command('set country 0')

        netlogo_link.command('setup')

        sales_series = []
        for period in range(num_periods):
            netlogo_link.command('go')
            current_sales = netlogo_link.report('current-tickets')
            sales_series.append(current_sales * 200000)

        netlogo_link.kill_workspace()
        return u_con, u_sr, sd_con, sd_sr, sales_series

    except Exception as e:
        print(f"   警告: 仿真出错 (u_con={u_con:.3f}, u_sr={u_sr:.0f}, sd_con={sd_con:.3f}, sd_sr={sd_sr:.0f}): {e}")
        if netlogo_link is not None:
            try:
                netlogo_link.kill_workspace()
            except:
                pass
        return u_con, u_sr, sd_con, sd_sr, None


# ===== 核心类定义 =====
class BayesianOptimizerTest:
    # 类属性，作为全局计数器
    _iteration_counter = 0

    def __init__(self, netlogo_path, nlogo_file, lottery_type="PB", max_allowed_cores=15):
        """
        贝叶斯优化器 (按指定流程) - Powerball专用版本
        :param netlogo_path: NetLogo 安装路径
        :param nlogo_file: NetLogo 模型文件路径
        :param lottery_type: 彩票类型 ("DCB" 或 "PB")
        :param max_allowed_cores: 允许使用的最大核心数
        """
        self.netlogo_path = netlogo_path
        self.nlogo_file = nlogo_file
        self.lottery_type = lottery_type
        self.max_allowed_cores = max_allowed_cores

        # --- 参数范围定义 (PB专用) ---
        # 定义 u_sr 的上界作为一个变量，方便修改
        # 扩大上界以支持更大范围的 sd_sr 搜索（最优值可能在7500-10000）
        U_SR_UPPER_BOUND = 40000
        # 根据 u_sr 上界计算 sd_sr 上界 (sd_sr = u_sr / 4)
        SD_SR_UPPER_BOUND = U_SR_UPPER_BOUND / 4.0
        # 定义 u_con 的上界
        U_CON_UPPER_BOUND = 1.0
        # 根据 u_con 上界计算 sd_con 上界 (sd_con = u_con / 4)
        SD_CON_UPPER_BOUND = U_CON_UPPER_BOUND / 3.0

        if self.lottery_type == "DCB":
            self.target_stats = {
                'total_sales': 6.47e11,
                'std_dev': 4.00e7,
                'skewness': 0.56,
                'kurtosis': 5.10
            }
            # 参数范围现在使用上方定义的变量
            self.param_ranges = {
                'u_con': [0.000001, U_CON_UPPER_BOUND],
                'u_sr': [5000, U_SR_UPPER_BOUND],
                'sd_con': [0.00000025, SD_CON_UPPER_BOUND],
                'sd_sr': [1250, SD_SR_UPPER_BOUND]
            }
        else:  # PB - Powerball
            self.target_stats = {
                'total_sales': 6.85e10,
                'std_dev': 5.35e7,
                'skewness': 12.05,
                'kurtosis': 214.99
            }
            self.param_ranges = {
                'u_con': [0.000001, U_CON_UPPER_BOUND],
                'u_sr': [1000, U_SR_UPPER_BOUND],
                'sd_con': [0.00000025, SD_CON_UPPER_BOUND],
                'sd_sr': [250, SD_SR_UPPER_BOUND]
            }

        # 定义搜索空间 (4个参数)
        self.dimensions = [
            Real(self.param_ranges['u_con'][0], self.param_ranges['u_con'][1], name='u_con'),
            Real(self.param_ranges['u_sr'][0], self.param_ranges['u_sr'][1], name='u_sr'),
            Real(self.param_ranges['sd_con'][0], self.param_ranges['sd_con'][1], name='sd_con'),
            Real(self.param_ranges['sd_sr'][0], self.param_ranges['sd_sr'][1], name='sd_sr')
        ]

        # 用于存储历史数据
        self.history_x = []
        self.history_y = []
        self.history_sd_con = []
        self.history_sd_sr = []
        self.history_loss = []
        self.history_iteration_type = []
        
        # 设置输出目录
        self.output_dir = CONFIG['output_dir']
        os.makedirs(self.output_dir, exist_ok=True)
        
        # CSV数据记录文件
        self.history_filename = os.path.join(self.output_dir, f"bayesian_optimization_history_{self.lottery_type}.csv")
        self.data_filename = os.path.join(self.output_dir, f"bayesian_optimization_data_{self.lottery_type}.csv")
        self.top5_filename = os.path.join(self.output_dir, f"bayesian_optimization_top5_{self.lottery_type}.csv")

    @classmethod
    def reset_counter(cls):
        """重置迭代计数器"""
        cls._iteration_counter = 0
    
    def generate_lhs_points(self, n_points, random_seed=42):
        """
        使用拉丁超立方采样(LHS)生成初始点
        :param n_points: 采样点数
        :param random_seed: 随机种子
        :return: 参数点列表 [(u_con, u_sr, sd_con, sd_sr), ...]
        """
        print(f"\n🎯 使用LHS生成 {n_points} 个初始采样点...")
        
        # 使用scipy的LHS采样
        sampler = qmc.LatinHypercube(d=4, seed=random_seed)
        sample = sampler.random(n=n_points)
        
        # 将采样值映射到参数范围
        points = []
        for i in range(n_points):
            u_con = self.param_ranges['u_con'][0] + sample[i][0] * (self.param_ranges['u_con'][1] - self.param_ranges['u_con'][0])
            u_sr = self.param_ranges['u_sr'][0] + sample[i][1] * (self.param_ranges['u_sr'][1] - self.param_ranges['u_sr'][0])
            sd_con = self.param_ranges['sd_con'][0] + sample[i][2] * (self.param_ranges['sd_con'][1] - self.param_ranges['sd_con'][0])
            sd_sr = self.param_ranges['sd_sr'][0] + sample[i][3] * (self.param_ranges['sd_sr'][1] - self.param_ranges['sd_sr'][0])
            points.append((u_con, u_sr, sd_con, sd_sr))
        
        # 显示生成的点
        for i, (u_con, u_sr, sd_con, sd_sr) in enumerate(points):
            print(f"   LHS-{i+1}: u_con={u_con:.6f}, u_sr={u_sr:.0f}, sd_con={sd_con:.6f}, sd_sr={sd_sr:.0f}")
        
        return points

    def calculate_statistics(self, sales_series):
        """计算统计量"""
        if sales_series is None or len(sales_series) == 0:
            print("警告: 销售数据为空")
            # 确保返回标量
            return {'total_sales': 0.0, 'std_dev': 0.0, 'skewness': 0.0, 'kurtosis': 0.0}

        # 确保输入是 numpy 数组
        sales_array = np.asarray(sales_series)

        if len(sales_array) == 0:
            print("警告: 销售数据数组为空")
            # 确保返回标量
            return {'total_sales': 0.0, 'std_dev': 0.0, 'skewness': 0.0, 'kurtosis': 0.0}

        if np.all(sales_array == sales_array[0]):
            # 所有值相等，标准差为0，偏度峰度也为0
            return {
                'total_sales': float(np.sum(sales_array)),  # 转换为Python标量
                'std_dev': 0.0,
                'skewness': 0.0,
                'kurtosis': 0.0  # scipy kurtosis 对常数会返回 -1.5, 加3后为1.5，但这不符合预期，所以直接设为0
            }

        stats_result = {
            'total_sales': float(np.sum(sales_array)),  # 转换为Python标量
            'std_dev': float(np.std(sales_array)),  # 转换为Python标量
            'skewness': float(stats.skew(sales_array)),  # 转换为Python标量
            'kurtosis': float(stats.kurtosis(sales_array) + 3)
            # scipy的kurtosis是 excess kurtosis，加3得到标准kurtosis, 转换为Python标量
        }
        # print(f" 统计计算完成: 总销量={stats_result['total_sales']:,.0f}")
        return stats_result

    def calculate_loss(self, simulated_stats, weights):
        """
        计算损失函数 (使用新公式)
        :param simulated_stats: 仿真得到的统计量字典
        :param weights: 权重字典
        :return: 损失函数值 (标量)
        """
        total_loss = 0
        for key in ['total_sales', 'std_dev', 'skewness', 'kurtosis']:
            # 确保是标量
            sim_val = np.asarray(simulated_stats[key]).item() if isinstance(simulated_stats[key],
                                                                            (list, np.ndarray)) else simulated_stats[
                key]
            target_val = self.target_stats[key]

            if target_val != 0:
                rel_error = abs(sim_val - target_val) / abs(target_val)
                term = 1 - np.exp(-rel_error)  # 新公式核心
            else:
                term = abs(sim_val)  # 如果目标为0，直接用绝对值

            weighted_term = weights[key] * term
            total_loss += weighted_term

        # 确保返回的是 Python 标量，而不是 numpy 标量
        return float(total_loss)

    def run_batch_simulations_parallel(self, tasks, n_jobs=None):
        """
        通用的并行仿真函数
        :param tasks: 任务列表 [(args1), (args2), ...]
        :param n_jobs: 并行数，默认使用 n_jobs_initial
        :return: 仿真结果列表
        """
        if n_jobs is None:
            n_jobs = min(len(tasks), self.max_allowed_cores)  # 根据任务数和核心数决定
        print(f"    准备使用 {n_jobs} 个进程并行执行 {len(tasks)} 次仿真...")
        results = Parallel(n_jobs=n_jobs, backend='multiprocessing')(
            delayed(_run_simulation_worker)(task) for task in tasks
        )
        return results

    def load_results_database(self, db_filename):
        """
        从CSV文件加载历史结果数据库
        :param db_filename: CSV文件名
        :return: DataFrame，如果文件不存在则返回None
        """
        if os.path.exists(db_filename):
            print(f" 发现历史结果数据库: {db_filename}，正在加载...")
            try:
                df = pd.read_csv(db_filename)
                print(f"完成 成功加载 {len(df)} 条历史记录。")
                return df
            except Exception as e:
                print(f"警告: 加载历史数据库时出错: {e}，将创建新的数据库。")
                return None
        else:
            print(f" 未发现历史结果数据库: {db_filename}，将创建新的。")
            return None

    def save_results_database(self, df, db_filename):
        """
        将DataFrame保存到CSV文件
        :param df: 包含结果的DataFrame
        :param db_filename: CSV文件名
        """
        df.to_csv(db_filename, index=False)
        print(f" 结果数据库已保存到: {db_filename}")

    def evaluate_manual_points(self, points_to_test, weights=None, runs_per_eval=1, db_filename="results_database_PB.csv", 
                              auto_verify_threshold=0.15, verify_runs=3):
        """
        评估手动输入的参数点，并保存/更新数据库
        对于Loss低于阈值的点，自动进行多次验证以提高可靠性
        
        :param points_to_test: 列表，包含手动提供的点，格式为 [(u_con, u_sr, sd_con, sd_sr), ...]
        :param weights: 计算损失时使用的权重字典
        :param runs_per_eval: 每次评估运行的仿真次数
        :param db_filename: 用于保存和加载结果的CSV文件名
        :param auto_verify_threshold: 自动验证的Loss阈值，低于此值的点将进行多次验证
        :param verify_runs: 验证时的运行次数
        """
        if weights is None:
            weights = {'total_sales': 0.4, 'std_dev': 0.3, 'skewness': 0.15, 'kurtosis': 0.15}

        print(f"\n [{datetime.now().strftime('%H:%M:%S')}] 开始评估 {len(points_to_test)} 个手动输入的Powerball参数点...")
        print(f"   [PIN] 自动验证策略: Loss < {auto_verify_threshold} 的点将自动运行 {verify_runs} 次取平均值")

        # 1. 加载现有数据库
        existing_df = self.load_results_database(db_filename)

        tasks = []
        for u_con, u_sr, sd_con, sd_sr in points_to_test:
            # 验证自定义点是否在范围内（可选，但推荐）
            u_con_ok = self.param_ranges['u_con'][0] <= u_con <= self.param_ranges['u_con'][1]
            u_sr_ok = self.param_ranges['u_sr'][0] <= u_sr <= self.param_ranges['u_sr'][1]
            sd_con_ok = self.param_ranges['sd_con'][0] <= sd_con <= self.param_ranges['sd_con'][1]
            sd_sr_ok = self.param_ranges['sd_sr'][0] <= sd_sr <= self.param_ranges['sd_sr'][1]

            if not all([u_con_ok, u_sr_ok, sd_con_ok, sd_sr_ok]):
                print(f"警告: 警告: 输入点 (u_con={u_con}, u_sr={u_sr}, sd_con={sd_con}, sd_sr={sd_sr}) 超出范围")
                print(f"     范围: u_con [{self.param_ranges['u_con'][0]}, {self.param_ranges['u_con'][1]}], "
                      f"u_sr [{self.param_ranges['u_sr'][0]}, {self.param_ranges['u_sr'][1]}], "
                      f"sd_con [{self.param_ranges['sd_con'][0]}, {self.param_ranges['sd_con'][1]}], "
                      f"sd_sr [{self.param_ranges['sd_sr'][0]}, {self.param_ranges['sd_sr'][1]}]")

            # 准备任务，考虑多次运行
            for _ in range(runs_per_eval):
                tasks.append((u_con, u_sr, sd_con, sd_sr, self.netlogo_path, self.nlogo_file, self.lottery_type, 1800))

        # 2. 并行执行第一轮仿真
        print(f"\n[LOOP] 第一轮评估: 运行 {len(points_to_test)} 个参数点...")
        results = self.run_batch_simulations_parallel(tasks, n_jobs=min(len(tasks), self.max_allowed_cores))

        # 3. 处理第一轮结果并识别需要验证的点
        df_data = []
        points_to_verify = []  # 需要验证的高潜力点
        
        if runs_per_eval > 1:
            # 将结果按点分组
            for i in range(0, len(results), runs_per_eval):
                group = results[i:i + runs_per_eval]
                u_con, u_sr, sd_con, sd_sr, _ = group[0]  # 从第一个副本获取参数

                all_sales_series = []
                for _, _, _, _, series in group:
                    if series is not None and len(series) > 0:
                        all_sales_series.append(np.array(series))

                if not all_sales_series:
                    print(f"错误: 所有针对点 (u_con={u_con}, ...) 的仿真均失败，跳过此点。")
                    continue

                mean_sales_series_array = np.mean(all_sales_series, axis=0)
                simulated_stats = self.calculate_statistics(mean_sales_series_array)
                loss_value = self.calculate_loss(simulated_stats, weights)

                # 检查是否需要验证
                if loss_value < auto_verify_threshold:
                    points_to_verify.append({
                        'params': (u_con, u_sr, sd_con, sd_sr),
                        'first_run_stats': simulated_stats,
                        'first_run_loss': loss_value,
                        'first_run_series': mean_sales_series_array
                    })
                    print(f"   [STAR] 发现潜力点! Loss={loss_value:.6f}, 参数({u_con:.3f}, {u_sr:.0f}, {sd_con:.3f}, {sd_sr:.0f}) - 将进行{verify_runs}次验证")

                df_data.append({
                    'u_con': u_con,
                    'u_sr': u_sr,
                    'sd_con': sd_con,
                    'sd_sr': sd_sr,
                    'Total Sales': simulated_stats['total_sales'],
                    'Std Dev': simulated_stats['std_dev'],
                    'Skewness': simulated_stats['skewness'],
                    'Kurtosis': simulated_stats['kurtosis'],
                    'Loss': loss_value,
                    'Verified': False,
                    'Verify_Runs': 1
                })
        else:
            # runs_per_eval == 1
            for u_con, u_sr, sd_con, sd_sr, sales_series in results:
                simulated_stats = self.calculate_statistics(sales_series)
                loss_value = self.calculate_loss(simulated_stats, weights)

                # 检查是否需要验证
                if loss_value < auto_verify_threshold:
                    points_to_verify.append({
                        'params': (u_con, u_sr, sd_con, sd_sr),
                        'first_run_stats': simulated_stats,
                        'first_run_loss': loss_value,
                        'first_run_series': sales_series
                    })
                    print(f"   [STAR] 发现潜力点! Loss={loss_value:.6f}, 参数({u_con:.3f}, {u_sr:.0f}, {sd_con:.3f}, {sd_sr:.0f}) - 将进行{verify_runs}次验证")

                df_data.append({
                    'u_con': u_con,
                    'u_sr': u_sr,
                    'sd_con': sd_con,
                    'sd_sr': sd_sr,
                    'Total Sales': simulated_stats['total_sales'],
                    'Std Dev': simulated_stats['std_dev'],
                    'Skewness': simulated_stats['skewness'],
                    'Kurtosis': simulated_stats['kurtosis'],
                    'Loss': loss_value,
                    'Verified': False,
                    'Verify_Runs': 1
                })
        
        # 4. 对高潜力点进行验证（再运行verify_runs-1次，加上第一次共verify_runs次）
        if points_to_verify:
            print(f"\n[SEARCH] 开始验证阶段: 对 {len(points_to_verify)} 个潜力点进行 {verify_runs} 次重复验证...")
            
            for point_info in points_to_verify:
                u_con, u_sr, sd_con, sd_sr = point_info['params']
                print(f"\n   验证点: u_con={u_con:.3f}, u_sr={u_sr:.0f}, sd_con={sd_con:.3f}, sd_sr={sd_sr:.0f}")
                print(f"   初始Loss: {point_info['first_run_loss']:.6f}")
                
                # 准备额外的验证任务（已有1次，再运行verify_runs-1次）
                verify_tasks = []
                for _ in range(verify_runs - 1):
                    verify_tasks.append((u_con, u_sr, sd_con, sd_sr, self.netlogo_path, 
                                       self.nlogo_file, self.lottery_type, 1800))
                
                # 执行验证
                verify_results = self.run_batch_simulations_parallel(verify_tasks, 
                                                                     n_jobs=min(len(verify_tasks), self.max_allowed_cores))
                
                # 收集所有运行的销售序列（包括第一次）
                all_verify_series = [point_info['first_run_series']]
                all_verify_losses = [point_info['first_run_loss']]
                
                for _, _, _, _, sales_series in verify_results:
                    if sales_series is not None and len(sales_series) > 0:
                        all_verify_series.append(np.array(sales_series))
                        stats = self.calculate_statistics(sales_series)
                        loss = self.calculate_loss(stats, weights)
                        all_verify_losses.append(loss)
                
                # 计算平均值
                if len(all_verify_series) >= verify_runs:
                    mean_verified_series = np.mean(all_verify_series, axis=0)
                    verified_stats = self.calculate_statistics(mean_verified_series)
                    verified_loss = self.calculate_loss(verified_stats, weights)
                    
                    print(f"   [OK] 验证完成:")
                    print(f"      - 各次Loss: {[f'{l:.6f}' for l in all_verify_losses]}")
                    print(f"      - 平均Loss: {verified_loss:.6f}")
                    print(f"      - Loss标准差: {np.std(all_verify_losses):.6f}")
                    
                    # 更新df_data中对应点的数据
                    for idx, row in enumerate(df_data):
                        if (row['u_con'] == u_con and row['u_sr'] == u_sr and 
                            row['sd_con'] == sd_con and row['sd_sr'] == sd_sr):
                            df_data[idx] = {
                                'u_con': u_con,
                                'u_sr': u_sr,
                                'sd_con': sd_con,
                                'sd_sr': sd_sr,
                                'Total Sales': verified_stats['total_sales'],
                                'Std Dev': verified_stats['std_dev'],
                                'Skewness': verified_stats['skewness'],
                                'Kurtosis': verified_stats['kurtosis'],
                                'Loss': verified_loss,
                                'Verified': True,
                                'Verify_Runs': verify_runs,
                                'Loss_Std': np.std(all_verify_losses)
                            }
                            break
                else:
                    print(f"   [WARN] 警告: 验证仿真部分失败，只有{len(all_verify_series)}次成功")

        # 5. 创建本次运行的 DataFrame
        new_df = pd.DataFrame(df_data)

        # 6. 合并或更新数据库
        if existing_df is not None and not existing_df.empty:
            print(f"-> 正在合并新结果与现有数据库...")
            # 将现有数据库和新数据合并
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            # 定义用于判断重复的列（参数）
            unique_cols = ['u_con', 'u_sr', 'sd_con', 'sd_sr']

            # 使用 drop_duplicates，keep='last' 确保如果存在重复参数，保留最新的（也就是本次运行的）结果
            updated_df = combined_df.drop_duplicates(subset=unique_cols, keep='last')
            print(f"完成 合并完成。去重后总记录数: {len(updated_df)}")
        else:
            # 如果没有现有数据库，则新数据就是最终数据库
            updated_df = new_df
            print(f"完成 首次运行，创建新数据库。记录数: {len(updated_df)}")

        # 7. 保存更新后的数据库
        self.save_results_database(updated_df, db_filename)

        # 8. 打印本次运行的结果汇总
        print("\n" + "=" * 120)
        print(" 本次Powerball手动测试点评估结果汇总 (已更新数据库):")
        print("=" * 120)
        
        # 分离已验证和未验证的点进行显示
        verified_df = new_df[new_df.get('Verified', False) == True]
        unverified_df = new_df[new_df.get('Verified', False) == False]
        
        if len(unverified_df) > 0:
            print("\n未验证的点（单次运行）:")
            print("-" * 120)
            display_cols = ['u_con', 'u_sr', 'sd_con', 'sd_sr', 'Total Sales', 'Std Dev', 'Skewness', 'Kurtosis', 'Loss']
            print(unverified_df[display_cols].to_string(index=False, float_format='%.4e'))
        
        if len(verified_df) > 0:
            print(f"\n[STAR] 已验证的高潜力点（{verify_runs}次运行平均）:")
            print("-" * 120)
            display_cols_verified = ['u_con', 'u_sr', 'sd_con', 'sd_sr', 'Total Sales', 'Std Dev', 
                                    'Skewness', 'Kurtosis', 'Loss', 'Loss_Std', 'Verify_Runs']
            # 只显示存在的列
            display_cols_verified = [col for col in display_cols_verified if col in verified_df.columns]
            print(verified_df[display_cols_verified].to_string(index=False, float_format='%.4e'))

        print("\n Powerball目标统计量:")
        print("-" * 40)
        for key, val in self.target_stats.items():
            print(f"{key:<12}: {val:>15.4e}")
        print("-" * 40)
        print("=" * 120)

        print(f"\n[OK] 评估 {len(new_df)} 个新点并更新数据库完成。")
        if len(verified_df) > 0:
            print(f"   其中 {len(verified_df)} 个点通过了{verify_runs}次验证（Loss < {auto_verify_threshold}）")
        return updated_df

    def auto_optimize(self, initial_points=None, initial_df=None, weights=None,
                      runs_per_eval=2, candidates_per_iter=12, explore_frac=0.03,
                      max_iters=50, target_loss=0.1, db_filename="results_database_PB.csv"):
        """
        自动迭代优化：基于已有点或初始点集，分析参数与Loss的关系，生成候选点并迭代直到达到target_loss。
        - initial_points: list of tuples to evaluate first if no initial_df provided
        - initial_df: DataFrame with existing evaluated points (columns must include Loss)
        """
        if weights is None:
            weights = {'total_sales': 0.4, 'std_dev': 0.3, 'skewness': 0.15, 'kurtosis': 0.15}

        # 1) Obtain starting database
        if initial_df is None:
            if initial_points is None or len(initial_points) == 0:
                raise ValueError("auto_optimize需要 initial_points 或 initial_df 之一作为起点")
            print(f"\n[AutoOpt] 评估 {len(initial_points)} 个初始点 (每点 {runs_per_eval} 次)")
            df = self.evaluate_manual_points(points_to_test=initial_points, weights=weights,
                                             runs_per_eval=runs_per_eval, db_filename=db_filename,
                                             auto_verify_threshold=0, verify_runs=1)
        else:
            df = initial_df.copy()

        # Make sure numeric
        df = df.copy()

        for it in range(1, max_iters + 1):
            print(f"\n[AutoOpt][Iter {it}/{max_iters}] 分析数据库，寻找最佳点并生成候选点...")

            # ensure Loss exists
            if 'Loss' not in df.columns or df['Loss'].isnull().all():
                raise RuntimeError('数据库中缺少有效的 Loss 列')

            best_idx = df['Loss'].idxmin()
            best_row = df.loc[best_idx]
            best_loss = float(best_row['Loss'])
            best_params = (float(best_row['u_con']), float(best_row['u_sr']), float(best_row['sd_con']), float(best_row['sd_sr']))

            print(f"   当前最佳 Loss={best_loss:.6f}, 参数={best_params}")
            if best_loss <= target_loss:
                print(f"[AutoOpt] 达到目标 Loss <= {target_loss}，停止迭代。")
                return df

            # Compute correlations between params and Loss to get directionality
            corr_cols = ['u_con', 'u_sr', 'sd_con', 'sd_sr', 'Loss']
            use_df = df[corr_cols].dropna()
            if len(use_df) < 3:
                corrs = {c: 0.0 for c in ['u_con', 'u_sr', 'sd_con', 'sd_sr']}
            else:
                corrs = use_df.corr()['Loss'].to_dict()

            # For each parameter, correlation sign indicates whether increasing param tends to increase Loss.
            # We'll move in the opposite direction of positive corr, and same direction for negative corr.
            directions = {}
            for p in ['u_con', 'u_sr', 'sd_con', 'sd_sr']:
                val = corrs.get(p, 0.0)
                # If positive corr, increasing p increases Loss -> step negative; else positive
                directions[p] = -1.0 if val > 0 else 1.0

            # Build candidates around best point
            candidates = []
            u_con_b, u_sr_b, sd_con_b, sd_sr_b = best_params
            # base step sizes relative to best value (but ensure minimum absolute step)
            step_u_con = max(abs(u_con_b) * explore_frac, 1e-4)
            step_u_sr = max(abs(u_sr_b) * explore_frac, 10.0)
            step_sd_con = max(abs(sd_con_b) * explore_frac, 1e-4)
            step_sd_sr = max(abs(sd_sr_b) * explore_frac, 10.0)

            import random
            random.seed(42 + it)

            # Deterministic directional candidates (one per param up/down based on direction)
            for p, step in [('u_con', step_u_con), ('u_sr', step_u_sr), ('sd_con', step_sd_con), ('sd_sr', step_sd_sr)]:
                dir_sign = directions[p]
                cand = {
                    'u_con': u_con_b,
                    'u_sr': u_sr_b,
                    'sd_con': sd_con_b,
                    'sd_sr': sd_sr_b
                }
                cand[p] = float(max(self.param_ranges[p][0], min(self.param_ranges[p][1], cand[p] + dir_sign * step)))
                candidates.append((cand['u_con'], cand['u_sr'], cand['sd_con'], cand['sd_sr']))

            # Randomized local exploration
            while len(candidates) < candidates_per_iter:
                u_con_c = float(max(self.param_ranges['u_con'][0], min(self.param_ranges['u_con'][1],
                                      u_con_b + random.uniform(-1, 1) * step_u_con * 2)))
                u_sr_c = float(max(self.param_ranges['u_sr'][0], min(self.param_ranges['u_sr'][1],
                                      u_sr_b + random.uniform(-1, 1) * step_u_sr * 2)))
                sd_con_c = float(max(self.param_ranges['sd_con'][0], min(self.param_ranges['sd_con'][1],
                                      sd_con_b + random.uniform(-1, 1) * step_sd_con * 2)))
                sd_sr_c = float(max(self.param_ranges['sd_sr'][0], min(self.param_ranges['sd_sr'][1],
                                      sd_sr_b + random.uniform(-1, 1) * step_sd_sr * 2)))
                cand_t = (u_con_c, u_sr_c, sd_con_c, sd_sr_c)
                if cand_t not in candidates:
                    candidates.append(cand_t)

            print(f"   生成 {len(candidates)} 个候选点，开始评估 (每点 {runs_per_eval} 次)...")

            # Evaluate candidates
            new_results = self.evaluate_manual_points(points_to_test=candidates, weights=weights,
                                                      runs_per_eval=runs_per_eval, db_filename=db_filename,
                                                      auto_verify_threshold=0, verify_runs=1)

            # Merge new_results into df for next iter
            # Keep only unique parameter combos
            combined = pd.concat([df, new_results], ignore_index=True)
            combined = combined.drop_duplicates(subset=['u_con', 'u_sr', 'sd_con', 'sd_sr'], keep='last')
            df = combined.reset_index(drop=True)

        print(f"[AutoOpt] 达到最大迭代次数 ({max_iters})，停止。最佳 Loss={df['Loss'].min():.6f}")
        return df


    def run_bayesian_optimization(self, n_lhs_points=12, n_iterations=50, n_runs_per_point=10, 
                                   n_cores_lhs=12, n_cores_bayes=10, weights=None):
        """
        执行完整的贝叶斯优化流程
        :param n_lhs_points: LHS初始采样点数
        :param n_iterations: 贝叶斯优化迭代次数
        :param n_runs_per_point: 贝叶斯优化中每个点的运行次数
        :param n_cores_lhs: LHS阶段并行核心数
        :param n_cores_bayes: 贝叶斯优化阶段并行核心数
        :param weights: 损失权重
        """
        if weights is None:
            weights = {'total_sales': 0.4, 'std_dev': 0.3, 'skewness': 0.15, 'kurtosis': 0.15}
        
        print(f"\n{'='*80}")
        print(f"🚀 开始贝叶斯优化流程")
        print(f"{'='*80}")
        print(f"   LHS初始采样: {n_lhs_points} 个点, {n_cores_lhs} 进程并行")
        print(f"   贝叶斯优化: {n_iterations} 次迭代, 每次1个点运行{n_runs_per_point}次, {n_cores_bayes} 进程并行")
        print(f"   输出目录: {self.output_dir}")
        print(f"{'='*80}\n")
        
        # 存储所有运行结果
        all_records = []
        evaluated_params = []  # 已评估的参数点
        evaluated_losses = []  # 对应的平均loss
        evaluated_stats = []   # 对应的平均统计量
        
        # ===== 第1阶段：LHS初始采样 =====
        print(f"\n{'='*80}")
        print(f"📍 第1阶段：LHS初始采样 ({n_lhs_points}个点)")
        print(f"{'='*80}")
        
        lhs_points = self.generate_lhs_points(n_lhs_points, random_seed=42)
        
        # 准备LHS任务（每个点运行1次）
        lhs_tasks = []
        for i, (u_con, u_sr, sd_con, sd_sr) in enumerate(lhs_points):
            lhs_tasks.append((u_con, u_sr, sd_con, sd_sr, self.netlogo_path, self.nlogo_file, 
                            self.lottery_type, 1800))
        
        print(f"\n🧵 启动 {n_cores_lhs} 个进程并行执行 {len(lhs_tasks)} 个LHS采样点...")
        lhs_results = self.run_batch_simulations_parallel(lhs_tasks, n_jobs=n_cores_lhs)
        
        # 处理LHS结果
        print(f"\n📊 处理LHS结果...")
        for i, (u_con, u_sr, sd_con, sd_sr, sales_series) in enumerate(lhs_results):
            if sales_series is not None:
                stats_result = self.calculate_statistics(sales_series)
                loss_value = self.calculate_loss(stats_result, weights)
                
                # 记录到数据库
                record = {
                    'Iteration_Label': f'LHS-{i+1}',
                    'u_con': u_con,
                    'u_sr': u_sr,
                    'sd_con': sd_con,
                    'sd_sr': sd_sr,
                    'Total Sales': stats_result['total_sales'],
                    'Std Dev': stats_result['std_dev'],
                    'Skewness': stats_result['skewness'],
                    'Kurtosis': stats_result['kurtosis'],
                    'Loss': loss_value
                }
                all_records.append(record)
                
                # 存储用于贝叶斯优化的数据
                params = [u_con, u_sr, sd_con, sd_sr]
                evaluated_params.append(params)
                evaluated_losses.append(loss_value)
                evaluated_stats.append(stats_result)
                
                print(f"   LHS-{i+1}: Loss={loss_value:.6f}")
        
        # 保存LHS结果
        if all_records:
            df = pd.DataFrame(all_records)
            df.to_csv(self.history_filename, index=False)
            print(f"\n💾 LHS结果已保存到: {self.history_filename}")
        
        # ===== 第2阶段：贝叶斯优化迭代 =====
        print(f"\n{'='*80}")
        print(f"📍 第2阶段：贝叶斯优化迭代 ({n_iterations}次)")
        print(f"{'='*80}")
        
        for iteration in range(n_iterations):
            print(f"\n{'─'*80}")
            print(f"🔄 迭代 {iteration+1}/{n_iterations}")
            print(f"{'─'*80}")
            
            # 使用贝叶斯优化选择下一个点
            from skopt import Optimizer
            from skopt.learning import GaussianProcessRegressor
            from skopt.learning.gaussian_process.kernels import Matern
            
            # 基于已有数据拟合高斯过程
            X = np.array(evaluated_params)
            y = np.array(evaluated_losses)
            
            # 创建优化器
            opt = Optimizer(
                dimensions=self.dimensions,
                base_estimator=GaussianProcessRegressor(
                    kernel=Matern(nu=2.5),
                    normalize_y=True,
                    noise="gaussian",
                    n_restarts_optimizer=5
                ),
                acq_func="EI",
                acq_optimizer="auto",
                random_state=42 + iteration
            )
            
            # 告诉优化器已有的数据
            opt.tell(X.tolist(), y.tolist())
            
            # 生成下一个候选点
            try:
                next_point = opt.ask()
                u_con, u_sr, sd_con, sd_sr = next_point
                print(f"   📍 候选点: u_con={u_con:.6f}, u_sr={u_sr:.0f}, sd_con={sd_con:.6f}, sd_sr={sd_sr:.0f}")
            except Exception as e:
                print(f"   ⚠️ 生成候选点失败: {e}")
                continue
            
            # 并行运行该点n_runs_per_point次
            print(f"   🧵 启动 {n_cores_bayes} 个进程并行运行该点 {n_runs_per_point} 次...")
            bayes_tasks = []
            for run_idx in range(n_runs_per_point):
                bayes_tasks.append((u_con, u_sr, sd_con, sd_sr, self.netlogo_path, self.nlogo_file, 
                                  self.lottery_type, 1800))
            
            bayes_results = self.run_batch_simulations_parallel(bayes_tasks, n_jobs=n_cores_bayes)
            
            # 处理结果
            run_losses = []
            run_stats_list = []
            
            for run_idx, (_, _, _, _, sales_series) in enumerate(bayes_results):
                if sales_series is not None:
                    stats_result = self.calculate_statistics(sales_series)
                    loss_value = self.calculate_loss(stats_result, weights)
                    run_losses.append(loss_value)
                    run_stats_list.append(stats_result)
                    
                    # 记录每次运行
                    record = {
                        'Iteration_Label': f'BayesIter{iteration+1}-Run{run_idx+1}',
                        'u_con': u_con,
                        'u_sr': u_sr,
                        'sd_con': sd_con,
                        'sd_sr': sd_sr,
                        'Total Sales': stats_result['total_sales'],
                        'Std Dev': stats_result['std_dev'],
                        'Skewness': stats_result['skewness'],
                        'Kurtosis': stats_result['kurtosis'],
                        'Loss': loss_value
                    }
                    all_records.append(record)
                    print(f"      Run {run_idx+1}: Loss={loss_value:.6f}")
            
            if len(run_losses) > 0:
                # 计算平均值
                avg_loss = np.mean(run_losses)
                avg_stats = {
                    'total_sales': np.mean([s['total_sales'] for s in run_stats_list]),
                    'std_dev': np.mean([s['std_dev'] for s in run_stats_list]),
                    'skewness': np.mean([s['skewness'] for s in run_stats_list]),
                    'kurtosis': np.mean([s['kurtosis'] for s in run_stats_list])
                }
                
                # 添加到贝叶斯优化数据
                params = [u_con, u_sr, sd_con, sd_sr]
                evaluated_params.append(params)
                evaluated_losses.append(avg_loss)
                evaluated_stats.append(avg_stats)
                
                print(f"   ✅ 平均Loss: {avg_loss:.6f} (成功: {len(run_losses)}/{n_runs_per_point})")
                
                # 实时保存
                df = pd.DataFrame(all_records)
                df.to_csv(self.history_filename, index=False)
            else:
                print(f"   ❌ 所有运行都失败")
        
        # ===== 第3阶段：保存最终结果 =====
        print(f"\n{'='*80}")
        print(f"📍 第3阶段：保存最终结果")
        print(f"{'='*80}")
        
        # 保存完整历史记录
        df = pd.DataFrame(all_records)
        df.to_csv(self.history_filename, index=False)
        print(f"💾 完整历史记录已保存到: {self.history_filename}")
        
        # 创建并保存去重平均数据
        df_averaged = self._create_averaged_dataset(df)
        df_averaged.to_csv(self.data_filename, index=False)
        print(f"💾 去重平均数据已保存到: {self.data_filename}")
        
        # 获取Top 5结果
        top5_df = df_averaged.sort_values('Loss').head(5).reset_index(drop=True)
        top5_df.to_csv(self.top5_filename, index=False)
        print(f"💾 Top 5结果已保存到: {self.top5_filename}")
        
        # 显示Top 5结果
        print(f"\n{'='*80}")
        print(f"🏆 Top 5 最优参数组合:")
        print(f"{'='*80}")
        
        for idx in range(len(top5_df)):
            row = top5_df.iloc[idx]
            print(f"\n   排名 #{idx+1}")
            print(f"   {'─'*76}")
            print(f"   参数组合:")
            print(f"      u_con   = {row['u_con']:.6f}")
            print(f"      u_sr    = {row['u_sr']:.0f}")
            print(f"      sd_con  = {row['sd_con']:.6f}")
            print(f"      sd_sr   = {row['sd_sr']:.0f}")
            print(f"   统计量均值:")
            print(f"      Total Sales = {row['Total Sales']:.4e}")
            print(f"      Std Dev     = {row['Std Dev']:.4e}")
            print(f"      Skewness    = {row['Skewness']:.4f}")
            print(f"      Kurtosis    = {row['Kurtosis']:.4f}")
            print(f"   Loss均值 = {row['Loss']:.6f}")
        
        print(f"\n{'='*80}")
        print(f"✅ 贝叶斯优化完成！")
        print(f"   总记录数: {len(df)}")
        print(f"   唯一参数组合数: {len(df_averaged)}")
        print(f"   全局最优Loss: {df_averaged['Loss'].min():.6f}")
        print(f"{'='*80}\n")
        
        return df_averaged
    
    def _create_averaged_dataset(self, df):
        """创建去重平均数据集"""
        param_columns = ['u_con', 'u_sr', 'sd_con', 'sd_sr']
        numeric_columns = ['Total Sales', 'Std Dev', 'Skewness', 'Kurtosis', 'Loss']
        
        grouped = df.groupby(param_columns)
        averaged_records = []
        
        for group_key, group_data in grouped:
            params = dict(zip(param_columns, group_key))
            averaged_record = params.copy()
            
            for col in numeric_columns:
                if col in group_data.columns:
                    averaged_record[col] = group_data[col].mean()
                else:
                    averaged_record[col] = 0.0
            
            if 'Iteration_Label' in group_data.columns:
                averaged_record['Iteration_Label'] = group_data['Iteration_Label'].iloc[0]
            else:
                averaged_record['Iteration_Label'] = f"Combined-{len(averaged_records)+1}"
            
            averaged_records.append(averaged_record)
        
        result_df = pd.DataFrame(averaged_records)
        expected_columns = ['Iteration_Label'] + param_columns + numeric_columns
        if all(col in result_df.columns for col in expected_columns):
            result_df = result_df[expected_columns]
        
        return result_df


# ===== 主程序 (贝叶斯优化模式) =====
def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 当前工作目录: {os.getcwd()}")

    # 从 CONFIG 读取参数
    NETLOGO_PATH = CONFIG['netlogo_path']
    NLOGO_FILE = CONFIG['nlogo_file']
    LOTTERY_TYPE = CONFIG['lottery_type']
    MAX_CORES_ALLOWED = CONFIG['max_cores_allowed']

    print(f"\n验证路径...")
    print(f"   NetLogo 路径: {NETLOGO_PATH} [{'存在' if os.path.exists(NETLOGO_PATH) else '不存在'}]")
    print(f"   模型文件: {NLOGO_FILE} [{'存在' if os.path.exists(NLOGO_FILE) else '不存在'}]")

    if not os.path.exists(NETLOGO_PATH) or not os.path.exists(NLOGO_FILE):
        print(f"路径不存在，请检查配置。")
        exit(1)

    try:
        # 创建优化器实例
        optimizer = BayesianOptimizerTest(
            netlogo_path=NETLOGO_PATH,
            nlogo_file=NLOGO_FILE,
            lottery_type=LOTTERY_TYPE,
            max_allowed_cores=MAX_CORES_ALLOWED
        )

        # 运行贝叶斯优化
        results_df = optimizer.run_bayesian_optimization(
            n_lhs_points=CONFIG['n_lhs_points'],
            n_iterations=CONFIG['n_iterations'],
            n_runs_per_point=CONFIG['n_runs_per_point'],
            n_cores_lhs=CONFIG['n_cores_lhs'],
            n_cores_bayes=CONFIG['n_cores_bayes'],
            weights=CONFIG['weights']
        )

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()