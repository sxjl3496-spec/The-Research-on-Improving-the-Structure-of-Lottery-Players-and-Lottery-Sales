cd "D:\BaiduSyncdisk\1DoctorStudy\1Doctor thesis\DoctorThesis\results"    
import excel using LotteryPanelDate2024, firstrow clear

encode shengfen, gen(id)
xtset id year
* 主回归更新：使用新公式
* 公式：ln T_t = ln T_{t-1} + ρ [ ln I_t + ln(I_{t-1} - σ) - ln(I_t - σ) ]
* 数据来源：全部使用实际 It1（非预期）
*------------------------*
* 1. 标记并删除无效观测
*------------------------*
//gen It1 = it1 // cpi
//gen It2 = it2 // cpi

local keyvars totallottery sportlottery wellottery It1 gIt1 beta pergdp popula
egen missing_count = rowmiss(`keyvars')
tabstat missing_count, by(year) statistics(mean count)
drop if missing_count > 0
drop missing_count
di "剩余有效观测数: `=_N'"

*------------------------*
* 2. 处理 beta
*------------------------*

list shengfen year beta if beta >= 1
replace beta = 0.9999 if beta >= 1
replace beta = . if beta <= 0
assert beta > 0 & beta < 1
gen lnbeta = ln(beta)


*------------------------*
* 3. 生成对数变量
*------------------------*

foreach y of varlist totallottery sportlottery wellottery {
    assert `y' > 0
    gen ln_`y' = ln(`y')
}

assert It1 > 0 & It2 > 0
assert gIt1 > 0 & gIt2 > 0
gen lnIt1 = ln(It1)
gen lngIt1 = ln(gIt1)
gen lnIt2 = ln(It2)
gen lngIt2 = ln(gIt2)

foreach v of varlist gdp pergdp popula houseprice peredu unemploy {
    assert `v' > 0
    gen ln`v' = ln(`v')
}

*------------------------*
* 4. 构造事件变量与复合变量
*------------------------*

gen worldcup = (inlist(year, 2010, 2014, 2018, 2022))
gen eurcup   = (inlist(year, 2008, 2012, 2016, 2021))

gen capping = 0
replace capping = 500  if year >= 2009 & year < 2013
replace capping = 1000 if year >= 2013

gen finacris = 0
replace finacris = 1    if year == 2008
replace finacris = 0.6  if year == 2009
replace finacris = 0.36 if year == 2010

//gen baninter = 0
replace baninter =1 if year >= 2015

gen sigma = -0.5172

/*
* 生成预期 I_t^E = I_{t-1} * g_{t-1}
gen I_E = L.It1 * L.gIt1

* 构造公式项：ln(I_t^E) + ln(I_{t-1}^E - sigma) - ln(I_t^E - sigma)
gen ln_I_E = ln(I_E)
gen ln_I_E_lag_minus_sigma = ln(L.I_E - sigma)   // I_{t-1}^E = L.I_E
gen ln_I_E_minus = ln(I_E - sigma)

gen core_formula = ln_I_E + ln_I_E_lag_minus - ln_I_E_minus
bysort id (year): gen L_core_formula = core_formula[_n-1]

* Step 1: 确保 It1 > 0（用于取对数）
assert It1 > 0 if !missing(It1)

* Step 2: 构造三项基本成分
gen ln_It           = ln(It1)                    // ln I_t
bysort id (year): gen ln_L_It_minus_sigma = ln(L.It1 - sigma)   // ln(I_{t-1} - σ)
gen ln_It_minus_sigma = ln(It1 - sigma)         // ln(I_t - σ)
*/

* 生成滞后一期变量（必须在回归前执行）
*------------------------*

bysort id (year): gen L_ln_totallottery = ln_totallottery[_n-1]
bysort id (year): gen L_ln_sportlottery = ln_sportlottery[_n-1]
bysort id (year): gen L_ln_wellottery  = ln_wellottery[_n-1]

*===============================================================================
* 主回归构造：使用 It1（流通市值法）
* 公式：ln T_t = ln T_{t-1} + ρ [ ln I_t + ln(I_{t-1} - σ) - ln(I_t - σ) ]
*===============================================================================

*===============================================================================
* 主回归变量构造：基于 It1 的预期形式（三项分离）
* 公式：ln T_t = ln T_{t-1} + ρ1·ln I_t^E + ρ2·ln(I_{t-1}^E - σ) + ρ3·[-ln(I_t^E - σ)]
* 其中 I_t^E = I_{t-1} * g_{t-1}
*===============================================================================

