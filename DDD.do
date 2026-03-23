*************************************** 第一步：数据导入 **************************
clear all
set more off
use Dateset.dta, clear



// 7. 生成对数变量
gen perspot = spotlottery/popula
gen perwel = wellottery/popula
foreach var of varlist perspot perwel totallottery wellottery spotlottery pergdp ///
 perrgdp peredu umemploy houseprice popula interest{
    gen ln`var' = log(`var')
}

// 8. 定义控制变量集
global lnxlist "lnpergdp worldcup eurcup lnumemploy lnpopula lnperedu lninterest lnhouseprice finacris capping"
global xlist "pergdp worldcup eurcup umemploy popula peredu interest finacris capping"
global lnzlist "lnpergdp lnumemploy lnpopula lnperedu lnhouseprice"
tabstat lnwellottery lnspotlottery lnpergdp worldcup eurcup lnumemploy lnpopula ///
lnperedu lninterest lnhouseprice finacris capping, stats(count mean sd p50 min max) columns(statistics)
// 9. 声明面板数据结构
xtset id year, delta(1)

// 保存基础数据
save "base_data.dta", replace

di "==================== 基础数据处理完成 ===================="

di "==================== 开始平行趋势检验 ===================="

// 准备数据
rename spotlottery sales_spot
rename wellottery sales_well
save "temp_pt.dta", replace

reshape long sales_, i(id year) j(lottery_type) string

// 创建DDD核心变量
gen treat_type = (lottery_type == "spot")
gen post = (year >= 2015)
gen ln_per_sales = .
replace ln_per_sales = lnperspot if lottery_type == "spot"
replace ln_per_sales = lnperwel if lottery_type == "well"

// 相对时间变量
gen rel_year = year - 2015
gen rel_year_pos = rel_year + 9
char rel_year_pos[omit] 8

// 动态DDD回归
xtreg ln_per_sales i.treat_type##i.treat_income##i.rel_year_pos ///
       $lnzlist, fe vce(cluster id)
estimates store ddd_dynamic_pt

// 平行趋势假设检验（政策前时期）
testparm i.treat_type#i.treat_income#i(1/7).rel_year_pos

// 保存结果到全局宏（使用更可靠的方法）
global pt_F = r(F)
global pt_pvalue = r(p)
global pt_pvalue_str : di %6.4f r(p)  // 使用: di格式
global pt_result = cond(r(p) > 0.1, "通过", "未通过")

// ============= 在restore之前输出结果 =============
di ""
di "=================================================="
di "平行趋势检验结果：$pt_result"
di "P值 = $pt_pvalue_str, F统计量 = " %6.3f $pt_F

if $pt_pvalue > 0.1 {
    di "结论：满足平行趋势假设，DDD估计可信"
}
else {
    di "⚠ 注意：平行趋势假设可能不成立"
}
di "=================================================="
di ""

// 提取系数并绘图
preserve
matrix b = e(b)
matrix V = e(V)
clear
set obs 18
gen year = 2006 + _n
gen estimate = .
gen stderr = .
gen ci_lower = .
gen ci_upper = .

