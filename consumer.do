cd "D:\BaiduSyncdisk\1DoctorStudy\1Doctor thesis\DoctorThesis\results"    
import excel using LotteryPanelDate2025, firstrow clear

encode shengfen, gen(id)
xtset id year



local keyvars totallottery sportlottery wellottery It1 pergdp popula
egen missing_count = rowmiss(`keyvars')
tabstat missing_count, by(year) statistics(mean count)
drop if missing_count > 0
drop missing_count
di "剩余有效观测数: `=_N'"


*------------------------*
* 3. 生成对数变量
*------------------------*

foreach y of varlist totallottery sportlottery wellottery{
    assert `y' > 0
    gen ln_`y' = ln(`y')
}

assert It1 > 0 & It2 > 0
gen lnIt1 = ln(It1)
gen lnIt2 = ln(It2)


foreach v of varlist consumer gdp pergdp popula houseprice peredu unemploy {
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
//根据双色球，期望收益测算
gen sigma = -0.5172

gen It1_sigma = It1 - sigma
gen lnIt1_sigma = ln(It1_sigma)
gen It2_sigma = It2 - sigma
gen lnIt2_sigma = ln(It2_sigma)

* 控制变量组
global controls "lnpopula lnpergdp lnhouseprice lnperedu lnunemploy worldcup ncp baninter capping finacris eurcup"
//



*===============================================
* 描述性统计表：用于论文附录或正文表格前
*===============================================

* 1. 定义需要做描述性统计的变量（替换为你的实际变量）
global desc_vars ///
    ln_totallottery ln_sportlottery ln_wellottery ///
    lnpergdp lnpopula lnhouseprice lnperedu lnunemploy 

* 2. 计算描述性统计并存储为矩阵（核心步骤）
* 先对变量做描述性统计，将结果存入矩阵
summarize $desc_vars




*===============================================================================
* 主回归估计：

*===============================================================================

* 总销量
xtreg ln_totallottery ///
    lnconsumer lnIt1 lnIt1_sigma ///
    $controls, fe vce(cluster id)
est store total_main_I1

xtreg ln_totallottery ///
    lnconsumer lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store total_main_I2

* 体育彩票
xtreg ln_sportlottery ///
    lnconsumer lnIt1 lnIt1_sigma ///
    $controls, fe vce(cluster id)
est store sport_main_I1

xtreg ln_sportlottery ///
    lnconsumer lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store sport_main_I2

* 福利彩票
xtreg ln_wellottery ///
    lnconsumer lnIt1 lnIt1_sigma ///
    $controls, fe vce(cluster id)
est store wel_main_I1

xtreg ln_wellottery ///
    lnconsumer lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store wel_main_I2

/////////////////////////////////////2015后/////////////////////////

	drop if year < 2015
foreach v of varlist cgrain coil cvegetable cmeat cchicken cfish cegg cmilk cfruits ccandy {
    assert `v' > 0
    gen ln`v' = ln(`v')
}

global lnconsumers "lncgrain lncoil lncvegetable lncmeat lncchicken lncfish lncegg lncmilk lncfruits lnccandy"
*========================================*
* 按人均 GDP 均值划分高收入组与低收入组
*========================================*

*========================================*
* 高收入组与低收入组划分（按年份均值）
*========================================*

* 1. 按年份计算人均 GDP 均值并生成分组变量
bysort year: egen mean_pergdp_year = mean(pergdp)
gen high_income = (pergdp >= mean_pergdp_year) if pergdp != .
drop mean_pergdp_year

* 2. 验证分组结果
tab high_income, summarize(pergdp) mean
tab year high_income, row





* 总销量


xtreg ln_totallottery ///
    $lnconsumers lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store total_mains_I2

* 体育彩票
xtreg ln_sportlottery ///
    $lnconsumers lnIt1 lnIt1_sigma ///
    $controls, fe vce(cluster id)
est store sport_mains_I1

xtreg ln_sportlottery ///
    $lnconsumers lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store sport_mains_I2

* 福利彩票
xtreg ln_wellottery ///
    $lnconsumers lnIt1 lnIt1_sigma ///
    $controls, fe vce(cluster id)
est store wel_mains_I1

xtreg ln_wellottery ///
    $lnconsumers lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store wel_mains_I2




* 总销量
xtreg ln_totallottery ///
    lncvegetable lnIt1 lnIt1_sigma ///
    $controls, fe vce(cluster id)
est store total_vegetable_I1

xtreg ln_totallottery ///
    lncvegetable lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store total_vegetable_I2

* 体育彩票
xtreg ln_sportlottery ///
    lncvegetable lnIt1 lnIt1_sigma ///
    $controls, fe vce(cluster id)
est store sport_vegetable_I1

xtreg ln_sportlottery ///
    lncvegetable lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store sport_vegetable_I2

* 福利彩票
xtreg ln_wellottery ///
    lncvegetable lnIt1 lnIt1_sigma ///
    $controls, fe vce(cluster id)
est store wel_vegetable_I1