* —— Step 1: 基于 It1 构造 I_t^E 和各项
bysort id (year): gen I_E1 = L.It1 * L.gIt1           // I_t^E,1
bysort id (year): gen I_E1_lag = I_E1[_n-1]          // I_{t-1}^E,1 = I_{t-2}*g_{t-2}

* 构造三项核心变量（命名风格与你一致）
gen ln_I_E1             = ln(I_E1)                    // ln(I_t^E)
gen ln_I_E1_lag_minus   = ln(I_E1_lag - sigma)        // ln(I_{t-1}^E - σ)
gen ln_I_E1_minus       = ln(I_E1 - sigma)            // ln(I_t^E - σ)，后续加负号

* 检查缺失
replace ln_I_E1             = . if missing(I_E1)
replace ln_I_E1_lag_minus   = . if missing(I_E1_lag, I_E1_lag - sigma)
replace ln_I_E1_minus       = . if missing(I_E1, I_E1 - sigma)

*===============================================================================
* 稳健性检验：基于 It2 构造预期变量（三项分离）
*===============================================================================

* —— Step 2: 基于 It2 构造 I_t^E,2
bysort id (year): gen I_E2 = L.It2 * L.gIt2           // I_t^E,2
bysort id (year): gen I_E2_lag = I_E2[_n-1]          // I_{t-1}^E,2

* 构造三项
gen ln_I_E2             = ln(I_E2)
gen ln_I_E2_lag_minus   = ln(I_E2_lag - sigma)
gen ln_I_E2_minus       = ln(I_E2 - sigma)

* 缺失处理
replace ln_I_E2             = . if missing(I_E2)
replace ln_I_E2_lag_minus   = . if missing(I_E2_lag, I_E2_lag - sigma)
replace ln_I_E2_minus       = . if missing(I_E2, I_E2 - sigma)

*===============================================================================
* 主回归估计：三项分离变量进入回归
* 左三列：基于 It1 构造的三项
* 右三列：基于 It2 构造的三项
*===============================================================================

* 控制变量组
global controls "lnpopula lnpergdp lnhouseprice lnperedu lnunemploy worldcup ncp baninter"
// capping finacris eurcup
*===============================================
* 描述性统计表：用于论文附录或正文表格前
*===============================================

* 方法 2：如果你想输出描述性统计，应该使用 sum 命令
global desc_vars ///
    ln_totallottery ln_sportlottery ln_wellottery ///
    lnbeta ///
    ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    ln_I_E2 ln_I_E2_lag_minus ln_I_E2_minus ///
    L_ln_totallottery L_ln_sportlottery L_ln_wellottery ///
    lnpergdp lnpopula lnhouseprice lnperedu lnunemploy ///
    worldcup ncp baninter
// 注意：使用 baninter（互联网禁令），banfree 不存在

* 使用 sum 输出描述性统计
sum $desc_vars, detail

* 先存储每个变量的统计量
estpost summarize $desc_vars, detail
esttab . , ///
    cells("mean(fmt(3)) sd(fmt(3)) min(fmt(3)) max(fmt(3))") ///
    label ///
    title("Table: Descriptive Statistics") ///
    nonumbers ///
    noobs ///
    mtitles("Summary")

*===============================================================================
* 主回归估计：三项分离变量进入回归
* 左三列：基于 It1 构造的三项
* 右三列：基于 It2 构造的三项
*===============================================================================

* 总销量
xtreg ln_totallottery L_ln_totallottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store total_main_E1

xtreg ln_totallottery L_ln_totallottery ///
    lnbeta ln_I_E2 ln_I_E2_lag_minus ln_I_E2_minus ///
    $controls, fe vce(cluster id)
est store total_main_E2

* 体育彩票
xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store sport_main_E1

xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta ln_I_E2 ln_I_E2_lag_minus ln_I_E2_minus ///
    $controls, fe vce(cluster id)
est store sport_main_E2

* 福利彩票
xtreg ln_wellottery L_ln_wellottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store wel_main_E1

xtreg ln_wellottery L_ln_wellottery ///
    lnbeta ln_I_E2 ln_I_E2_lag_minus ln_I_E2_minus ///
    $controls, fe vce(cluster id)
est store wel_main_E2

*===============================================================================
* 输出表格：左三列=It1主回归，右三列=It2稳健性
*===============================================================================