forvalues t = 1/18 {
    local var "1.treat_type#1.treat_income#`t'.rel_year_pos"
    capture matrix b_sub = b[1, "`var'"]
    if _rc == 0 {
        replace estimate = b_sub[1,1] in `t'
        matrix v_sub = V["`var'", "`var'"]
        replace stderr = sqrt(v_sub[1,1]) in `t'
        replace ci_lower = estimate - 1.96*stderr in `t'
        replace ci_upper = estimate + 1.96*stderr in `t'
    }
}
drop if missing(estimate)

twoway (scatter estimate year if year <= 2014, mcolor(blue) msymbol(O)) ///
       (scatter estimate year if year >= 2015, mcolor(red) msymbol(D)) ///
       (rcap ci_lower ci_upper year, lcolor(gray%50)) ///
       , xline(2014.5, lpattern(dash)) yline(0) ///
       xtitle("年份") ytitle("三重差分系数") ///
       title("平行趋势检验：体彩 vs 福彩") ///
       legend(order(1 "政策前" 2 "政策后")) ///
       xlabel(2007(2)2024, angle(45)) ///
       note("平行趋势检验结果：$pt_result (P值 = $pt_pvalue_str)")

graph export "parallel_trend_spot_vs_well.png", replace width(1200) height(800)
restore

// 恢复原始数据
use "temp_pt.dta", clear
erase "temp_pt.dta"

. ************************** 第四步：准备主回归数据（体彩 vs 福彩） **************************
. use "base_data.dta", clear

. rename spotlottery sales_spot
. rename wellottery sales_well

. gen lnsales_spot = log(sales_spot) if sales_spot > 0
. gen lnsales_well = log(sales_well) if sales_well > 0

. // 👇 在这里提前生成 sales_bet（需要 betting_ratio 已存在）
. gen sales_bet = sales_spot * betting_ratio

. 
. // 面板1：体彩
. preserve
. keep id year treat_income lnsales_spot $lnxlist sales_bet   // 👈 保留 sales_bet
. gen lottery_type = "spot"
. gen treat_type = 1
. gen post = (year >= 2015)
. rename lnsales_spot lnsales
. save "ddd_spot.dta", replace
. restore

. 
. // 面板2：福彩（福彩不需要 sales_bet，但为合并结构一致，可设为缺失或0）
. preserve
. keep id year treat_income lnsales_well $lnxlist
. gen lottery_type = "well"
. gen treat_type = 0
. gen post = (year >= 2015)
. rename lnsales_well lnsales
. gen sales_bet = .   // 或者 gen sales_bet = 0，根据你的研究设计
. save "ddd_well.dta", replace
. restore

. 
. // 合并
. use "ddd_spot.dta", clear
. append using "ddd_well.dta"
. save "main_panel.dta", replace


gen lnsales_bet = log(sales_bet) if sales_bet > 0
preserve
keep id year treat_income lnsales_bet $lnxlist
gen lottery_type = "bet"
gen treat_type = 1
gen post = (year >= 2015)
rename lnsales_bet lnsales
save "ddd_bet_for_robust.dta", replace
restore

di "==================== 主回归数据准备完成 ===================="

************************** 第五步：运行主回归模型（M1–M5） **************************
use "main_panel.dta", clear

// M1: 仅个体FE
xtreg lnsales treat_type treat_income post ///
       treat_type#treat_income treat_type#post treat_income#post ///
       treat_type#treat_income#post ///
       $lnxlist, fe robust
estimates store ddd_spot_m1

// M2: 仅时点FE
tab year, gen(year_dum)
drop year_dum1
reg lnsales treat_type treat_income post ///
    treat_type#treat_income treat_type#post treat_income#post ///
    treat_type#treat_income#post ///
    $lnxlist year_dum*, vce(cluster id)
estimates store ddd_spot_m2

// M3: 双向FE（基准）
xtreg lnsales treat_type treat_income post ///
       treat_type#treat_income treat_type#post treat_income#post ///
       treat_type#treat_income#post ///
       $lnxlist year_dum*, fe robust
estimates store ddd_spot_m3

// M4: 随机效应（RE）
xtreg lnsales treat_type treat_income post ///
       treat_type#treat_income treat_type#post treat_income#post ///
       treat_type#treat_income#post ///
       $lnxlist year_dum*, re robust
estimates store ddd_spot_m4

// M5: 双向FE + 无控制变量
xtreg lnsales treat_type treat_income post ///
       treat_type#treat_income treat_type#post treat_income#post ///
       treat_type#treat_income#post ///
       i.year, fe robust
estimates store ddd_spot_m5

di "==================== 主回归模型（M1–M5）完成 ===================="

************************** 第六步：稳健性检验（仅保留4项） **************************
use "base_data.dta", clear

rename spotlottery sales_spot
rename wellottery sales_well

// 重新生成对数销售额（虽然 robust_main 不直接用，但 keep 需要）
gen lnsales_spot = log(sales_spot) if sales_spot > 0
gen lnsales_well = log(sales_well) if sales_well > 0

// 构建稳健性数据集 —— 关键：保留 perrgdp
preserve
keep id year pronum treat_income lnsales_spot $lnxlist perrgdp   // ✅
gen lottery_type = "spot"
gen treat_type = 1
gen post = (year >= 2015)
rename lnsales_spot lnsales
save "robust_spot.dta", replace
restore

preserve
keep id year pronum treat_income lnsales_well $lnxlist perrgdp   // ✅
gen lottery_type = "well"
gen treat_type = 0
gen post = (year >= 2015)
rename lnsales_well lnsales
save "robust_well.dta", replace
restore

use "robust_spot.dta", clear
append using "robust_well.dta"
save "robust_main.dta", replace

// === 稳健性1：更换收入分组（四分位数） ===
use "robust_main.dta", clear
bysort year: egen p75_perrgdp = pctile(perrgdp), p(75)   // ✅ 现在 perrgdp 存在！
gen treat_income_new = (perrgdp >= p75_perrgdp) | (pronum == 13)

xtreg lnsales treat_type treat_income_new post ///
       treat_type#treat_income_new treat_type#post treat_income_new#post ///
       treat_type#treat_income_new#post ///
       $lnxlist i.year, fe robust
estimates store robust_income

// ... 其他稳健性保持不变 ...

// === 稳健性2：安慰剂检验（虚构2012年政策） ===
use "robust_main.dta", clear
gen post_placebo = (year >= 2012)

reghdfe lnsales treat_type##treat_income##post_placebo $lnxlist, ///
        absorb(id year) vce(cluster id)
estimates store robust_placebo

// ==============================
// 稳健性3：缩尾处理（Winsorizing）
// ==============================

// 首先确保安装 winsor2（如未安装）
capture which winsor2
if _rc != 0 {
    ssc install winsor2, replace
}

// 载入原始基础数据
use "base_data.dta", clear

// 重命名彩票销量变量（与主分析一致）
rename spotlottery sales_spot
rename wellottery sales_well

// 生成竞猜型销量（使用 betting_ratio）
gen sales_bet = sales_spot * betting_ratio

// 对三个销量变量进行 1% 和 99% 缩尾处理
foreach var of varlist sales_spot sales_well sales_bet {
    winsor2 `var', cuts(1 99) suffix(_w)  
    // 生成 `var'_w，例如 sales_spot_w
}

// 生成缩尾后的对数销量（仅对正数取 log）
foreach var in spot well bet {
    gen lnsales_`var'_w = ln(sales_`var'_w) if sales_`var'_w > 0
}

// -------------------------------
// 构建缩尾版稳健性数据集（体彩 vs 福彩）
// -------------------------------
preserve
keep id year pronum treat_income lnsales_spot_w $lnxlist
rename lnsales_spot_w lnsales
gen lottery_type = "spot"
gen treat_type = 1
gen post = (year >= 2015)
save "robust_winsor_spot.dta", replace
restore

// -------------------------------
// 构建缩尾版稳健性数据集（竞猜型 vs 福彩）
// -------------------------------
preserve
keep id year pronum treat_income lnsales_bet_w $lnxlist
rename lnsales_bet_w lnsales
gen lottery_type = "bet"
gen treat_type = 1
gen post = (year >= 2015)
save "robust_winsor_bet.dta", replace
restore

// -------------------------------
// 构建福彩对照组（保持不变，因 treat_type=0）
// -------------------------------
preserve
keep id year pronum treat_income lnsales_well_w $lnxlist
rename lnsales_well_w lnsales
gen lottery_type = "well"
gen treat_type = 0
gen post = (year >= 2015)
save "robust_winsor_well.dta", replace
restore

// -------------------------------
// 合并数据：体彩 vs 福彩（缩尾版）
// -------------------------------
use "robust_winsor_spot.dta", clear
append using "robust_winsor_well.dta"


// 运行 DDD 模型（对应原 M3：个体+年份 FE）
reghdfe lnsales treat_type##treat_income##post $lnxlist, ///
        absorb(id year) vce(cluster id)
estimates store robust_winsor_spot



// 清理临时文件
capture erase "robust_winsor_spot.dta"
capture erase "robust_winsor_bet.dta"
capture erase "robust_winsor_well.dta"

di "=== 缩尾处理（Winsorizing）稳健性检验完成 ==="

// === 稳健性4：保留 ddd_bet_m3（竞猜型 vs 福彩，双向FE） ===
use "ddd_bet_for_robust.dta", clear
append using "robust_well.dta"

tab year, gen(yd)
drop yd1
xtreg lnsales treat_type treat_income post ///
       treat_type#treat_income treat_type#post treat_income#post ///
       treat_type#treat_income#post ///
       $lnxlist yd*, fe robust
estimates store robust_bet_m3

di "==================== 稳健性检验完成 ===================="

************************** 第七步：输出结果 **************************
local controls lnpergdp worldcup eurcup lnumemploy lnpopula lnperedu lninterest lnhouseprice finacris capping

// 表1：主回归（M1–M5）
esttab ddd_spot_m1 ddd_spot_m2 ddd_spot_m3 ddd_spot_m4 ddd_spot_m5, ///
    b(3) se(3) star(* 0.1 ** 0.05 *** 0.01) ///
    keep(treat_type treat_income post 1.treat_type#1.treat_income#1.post `controls') ///
    stats(N r2_a, fmt(0 3)) ///
    mtitle("M1: 个体FE" "M2: 时点FE" "M3: 双向FE" "M4: 随机RE" "M5: 无控制") ///
    title("表1: 主回归结果（体彩 vs 福彩）") ///
    coeflabels( ///
        treat_type "体彩处理组" ///
        treat_income "高收入地区" ///
        post "政策后 (2015+)" ///
        1.treat_type#1.treat_income#1.post "DDD 核心系数" ///
        lnpergdp "人均GDP (对数)" ///
        worldcup "世界杯" ///
        eurcup "欧洲杯" ///
        lnumemploy "失业率 (对数)" ///
        lnpopula "人口 (对数)" ///
        lnperedu "人均教育年限 (对数)" ///
        lninterest "利率 (对数)" ///
		lnhouseprice "房价(对数)" ///
        finacris "金融危机" ///
        capping "头奖封顶额" ///
    ) ///
    order(1.treat_type#1.treat_income#1.post treat_type treat_income post `controls') ///
    compress nogap

// 表2：稳健性检验（体彩 vs 福彩 + 竞猜型稳健项）
esttab ddd_spot_m3 robust_income robust_placebo robust_winsor_spot robust_bet_m3, ///
    b(3) se(3) star(* 0.1 ** 0.05 *** 0.01) ///
    keep( ///
        1.treat_type#1.treat_income#1.post ///
        1.treat_type#1.treat_income_new#1.post ///
        1.treat_type#1.treat_income#1.post_placebo ///
        `controls' ///
    ) ///
    not ///
    stats(N r2_a, fmt(0 3)) ///
    mtitle("基准回归" "收入分组稳健性" "安慰剂检验" "极端值处理" "竞猜型子样本") ///
    title("表2: 稳健性检验") ///
    coeflabels( ///
        1.treat_type#1.treat_income#1.post "DDD (基准)" ///
        1.treat_type#1.treat_income_new#1.post "DDD (新分组)" ///
        1.treat_type#1.treat_income#1.post_placebo "DDD (安慰剂)" ///
        ///
        lnpergdp "人均GDP (对数)" ///
        worldcup "世界杯" ///
        eurcup "欧洲杯" ///
        lnumemploy "失业率 (对数)" ///
        lnpopula "人口 (对数)" ///
        lnperedu "人均教育年限 (对数)" ///
        lninterest "利率 (对数)" ///
		lnhouseprice "房价(对数)" ///
        finacris "金融危机" ///
        capping "头奖封顶额" ///
    ) ///
    order(1.treat_type#1.treat_income#1.post ///
          1.treat_type#1.treat_income_new#1.post ///
          1.treat_type#1.treat_income#1.post_placebo ///
          `controls') ///
    compress nogap



// 清理临时文件
capture erase base_data.dta
capture erase temp_pt.dta
capture erase ddd_spot.dta
capture erase ddd_well.dta
capture erase main_panel.dta
capture erase robust_spot.dta
capture erase robust_well.dta
capture erase robust_main.dta
capture erase ddd_bet_for_robust.dta

