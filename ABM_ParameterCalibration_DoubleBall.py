# Powerball贝叶斯优化脚本
# 参数定义说明：
# u_con: 消费效用参数，影响代理人对一般消费品的效用评估
# u_sr: 主观阻力参数(subjective resistance)，代表代理人购买彩票时的主观阻力水平
# sd_con: 消费效用的标准差参数，反映消费效用的波动性
# sd_sr: 主观阻力的标准差参数，反映主观阻力的波动性
#
# 贝叶斯优化策略：
# - 初始阶段：使用拉丁超立方采样(LHS)生成初始点，每个点运行指定次数取平均
# - 迭代优化：每次选择指定数量的最有潜力的点（基于Expected Improvement），各运行指定次数取平均
# - 输出Top 5最优参数组合及其统计量

# =============================================================================
# 【配置参数】- 修改这里以调整优化设置
# =============================================================================
CONFIG = {
    # --- 文件路径 ---
    'netlogo_path': r"D:/netlogo",
    'nlogo_file': r"D:/BaiduSyncdisk/1DoctorStudy/1Doctor thesis/ABM-LOTTERY/normal20260203distribution_v2_sensitivity.nlogo",

    # --- 彩票类型 ("PB"=Powerball, "DCB"=双色球的缩写) ---
    'lottery_type': "PB",

    # --- 并行与随机 ---
    'max_cores_allowed': 12,      # 最大并行核心数
    'random_seed': 42,             # 随机种子

    # --- 贝叶斯优化核心参数 ---
    'n_initial': 12,               # LHS 初始打点数
    'n_iterations': 100,          # 贝叶斯迭代次数
    'points_per_iter': 1,         # 每次迭代评估的候选点数
    'num_runs_per_point': 3,      # 每个参数点重复仿真次数

    # --- 损失函数权重 (total_sales, std_dev, skewness, kurtosis) ---
    'weights': {
        'total_sales': 0.4,
        'std_dev': 0.2,
        'skewness': 0.2,
        'kurtosis': 0.2
    }
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
from joblib import Parallel, delayed
import warnings
warnings.filterwarnings('ignore')


# ===== 辅助函数：用于在子进程中运行单次仿真 =====
def _run_simulation_worker(args):
    """
    用于并行执行的辅助函数
    args: 包含 (u_con, u_sr, sd_con, sd_sr, netlogo_path, nlogo_file, lottery_type, num_periods, seed) 的元组
    """
    u_con, u_sr, sd_con, sd_sr, netlogo_path, nlogo_file, lottery_type, num_periods, seed = args

    print(f"   🔄 [{datetime.now().strftime('%H:%M:%S')}] 子进程仿真 (u_con={u_con:.3f}, u_sr={u_sr:.0f}, sd_con={sd_con:.3f}, sd_sr={sd_sr:.0f}, seed={seed})")

    netlogo_link = None
    try:
        # 初始化 NetLogo
        netlogo_link = pynetlogo.NetLogoLink(netlogo_home=netlogo_path, gui=False)
        netlogo_link.load_model(nlogo_file)

        # 设置随机种子以控制波动
        netlogo_link.command(f'random-seed {seed}')
        
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
        print(f"   ⚠️ 仿真出错 (u_con={u_con:.3f}, u_sr={u_sr:.0f}, sd_con={sd_con:.3f}, sd_sr={sd_sr:.0f}): {e}")
        if netlogo_link is not None:
            try:
                netlogo_link.kill_workspace()
            except:
                pass
        return u_con, u_sr, sd_con, sd_sr, None


# ===== 核心类定义 =====
class BayesianOptimizer:
    def __init__(self, netlogo_path, nlogo_file, lottery_type="PB", max_allowed_cores=12, random_seed=42):
        """
        贝叶斯优化器 - Powerball专用版本
        :param netlogo_path: NetLogo 安装路径
        :param nlogo_file: NetLogo 模型文件路径
        :param lottery_type: 彩票类型 ("DCB" 或 "PB")
        :param max_allowed_cores: 允许使用的最大核心数
        :param random_seed: 随机种子
        """
        self.netlogo_path = netlogo_path
        self.nlogo_file = nlogo_file
        self.lottery_type = lottery_type
        self.max_allowed_cores = max_allowed_cores
        self.random_seed = random_seed
        np.random.seed(random_seed)

        # --- 参数范围定义 (PB专用) ---
        U_SR_UPPER_BOUND = 70000
        SD_SR_UPPER_BOUND = U_SR_UPPER_BOUND / 1.0
        U_CON_UPPER_BOUND = 1.0
        SD_CON_UPPER_BOUND = U_CON_UPPER_BOUND / 1.0

        if self.lottery_type == "DCB":
            self.target_stats = {
                'total_sales': 6.47e11,
                'std_dev': 4.00e7,
                'skewness': 0.56,
                'kurtosis': 5.10
            }
            self.param_ranges = {
                'u_con': [0.000001, U_CON_UPPER_BOUND],
                'u_sr': [0.0000001, U_SR_UPPER_BOUND],
                'sd_con': [0.00000025, SD_CON_UPPER_BOUND],
                'sd_sr': [0.0000001, SD_SR_UPPER_BOUND]
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
                'u_sr': [0.0000001, U_SR_UPPER_BOUND],
                'sd_con': [0.00000025, SD_CON_UPPER_BOUND],
                'sd_sr': [0.0000001, SD_SR_UPPER_BOUND]
            }

        # 定义搜索空间 (4个参数)
        self.dimensions = [
            Real(self.param_ranges['u_con'][0], self.param_ranges['u_con'][1], name='u_con'),
            Real(self.param_ranges['u_sr'][0], self.param_ranges['u_sr'][1], name='u_sr'),
            Real(self.param_ranges['sd_con'][0], self.param_ranges['sd_con'][1], name='sd_con'),
            Real(self.param_ranges['sd_sr'][0], self.param_ranges['sd_sr'][1], name='sd_sr')
        ]

        # 用于存储历史数据
        self.all_params = []  # 所有测试的参数
        self.all_losses = []  # 对应的loss值
        self.all_stats = []   # 对应的统计量
        self.best_loss_history = []  # 每次迭代的最优loss
        self.iteration_labels = []  # 记录每个点的迭代标签（如"LHS-1", "Iter1-1"）
        
        # CSV数据记录文件
        self.csv_filename = f"bayesian_optimization_data_{self.lottery_type}.csv"
        self._initialize_csv()

    def _initialize_csv(self):
        """
        初始化CSV数据记录文件，创建表头
        """
        # 检查文件是否已存在
        if os.path.exists(self.csv_filename):
            print(f"   ⚠️ 发现已存在的数据记录文件: {self.csv_filename}")
            response = input("   是否覆盖？(y/n): ")
            if response.lower() != 'y':
                # 生成带时间戳的新文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.csv_filename = f"bayesian_optimization_data_{self.lottery_type}_{timestamp}.csv"
                print(f"   ✅ 使用新文件名: {self.csv_filename}")
        
        # 创建表头
        header = ['Iteration_Label', 'u_con', 'u_sr', 'sd_con', 'sd_sr', 
                  'Total Sales', 'Std Dev', 'Skewness', 'Kurtosis', 'Loss']
        df = pd.DataFrame(columns=header)
        df.to_csv(self.csv_filename, index=False)
        print(f"   📝 数据记录文件已初始化: {self.csv_filename}")
    
    def _save_point_to_csv(self, params, stats, loss, iteration_label):
        """
        将单个评估点保存到CSV文件
        :param params: [u_con, u_sr, sd_con, sd_sr]
        :param stats: 统计量字典
        :param loss: Loss值
        :param iteration_label: 迭代标签（如"LHS-1", "Iter1-1"）
        """
        # 准备数据行
        data_row = {
            'Iteration_Label': iteration_label,
            'u_con': params[0],
            'u_sr': params[1],
            'sd_con': params[2],
            'sd_sr': params[3],
            'Total Sales': stats['total_sales'],
            'Std Dev': stats['std_dev'],
            'Skewness': stats['skewness'],
            'Kurtosis': stats['kurtosis'],
            'Loss': loss
        }
        
        # 追加到CSV文件
        df = pd.DataFrame([data_row])
        df.to_csv(self.csv_filename, mode='a', header=False, index=False)
        
    def generate_lhs_initial_points(self, n_points=12):
        """
        使用拉丁超立方采样生成初始点
        :param n_points: 生成的点数
        :return: 初始参数点列表
        """
        print(f"\n🎲 [{datetime.now().strftime('%H:%M:%S')}] 使用拉丁超立方采样生成{n_points}个初始点...")
        
        # 创建LHS采样器
        sampler = qmc.LatinHypercube(d=4, seed=self.random_seed)
        samples = sampler.random(n=n_points)
        
        # 缩放到实际参数范围
        initial_points = []
        for sample in samples:
            u_con = self.param_ranges['u_con'][0] + sample[0] * (self.param_ranges['u_con'][1] - self.param_ranges['u_con'][0])
            u_sr = self.param_ranges['u_sr'][0] + sample[1] * (self.param_ranges['u_sr'][1] - self.param_ranges['u_sr'][0])
            sd_con = self.param_ranges['sd_con'][0] + sample[2] * (self.param_ranges['sd_con'][1] - self.param_ranges['sd_con'][0])
            sd_sr = self.param_ranges['sd_sr'][0] + sample[3] * (self.param_ranges['sd_sr'][1] - self.param_ranges['sd_sr'][0])
            initial_points.append([u_con, u_sr, sd_con, sd_sr])
        
        print(f"   ✅ 初始点生成完成")
        return initial_points

    def calculate_statistics(self, sales_series):
        """计算统计量"""
        if sales_series is None or len(sales_series) == 0:
            return {'total_sales': 0.0, 'std_dev': 0.0, 'skewness': 0.0, 'kurtosis': 0.0}

        sales_array = np.asarray(sales_series)
        if len(sales_array) == 0:
            return {'total_sales': 0.0, 'std_dev': 0.0, 'skewness': 0.0, 'kurtosis': 0.0}

        if np.all(sales_array == sales_array[0]):
            return {
                'total_sales': float(np.sum(sales_array)),
                'std_dev': 0.0,
                'skewness': 0.0,
                'kurtosis': 0.0
            }

        stats_result = {
            'total_sales': float(np.sum(sales_array)),
            'std_dev': float(np.std(sales_array)),
            'skewness': float(stats.skew(sales_array)),
            'kurtosis': float(stats.kurtosis(sales_array) + 3)
        }
        return stats_result

    def calculate_loss(self, simulated_stats, weights):
        """
        计算损失函数
        :param simulated_stats: 仿真得到的统计量字典
        :param weights: 权重字典
        :return: 损失函数值
        """
        total_loss = 0
        for key in ['total_sales', 'std_dev', 'skewness', 'kurtosis']:
            sim_val = np.asarray(simulated_stats[key]).item() if isinstance(simulated_stats[key], (list, np.ndarray)) else simulated_stats[key]
            target_val = self.target_stats[key]

            if target_val != 0:
                rel_error = abs(sim_val - target_val) / abs(target_val)
                term = 1 - np.exp(-rel_error)
            else:
                term = abs(sim_val)

            weighted_term = weights[key] * term
            total_loss += weighted_term

        return float(total_loss)

    def evaluate_point(self, params, weights, num_runs):
        """
        评估单个参数点（运行多次取平均）
        :param params: [u_con, u_sr, sd_con, sd_sr]
        :param weights: 损失权重
        :param num_runs: 重复运行次数
        :return: 平均loss和统计量
        """
        u_con, u_sr, sd_con, sd_sr = params
        
        # 准备多次运行任务（每次使用不同的随机种子）
        tasks = []
        base_seed = self.random_seed + len(self.all_params) * 100
        for i in range(num_runs):
            seed = base_seed + i
            tasks.append((u_con, u_sr, sd_con, sd_sr, self.netlogo_path, self.nlogo_file, 
                         self.lottery_type, 1800, seed))
        
        # 并行执行
        results = Parallel(n_jobs=min(num_runs, self.max_allowed_cores), backend='multiprocessing')(
            delayed(_run_simulation_worker)(task) for task in tasks
        )
        
        # 收集结果
        losses = []
        all_stats = []
        for _, _, _, _, sales_series in results:
            if sales_series is not None:
                simulated_stats = self.calculate_statistics(sales_series)
                loss = self.calculate_loss(simulated_stats, weights)
                losses.append(loss)
                all_stats.append(simulated_stats)
        
        if len(losses) == 0:
            return None, None
        
        # 计算平均loss和平均统计量
        avg_loss = np.mean(losses)
        avg_stats = {
            'total_sales': np.mean([s['total_sales'] for s in all_stats]),
            'std_dev': np.mean([s['std_dev'] for s in all_stats]),
            'skewness': np.mean([s['skewness'] for s in all_stats]),
            'kurtosis': np.mean([s['kurtosis'] for s in all_stats])
        }
        
        return avg_loss, avg_stats

    def run_bayesian_optimization(self, n_initial=12, n_iterations=50, points_per_iter=1, weights=None):
        """
        运行完整的贝叶斯优化流程
        :param n_initial: 初始采样点数
        :param n_iterations: 迭代次数
        :param points_per_iter: 每次迭代选择的点数
        :param weights: 损失权重
        :return: 优化结果
        """
        if weights is None:
            weights = {'total_sales': 0.4, 'std_dev': 0.2, 'skewness': 0.2, 'kurtosis': 0.2}
        
        print(f"\n{'='*80}")
        print(f"🚀 开始贝叶斯优化 - {self.lottery_type}")
        print(f"{'='*80}")
        print(f"   初始点数: {n_initial}")
        print(f"   迭代次数: {n_iterations}")
        print(f"   每次迭代点数: {points_per_iter}")
        print(f"   每点运行次数: {CONFIG['num_runs_per_point']}")
        print(f"   总仿真次数: {(n_initial + n_iterations * points_per_iter) * CONFIG['num_runs_per_point']}")
        print(f"{'='*80}\n")
        
        # ===== 第1阶段：初始化采样 =====
        print(f"\n{'='*80}")
        print(f"📍 第1阶段：初始化采样（LHS）")
        print(f"{'='*80}")
        
        initial_points = self.generate_lhs_initial_points(n_initial)
        
        print(f"\n   开始评估{n_initial}个初始点（每点运行{CONFIG['num_runs_per_point']}次）...")
        for i, params in enumerate(initial_points):
            iteration_label = f"LHS-{i+1}"
            print(f"\n   ▶ 初始点 {i+1}/{n_initial} [{iteration_label}]: u_con={params[0]:.6f}, u_sr={params[1]:.0f}, sd_con={params[2]:.6f}, sd_sr={params[3]:.0f}")
            avg_loss, avg_stats = self.evaluate_point(params, weights, num_runs=CONFIG['num_runs_per_point'])
            
            if avg_loss is not None:
                self.all_params.append(params)
                self.all_losses.append(avg_loss)
                self.all_stats.append(avg_stats)
                self.iteration_labels.append(iteration_label)
                
                # 实时保存到CSV
                self._save_point_to_csv(params, avg_stats, avg_loss, iteration_label)
                
                print(f"      ✅ 平均Loss: {avg_loss:.6f}")
                print(f"      💾 已保存到 {self.csv_filename}")
            else:
                print(f"      ❌ 评估失败")
        
        if len(self.all_losses) > 0:
            current_best = min(self.all_losses)
            self.best_loss_history.append(current_best)
            print(f"\n   📊 初始化阶段完成，当前最优Loss: {current_best:.6f}")
        
        # ===== 第2阶段：贝叶斯优化迭代 =====
        print(f"\n{'='*80}")
        print(f"📍 第2阶段：贝叶斯优化迭代")
        print(f"{'='*80}")
        
        for iteration in range(n_iterations):
            print(f"\n{'─'*80}")
            print(f"🔄 迭代 {iteration+1}/{n_iterations}")
            print(f"{'─'*80}")
            
            if len(self.all_params) < 2:
                print(f"   ⚠️ 数据不足，无法继续优化")
                break
            
            # 使用gp_minimize选择下一批最有潜力的点
            def objective_wrapper(x):
                """包装函数用于gp_minimize"""
                return self.evaluate_point(x, weights, num_runs=1)[0]
            
            # 基于已有数据拟合高斯过程
            X = np.array(self.all_params)
            y = np.array(self.all_losses)
            
            # 使用Expected Improvement选择新点
            from skopt import Optimizer
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
                random_state=self.random_seed + iteration
            )
            
            # 告诉优化器已有的数据
            opt.tell(X.tolist(), y.tolist())
            
            # 选择下一批点
            next_points = []
            for i in range(points_per_iter):
                next_point = opt.ask()
                next_points.append(next_point)
            
            # 评估这批点
            print(f"\n   开始评估{points_per_iter}个新点（每点运行{CONFIG['num_runs_per_point']}次）...")
            for i, params in enumerate(next_points):
                iteration_label = f"Iter{iteration+1}-{i+1}"
                print(f"\n   ▶ 新点 {i+1}/{points_per_iter} [{iteration_label}]: u_con={params[0]:.6f}, u_sr={params[1]:.0f}, sd_con={params[2]:.6f}, sd_sr={params[3]:.0f}")
                avg_loss, avg_stats = self.evaluate_point(params, weights, num_runs=CONFIG['num_runs_per_point'])
                
                if avg_loss is not None:
                    self.all_params.append(params)
                    self.all_losses.append(avg_loss)
                    self.all_stats.append(avg_stats)
                    self.iteration_labels.append(iteration_label)
                    
                    # 实时保存到CSV
                    self._save_point_to_csv(params, avg_stats, avg_loss, iteration_label)
                    
                    print(f"      ✅ 平均Loss: {avg_loss:.6f}")
                    print(f"      💾 已保存到 {self.csv_filename}")
                else:
                    print(f"      ❌ 评估失败")
            
            # 更新最优记录
            if len(self.all_losses) > 0:
                current_best = min(self.all_losses)
                self.best_loss_history.append(current_best)
                print(f"\n   📊 迭代{iteration+1}完成，当前最优Loss: {current_best:.6f}")
                print(f"      总评估点数: {len(self.all_params)}")
        
        # ===== 第3阶段：输出结果 =====
        self.print_results()
        
        # ===== 生成数据统计报告 =====
        self.generate_data_summary()
        
        return self.get_top_results(top_k=5)

    def generate_data_summary(self):
        """生成数据记录统计报告"""
        print(f"\n{'='*80}")
        print(f"📊 数据记录统计报告")
        print(f"{'='*80}")
        
        # 读取完整的CSV数据
        if not os.path.exists(self.csv_filename):
            print(f"   ❌ 数据文件不存在: {self.csv_filename}")
            return
        
        df = pd.read_csv(self.csv_filename)
        
        print(f"\n📁 数据文件: {self.csv_filename}")
        print(f"   总记录数: {len(df)}")
        print(f"   文件大小: {os.path.getsize(self.csv_filename) / 1024:.2f} KB")
        
        # 按阶段统计
        lhs_count = len(df[df['Iteration_Label'].str.startswith('LHS')])
        iter_count = len(df[df['Iteration_Label'].str.startswith('Iter')])
        
        print(f"\n📈 数据分布:")
        print(f"   LHS初始采样: {lhs_count} 个点")
        print(f"   贝叶斯优化迭代: {iter_count} 个点")
        
        # Loss统计
        print(f"\n📉 Loss统计:")
        print(f"   最小Loss: {df['Loss'].min():.6f}")
        print(f"   最大Loss: {df['Loss'].max():.6f}")
        print(f"   平均Loss: {df['Loss'].mean():.6f}")
        print(f"   标准差: {df['Loss'].std():.6f}")
        
        # 参数范围
        print(f"\n🔍 参数探索范围:")
        for param in ['u_con', 'u_sr', 'sd_con', 'sd_sr']:
            print(f"   {param:8s}: [{df[param].min():.6f}, {df[param].max():.6f}]")
        
        # 最优点信息
        best_idx = df['Loss'].idxmin()
        best_row = df.iloc[best_idx]
        print(f"\n🏆 最优点详情:")
        print(f"   迭代标签: {best_row['Iteration_Label']}")
        print(f"   u_con:  {best_row['u_con']:.6f}")
        print(f"   u_sr:   {best_row['u_sr']:.0f}")
        print(f"   sd_con: {best_row['sd_con']:.6f}")
        print(f"   sd_sr:  {best_row['sd_sr']:.0f}")
        print(f"   Loss:   {best_row['Loss']:.6f}")
        
        print(f"\n{'='*80}")
        print(f"✅ 所有数据已完整记录到: {self.csv_filename}")
        print(f"{'='*80}\n")
    
    def get_top_results(self, top_k=5):
        """
        获取Top K最优结果
        :param top_k: 返回前k个最优结果
        :return: DataFrame包含最优参数和统计量
        """
        if len(self.all_losses) == 0:
            return None
        
        # 按loss排序
        sorted_indices = np.argsort(self.all_losses)[:top_k]
        
        top_results = []
        for idx in sorted_indices:
            result = {
                'u_con': self.all_params[idx][0],
                'u_sr': self.all_params[idx][1],
                'sd_con': self.all_params[idx][2],
                'sd_sr': self.all_params[idx][3],
                'Total Sales': self.all_stats[idx]['total_sales'],
                'Std Dev': self.all_stats[idx]['std_dev'],
                'Skewness': self.all_stats[idx]['skewness'],
                'Kurtosis': self.all_stats[idx]['kurtosis'],
                'Loss': self.all_losses[idx]
            }
            top_results.append(result)
        
        return pd.DataFrame(top_results)

    def print_results(self):
        """打印优化结果"""
        print(f"\n{'='*80}")
        print(f"🏆 贝叶斯优化完成")
        print(f"{'='*80}")
        
        if len(self.all_losses) == 0:
            print("   ❌ 没有成功评估的点")
            return
        
        # Top 5结果
        top_5 = self.get_top_results(top_k=5)
        
        print(f"\n📊 Top 5 最优参数组合:\n")
        for i, row in top_5.iterrows():
            print(f"   {'─'*76}")
            print(f"   排名 #{i+1}")
            print(f"   {'─'*76}")
            print(f"   参数组合:")
            print(f"      u_con   = {row['u_con']:.6f}")
            print(f"      u_sr    = {row['u_sr']:.0f}")
            print(f"      sd_con  = {row['sd_con']:.6f}")
            print(f"      sd_sr   = {row['sd_sr']:.0f}")
            print(f"   目标统计量:")
            print(f"      Total Sales = {row['Total Sales']:.2e}")
            print(f"      Std Dev     = {row['Std Dev']:.2e}")
            print(f"      Skewness    = {row['Skewness']:.4f}")
            print(f"      Kurtosis    = {row['Kurtosis']:.4f}")
            print(f"   Loss = {row['Loss']:.6f}")
        
        print(f"\n   {'='*76}")
        print(f"   总评估点数: {len(self.all_params)}")
        print(f"   全局最优Loss: {min(self.all_losses):.6f}")
        print(f"   {'='*76}\n")
        
        # 保存到CSV
        output_file = f"bayesian_optimization_top5_{self.lottery_type}.csv"
        top_5.to_csv(output_file, index=False)
        print(f"   💾 Top 5结果已保存到: {output_file}")
        
        # 保存完整历史
        full_results = self.get_all_results()
        history_file = f"bayesian_optimization_history_{self.lottery_type}.csv"
        full_results.to_csv(history_file, index=False)
        print(f"   💾 完整历史已保存到: {history_file}")

    def get_all_results(self):
        """获取所有评估结果"""
        all_results = []
        for i in range(len(self.all_losses)):
            result = {
                'u_con': self.all_params[i][0],
                'u_sr': self.all_params[i][1],
                'sd_con': self.all_params[i][2],
                'sd_sr': self.all_params[i][3],
                'Total Sales': self.all_stats[i]['total_sales'],
                'Std Dev': self.all_stats[i]['std_dev'],
                'Skewness': self.all_stats[i]['skewness'],
                'Kurtosis': self.all_stats[i]['kurtosis'],
                'Loss': self.all_losses[i]
            }
            all_results.append(result)
        
        return pd.DataFrame(all_results)