esttab total_main_E1 sport_main_E1 wel_main_E1 ///
        total_main_E2 sport_main_E2 wel_main_E2 ///
    , tex /// //booktabs /// 
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles("总销量\\(It1主回归\\)" ///
            "体育彩票\\(It1主回归\\)" ///
            "福利彩票\\(It1主回归\\)" ///
            "总销量\\(It2稳健性\\)" ///
            "体育彩票\\(It2稳健性\\)" ///
            "福利彩票\\(It2稳健性\\)") ///
    title("表1：基于预期资金收益率 \$I_t^E\$ 的固定效应回归结果") ///
    label ///
    alignment(@{}l*{6}{c}@{}) ///
    collabels(none) ///
    stats(N r2_a, fmt(%9.0f %9.3f) labels("观测数" "调整R²")) ///
    addnotes("注：(1) 所有模型均控制省份固定效应、时间趋势及以下变量：" ///
             "人均GDP、人口、房价、教育水平、失业率、世界杯、欧洲杯、金融危机、销售上限、互联网禁令；" ///
             "(2) 核心解释变量为三项分离形式：" ///
             "lnIE: \$\\ln I_t^E\$," ///
             "lnILs: \$\\ln(I_{t-1}^E - \\sigma)\$," ///
             "lnIEs: \$\\ln(I_t^E - \\sigma)\$," ///
             "其中 \$I_t^E = I_{t-1} \\times g_{t-1}\$；" ///
             "(3) 理论预期：前两项系数为正，第三项 \$\\ln(I_t^E - \\sigma)\$ 的系数应为负；" ///
             "(4) 所有标准误聚类至省份层面。") ///
    fragment


*===============================================================================
* 收入异质性分析：高/低收入分组回归（优先展示）
* 分组方法：按人均 GDP 是否高于当年 30 省份均值（动态分组，与论文一致）
* 论文章节：第 4 章 第 4.1 节 时间偏好的收入异质性分析
*===============================================================================

* 生成收入分组虚拟变量（按人均 GDP 是否高于当年均值）
bysort year: egen pergdp_mean = mean(pergdp)  // 使用原始值，非对数
gen HighIncome = (pergdp >= pergdp_mean) if !missing(pergdp)
label define highinc_lbl 1 "高收入地区" 0 "低收入地区"
label values HighIncome highinc_lbl

* 显示分组描述性统计
disp "=========================================="
disp "收入分组描述性统计"
disp "=========================================="
tabulate HighIncome
bysort HighIncome: sum pergdp

* 生成交互项（分组回归用）
gen lnbeta_High = lnbeta * HighIncome
gen lnbeta_Low = lnbeta * (1-HighIncome)
gen ln_I_E1_High = ln_I_E1 * HighIncome
gen ln_I_E1_Low = ln_I_E1 * (1-HighIncome)
gen ln_I_E1_lag_minus_High = ln_I_E1_lag_minus * HighIncome
gen ln_I_E1_lag_minus_Low = ln_I_E1_lag_minus * (1-HighIncome)
gen ln_I_E1_minus_High = ln_I_E1_minus * HighIncome
gen ln_I_E1_minus_Low = ln_I_E1_minus * (1-HighIncome)

*===============================================================================
* 分组回归：高收入地区 vs 低收入地区
* 仅使用 It1 构造的三项分离变量
*===============================================================================

*---------------------------------------
* 高收入地区子样本
*---------------------------------------
xtreg ln_totallottery L_ln_totallottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if HighIncome==1, fe vce(cluster id)
est store total_high

xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if HighIncome==1, fe vce(cluster id)
est store sport_high

xtreg ln_wellottery L_ln_wellottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if HighIncome==1, fe vce(cluster id)
est store wel_high

*---------------------------------------
* 低收入地区子样本
*---------------------------------------
xtreg ln_totallottery L_ln_totallottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if HighIncome==0, fe vce(cluster id)
est store total_low

xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if HighIncome==0, fe vce(cluster id)
est store sport_low

xtreg ln_wellottery L_ln_wellottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if HighIncome==0, fe vce(cluster id)
est store wel_low

*===============================================================================
* 输出表格：左三列=高收入地区，右三列=低收入地区
*===============================================================================

esttab total_high sport_high wel_high ///
        total_low sport_low wel_low ///
    , ///
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles("总销量\\(高收入\\)" ///
            "体育彩票\\(高收入\\)" ///
            "福利彩票\\(高收入\\)" ///
            "总销量\\(低收入\\)" ///
            "体育彩票\\(低收入\\)" ///
            "福利彩票\\(低收入\\)") ///
    title("表 2：跨期欧拉方程——高/低收入地区分组回归结果") ///
    label ///
    alignment(@{}l*{6}{c}@{}) ///
    collabels(none) ///
    stats(N r2_a, fmt(%9.0f %9.3f) labels("观测数" "调整 R²")) ///
    addnotes("注：(1) 高/低收入地区按当年人均 GDP 是否高于 30 省份均值划分；" ///
             "(2) 所有模型均控制省份固定效应、时间趋势及控制变量；" ///
             "(3) 核心解释变量为三项分离形式：" ///
             "lnIE: \$\\ln I_t^E\$," ///
             "lnILs: \$\\ln(I_{t-1}^E - \\sigma)\$," ///
             "lnIEs: \$\\ln(I_t^E - \\sigma)\$；" ///
             "(4) 所有标准误聚类至省份层面；" ///
             "(5) * p<0.1, ** p<0.05, *** p<0.01。") ///
    fragment

