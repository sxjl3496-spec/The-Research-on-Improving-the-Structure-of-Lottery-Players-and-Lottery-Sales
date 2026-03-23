"""
绘图模块
"""

from .convergence_plot import (
    plot_convergence_from_results,
    plot_convergence_with_history,
    plot_multi_metric_convergence
)

from .cap_sensitivity_plots import (
    plot_cap_sensitivity_main,
    plot_cap_sensitivity_detailed
)

from .probability_sensitivity_plots import (
    plot_probability_sensitivity_main,
    plot_probability_sensitivity_detailed,
    plot_lottery_rules_heatmap
)

from .joint_sensitivity_plots import (
    plot_joint_sensitivity_3d,
    plot_joint_sensitivity_contour,
    plot_parameter_tradeoff,
    plot_pareto_frontier_joint
)

from .appendix_plots import (
    plot_pareto_frontier,
    plot_participation_heatmap,
    plot_per_capita_purchase,
    plot_correlation_heatmap,
    plot_sales_structure_stacked,
    plot_expected_improvement,
    generate_all_appendix_plots
)

__all__ = [
    'plot_convergence_from_results',
    'plot_convergence_with_history',
    'plot_multi_metric_convergence',
    'plot_cap_sensitivity_main',
    'plot_cap_sensitivity_detailed',
    'plot_probability_sensitivity_main',
    'plot_probability_sensitivity_detailed',
    'plot_lottery_rules_heatmap',
    'plot_joint_sensitivity_3d',
    'plot_joint_sensitivity_contour',
    'plot_parameter_tradeoff',
    'plot_pareto_frontier_joint',
    'plot_pareto_frontier',
    'plot_participation_heatmap',
    'plot_per_capita_purchase',
    'plot_correlation_heatmap',
    'plot_sales_structure_stacked',
    'plot_expected_improvement',
    'generate_all_appendix_plots',
]