# ===== 主程序 =====
def main():
    print(f"📍 [{datetime.now().strftime('%H:%M:%S')}] 当前工作目录: {os.getcwd()}")

    # 从 CONFIG 读取参数
    NETLOGO_PATH = CONFIG['netlogo_path']
    NLOGO_FILE = CONFIG['nlogo_file']
    LOTTERY_TYPE = CONFIG['lottery_type']
    MAX_CORES_ALLOWED = CONFIG['max_cores_allowed']
    RANDOM_SEED = CONFIG['random_seed']

    print(f"\n🔍 验证路径...")
    print(f"   NetLogo 路径: {NETLOGO_PATH} [{'✅' if os.path.exists(NETLOGO_PATH) else '❌'}]")
    print(f"   模型文件: {NLOGO_FILE} [{'✅' if os.path.exists(NLOGO_FILE) else '❌'}]")

    if not os.path.exists(NETLOGO_PATH) or not os.path.exists(NLOGO_FILE):
        print(f"❌ 路径不存在，请检查配置。")
        exit(1)

    try:
        # 创建优化器实例
        optimizer = BayesianOptimizer(
            netlogo_path=NETLOGO_PATH,
            nlogo_file=NLOGO_FILE,
            lottery_type=LOTTERY_TYPE,
            max_allowed_cores=MAX_CORES_ALLOWED,
            random_seed=RANDOM_SEED
        )

        # 运行贝叶斯优化
        top_results = optimizer.run_bayesian_optimization(
            n_initial=CONFIG['n_initial'],
            n_iterations=CONFIG['n_iterations'],
            points_per_iter=CONFIG['points_per_iter'],
            weights=CONFIG['weights']
        )

        print("\n🎉 贝叶斯优化流程完成!")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