*===============================================================================
* 简化版表格：仅展示核心变量（滞后被解释变量 + 时间偏好 + 收益率项）
*===============================================================================

esttab total_high sport_high wel_high ///
        total_low sport_low wel_low ///
    , ///
    keep(L_ln_* lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus) ///
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles("总销量\\(高收入\\)" ///
            "体育彩票\\(高收入\\)" ///
            "福利彩票\\(高收入\\)" ///
            "总销量\\(低收入\\)" ///
            "体育彩票\\(低收入\\)" ///
            "福利彩票\\(低收入\\)") ///
    title("表 3：跨期欧拉方程核心变量对比——高/低收入地区") ///
    label ///
    alignment(@{}l*{6}{c}@{}) ///
    collabels(none) ///
    stats(N r2_a, fmt(%9.0f %9.3f) labels("观测数" "调整 R²")) ///
    addnotes("注：为节省篇幅，本表仅报告核心变量系数，包括滞后被解释变量、时间偏好（lnbeta）及收益率三项。控制变量包括人口、GDP、房价、教育、失业率及事件虚拟变量。") ///
    fragment

*===============================================================================
* 系数差异检验：使用交互项方法
* 检验高/低收入组所有核心变量系数是否显著不同
* 核心变量：L_ln_* (滞后被解释变量)、lnbeta (时间偏好)、ln_I_E1 (预期收益率)、
*          ln_I_E1_lag_minus (滞后风险调整)、ln_I_E1_minus (当期风险调整)
*===============================================================================

* 方法：使用交互项直接检验（推荐）
* 交互项系数表示高收入地区相对于低收入地区的系数差异

*---------------------------------------
* 总销量：包含所有核心变量的交互项
*---------------------------------------
xtreg ln_totallottery ///
    c.L_ln_totallottery#i.HighIncome ///
    c.lnbeta#i.HighIncome ///
    c.ln_I_E1#i.HighIncome ///
    c.ln_I_E1_lag_minus#i.HighIncome ///
    c.ln_I_E1_minus#i.HighIncome ///
    L_ln_totallottery lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store total_diff

*---------------------------------------
* 体育彩票：包含所有核心变量的交互项
*---------------------------------------
xtreg ln_sportlottery ///
    c.L_ln_sportlottery#i.HighIncome ///
    c.lnbeta#i.HighIncome ///
    c.ln_I_E1#i.HighIncome ///
    c.ln_I_E1_lag_minus#i.HighIncome ///
    c.ln_I_E1_minus#i.HighIncome ///
    L_ln_sportlottery lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store sport_diff

*---------------------------------------
* 福利彩票：包含所有核心变量的交互项
*---------------------------------------
xtreg ln_wellottery ///
    c.L_ln_wellottery#i.HighIncome ///
    c.lnbeta#i.HighIncome ///
    c.ln_I_E1#i.HighIncome ///
    c.ln_I_E1_lag_minus#i.HighIncome ///
    c.ln_I_E1_minus#i.HighIncome ///
    L_ln_wellottery lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store wel_diff

*---------------------------------------
* 输出所有核心变量的系数差异检验结果
*---------------------------------------
esttab total_diff sport_diff wel_diff ///
    , ///
    keep(*HighIncome*) ///
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles("总销量" "体育彩票" "福利彩票") ///
    title("表 4：跨期欧拉方程系数差异检验（高收入 - 低收入）") ///
    label ///
    collabels("交互项系数" "交互项系数" "交互项系数") ///
    addnotes("注：(1) 表中报告的是交互项系数，表示高收入地区相对于低收入地区的系数差异；" ///
             "(2) 核心变量包括：滞后被解释变量 (L_ln_*)、时间偏好 (lnbeta)、" ///
             "预期收益率 (ln_I_E1)、滞后风险调整 (ln_I_E1_lag_minus)、" ///
             "当期风险调整 (ln_I_E1_minus)；" ///
             "(3) 若交互项系数显著为正，说明该变量在高收入地区的正向效应更强；" ///
             "(4) * p<0.1, ** p<0.05, *** p<0.01。") ///
    fragment