xtreg ln_wellottery ///
    lncvegetable lnIt2 lnIt2_sigma ///
    $controls, fe vce(cluster id)
est store wel_vegetable_I2





*===============================================================================
* 2015年后输出表格：It1主回归
*===============================================================================

esttab total_main_I1 sport_main_I1 wel_main_I1 ///
        total_vegetable_I1 sport_vegetable_I1 wel_vegetable_I1 ///
    ,  tex /// //booktabs /// 
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles("总销量\\(社会消费品总额\\)" ///
            "体育彩票\\(社会消费品总额\\)" ///
            "福利彩票\\(社会消费品总额\\)" ///
            "总销量\\(人均蔬菜消费量\\)" ///
            "体育彩票\\(人均蔬菜消费量\\)" ///
            "福利彩票\\(人均蔬菜消费量\\)") ///
    title("表1：基于预期资金收益率 \$I_t^E\$ 的固定效应回归结果") ///
    label ///
    alignment(@{}l*{6}{c}@{}) ///
    collabels(none) ///
    stats(N r2_a, fmt(%9.0f %9.3f) labels("观测数" "调整R²")) ///
    addnotes("注：(1) 所有模型均控制省份固定效应、时间趋势及以下变量：" ///
             "人均GDP、人口、房价、教育水平、失业率、世界杯、欧洲杯、金融危机、销售上限、互联网禁令；" ///
             "(4) 所有标准误聚类至省份层面。") ///
    fragment
*===============================================================================
* 2015年后输出表格：It2稳健性
*===============================================================================

esttab total_main_I2 sport_main_I2 wel_main_I2 ///
        total_vegetable_I2 sport_vegetable_I2 wel_vegetable_I2 ///
    , tex /// //booktabs /// 
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles("总销量\\(社会消费品总额\\)" ///
            "体育彩票\\(社会消费品总额\\)" ///
            "福利彩票\\(社会消费品总额\\)" ///
            "总销量\\(人均蔬菜消费量\\)" ///
            "体育彩票\\(人均蔬菜消费量\\)" ///
            "福利彩票\\(人均蔬菜消费量\\)") ///
    title("表1：基于预期资金收益率 \$I_t^E\$ 的固定效应回归结果") ///
    label ///
    alignment(@{}l*{6}{c}@{}) ///
    collabels(none) ///
    stats(N r2_a, fmt(%9.0f %9.3f) labels("观测数" "调整R²")) ///
    addnotes("注：(1) 所有模型均控制省份固定效应、时间趋势及以下变量：" ///
             "人均GDP、人口、房价、教育水平、失业率、世界杯、欧洲杯、金融危机、销售上限、互联网禁令；" ///
             "(4) 所有标准误聚类至省份层面。") ///
    fragment



*===============================================================================
* 全部年份输出表格：左三列=It1主回归，右三列=It2稳健性
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
             "(4) 所有标准误聚类至省份层面。") ///
    fragment


*========================================*
* 分组回归：高收入组 vs 低收入组
*========================================*

* --- 基准回归 (lnconsumer) ---
* 高收入组
xtreg ln_totallottery lnconsumer lnIt1 lnIt1_sigma $controls if high_income == 1, fe vce(cluster id)
est store high_base

* 低收入组
xtreg ln_totallottery lnconsumer lnIt1 lnIt1_sigma $controls if high_income == 0, fe vce(cluster id)
est store low_base

* --- 细分消费回归 ($lnconsumers) ---
* 高收入组
xtreg ln_totallottery $lnconsumers lnIt1 lnIt1_sigma $controls if high_income == 1, fe vce(cluster id)
est store high_detail

* 低收入组
xtreg ln_totallottery $lnconsumers lnIt1 lnIt1_sigma $controls if high_income == 0, fe vce(cluster id)
est store low_detail

* --- 蔬菜消费回归 (lncvegetable) ---
* 高收入组
xtreg ln_totallottery lncvegetable lnIt1 lnIt1_sigma $controls if high_income == 1, fe vce(cluster id)
est store high_veg

* 低收入组
xtreg ln_totallottery lncvegetable lnIt1 lnIt1_sigma $controls if high_income == 0, fe vce(cluster id)
est store low_veg

*========================================*
* 输出综合对比表格
*========================================*
esttab high_base low_base high_detail low_detail high_veg low_veg, ///
    b(%6.3f) se(%6.3f) star(* 0.1 ** 0.05 *** 0.01) ///
    mtitles("高收入\\(基准)" "低收入\\(基准)" ///
            "高收入\\(细分)" "低收入\\(细分)" ///
            "高收入\\(蔬菜)" "低收入\\(蔬菜)") ///
    title("表 X：高收入组与低收入组分组回归结果") ///
    stats(N r2_a, labels("观测数" "调整 R²")) ///
    addnotes("注：(1) 分组依据为各地区人均 GDP 是否高于当年均值；" ///
             "(2) 基准列使用 lnconsumer，细分列使用 10 类消费变量，蔬菜列仅使用 lncvegetable。") ///
    fragment