*---------------------------------------
* 使用 testparm 检验各核心变量交互项的联合显著性
*---------------------------------------
disp "=========================================="
disp "总销量：各核心变量系数差异检验"
disp "=========================================="
disp "L_ln_totallottery 系数差异："
testparm c.L_ln_totallottery#i.HighIncome
disp "lnbeta 系数差异："
testparm c.lnbeta#i.HighIncome
disp "ln_I_E1 系数差异："
testparm c.ln_I_E1#i.HighIncome
disp "ln_I_E1_lag_minus 系数差异："
testparm c.ln_I_E1_lag_minus#i.HighIncome
disp "ln_I_E1_minus 系数差异："
testparm c.ln_I_E1_minus#i.HighIncome

disp "=========================================="
disp "体育彩票：各核心变量系数差异检验"
disp "=========================================="
disp "L_ln_sportlottery 系数差异："
testparm c.L_ln_sportlottery#i.HighIncome
disp "lnbeta 系数差异："
testparm c.lnbeta#i.HighIncome
disp "ln_I_E1 系数差异："
testparm c.ln_I_E1#i.HighIncome
disp "ln_I_E1_lag_minus 系数差异："
testparm c.ln_I_E1_lag_minus#i.HighIncome
disp "ln_I_E1_minus 系数差异："
testparm c.ln_I_E1_minus#i.HighIncome

disp "=========================================="
disp "福利彩票：各核心变量系数差异检验"
disp "=========================================="
disp "L_ln_wellottery 系数差异："
testparm c.L_ln_wellottery#i.HighIncome
disp "lnbeta 系数差异："
testparm c.lnbeta#i.HighIncome
disp "ln_I_E1 系数差异："
testparm c.ln_I_E1#i.HighIncome
disp "ln_I_E1_lag_minus 系数差异："
testparm c.ln_I_E1_lag_minus#i.HighIncome
disp "ln_I_E1_minus 系数差异："
testparm c.ln_I_E1_minus#i.HighIncome

*---------------------------------------
* 输出系数差异详细信息（包含所有核心变量）
*---------------------------------------
disp "=========================================="
disp "系数差异详细信息（总销量）"
disp "=========================================="
esttab total_diff, keep(*HighIncome*) b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01)

*===============================================================================
* 图示：lnbeta 系数及其 95% 置信区间对比（可选）
* 需要安装 coefplot: ssc install coefplot
*===============================================================================

coefplot total_high sport_high wel_high ///
         total_low sport_low wel_low ///
    , keep(lnbeta) ///
    ci(95) ///
    title("时间偏好系数 (lnbeta) 对比：高/低收入地区") ///
    xtitle("彩票类型") ///
    ytitle("系数估计值") ///
    legend(label(1 "高收入") label(2 "低收入")) ///
    color(blue red)


*===============================================================================
* 稳健性检验 1 & 2：基于已有变量扩展（无需重复生成 I_E1 等）
* 注意：以下命令接续你已完成的主回归部分
*===============================================================================

* ————————————————————————————————
* 稳健性检验 1：将后两项合并为比值项
* 即：用 ln[(I_{t-1}^E - σ)/(I_t^E - σ)] 替代单独两项
* ————————————————————————————————
gen ln_ratio_combined = ln_I_E1_lag_minus - ln_I_E1_minus
replace ln_ratio_combined = . if missing(ln_I_E1_lag_minus, ln_I_E1_minus)

* 对 It2 同样操作
gen ln_ratio_combined_It2 = ln_I_E2_lag_minus - ln_I_E2_minus
replace ln_ratio_combined_It2 = . if missing(ln_I_E2_lag_minus, ln_I_E2_minus)

* ————————————————————————————————
* 稳健性检验 2：拆解 ln_I_E1 = ln(It1[_n-1]) + ln(gIt1[_n-1])
* 使用原始滞后项，避免构造乘积带来的潜在问题
* ————————————————————————————————
bysort id (year): gen L_lnIt1 = lnIt1[_n-1]      // ln(I_{t-1})
bysort id (year): gen L_lngIt1 = lngIt1[_n-1]    // ln(g_{t-1})
bysort id (year): gen L_lnIt2 = lnIt2[_n-1]      // ln(I_{t-1})
bysort id (year): gen L_lngIt2 = lngIt2[_n-1]    // ln(g_{t-1})
*===============================================================================
* 稳健性回归估计（每类彩票两个模型）
*===============================================================================

* ———— 总销量 ————
* 模型 A：使用比值项替代后两部分
xtreg ln_totallottery L_ln_totallottery ///
    lnbeta ln_I_E1 ln_ratio_combined ///
    $controls, fe vce(cluster id)
est store total_robust_ratio

* 模型 B：拆解预期项
xtreg ln_totallottery L_ln_totallottery ///
    lnbeta L_lnIt1 L_lngIt1 ln_ratio_combined ///
    $controls, fe vce(cluster id)
est store total_robust_decomp

* ———— 体育彩票 ————
xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta ln_I_E1 ln_ratio_combined ///
    $controls, fe vce(cluster id)
est store sport_robust_ratio

xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta L_lnIt1 L_lngIt1 ln_ratio_combined ///
    $controls, fe vce(cluster id)
est store sport_robust_decomp

* ———— 福利彩票 ————
xtreg ln_wellottery L_ln_wellottery ///
    lnbeta ln_I_E1 ln_ratio_combined ///
    $controls, fe vce(cluster id)
est store wel_robust_ratio

xtreg ln_wellottery L_ln_wellottery ///
    lnbeta L_lnIt1 L_lngIt1 ln_ratio_combined ///
    $controls, fe vce(cluster id)
est store wel_robust_decomp

*===============================================================================
* 输出：稳健性检验综合表（6列）
* 稳健性检验 1：将后两项合并为比值项
* 即：用 ln[(I_{t-1}^E - σ)/(I_t^E - σ)] 替代单独两项
* 稳健性检验 2：拆解 ln_I_E1 = ln(It1[_n-1]) + ln(gIt1[_n-1])
* 使用原始滞后项，避免构造乘积带来的潜在问题
*===============================================================================

esttab total_robust_ratio sport_robust_ratio wel_robust_ratio ///
        total_robust_decomp sport_robust_decomp wel_robust_decomp, ///
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles( ///
        "总销量\n(比值项)" "体彩\n(比值项)" "福彩\n(比值项)" ///
           "总销量\n(拆解项)" "体彩\n(拆解项)" "福彩\n(拆解项)" ///
    ) ///
    title("附表X：稳健性检验——替换核心解释变量形式") ///
    label /// //booktabs ///
    alignment(@{}l*{6}{c}@{}) ///
    collabels(none) ///
    stats(N r2_a, fmt(%9.0f %9.3f) labels("观测数" "调整R²")) ///
    addnotes("注：(1) 所有模型均控制省份固定效应、时间趋势与 \$controls 变量；" ///
             "(2) 左三列将 $\ln(I_{t-1}^E - \sigma)$ 和 $\ln(I_t^E - \sigma)$ 合并为单一比值项：" ///
             "$\ln\left(\frac{I_{t-1}^E - \sigma}{I_t^E - \sigma}\right)$；" ///
             "(3) 右三列进一步将 $\ln I_t^E$ 拆解为 $\ln I_{t-1}$ 与 $\ln g_{t-1}$ 两项独立变量；" ///
             "(4) 所有标准误聚类至省份层面。") ///
    fragment

*===============================================================================
稳健性检验 2：按人均 GDP 中位数分组（子样本回归）—— 静态分组，仅供参考
    * 注意：此为静态分组，与论文主分析的动态分组不同，仅供参考
*===============================================================================

* Step 1: 计算全样本人均GDP中位数（原始值，非对数）
sum pergdp, detail
local med_pergdp = r(p50)
di as result "人均GDP中位数 = `med_pergdp' 元"

* Step 2: 生成分组变量（不改变原数据结构）
gen high_inc_group = (pergdp >= `med_pergdp') if !missing(pergdp)
label define hg 0 "低收入地区" 1 "高收入地区"
label values high_inc_group hg
tab high_inc_group

*===============================================================================
* 子样本回归：保持与主回归变量一致（三项分离 + I_E1）
* 注意：这里使用的是主回归左侧的模型（It1构造的 I_E1），更具可比性
*===============================================================================

* ———— 总销量 ————
* 低收入组
xtreg ln_totallottery L_ln_totallottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if high_inc_group == 0, fe vce(cluster id)
est store total_robust_low

* 高收入组
xtreg ln_totallottery L_ln_totallottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if high_inc_group == 1, fe vce(cluster id)
est store total_robust_high

* ———— 体育彩票 ————
xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if high_inc_group == 0, fe vce(cluster id)
est store sport_robust_low

xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if high_inc_group == 1, fe vce(cluster id)
est store sport_robust_high

* ———— 福利彩票 ————
xtreg ln_wellottery L_ln_wellottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if high_inc_group == 0, fe vce(cluster id)
est store wel_robust_low

xtreg ln_wellottery L_ln_wellottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls if high_inc_group == 1, fe vce(cluster id)
est store wel_robust_high

*===============================================================================
* 输出表格：子样本稳健性检验（6列）
* 稳健性检验3：按人均GDP中位数分组（子样本回归）
* 方法：使用主回归设定，在高低收入组分别估计
*===============================================================================

esttab total_robust_low total_robust_high ///
        sport_robust_low sport_robust_high ///
        wel_robust_low wel_robust_high, ///
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles( ///    // booktabs ///
        "总销量\n(低收入)" "体彩\n(低收入)" "福彩\n(低收入)" ///
         "总销量\n(高收入)" "体彩\n(高收入)" "福彩\n(高收入)" ///
    ) ///
    title("附表X：子样本回归——按人均GDP中位数分组") ///
    label ///
    alignment(@{}l*{6}{c}@{}) ///
    collabels(none) ///
    stats(N r2_a, fmt(%9.0f %9.3f) labels("观测数" "调整R²")) ///
    addnotes("注：(1) 样本按全样本人均GDP中位数分组：" ///
             "低收入组 = \$pergdp < median\$，高收入组 = \$pergdp \geq median\$；" ///
             "(2) 所有模型设定与主回归（表1）完全相同；" ///
             "(3) 控制变量包括省份固定效应、时间趋势及其他经济控制变量；" ///
             "(4) 标准误聚类至省份层面。") ///
    fragment
	
* -------------------------------
* 稳健性检验4：时间动态与外生性（附录表）
* -------------------------------

* 生成滞后/领先项
bysort id (year): gen L2_ln_I_E1 = ln_I_E1[_n-2]
bysort id (year): gen F1_ln_I_E1 = ln_I_E1[_n+1]  // 领先一期
bysort id (year): gen L_ln_I_E1 = ln_I_E1[_n-1]   // 滞后一期

* 回归 (1)：基准扩展（无额外动态项）
quietly xtreg ln_totallottery L_ln_totallottery ///
    lnbeta L2_ln_I_E1 ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store m1_base_ext

* 回归 (2)：加入领先项 F1，但不加 L
quietly xtreg ln_totallottery L_ln_totallottery ///
    lnbeta L2_ln_I_E1 ln_I_E1 F1_ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store m2_forward_only

* 回归 (3)：完全设定（含 L + F + L2）
quietly xtreg ln_totallottery L_ln_totallottery ///
    lnbeta L2_ln_I_E1 L_ln_I_E1 ln_I_E1 F1_ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store m3_full_set

* 稳健性检验5：时间动态与外生性
* 在 Stata 窗口中直接显示三联表
esttab m1_base_ext m2_forward_only m3_full_set ///
    , label /// 使用变量标签（如果定义了的话）booktabs /// 使用专业排版风格
      b(%6.3f) se(%6.3f) /// 系数和标准误保留三位小数
      star(* 0.1 ** 0.05 *** 0.01) /// 显著性星号
      mtitles("(1) 基准扩展" "(2) 加领先项" "(3) 完全设定") /// 列标题
      stats(N r2_w, fmt(%9.0f %9.3f) labels("Observations" "Adj. R²")) /// 统计量
      nogaps /// 让输出更紧凑
      note("标准误聚类至省份层面。" ///
           "Robust standard errors clustered at province level." ///
           "$^{*} p<0.1$, $^{**} p<0.05$, $^{***} p<0.01$")
	
/*	
	* 定义通用回归命令宏
capture program drop run_robust_regression
program define run_robust_regression
    args depvar
    
    xtreg `depvar' L_`depvar' ///
        lnbeta L2_ln_I_E1 L_ln_I_E1 ln_I_E1 F1_ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
        $controls, fe vce(cluster id)
        
    est store robust_`depvar'_full
end

* 分别运行
run_robust_regression ln_totallottery
run_robust_regression ln_sportlottery
run_robust_regression ln_wellottery

* 输出对比表
esttab robust_ln_totallottery robust_ln_sportlottery robust_ln_wellottery ///
    , b(%6.3f) se star(* 0.1 ** 0.05 *** 0.01) mtitles("Total" "Sports" "Welfare") ///
    title("Appendix Table X: Robustness by Lottery Type")
	*/

*稳健性5 使用 xtabond2 运行系统 GMM，并正确聚类
mata: mata set matafavor speed, perm
* 不再对核心变量使用 GMM 工具，仅保留滞后的被解释变量
// controls "lnpopula lnpergdp lnhouseprice lnperedu lnunemploy worldcup ncp baninter"
xtabond2 ln_totallottery L.ln_totallottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls ///
    , gmm(L.ln_totallottery lnbeta lnpopula lnpergdp lnhouseprice lnperedu lnunemploy, lag(2 2) collapse) ///
      iv(ln_I_E1_lag_minus ln_I_E1_minus ln_I_E1 worldcup ncp baninter, equation(level)) ///
      twostep small robust h(2)  
	  
/*	  
xtabond2 ln_totallottery L.ln_totallottery ///
    lnbeta ln_I_E1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls ///
    , gmm(L.ln_totallottery lnbeta ln_I_E1 lnpopula lnpergdp lnhouseprice lnperedu lnunemploy, lag(2 2) collapse) ///
      iv(ln_I_E1_lag_minus ln_I_E1_minus worldcup ncp baninter, equation(level)) ///
      twostep small robust h(2) 
*/
	  
	  


	



* 储存模型以便输出
est sto gmm_sys
	
tempfile original_data
save `original_data', replace




*===============================================================================
//机制检验，仅看上一期L_lnIt1对彩票销量的影响。我们构造的I^E不一定符合现实
//但是在t期的预期总要是要关注t-1期的信息。)
*===============================================================================
/*
bysort id (year): gen L_lnIt1 = lnIt1[_n-1]      // ln(I_{t-1})
bysort id (year): gen L_lngIt1 = lngIt1[_n-1]    // ln(g_{t-1})
bysort id (year): gen L_lnIt2 = lnIt2[_n-1]      // ln(I_{t-1})
bysort id (year): gen L_lngIt2 = lngIt2[_n-1]    // ln(g_{t-1})
*/
* 总销量
xtreg ln_totallottery L_ln_totallottery ///
    lnbeta L_lnIt1 L_lngIt1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store total_main_I1

xtreg ln_totallottery L_ln_totallottery ///
    lnbeta L_lnIt2 L_lngIt2 ln_I_E2_lag_minus ln_I_E2_minus ///
    $controls, fe vce(cluster id)
est store total_main_I2

* 体育彩票
xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta L_lnIt1 L_lngIt1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store sport_main_I1

xtreg ln_sportlottery L_ln_sportlottery ///
    lnbeta L_lnIt2 L_lngIt2 ln_I_E2_lag_minus ln_I_E2_minus ///
    $controls, fe vce(cluster id)
est store sport_main_I2

* 福利彩票
xtreg ln_wellottery L_ln_wellottery ///
    lnbeta L_lnIt1 L_lngIt1 ln_I_E1_lag_minus ln_I_E1_minus ///
    $controls, fe vce(cluster id)
est store wel_main_I1

xtreg ln_wellottery L_ln_wellottery ///
    lnbeta L_lnIt2 L_lngIt2 ln_I_E2_lag_minus ln_I_E2_minus ///
    $controls, fe vce(cluster id)
est store wel_main_I2

*===============================================================================
* 输出表格：左三列=It1主回归，右三列=It2稳健性
*===============================================================================

esttab total_main_I1 sport_main_I1 wel_main_I1 ///
        total_main_I2 sport_main_I2 wel_main_I2 ///
    , /// //booktabs /// 
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles("总销量\\(It1主回归\\)" ///
            "体育彩票\\(It1主回归\\)" ///
            "福利彩票\\(It1主回归\\)" ///
            "总销量\\(It2稳健性\\)" ///
            "体育彩票\\(It2稳健性\\)" ///
            "福利彩票\\(It2稳健性\\)") ///
    title("表1：基于预期资金收益率 \$I_t^E\$ 的固定效应回归结果") ///
    label ///
    alignment(@{}l*{6}{c}@{}) ///
    collabels(none) ///
    stats(N r2_a, fmt(%9.0f %9.3f) labels("观测数" "调整R²")) ///
    addnotes("注：(1) 所有模型均控制省份固定效应、时间趋势及以下变量：" ///
             "人均GDP、人口、房价、教育水平、失业率、世界杯、欧洲杯、金融危机、销售上限、互联网禁令；" ///
             "(2) 核心解释变量为三项分离形式：" ///
             "lnIE: \$\\ln I_t^E\$," ///
             "lnILs: \$\\ln(I_{t-1}^E - \\sigma)\$," ///
             "lnIEs: \$\\ln(I_t^E - \\sigma)\$," ///
             "其中 \$I_t^E = I_{t-1} \\times g_{t-1}\$；" ///
             "(3) 理论预期：前两项系数为正，第三项 \$\\ln(I_t^E - \\sigma)\$ 的系数应为负；" ///
             "(4) 所有标准误聚类至省份层面。") ///
    fragment


