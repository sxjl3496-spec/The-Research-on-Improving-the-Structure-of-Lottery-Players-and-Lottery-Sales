globals [
  ;country
  high-income ; 高可支配收入人群门槛值（扣除了生活成本，可用于娱乐消费的部分）
  meddle-income ;中等可支配收入人群
  low-income ; 低可支配收入人群门槛值
  ;ratio ; 高收入人群比例
  ;p ; 彩票中奖概率
  p1 p2 p3 p4 p5 p6 p7 p8 p9
  ;α ;财富分布，α越小财富分布越均匀，α越大财富分布越不均匀，α=1财富成二八分布定律
  ;c ; 彩票价格
  ;lottery_types ; 彩票种类
  k_para ; 每类彩票的最头奖计算系数（即彩票的最低头奖除以头奖中奖概率，也是最低头奖的期望收益）
  lambda ;泊松分布随机数，滑块无法直接修改。
  pool ; 奖池初始金额
  K;封顶额头奖，可调节
  j2 ;二等奖金额
  jc ;期望收益等于彩票价格时的头奖金额
  oj ;其它奖金期望收益
  low_cap ;奖池低于 1 亿时的封顶额
  high_cap;奖池高于 1 亿时的封顶额
  ;add_cap; added value of the capped amount
  add_para ; The parameter used to adjust the amount of th add_cap value
  Kcap; 初始头奖额度
  ;cap; 封顶额制度
  a0  ; 社会彩民占比
  num-K ;中奖次数
  winners;中奖人数
  people;平均每家彩票店购彩人数
  ratio ;高收入人群比例，滑块无法直接修改。
  buyers;彩民人数
  total-tickets ;彩票总销量
  total-periods; 总期数
  wealth-list ;; 存储代理人的财富值
  pareto ; 方便调整不同国家的 gini 系数和财富分布
  gini2 ; 为了方便输出 gini 数值
  current-tickets ; 当期彩票销量
  gamma; 一等奖之外的其它奖的返奖金额占当期销售额的比例
  gamma-a;gamma 随机数分布参数
  gamma-b; gamma 随机数形状参数
  highprize ; 双色球高级奖金
  lowprize; 双色球低级奖金
  current-first-price; 当期一等奖返奖金额
  current-other-price; 当期其它奖金返奖金额
  current-wintickets; 当期中奖注数
  current-j2tickets; 当期二等奖中奖注数
  current-j2-price ;双色球当期二等奖返奖金额
  tax ; 公益税，不返奖的部分
  lit; lottery income tax ,彩票所得税
  ;RTAP;real tax adjust parameters
  year-buy ; 经常买彩票的人
  buys ;累计购彩次数
  ER ;期望收益
  ;
  ;upper-sr; the upper of subjective resistance
  ;lower-sr; the lower of subjective resistance

  ;;; === 新增：敏感性分析统计变量 ===
  ; 高/中/低购买量分类统计 (按累计购买彩票数量)
  high-buyers-count    ; 高购买量人群数 (累计购买>100 注)
  middle-buyers-count  ; 中购买量人群数 (累计购买 10-100 注)
  low-buyers-count     ; 低购买量人群数 (累计购买<10 注)

  ; 高/中/低支出分类统计 (按累计支出金额，单位：万元)
  high-spenders-count   ; 高支出人群 (累计支出>0.2 万元)
  middle-spenders-count ; 中支出人群 (累计支出 0.02-0.2 万元)
  low-spenders-count    ; 低支出人群 (累计支出<0.02 万元)

  ; 购买频率分类统计
  year-regular-buyers   ; 年经常购买者 (每月至少 1 次，buy > total-periods/12)
  year-casual-buyers    ; 年一般购买者 (每年几次，buy > total-periods/150 且 <= total-periods/12)
  uninterested-buyers   ; 不感兴趣者 (buy <= total-periods/150)

  ; 按收入分组的频繁购买者统计
  high-income-frequent  ; 高收入频繁购买者
  middle-income-frequent; 中收入频繁购买者
  low-income-frequent   ; 低收入频繁购买者

  ; 随机种子 (用于可重复实验)
  exp-seed
]

turtles-own [
  year-wealth ; 一年内拥有的可支配财富
  believe ; 购彩意愿
  lottery-tickets ;购买的彩票数
  buy ;购彩次数
  tickets ;每期够买的彩票数量
  holders ;累计是否购买彩票
  per-holders  ;单期的是否购买彩票
    ; 在每一期开始时，将 believe 重置为初始的随机值
  initial-believe ;初始购彩意愿
  p-e ;预期自己中奖的主观概率
  once-buyer  ;至少购买一次彩票的人
  year-buyer  ;每年购买彩票的人
  month-buyer ;每月购买彩票的人
  week-buyer  ;每周购买彩票的人
  convenience; 购彩便利性
  sr; subjective resistance 购买彩票的主观阻力
    ;upper-con; the upper of convenience
  ;lower-con; the lower of convenience

  ;;; === 新增：代理人层面追踪变量 ===
  total-spending   ; 累计购彩支出 (单位：元)
  total-winning    ; 累计中奖金额 (单位：元)
  net-gain         ; 净收益 (total-winning - total-spending)

  ;;; 购买频率分类标识
  freq-regular     ; 经常购买者标识 (每月至少 1 次)
  freq-casual      ; 一般购买者标识 (每年几次)
  freq-none        ; 不感兴趣标识
]

to setup
  clear-all
  set people 0.0001;平均每家彩票店购彩人数
  set winners 0
  set buyers 0; 初始彩民人数为0
  ;set Kcap (c * (1 - tax) / (1 * p)) + o * max list (pool - (c * (1 - tax) / (1 * p)) * 10) 0
     ; 初始化购彩意愿
  ;set K Kcap
  set a0 0.0001 ; 社会彩民占比（一年150期为例）
  ;set α 1
  set num-K 0
  set current-tickets 0
  set current-j2tickets 0
  set current-j2-price 0
  set j2 20 ; 二等奖奖金

  ;;; === 新增：初始化敏感性分析统计变量 ===
  set exp-seed 20260224  ; 默认随机种子，BehaviorSpace 可覆盖

  if country = 0 [
    set agents 2580
    set low-income 1.5
    set high-income 3.6
    set pareto 3.14
    set lit 0.24
  ]

  if country = 1 [
    set agents 11480
    set low-income 3.14
    set high-income 9.42
    set pareto 2.542
    set tax 0.49
    set lit 0.20
  ]

  if lottery_types = 0 [;powerball
    set p 0.0000000034 ;中奖概率 Runing BehaviorSpace need add ;
        set p2 0.00000008555
        set p3 0.000001
        set p4 0.000027378
        set p5 0.00006899
        set p6 0.0017248
        set p7 0.00142
        set p8 0.01
        set p9 0.026
        set Kcap 2000
    set pool 0
   ; set o 1
    set c 0.0002 ;彩票价格
    set low_cap (1 / p) * (2000 / 292201338) * 0.48
    set oj 0.000032 ;其它奖金期望收益
    ;set sr 22000
    ;set convenience 0.5
    ;set cap 0
  ]

 if lottery_types = 1 [;双色球
  ;set p 0.0000000565 ;中奖概率 Runing BehaviorSpace need add ;
   set p2 0.000000846
   set p3 0.00000914
   set p4 0.000434
   set p5 0.0077577
   set p6 0.05889
    set oj 0.000010854436;其它奖金总期望收益（以2元每注期望收益）
    set pool 40000  ;奖池初始金额为4亿
   set K_para 500 / 17721088
  set low_cap (1 / p) * K_para + add_cap

  ;adjust the capping amounts of jackpot

  ;set add_cap 0;((c / p) - low_cap) * add_para
  set high_cap 2 * low_cap
  set c 0.0002 ;彩票价格
  set K low_cap
  ;set add_para p * add_cap / (c - 2 * k_para)
    ;set cap 1
    ;set pool 100000
     ; set convenience 0.137
  ;  set xs 0.65
    ;set sr 7300
  ]

    ;滑块无法修改需要手动修改的参数。
    ;set ratio 0.2
    ;set lambda 100
    ;set total-periods 1 ; 初始化总期数




    ; 创建代理人
  create-turtles agents [
    set size 0.25
    set shape "circle"
    set lottery-tickets 0
    set buy 0

    ;;; === 新增：初始化代理人追踪变量 ===
    set total-spending 0
    set total-winning 0
    set net-gain 0
    set freq-regular 0
    set freq-casual 0
    set freq-none 0

    ;setxy 0 random-ycor
    ;setxy  wealth ycor

    ;财富设置
    set wealth-list []
    set year-wealth generate-pareto pareto ;; 使用定义的幂律分布生成函数，参数可以调整
    set wealth-list lput year-wealth wealth-list

    ;sr parameter
    ;let sr0 random-float (upper-sr - lower-sr) ;uniform distribution
    ;set sr sr0 + lower-sr
    set sr random-normal u-sr sd-sr ;normal distribution
    ;人群用颜色分类
    ifelse (year-wealth < low-income) [
      set color red ; 低收入人群为红色
    ] [
      ifelse (year-wealth > high-income)[
      set color green ; 高收入人群为绿色
      ]
      [
        set color blue ; 中收入人群为蓝色
      ]
    ]
    ;y轴位置
    if color = red [
      ;; 红色turtles在y轴下三分之一位置
     let wz random-float 7
      let y-position wz
      set ycor y-position
      ;move-to (list xcor random-y)
    ]
    if color = blue [
      ;; 蓝色turtles在y轴中间三分之一位置
      let wz random-float 5
      let y-position wz + 7
      set ycor y-position
      ;move-to (list xcor random-y)
    ]
    if color = green [
      ;; 绿色turtles在y轴上三分之一位置
       let wz random-float 3
      let y-position wz + 12
      set ycor y-position
      ;move-to (list xcor random-y)
    ]
    ; 随机生成初始的购彩意愿
    ; 生成泊松分布的初始信念值
    ; 泊松分布的参数，峰值对应的值
    ; let value random-poisson lambda
    ; set initial-believe (value / 1000) + p
    set lambda (10000 * a0)
    let value random-poisson lambda
    set initial-believe (value / 10000) + p
    ;set p-e  initial-believe + p
    ;set p-e min list (initial-believe + random-float 1) 1
  ]

  reset-ticks
end

to go
  reset-winners ; 重置中奖人数为 0
  set total-periods total-periods + 1
  update-K
  ask turtles [
    ;work
    update-believe
    decide-buy-lottery

    move
  ]

  update-pool
  update-classification-stats  ;;; === 新增：更新分类统计 ===
  tick
  ; print (word "high-income-people-ratio: " high-income-people-ratio "meddle-income-people-ratio: " middle-income-people-ratio "low-income-people-ratio: " low-income-people-ratio
   ; ", all-lottery: " all-lottery ", wealth-max: " wealth-max ", wealth-min: " wealth-min ", gini:" gini_2 ",E-R:" E-R)
end

to reset-winners
  set winners 0 ; 重置中奖人数为 0
  set buyers 0 ; 重置彩民人数为 0
  set current-tickets 0 ; 重置当期初始彩票为 0
  set current-first-price 0 ;重置当期一等奖返奖总金额
  set current-wintickets 0 ; 重置当期中奖注数
  set current-other-price 0 ; 重置当期其它奖金
  set year-buy 0 ;重置当期的常够彩票人数
  set current-j2tickets 0 ;重置当期二等奖注数
  set current-j2-price 0 ;重置当期二等奖返奖金额
end

;;; =====================================================
;;; === 新增：分类统计更新过程 ===
;;; =====================================================
to update-classification-stats
  ;;; 1. 购买量分类统计 (按累计购买彩票数量)
  set high-buyers-count count turtles with [lottery-tickets > 100]     ; 高购买量 (>100 注)
  set middle-buyers-count count turtles with [lottery-tickets >= 10 and lottery-tickets <= 100]  ; 中购买量 (10-100 注)
  set low-buyers-count count turtles with [lottery-tickets < 10]       ; 低购买量 (<10 注)

  ;;; 2. 支出分类统计 (按累计支出金额，单位：元)
  set high-spenders-count count turtles with [total-spending > 2000]      ; 高支出 (>0.2 万元)
  set middle-spenders-count count turtles with [total-spending >= 200 and total-spending <= 2000]  ; 中支出 (0.02-0.2 万元)
  set low-spenders-count count turtles with [total-spending < 200]        ; 低支出 (<0.02 万元)

  ;;; 3. 购买频率分类统计
  set year-regular-buyers count turtles with [freq-regular = 1]    ; 经常购买者 (每月至少 1 次)
  set year-casual-buyers count turtles with [freq-casual = 1]      ; 一般购买者 (每年几次)
  set uninterested-buyers count turtles with [freq-none = 1]       ; 不感兴趣者

  ;;; 4. 按收入分组的频繁购买者统计 (频繁购买者定义：每月至少购买 1 次)
  set high-income-frequent count turtles with [color = green and freq-regular = 1]
  set middle-income-frequent count turtles with [color = blue and freq-regular = 1]
  set low-income-frequent count turtles with [color = red and freq-regular = 1]
end

;to work
   ; 代理人的工作逻辑，根据代理人的收入增加财富
   ;ifelse (color = red) [
   ;   set wealth wealth + LM
   ;  ] [
   ;   set wealth wealth + HM
   ; ]
;end
to update-K ;更新封顶额头奖
  if country = 0 [
    set agents 2608
    set low-income 1.5
    set high-income 3.6
    set pareto 3.14
    set lit 0.24
    set tax 0.5
  ]

  if country = 1 [
    set agents 11480
    set low-income 3.14
    set high-income 9.42
    set pareto 2.542
    set tax 0.49
    set lit 0.20
  ]
   if lottery_types = 0 [;powerball
    ;set p 0.0000000034 ;中奖概率
        set p2 0.00000008555
        set p3 0.000001
        set p4 0.000027378
        set p5 0.00006899
        set p6 0.0017248
        set p7 0.00142
        set p8 0.01
        set p9 0.026
    ;set o 1
    ;set c 0.0002 ;彩票价格

    set oj 0.000032 ;其它奖金期望收益
    ;set cap 0
  ]

 if lottery_types = 1 [;双色球
  ;set p 0.0000000565 ;中奖概率
   set p2 0.000000846
   set p3 0.00000914
   set p4 0.000434
   set p5 0.0077577
   set p6 0.05889
  ;set o 0
  ;set c 0.0002 ;彩票价格
 ; set K (1 / p) * (500 / 17700000)
    ;set xs 0.65
    set oj 0.000010854436;(j2 * 0.000000846 + 0.0000486247);其它奖金期望收益
    ;set cap 1
    ;set pool 100000
  ]

  if cap = 0 [; powerball无封顶额规则
    set k_para 2000 / 292201338
    set low_cap (1 / p) * k_para * 0.48
    set K max list pool low_cap
  ]

  if cap = 1 [; 双色球封顶额规则
    set k_para 500 / 17721088
    set low_cap (1 / p) * k_para + add_cap
    set high_cap 2 * low_cap
   ; ifelse (p > 0.0000000565)[
    ;  set K min list K high_cap
   ; ]
   ; [
    ;  set K max list K low_cap
  ;]
  ]

end
to update-believe

  let addbelieve 0 ; 初始增加的购彩意愿
    ; 在每一期开始时，将 believe 重置为初始的随机值
    set believe initial-believe
  ; 财富意愿中的调节系数
  ; 如果奖池大于K，增加购彩意愿
  ;let convenience0 random-float (upper-con - lower-con)
  ;set convenience convenience0 + lower-con
  set convenience random-normal u-con sd-con
 if cap = 0[
    ;使用NetLogo的atan函数获取角度
    let a sr * year-wealth * p

    set jc (c - oj) / p
    let E_price min list K pool
    let index (- a * (E_price * (1 - lit) - jc))
    let eindex min list index 300
    set believe convenience / (1 + (exp eindex))
  ]

if cap = 1[
    ;使用NetLogo的atan函数获取角度
    let a sr * year-wealth * p

    set jc (c - oj) / p
    set ER oj * 10000
    let E_price min list K pool
    let index (- a * (E_price * (1 - lit) - jc))
    let eindex min list index 300
    set believe convenience / (1 + (exp eindex))
  ]
end



to decide-buy-lottery
  ; 购买彩票的逻辑
  let wealth year-wealth / 150
  set per-holders 0
  set p-e random-float 1
  set tickets ceiling(1 / p-e) ; 每次购买彩票的数量和主观中奖概率相关，celling 表示向上取整
  let cost c * tickets ; 购买彩票的总花费
  ifelse (believe > random-float 1) [
    ifelse (wealth >= c)[; 检查是否有足够的财富购买彩票
    ifelse (wealth >= cost) [
        ]
        [;财富 wealth 小于 cost
      set tickets floor(wealth / c) ; floor 表示向下取整。
      set cost c * tickets ; 重新计算实际花费
    ]
      ;set wealth wealth - cost

      ;;; === 新增：记录累计支出 ===
      set total-spending total-spending + (cost * 10000) ; 转换为元

      set lottery-tickets lottery-tickets + tickets
      set total-tickets total-tickets + tickets
      ;set K min list (max list pool 0)  ((c / (2 * p)) + o * max list (pool - (c / (2 * p)) * tickets) 0)
      set current-tickets current-tickets + tickets
      set buyers buyers + 1
      set buy buy + 1
      set holders 1
      set per-holders 1

     ;仅当中奖概率低于十万分之 1 时
        let ep (100000 * p)
      let odds random-float 1
      ; 检查是否中奖
      ifelse (odds < ep * tickets) [; 是否中头奖
        set winners winners + 1
        set num-K num-k + 1
        set current-wintickets current-wintickets + 1
        let jackpot pool / ( winners * tickets ) ;不封顶时的头奖

        ifelse (cap > 0)[;封顶时
           ;let ecost (50000 * cost)
          set current-first-price current-first-price + K * tickets
          ;;; === 新增：记录头奖中奖金额 ===
          set total-winning total-winning + (K * tickets * 10000) ; 转换为元
        ]
        [;不封顶时
          ;set pool pool + ecost - jackpot * tickets
           set current-first-price current-first-price + jackpot * tickets
          ;;; === 新增：记录头奖中奖金额 ===
          set total-winning total-winning + (jackpot * tickets * 10000) ; 转换为元
          ;set year-wealth year-wealth + jackpot * tickets
        ]
      ]
        [;财富wealth 小于 cost
      set tickets floor(wealth / c) ; floor表示向下取整。
    ]
      ;set wealth wealth - cost

      set lottery-tickets lottery-tickets + tickets
      set total-tickets total-tickets + tickets
      ;set K min list (max list pool 0)  ((c / (2 * p)) + o * max list (pool - (c / (2 * p)) * tickets) 0)
      set current-tickets current-tickets + tickets
      set buyers buyers + 1
      set buy buy + 1
      set holders 1
      set per-holders 1

     ;仅当中奖概率低于十万分之1时
        set ep (100000 * p)
      set odds random-float 1
      ; 检查是否中奖
      ifelse (odds < ep * tickets) [; 是否中头奖
        set winners winners + 1
        set num-K num-k + 1
        set current-wintickets current-wintickets + 1
        let jackpot pool / ( winners * tickets ) ;不封顶时的头奖

        ifelse (cap > 0)[;封顶时
           ;let ecost (50000 * cost)
          set current-first-price current-first-price + K * tickets
        ]
        [;不封顶时
          ;set pool pool + ecost - jackpot * tickets
           set current-first-price current-first-price + jackpot * tickets
          ;set year-wealth year-wealth + jackpot * tickets
        ]
      ]
      [;;;;中其它奖抵扣奖池
       if lottery_types = 0[;powerball

        if odds < p2 * 100000[;win p-5
          set current-other-price current-other-price + 100
          set total-winning total-winning + (100 * 10000) ; 记录中奖金额
        ]

            if odds < p3 * 100000[;win p-4+powerball
          set current-other-price current-other-price + 5
          set total-winning total-winning + (5 * 10000)
        ]

            if odds < p4 * 36523[;win p-4
          set current-other-price current-other-price + 0.01 * 2.73
          set total-winning total-winning + (0.01 * 2.73 * 10000)
        ]

                if odds < p5 * 14492[;win p-3+powerball
          set current-other-price current-other-price + 0.01 * 6.9
          set total-winning total-winning + (0.01 * 6.9 * 10000)
        ]

                  if odds < p6 * 579[;win p-3
          set current-other-price current-other-price + 0.0007 * 172.71
          set total-winning total-winning + (0.0007 * 172.71 * 10000)
        ]

                    if odds < p7 * 714[;win p-2+powerball
          set current-other-price current-other-price + 0.0007 * 140
          set total-winning total-winning + (0.0007 * 140 * 10000)
        ]

                      if odds < p8 * 91.979[;win p-1+powerball
          set current-other-price current-other-price + 0.0004 * 1087
          set total-winning total-winning + (0.0004 * 1087 * 10000)
        ]

                        if odds < p9 * 32[;win p-powerball
          set current-other-price current-other-price + 0.0004 * 2631
          set total-winning total-winning + (0.0004 * 2631 * 10000)
        ]
                      ]


      if lottery_types = 1[;red-blue ball

          if odds < p2 * 1000000[;win p2
          set current-other-price current-other-price + j2 / 10
          set total-winning total-winning + ((j2 / 10) * 10000)
          ;set current-j2-price current-j2-price + j2 / 10
            ;set current-j2tickets current-j2tickets + 1
        ]

            if odds < p3 * 100000[;win p3
          set current-other-price current-other-price + 0.3
          set total-winning total-winning + (0.3 * 10000)
        ]

            if odds < p4 * 2304[;win p4
          set current-other-price current-other-price + 0.02 * 43.4
          set total-winning total-winning + (0.02 * 43.4 * 10000)
        ]

            if odds < p5 * 128.9[;win p5
          set current-other-price current-other-price + 0.001 * 775.8
          set total-winning total-winning + (0.001 * 775.8 * 10000)
        ]

                  if odds < p6 * 16.98[;win p6
          set current-other-price current-other-price + 0.0005 * 5889.3
          set total-winning total-winning + (0.0005 * 5889.3 * 10000)
        ]

     ]

     ;;; === 新增：更新净收益 ===
     set net-gain total-winning - total-spending

    ]
    ]

   [; 如果财富不购，无法买彩票，财富不变
   ; set year-wealth year-wealth
    set tickets 0
    ;set buyers buyers
    ;set holders holders
    ;set total-tickets total-tickets
    ;set buy buy
  ]
  ] [
    ; 如果不购买彩票，财富不变
    ;set year-wealth year-wealth
    set tickets 0
   ; set buyers buyers
    ;set holders holders
    ;set total-tickets total-tickets
    ;set buy buy
  ]
end











to update-pool  ;更新奖池
  if cap = 0 [;powerball pool
    ifelse(winners > 0)[
     ;set pool current-tickets * c * 100000 - current-other-price
     ;set pool 2000 * 0.48
      set pool (1 / p) * (2000 / 292201338) * (1 - tax)
    ][
      set pool pool + (current-tickets * c * 100000 * (1 - tax) - current-other-price) ;
    ]
  ]

  if cap = 1 [;双色球奖池
    set lowprize current-tickets * 100000 * (p3 * 0.3 + p4 * 0.02 + p5 * 0.001 + p6 * 0.0005)
    set highprize current-tickets * c * 100000 * (1 - tax) - lowprize;current-tickets * c * 100000 * (1 - tax) - current-other-price + current-j2-price
    set current-j2tickets current-tickets * 100000 * p2
    set current-j2-price highprize * 0.25
    ;set j2 highprize * 0.25 /  current-j2tickets
  ifelse (current-wintickets > 0)[;有人中奖时
  ifelse (pool < 10000)[;奖池低于1亿时

    set K min list ((0.75 * highprize + pool) / current-wintickets) low_cap
  ]
  [;奖池高于1亿时
    set highprize current-tickets * c * 100000 * (1 - tax) - current-other-price
        ;set low_cap (1 / p) * (500 / 17700000) + add_cap
    let K-1 min list ((0.55 * highprize + pool) / current-wintickets) low_cap
    let K-2 min list (0.20 * highprize / current-wintickets) low_cap
    set K K-1 + K-2
  ]
  ]
  [;无人中奖时
     ifelse (pool < 10000)[;奖池小于1亿时
       set K k_para / p
      ]
     [; 奖池大于1亿时
    set K (random low_cap) + low_cap
      ]
  ]
    ifelse (current-j2tickets > 0)[
    set j2 min list (highprize * 0.25 / current-j2tickets) 500
    ]
    [;无人中二等奖
    ]
    let current-price current-first-price + current-other-price ;当期返奖等于一等奖返奖金额+其它奖返奖金额
    let abandon-rate (random-float 0.24) + 0.76
    set pool pool + ((current-tickets * c * 100000 * (1 - tax)) - k * current-wintickets - current-j2-price - lowprize * abandon-rate) * (1)
    set pool max list pool 0
  ]

  if lottery_types = 2 [;Euromillions pool封顶额规则
     set highprize current-tickets * c * 100000 * (1 - tax)
   ifelse (current-wintickets > 0)[;有中奖的情况
   ;  set K max list (min list ((pool + highprize) / current-wintickets) high_cap) low_cap
    ]
    [;无中奖情况
   ;   set K max list (min list pool high_cap) low_cap
    ]
    set highprize current-tickets * c * 100000 * (1 - tax)
    set pool max list (pool + highprize - k * current-wintickets) 0
  ]

end


to move
let x-position lottery-tickets / 4 ; 1000 代表总代理人数
set xcor x-position / 40

  ;;; === 原有：统计经常购买彩票的人数 ===
  ifelse(buy > total-periods / 150)[
    set year-buyer 1
  ]
  [
    set year-buyer 0
  ]
  ifelse(buy > total-periods / 12.5)[
    set month-buyer 1
  ]
  [
    set month-buyer 0
  ]
  ifelse(buy > total-periods / 3)[
    set week-buyer 1
  ]
  [
    set week-buyer 0
  ]
  ifelse(buy > 1)[
    set once-buyer 1
  ]
  [
    set once-buyer 0
  ]

  ;;; === 新增：购买频率分类 (按用户要求) ===
  ; 经常购买者：每月至少 1 次 (buy > total-periods/12)
  ifelse (buy > total-periods / 12) [
    set freq-regular 1
    set freq-casual 0
    set freq-none 0
  ]
  [
    ; 一般购买者：每年几次 (buy > total-periods/150 且 <= total-periods/12)
    ifelse (buy > total-periods / 150) [
      set freq-regular 0
      set freq-casual 1
      set freq-none 0
    ]
    [
      ; 不感兴趣：超过一年才购买一次或从不购买 (buy <= total-periods/150)
      set freq-regular 0
      set freq-casual 0
      set freq-none 1
    ]
  ]

end





to update-lorenz-plot
 ; 绘制表示财富分布绝对均衡的斜线
 clear-plot
  set-current-plot-pen "equal"
  plot 0
  plot 1
  ;绘制表示财富分布极端不均衡的折线
  set-current-plot-pen "dominant"
  plot-pen-down
  plotxy 0 0
  plotxy 1 0
  plotxy 1 1
  plot-pen-up
  ;绘制洛伦兹曲线
  set-current-plot-pen "lorenz"
  set-plot-pen-interval 1 / agents
  plot 0

  let sorted-wealths sort [year-wealth] of turtles
  let total-wealth sum sorted-wealths
  let wealth-sum-so-far 0
  let index 0
  let gini 0

  repeat agents [
    set wealth-sum-so-far (wealth-sum-so-far + item index sorted-wealths)
    plot (wealth-sum-so-far / total-wealth)
    set index (index + 1)
    set gini gini + ((index / agents) - (wealth-sum-so-far / total-wealth)) / agents
  ]
    set-current-plot "gini"
  plot gini * 2
; set gini2 (gini * 2)
 ; report gini2
end

to-report gini_2
  let sorted-wealths sort [year-wealth] of turtles
  let total-wealth sum sorted-wealths
  let wealth-sum-so-far 0
  let index 0
  let gini 0
 repeat agents [
    set wealth-sum-so-far (wealth-sum-so-far + item index sorted-wealths)
    set index (index + 1)
    set gini gini + ((index / agents) - (wealth-sum-so-far / total-wealth)) / agents
  ]
  set gini2 gini * 2
  report gini2
end

to-report generate-pareto [alpha]
  let u random-float 1
  report (1 - u) ^ (1 / (1 - alpha))
  end

 to-report wealth-max
  let max-wealth-value max [year-wealth] of turtles
  report max-wealth-value
end

to-report wealth-min
  let min-wealth-value min [year-wealth] of turtles
  report min-wealth-value
end

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
to-report high-income-people-ratio
  let high-income-people count turtles with [color = green]
  let H-ratio high-income-people / agents
  report H-ratio
end

to-report low-income-people-ratio
  let low-income-people count turtles with [color = red]
  let L-ratio low-income-people / agents
  report L-ratio
end

to-report middle-income-people-ratio
  let middle-income-people count turtles with [color = blue]
  let M-ratio middle-income-people / agents
  report M-ratio
end

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

to-report all-lottery
  let highincome-lottery sum [lottery-tickets] of turtles with [color = green]
  let middleincome-lottery sum [lottery-tickets] of turtles with [color = blue]
  let lowincome-lottery sum [lottery-tickets] of turtles with [color = red]
  let totallottery sum [lottery-tickets] of turtles
  ; 返回一个列表，包含高、中、低收入组的彩票数量
  report (list totallottery highincome-lottery middleincome-lottery lowincome-lottery)
end
  to-report total-lottery
  let toloto sum [lottery-tickets] of turtles
  report toloto * 200000
  end
  to-report high-income-lottery
  let hiloto sum [lottery-tickets] of turtles with [color = green]
  report hiloto * 200000
  end
  to-report middle-income-lottery
  let midloto sum [lottery-tickets] of turtles with [color = blue]
  report midloto * 200000
  end
  to-report low-income-lottery
  let loloto sum [lottery-tickets] of turtles with [color = red]
  report loloto * 200000
  end








;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
to update-lottery-tickets
 ;
 ;clear-plot
  ;高收入人群彩票销量
  set-current-plot-pen "high-income-lottery"
  plot sum [lottery-tickets] of turtles with [color = green]
  ;中等收入人群彩票销量
  set-current-plot-pen "middle-income-lottery"
  plot sum [lottery-tickets] of turtles with [color = blue]
  ;低收入人群彩票销量
 set-current-plot-pen "low-income-lottery"
  plot sum [lottery-tickets] of turtles with [color = red]
  set-current-plot-pen "total-lottery"
  plot sum [lottery-tickets] of turtles
end
;to-report  all-tickets








  to-report high-income-agents-proportion
  let HIL sum [tickets] of turtles with [color = green]
  let LIL sum [tickets] of turtles with [color = red]
  let MIL sum [tickets] of turtles with [color = blue]
  let totallottery sum [tickets] of turtles
  ifelse (total-lottery > 0) [
    report HIL / totallottery
  ] [
    report 0 ; 避免除以0错误
  ]
end

to-report JK
  report K
end
to-report jackpotcap
  report low_cap
  report high_cap
end
to-report E-R
  report ER
end
 to-report pool-amount
  report pool
end

to-report  the-current-wintickets
  report  current-wintickets
end

to-report  num-winners
  report  winners
end

to-report the-num-k
  report num-k
end

to-report add-cap
  report add_cap
end

to-report add-para
  if cap = 1 [; 双色球封顶额规则
    set k_para 500 / 17721088
  ]
  set add_para p * 2 * add_cap / (c - 2 * k_para)
  report add_para
end
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;


  to-report all-participation
  ; 高参与 (绿色)
  let HIP sum [holders] of turtles with [color = green]
  let total-high count turtles with [color = green]
  let highparticipation ifelse-value (total-high > 0) [
    HIP / total-high
  ] [
    0
  ]

  ; 中参与 (蓝色)
  let MIP sum [holders] of turtles with [color = blue]
  let total-middle count turtles with [color = blue]
  let middleparticipation ifelse-value (total-middle > 0) [
    MIP / total-middle
  ] [
    0
  ]

  ; 低参与 (红色)
  let LIP sum [holders] of turtles with [color = red]
  let total-low count turtles with [color = red]
  let lowparticipation ifelse-value (total-low > 0) [
    LIP / total-low
  ] [
    0
  ]

  ; 总参与（所有海龟）
  let TP sum [holders] of turtles
  let total-turtles count turtles
  let totalparticipation ifelse-value (total-turtles > 0) [
    TP / total-turtles
  ] [
    0
  ]

  ; 返回一个列表，包含高、中、低及总参与率
  ;report (list high-participation middle-participation low-participation total-participation)
  report highparticipation
  report middleparticipation
  report lowparticipation
  report totalparticipation
end
to-report total-participation
  ; 总参与（所有海龟）
  let TP sum [holders] of turtles
  let total-turtles count turtles
  let totalparticipation ifelse-value (total-turtles > 0) [
    TP / total-turtles
  ] [
    0
  ]
  report totalparticipation
  end
  to-report high-participation
 ; report sum [lottery-tickets] of turtles; 高参与 (绿色)
  let HIP sum [holders] of turtles with [color = green]
  let total-high count turtles with [color = green]
  let highparticipation ifelse-value (total-high > 0) [
    HIP / total-high
  ] [
    0
  ]
  report highparticipation
  end

  to-report middle-participation
  ; 中参与 (蓝色)
  let MIP sum [holders] of turtles with [color = blue]
  let total-middle count turtles with [color = blue]
  let middleparticipation ifelse-value (total-middle > 0) [
    MIP / total-middle
  ] [
    0
  ]
  report middleparticipation
  end
  to-report low-participation
    ; 低参与 (红色)
  let LIP sum [holders] of turtles with [color = red]
  let total-low count turtles with [color = red]
  let lowparticipation ifelse-value (total-low > 0) [
    LIP / total-low
  ] [
    0
  ]
  report lowparticipation
  end
;to-report the-high-buy
 ; set-current-plot-pen "high-buyers"
 ; set high-buy count turtles with [buy > 0]
  ;report high-buy
;end

;//////////////////////////////////////////////////////////////////////////////////////////////
to update-participation
  ;高收入人群彩票销量
  set-current-plot-pen "high-participation"
  let HIP sum [holders] of turtles with [color = green]
  let h-total-holders count turtles with [color = green]
  ifelse (h-total-holders > 0) [
    plot HIP / h-total-holders
  ] [
    plot 0 ; 避免除以0错误
  ]
  ;中等收入人群彩票销量
  set-current-plot-pen "meddle-participation"
  let MIP sum [holders] of turtles with [color = blue]
  let m-total-holders count turtles with [color = blue]
  ifelse (m-total-holders > 0) [
    plot MIP / m-total-holders
  ] [
    plot 0 ; 避免除以0错误
  ]
  ;低收入人群彩票销量
  set-current-plot-pen "low-participation"
  let LIP sum [holders] of turtles with [color = red]
  let l-total-holders count turtles with [color = red]
  ifelse (l-total-holders > 0) [
    plot LIP / l-total-holders
  ] [
    plot 0 ; 避免除以0错误
  ]
  set-current-plot-pen "total-participation"
  let TP sum [holders] of turtles
  ifelse (agents > 0) [
    plot TP / agents
  ] [
    plot 0 ; 避免除以0错误
  ]
end

to update-per-participation
  ;高收入人群彩票销量
  set-current-plot-pen "high-per-participation"
  let HIP sum [per-holders] of turtles with [color = green]
  let h-total-holders count turtles with [color = green]
  ifelse (h-total-holders > 0) [
    plot HIP / h-total-holders
  ] [
    plot 0 ; 避免除以0错误
  ]
  ;中等收入人群彩票销量
  set-current-plot-pen "middle-per-participation"
  let MIP sum [per-holders] of turtles with [color = blue]
  let m-total-holders count turtles with [color = blue]
  ifelse (m-total-holders > 0) [
    plot MIP / m-total-holders
  ] [
    plot 0 ; 避免除以0错误
  ]
  ;低收入人群彩票销量
  set-current-plot-pen "low-per-participation"
  let LIP sum [per-holders] of turtles with [color = red]
  let l-total-holders count turtles with [color = red]
  ifelse (l-total-holders > 0) [
    plot LIP / l-total-holders
  ] [
    plot 0 ; 避免除以0错误
  ]
  set-current-plot-pen "total-per-participation"
  let TP sum [per-holders] of turtles
  ifelse (agents > 0) [
    plot TP / agents
  ] [
    plot 0 ; 避免除以0错误
  ]
end

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
to update-current-tickets
  set-current-plot-pen "high-current-tickets"
  let HCT sum [tickets] of turtles with [color = green]
  plot HCT * 20

  set-current-plot-pen "middle-current-tickets"
  let MCT sum [tickets] of turtles with [color = blue]
  plot MCT * 20

  set-current-plot-pen "low-current-tickets"
  let LCT sum [tickets] of turtles with [color = red]
  plot LCT * 20

  set-current-plot-pen "total-current-tickets"
  let TCT sum [tickets] of turtles
  plot TCT * 20
end
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
to update-year-buyer
  set-current-plot-pen "high-year-buyer"
  let HYB sum [year-buyer] of turtles with [color = green]
  plot HYB

  set-current-plot-pen "middle-year-buyer"
  let MYB sum [year-buyer] of turtles with [color = blue]
  plot MYB

  set-current-plot-pen "low-year-buyer"
  let LYB sum [year-buyer] of turtles with [color = red]
  plot LYB

  set-current-plot-pen "total-year-buyer"
  let TYB sum [year-buyer] of turtles
  plot TYB
end
to-report lottery-year-buyer
  let high-year-buyer sum [year-buyer] of turtles with [color = green]
  let middle-year-buyer sum [year-buyer] of turtles with [color = blue]
  let low-year-buyer sum [year-buyer] of turtles with [color = red]
  let total-year-buyer sum [year-buyer] of turtles
  ;report (list total-year-buyer high-year-buyer middle-year-buyer low-year-buyer)
  report total-year-buyer
  report high-year-buyer
  report middle-year-buyer
  report low-year-buyer
end

to update-month-buyer
  set-current-plot-pen "high-month-buyer"
  let HMB sum [month-buyer] of turtles with [color = green]
  plot HMB

  set-current-plot-pen "middle-month-buyer"
  let MMB sum [month-buyer] of turtles with [color = blue]
  plot MMB

  set-current-plot-pen "low-month-buyer"
  let LMB sum [month-buyer] of turtles with [color = red]
  plot LMB

  set-current-plot-pen "total-month-buyer"
  let TMB sum [month-buyer] of turtles
  plot TMB
end
to-report lottery-month-buyer
  let high-month-buyer sum [month-buyer] of turtles with [color = green]
  let middle-month-buyer sum [month-buyer] of turtles with [color = blue]
  let low-month-buyer sum [month-buyer] of turtles with [color = red]
  let total-month-buyer sum [month-buyer] of turtles
  ;report (list total-month-buyer high-month-buyer middle-month-buyer low-month-buyer)
  report total-month-buyer
  report high-month-buyer
  report middle-month-buyer
  report low-month-buyer
end


to update-week-buyer
  set-current-plot-pen "high-week-buyer"
  let HWB sum [week-buyer] of turtles with [color = green]
  plot HWB

  set-current-plot-pen "middle-week-buyer"
  let MWB sum [week-buyer] of turtles with [color = blue]
  plot MWB

  set-current-plot-pen "low-week-buyer"
  let LWB sum [week-buyer] of turtles with [color = red]
  plot LWB

  set-current-plot-pen "total-week-buyer"
  let TWB sum [week-buyer] of turtles
  plot TWB
end
to-report lottery-week-buyer
  let high-week-buyer sum [week-buyer] of turtles with [color = green]
  let middle-week-buyer sum [week-buyer] of turtles with [color = blue]
  let low-week-buyer sum [week-buyer] of turtles with [color = red]
  let total-week-buyer sum [week-buyer] of turtles
  ;report (list total-week-buyer high-week-buyer middle-week-buyer low-week-buyer)
  report total-week-buyer
  report high-week-buyer
  report middle-week-buyer
  report low-week-buyer
end


to update-once-buyer
  set-current-plot-pen "high-once-buyer"
  let HOB sum [once-buyer] of turtles with [color = green]
  plot HOB

  set-current-plot-pen "middle-once-buyer"
  let MOB sum [once-buyer] of turtles with [color = blue]
  plot MOB

  set-current-plot-pen "low-once-buyer"
  let LOB sum [once-buyer] of turtles with [color = red]
  plot LOB

  set-current-plot-pen "total-once-buyer"
  let TOB sum [once-buyer] of turtles
  plot TOB
end
to-report lottery-once-buyer
  let high-once-buyer sum [once-buyer] of turtles with [color = green]
  let middle-once-buyer sum [once-buyer] of turtles with [color = blue]
  let low-once-buyer sum [once-buyer] of turtles with [color = red]
  let total-once-buyer sum [once-buyer] of turtles
  ;report (list total-once-buyer high-once-buyer middle-once-buyer low-once-buyer)
  report total-once-buyer
  report high-once-buyer
  report middle-once-buyer
  report middle-once-buyer
end

;;; =====================================================
;;; === 新增：敏感性分析 reporter ===
;;; =====================================================
to-report high-buyers-count-report
  report high-buyers-count
end

to-report middle-buyers-count-report
  report middle-buyers-count
end

to-report low-buyers-count-report
  report low-buyers-count
end

to-report high-spenders-count-report
  report high-spenders-count
end

to-report middle-spenders-count-report
  report middle-spenders-count
end

to-report low-spenders-count-report
  report low-spenders-count
end

to-report year-regular-buyers-report
  report year-regular-buyers
end

to-report year-casual-buyers-report
  report year-casual-buyers
end

to-report uninterested-buyers-report
  report uninterested-buyers
end

to-report high-income-frequent-report
  report high-income-frequent
end

to-report middle-income-frequent-report
  report middle-income-frequent
end

to-report low-income-frequent-report
  report low-income-frequent
end

to-report avg-spending-report
  ifelse count turtles > 0 [
    report (sum [total-spending] of turtles) / count turtles
  ] [
    report 0
  ]
end

to-report avg-winning-report
  ifelse count turtles > 0 [
    report (sum [total-winning] of turtles) / count turtles
  ] [
    report 0
  ]
end

to-report avg-net-gain-report
  ifelse count turtles > 0 [
    report (sum [net-gain] of turtles) / count turtles
  ] [
    report 0
  ]
end

;;; 按收入分组的平均支出
to-report high-income-avg-spending
  let hi-turtles turtles with [color = green]
  ifelse count hi-turtles > 0 [
    report (sum [total-spending] of hi-turtles) / count hi-turtles
  ] [
    report 0
  ]
end

to-report middle-income-avg-spending
  let mi-turtles turtles with [color = blue]
  ifelse count mi-turtles > 0 [
    report (sum [total-spending] of mi-turtles) / count mi-turtles
  ] [
    report 0
  ]
end

to-report low-income-avg-spending
  let li-turtles turtles with [color = red]
  ifelse count li-turtles > 0 [
    report (sum [total-spending] of li-turtles) / count li-turtles
  ] [
    report 0
  ]
end


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
to update-histogram-buy
  set-current-plot-pen "total-buy"
  set-plot-pen-mode 1
  let num-buy [buy] of turtles  ;统计buy中的购买人数最多的buy
  let max-buy max [buy] of turtles ;统计turtles中最大的购买次数buy
  let y-range count turtles with [buy = num-buy]
  let x-range max-buy + 1;total-periods + 1
  set-plot-x-range 0 x-range
  set-plot-y-range 0 y-range + 1
  histogram [buy] of turtles
end
to update-histogram-lottery-tickets
  set-current-plot-pen "total-tickets"
  set-plot-pen-mode 1
  let num-tickets [lottery-tickets] of turtles  ;统计lottery-tickets中的购买人数最多的lottery-tickets
  let max-tickets max [lottery-tickets] of turtles ; 统计turtles中，购买彩票量最大的lottery-tickets
  let y-range2 count turtles with [lottery-tickets = num-tickets]
  let x-range2 max-tickets + 1;total-periods + 1
  set-plot-x-range 0 x-range2
  set-plot-y-range 0 y-range2 + 1
  histogram [lottery-tickets] of turtles
end
@#$#@#$#@
GRAPHICS-WINDOW
190
13
1473
422
-1
-1
25.0
1
10
1
1
1
0
1
1
1
0
50
0
15
0
0
1
ticks
50.0

BUTTON
21
13
84
46
NIL
SETUP
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
111
16
174
49
NIL
go
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

PLOT
1747
18
2012
226
participation
times
participation%
0.0
10.0
0.0
1.0
true
false
"" "update-participation"
PENS
"high-participation" 1.0 0 -13840069 true "" ""
"low-participation" 1.0 0 -5298144 true "" ""
"total-participation" 1.0 0 -16777216 true "" ""
"meddle-participation" 1.0 0 -14730904 true "" ""

PLOT
818
423
1135
629
pool-amount
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot pool-amount"

PLOT
1741
230
2013
433
num-winners
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot num-winners"

PLOT
1480
20
1740
225
the-num-k
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot the-num-k"

SLIDER
11
49
183
82
agents
agents
0
20000
11480.0
100
1
NIL
HORIZONTAL

PLOT
268
422
493
626
total-tickets
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" "update-lottery-tickets"
PENS
"high-income-lottery" 1.0 0 -13840069 true "" ""
"low-income-lottery" 1.0 0 -2674135 true "" ""
"middle-income-lottery" 1.0 0 -14070903 true "" ""
"total-lottery" 1.0 0 -16777216 true "" ""

PLOT
1484
433
1871
635
Lorenz curve
population %
wealth %
0.0
1.0
0.0
1.0
true
true
"" "update-lorenz-plot"
PENS
"lorenz" 1.0 0 -2674135 true "" ""
"equal" 1.0 0 -7500403 true "" ""
"dominant" 1.0 0 -16449023 true "" ""

PLOT
1498
257
1696
414
gini
time
gini
0.0
1.0
0.0
1.0
true
false
"" ""
PENS
"gini" 1.0 0 -16777216 true "" ""

PLOT
11
444
266
644
per-participation
times
participation%
0.0
10.0
0.0
0.1
true
false
"" "update-per-participation"
PENS
"total-per-participation" 1.0 0 -16777216 true "" ""
"high-per-participation" 1.0 0 -13840069 true "" ""
"middle-per-participation" 1.0 0 -14070903 true "" ""
"low-per-participation" 1.0 0 -5298144 true "" ""

PLOT
492
422
815
627
current-tickets
time
tickets
0.0
10.0
0.0
10.0
true
false
"" "update-current-tickets"
PENS
"total-current-tickets" 1.0 0 -16777216 true "" ""
"high-current-tickets" 1.0 0 -13840069 true "" ""
"middle-current-tickets" 1.0 0 -13345367 true "" ""
"low-current-tickets" 1.0 0 -2674135 true "" ""

SLIDER
11
262
183
295
c
c
0
10
2.0E-4
0.0002
1
NIL
HORIZONTAL

PLOT
1138
426
1406
629
the-current-wintickets
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot the-current-wintickets"

SLIDER
11
120
183
153
lottery_types
lottery_types
0
5
0.0
1
1
NIL
HORIZONTAL

PLOT
24
678
224
828
Lowprize
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"" 1.0 0 -16777216 true "" "plot lowprize"

PLOT
2032
184
2232
334
year-buyer
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" "update-year-buyer"
PENS
"total-year-buyer" 1.0 0 -16777216 true "" ""
"high-year-buyer" 1.0 0 -13840069 true "" ""
"middle-year-buyer" 1.0 0 -13791810 true "" ""
"low-year-buyer" 1.0 0 -2674135 true "" ""

PLOT
2033
32
2233
182
once-buyer
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" "update-once-buyer"
PENS
"total-once-buyer" 1.0 0 -16777216 true "" ""
"low-once-buyer" 1.0 0 -2674135 true "" ""
"middle-once-buyer" 1.0 0 -13345367 true "" ""
"high-once-buyer" 1.0 0 -13840069 true "" ""

PLOT
2033
335
2233
485
month-buyer
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" "update-month-buyer"
PENS
"total-month-buyer" 1.0 0 -16777216 true "" ""
"low-month-buyer" 1.0 0 -2674135 true "" ""
"middle-month-buyer" 1.0 0 -13345367 true "" ""
"high-month-buyer" 1.0 0 -13840069 true "" ""

PLOT
2034
490
2234
640
week-buyer
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" "update-week-buyer"
PENS
"total-week-buyer" 1.0 0 -16777216 true "" ""
"low-week-buyer" 1.0 0 -2674135 true "" ""
"middle-week-buyer" 1.0 0 -13345367 true "" ""
"high-week-buyer" 1.0 0 -13840069 true "" ""

SLIDER
9
191
181
224
cap
cap
0
1
1.0
1
1
NIL
HORIZONTAL

PLOT
1202
673
1402
823
OJ
NIL
NIL
0.0
10.0
0.0
3.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot ER"

PLOT
1004
672
1204
822
J2
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot j2"

PLOT
803
672
1003
822
JC
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot jc"

PLOT
427
681
627
831
Current-j2tickets
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot current-j2tickets"

PLOT
226
680
426
830
Current-j2-price
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot current-j2-price"

SLIDER
10
156
182
189
country
country
0
2
1.0
1
1
NIL
HORIZONTAL

PLOT
624
680
824
830
K
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot K"

SLIDER
11
87
183
120
p
p
0
1
3.4E-9
0.0000000001
1
NIL
HORIZONTAL

PLOT
909
71
1383
388
histogram-buy
NIL
NIL
0.0
500.0
0.0
1000.0
true
true
"" "update-histogram-buy"
PENS
"total-buy" 1.0 0 -16777216 true "" ""

PLOT
386
74
884
387
histogram-tickets
NIL
NIL
0.0
10.0
0.0
10.0
true
true
"" "update-histogram-lottery-tickets"
PENS
"total-tickets" 1.0 0 -16777216 true "" ""

SLIDER
7
304
179
337
u-sr
u-sr
5000
25000
8500.0
500
1
NIL
HORIZONTAL

SLIDER
7
372
179
405
u-con
u-con
0
1
0.1485
0.01
1
NIL
HORIZONTAL

SLIDER
8
406
180
439
sd-con
sd-con
0
1
0.035
0.037
1
NIL
HORIZONTAL

SLIDER
7
337
179
370
sd-sr
sd-sr
100
3000
2000.0
500
1
NIL
HORIZONTAL

SLIDER
10
227
182
260
add_cap
add_cap
-1000
10000
100.0
100
1
NIL
HORIZONTAL

@#$#@#$#@
## WHAT IS IT?

(a general understanding of what the model is trying to show or explain)

## HOW IT WORKS

(what rules the agents use to create the overall behavior of the model)

## HOW TO USE IT

(how to use the model, including a description of each of the items in the Interface tab)

## THINGS TO NOTICE

(suggested things for the user to notice while running the model)

## THINGS TO TRY

(suggested things for the user to try to do (move sliders, switches, etc.) with the model)

## EXTENDING THE MODEL

(suggested things to add or change in the Code tab to make the model more complicated, detailed, accurate, etc.)

## NETLOGO FEATURES

(interesting or unusual features of NetLogo that the model uses, particularly in the Code tab; or where workarounds were needed for missing features)

## RELATED MODELS

(models in the NetLogo Models Library and elsewhere which are of related interest)

## CREDITS AND REFERENCES

(a reference to the model's URL on the web if it has one, as well as any other necessary credits, citations, and links)
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

airplane
true
0
Polygon -7500403 true true 150 0 135 15 120 60 120 105 15 165 15 195 120 180 135 240 105 270 120 285 150 270 180 285 210 270 165 240 180 180 285 195 285 165 180 105 180 60 165 15

arrow
true
0
Polygon -7500403 true true 150 0 0 150 105 150 105 293 195 293 195 150 300 150

box
false
0
Polygon -7500403 true true 150 285 285 225 285 75 150 135
Polygon -7500403 true true 150 135 15 75 150 15 285 75
Polygon -7500403 true true 15 75 15 225 150 285 150 135
Line -16777216 false 150 285 150 135
Line -16777216 false 150 135 15 75
Line -16777216 false 150 135 285 75

bug
true
0
Circle -7500403 true true 96 182 108
Circle -7500403 true true 110 127 80
Circle -7500403 true true 110 75 80
Line -7500403 true 150 100 80 30
Line -7500403 true 150 100 220 30

butterfly
true
0
Polygon -7500403 true true 150 165 209 199 225 225 225 255 195 270 165 255 150 240
Polygon -7500403 true true 150 165 89 198 75 225 75 255 105 270 135 255 150 240
Polygon -7500403 true true 139 148 100 105 55 90 25 90 10 105 10 135 25 180 40 195 85 194 139 163
Polygon -7500403 true true 162 150 200 105 245 90 275 90 290 105 290 135 275 180 260 195 215 195 162 165
Polygon -16777216 true false 150 255 135 225 120 150 135 120 150 105 165 120 180 150 165 225
Circle -16777216 true false 135 90 30
Line -16777216 false 150 105 195 60
Line -16777216 false 150 105 105 60

car
false
0
Polygon -7500403 true true 300 180 279 164 261 144 240 135 226 132 213 106 203 84 185 63 159 50 135 50 75 60 0 150 0 165 0 225 300 225 300 180
Circle -16777216 true false 180 180 90
Circle -16777216 true false 30 180 90
Polygon -16777216 true false 162 80 132 78 134 135 209 135 194 105 189 96 180 89
Circle -7500403 true true 47 195 58
Circle -7500403 true true 195 195 58

circle
false
0
Circle -7500403 true true 0 0 300

circle 2
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240

cow
false
0
Polygon -7500403 true true 200 193 197 249 179 249 177 196 166 187 140 189 93 191 78 179 72 211 49 209 48 181 37 149 25 120 25 89 45 72 103 84 179 75 198 76 252 64 272 81 293 103 285 121 255 121 242 118 224 167
Polygon -7500403 true true 73 210 86 251 62 249 48 208
Polygon -7500403 true true 25 114 16 195 9 204 23 213 25 200 39 123

cylinder
false
0
Circle -7500403 true true 0 0 300

dot
false
0
Circle -7500403 true true 90 90 120

face happy
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 255 90 239 62 213 47 191 67 179 90 203 109 218 150 225 192 218 210 203 227 181 251 194 236 217 212 240

face neutral
false
0
Circle -7500403 true true 8 7 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Rectangle -16777216 true false 60 195 240 225

face sad
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 168 90 184 62 210 47 232 67 244 90 220 109 205 150 198 192 205 210 220 227 242 251 229 236 206 212 183

fish
false
0
Polygon -1 true false 44 131 21 87 15 86 0 120 15 150 0 180 13 214 20 212 45 166
Polygon -1 true false 135 195 119 235 95 218 76 210 46 204 60 165
Polygon -1 true false 75 45 83 77 71 103 86 114 166 78 135 60
Polygon -7500403 true true 30 136 151 77 226 81 280 119 292 146 292 160 287 170 270 195 195 210 151 212 30 166
Circle -16777216 true false 215 106 30

flag
false
0
Rectangle -7500403 true true 60 15 75 300
Polygon -7500403 true true 90 150 270 90 90 30
Line -7500403 true 75 135 90 135
Line -7500403 true 75 45 90 45

flower
false
0
Polygon -10899396 true false 135 120 165 165 180 210 180 240 150 300 165 300 195 240 195 195 165 135
Circle -7500403 true true 85 132 38
Circle -7500403 true true 130 147 38
Circle -7500403 true true 192 85 38
Circle -7500403 true true 85 40 38
Circle -7500403 true true 177 40 38
Circle -7500403 true true 177 132 38
Circle -7500403 true true 70 85 38
Circle -7500403 true true 130 25 38
Circle -7500403 true true 96 51 108
Circle -16777216 true false 113 68 74
Polygon -10899396 true false 189 233 219 188 249 173 279 188 234 218
Polygon -10899396 true false 180 255 150 210 105 210 75 240 135 240

house
false
0
Rectangle -7500403 true true 45 120 255 285
Rectangle -16777216 true false 120 210 180 285
Polygon -7500403 true true 15 120 150 15 285 120
Line -16777216 false 30 120 270 120

leaf
false
0
Polygon -7500403 true true 150 210 135 195 120 210 60 210 30 195 60 180 60 165 15 135 30 120 15 105 40 104 45 90 60 90 90 105 105 120 120 120 105 60 120 60 135 30 150 15 165 30 180 60 195 60 180 120 195 120 210 105 240 90 255 90 263 104 285 105 270 120 285 135 240 165 240 180 270 195 240 210 180 210 165 195
Polygon -7500403 true true 135 195 135 240 120 255 105 255 105 285 135 285 165 240 165 195

line
true
0
Line -7500403 true 150 0 150 300

line half
true
0
Line -7500403 true 150 0 150 150

pentagon
false
0
Polygon -7500403 true true 150 15 15 120 60 285 240 285 285 120

person
false
0
Circle -7500403 true true 110 5 80
Polygon -7500403 true true 105 90 120 195 90 285 105 300 135 300 150 225 165 300 195 300 210 285 180 195 195 90
Rectangle -7500403 true true 127 79 172 94
Polygon -7500403 true true 195 90 240 150 225 180 165 105
Polygon -7500403 true true 105 90 60 150 75 180 135 105

plant
false
0
Rectangle -7500403 true true 135 90 165 300
Polygon -7500403 true true 135 255 90 210 45 195 75 255 135 285
Polygon -7500403 true true 165 255 210 210 255 195 225 255 165 285
Polygon -7500403 true true 135 180 90 135 45 120 75 180 135 210
Polygon -7500403 true true 165 180 165 210 225 180 255 120 210 135
Polygon -7500403 true true 135 105 90 60 45 45 75 105 135 135
Polygon -7500403 true true 165 105 165 135 225 105 255 45 210 60
Polygon -7500403 true true 135 90 120 45 150 15 180 45 165 90

sheep
false
15
Circle -1 true true 203 65 88
Circle -1 true true 70 65 162
Circle -1 true true 150 105 120
Polygon -7500403 true false 218 120 240 165 255 165 278 120
Circle -7500403 true false 214 72 67
Rectangle -1 true true 164 223 179 298
Polygon -1 true true 45 285 30 285 30 240 15 195 45 210
Circle -1 true true 3 83 150
Rectangle -1 true true 65 221 80 296
Polygon -1 true true 195 285 210 285 210 240 240 210 195 210
Polygon -7500403 true false 276 85 285 105 302 99 294 83
Polygon -7500403 true false 219 85 210 105 193 99 201 83

square
false
0
Rectangle -7500403 true true 30 30 270 270

square 2
false
0
Rectangle -7500403 true true 30 30 270 270
Rectangle -16777216 true false 60 60 240 240

star
false
0
Polygon -7500403 true true 151 1 185 108 298 108 207 175 242 282 151 216 59 282 94 175 3 108 116 108

target
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240
Circle -7500403 true true 60 60 180
Circle -16777216 true false 90 90 120
Circle -7500403 true true 120 120 60

tree
false
0
Circle -7500403 true true 118 3 94
Rectangle -6459832 true false 120 195 180 300
Circle -7500403 true true 65 21 108
Circle -7500403 true true 116 41 127
Circle -7500403 true true 45 90 120
Circle -7500403 true true 104 74 152

triangle
false
0
Polygon -7500403 true true 150 30 15 255 285 255

triangle 2
false
0
Polygon -7500403 true true 150 30 15 255 285 255
Polygon -16777216 true false 151 99 225 223 75 224

truck
false
0
Rectangle -7500403 true true 4 45 195 187
Polygon -7500403 true true 296 193 296 150 259 134 244 104 208 104 207 194
Rectangle -1 true false 195 60 195 105
Polygon -16777216 true false 238 112 252 141 219 141 218 112
Circle -16777216 true false 234 174 42
Rectangle -7500403 true true 181 185 214 194
Circle -16777216 true false 144 174 42
Circle -16777216 true false 24 174 42
Circle -7500403 false true 24 174 42
Circle -7500403 false true 144 174 42
Circle -7500403 false true 234 174 42

turtle
true
0
Polygon -10899396 true false 215 204 240 233 246 254 228 266 215 252 193 210
Polygon -10899396 true false 195 90 225 75 245 75 260 89 269 108 261 124 240 105 225 105 210 105
Polygon -10899396 true false 105 90 75 75 55 75 40 89 31 108 39 124 60 105 75 105 90 105
Polygon -10899396 true false 132 85 134 64 107 51 108 17 150 2 192 18 192 52 169 65 172 87
Polygon -10899396 true false 85 204 60 233 54 254 72 266 85 252 107 210
Polygon -7500403 true true 119 75 179 75 209 101 224 135 220 225 175 261 128 261 81 224 74 135 88 99

wheel
false
0
Circle -7500403 true true 3 3 294
Circle -16777216 true false 30 30 240
Line -7500403 true 150 285 150 15
Line -7500403 true 15 150 285 150
Circle -7500403 true true 120 120 60
Line -7500403 true 216 40 79 269
Line -7500403 true 40 84 269 221
Line -7500403 true 40 216 269 79
Line -7500403 true 84 40 221 269

wolf
false
0
Polygon -16777216 true false 253 133 245 131 245 133
Polygon -7500403 true true 2 194 13 197 30 191 38 193 38 205 20 226 20 257 27 265 38 266 40 260 31 253 31 230 60 206 68 198 75 209 66 228 65 243 82 261 84 268 100 267 103 261 77 239 79 231 100 207 98 196 119 201 143 202 160 195 166 210 172 213 173 238 167 251 160 248 154 265 169 264 178 247 186 240 198 260 200 271 217 271 219 262 207 258 195 230 192 198 210 184 227 164 242 144 259 145 284 151 277 141 293 140 299 134 297 127 273 119 270 105
Polygon -7500403 true true -1 195 14 180 36 166 40 153 53 140 82 131 134 133 159 126 188 115 227 108 236 102 238 98 268 86 269 92 281 87 269 103 269 113

x
false
0
Polygon -7500403 true true 270 75 225 30 30 225 75 270
Polygon -7500403 true true 30 75 75 30 270 225 225 270
@#$#@#$#@
NetLogo 6.4.0
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
<experiments>
  <experiment name="pb-test" repetitions="1" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <timeLimit steps="1500"/>
    <metric>K</metric>
    <metric>low_cap</metric>
    <metric>current-tickets</metric>
    <metric>all-lottery</metric>
    <metric>pool-amount</metric>
    <metric>all-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="agents">
      <value value="11480"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="c">
      <value value="2.0E-4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lottery_types">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="country">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="cap">
      <value value="1"/>
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="P">
      <value value="1.0E-9"/>
      <value value="5.65E-9"/>
      <value value="1.0E-8"/>
      <value value="5.65E-8"/>
      <value value="7.14E-8"/>
      <value value="1.0E-7"/>
      <value value="5.0E-6"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="powerball 11.26" repetitions="1" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <timeLimit steps="1500"/>
    <metric>K</metric>
    <metric>current-tickets</metric>
    <metric>all-lottery</metric>
    <metric>pool-amount</metric>
    <metric>all-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="c">
      <value value="2.0E-4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lottery_types">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="agents">
      <value value="2608"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="p">
      <value value="3.4E-8"/>
      <value value="1.0E-8"/>
      <value value="6.8E-9"/>
      <value value="3.4E-9"/>
      <value value="1.0E-9"/>
      <value value="6.8E-10"/>
      <value value="3.4E-10"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="cap">
      <value value="0"/>
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="country">
      <value value="0"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="red-blue powerball" repetitions="1" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <timeLimit steps="1500"/>
    <metric>K</metric>
    <metric>current-tickets</metric>
    <metric>all-lottery</metric>
    <metric>pool-amount</metric>
    <metric>all-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="c">
      <value value="2.0E-4"/>
    </enumeratedValueSet>
    <subExperiment>
      <enumeratedValueSet variable="lottery_types">
        <value value="1"/>
      </enumeratedValueSet>
      <enumeratedValueSet variable="cap">
        <value value="1"/>
      </enumeratedValueSet>
      <enumeratedValueSet variable="country">
        <value value="1"/>
      </enumeratedValueSet>
      <enumeratedValueSet variable="p">
        <value value="5.65E-8"/>
      </enumeratedValueSet>
    </subExperiment>
    <subExperiment>
      <enumeratedValueSet variable="lottery_types">
        <value value="0"/>
      </enumeratedValueSet>
      <enumeratedValueSet variable="cap">
        <value value="0"/>
      </enumeratedValueSet>
      <enumeratedValueSet variable="country">
        <value value="0"/>
      </enumeratedValueSet>
      <enumeratedValueSet variable="p">
        <value value="3.4E-9"/>
      </enumeratedValueSet>
    </subExperiment>
  </experiment>
  <experiment name="only red-blue ball" repetitions="2" runMetricsEveryStep="true">
    <setup>setup
set lottery_types 1
set c 2.0E-4
set agents 11480
set p 5.65E-8
set cap 1
set country 1</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>K</metric>
    <metric>current-tickets</metric>
    <metric>total-lottery</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>pool-amount</metric>
    <metric>all-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <steppedValueSet variable="sr" first="7000" step="100" last="8000"/>
    <steppedValueSet variable="convenience" first="0.1" step="0.02" last="0.2"/>
  </experiment>
  <experiment name="test-powerball" repetitions="1" runMetricsEveryStep="true">
    <setup>setup
set c 2.0E-4
set lottery_types 0
set p 3.4E-9
set agents 2608
set cap 0
set country 0</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>pool-amount</metric>
    <metric>JK</metric>
    <metric>current-tickets</metric>
    <metric>total-lottery</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>high-participation</metric>
    <metric>middle-participation</metric>
    <metric>low-participation</metric>
    <metric>total-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <subExperiment>
      <steppedValueSet variable="sr" first="16000" step="1000" last="18000"/>
      <steppedValueSet variable="convenience" first="0.1" step="0.1" last="0.3"/>
    </subExperiment>
    <subExperiment>
      <steppedValueSet variable="sr" first="19000" step="1000" last="21000"/>
      <steppedValueSet variable="convenience" first="0.3" step="0.1" last="0.7"/>
    </subExperiment>
    <subExperiment>
      <steppedValueSet variable="sr" first="22000" step="1000" last="24000"/>
      <steppedValueSet variable="convenience" first="0.6" step="0.1" last="1"/>
    </subExperiment>
    <subExperiment>
      <enumeratedValueSet variable="sr">
        <value value="25000"/>
      </enumeratedValueSet>
      <steppedValueSet variable="convenience" first="0.7" step="0.1" last="1"/>
    </subExperiment>
  </experiment>
  <experiment name="test-powerball (copy)" repetitions="9" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>pool-amount</metric>
    <metric>current-tickets</metric>
    <metric>total-lottery</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>all-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="c">
      <value value="2.0E-4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lottery_types">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="p">
      <value value="3.4E-9"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="agents">
      <value value="2608"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="cap">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="country">
      <value value="0"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="pb stochastic parameters" repetitions="9" runMetricsEveryStep="true">
    <setup>setup
set c 2.0E-4
set lottery_types 0
set p 3.4E-9
set agents 2608
set cap 0
set country 0</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>JK</metric>
    <metric>pool-amount</metric>
    <metric>current-tickets</metric>
    <metric>total-lottery</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>high-participation</metric>
    <metric>middle-participation</metric>
    <metric>low-participation</metric>
    <metric>total-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="upper-sr">
      <value value="24000"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lower-sr">
      <value value="19000"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="upper-con">
      <value value="0.9"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lower-con">
      <value value="0.433"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="rbb stochastic parameters" repetitions="9" runMetricsEveryStep="true">
    <setup>setup
set lottery_types 1
set c 2.0E-4
set agents 11480
set p 5.65E-8
set cap 1
set country 1</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>JK</metric>
    <metric>pool-amount</metric>
    <metric>current-tickets</metric>
    <metric>total-lottery</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>high-participation</metric>
    <metric>middle-participation</metric>
    <metric>low-participation</metric>
    <metric>total-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="upper-con">
      <value value="0.9"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="upper-sr">
      <value value="24000"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lower-sr">
      <value value="19000"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lower-con">
      <value value="0.443"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="rbb normal" repetitions="9" runMetricsEveryStep="true">
    <setup>setup
set lottery_types 1
set c 2.0E-4
set agents 11480
set p 5.65E-8
set cap 1
set country 1</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>JK</metric>
    <metric>pool-amount</metric>
    <metric>current-tickets</metric>
    <metric>total-lottery</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>high-participation</metric>
    <metric>middle-participation</metric>
    <metric>low-participation</metric>
    <metric>total-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="sd-sr">
      <value value="2000"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="sd-con">
      <value value="0.035"/>
    </enumeratedValueSet>
    <subExperiment>
      <enumeratedValueSet variable="u-sr">
        <value value="8500"/>
      </enumeratedValueSet>
      <enumeratedValueSet variable="u-con">
        <value value="0.1485"/>
      </enumeratedValueSet>
    </subExperiment>
  </experiment>
  <experiment name="pb normal" repetitions="100" runMetricsEveryStep="true">
    <setup>setup
set c 2.0E-4
set lottery_types 0
set p 3.4E-9
set agents 2608
set cap 0
set country 0</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>JK</metric>
    <metric>pool-amount</metric>
    <metric>current-tickets</metric>
    <metric>total-lottery</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>high-participation</metric>
    <metric>middle-participation</metric>
    <metric>low-participation</metric>
    <metric>total-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="sd-sr">
      <value value="1300"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="sd-con">
      <value value="0.1"/>
    </enumeratedValueSet>
    <subExperiment>
      <enumeratedValueSet variable="u-sr">
        <value value="18000"/>
      </enumeratedValueSet>
      <enumeratedValueSet variable="u-con">
        <value value="0.28"/>
      </enumeratedValueSet>
    </subExperiment>
  </experiment>
  <experiment name="rbb-cap-test" repetitions="6" runMetricsEveryStep="true">
    <setup>setup
set lottery_types 1
set c 2.0E-4
set agents 11480
set cap 1
set country 1</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>add-para</metric>
    <metric>JK</metric>
    <metric>pool-amount</metric>
    <metric>current-tickets</metric>
    <metric>the-num-k</metric>
    <metric>total-lottery</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>high-participation</metric>
    <metric>middle-participation</metric>
    <metric>low-participation</metric>
    <metric>total-participation</metric>
    <metric>lottery-once-buyer</metric>
    <metric>lottery-year-buyer</metric>
    <metric>lottery-month-buyer</metric>
    <metric>lottery-week-buyer</metric>
    <enumeratedValueSet variable="p">
      <value value="5.65E-8"/>
    </enumeratedValueSet>
    <steppedValueSet variable="add_cap" first="0" step="100" last="4000"/>
  </experiment>
  <experiment name="JackpotCap_Full_Sensitivity_45runs" repetitions="9" runMetricsEveryStep="true">
    <setup>setup
set c 0.0002
set lottery_types 1
set agents 11480
set p 0.0000000565
set cap 1
set country 1
set u-con 0.0568
set sd-con 0.000027
set u-sr 355.16
set sd-sr 0.729</setup>
    <go>go</go>
    <timeLimit steps="1800"/>
    <metric>ticks</metric>
    <metric>total-periods</metric>
    <metric>pool</metric>
    <metric>K</metric>
    <metric>add_cap</metric>
    <metric>total-tickets</metric>
    <metric>buyers</metric>
    <metric>gini_2</metric>
    <metric>high-buyers-count-report</metric>
    <metric>middle-buyers-count-report</metric>
    <metric>low-buyers-count-report</metric>
    <metric>high-spenders-count-report</metric>
    <metric>middle-spenders-count-report</metric>
    <metric>low-spenders-count-report</metric>
    <metric>year-regular-buyers-report</metric>
    <metric>year-casual-buyers-report</metric>
    <metric>uninterested-buyers-report</metric>
    <metric>high-income-frequent-report</metric>
    <metric>middle-income-frequent-report</metric>
    <metric>low-income-frequent-report</metric>
    <metric>avg-spending-report</metric>
    <metric>avg-winning-report</metric>
    <metric>avg-net-gain-report</metric>
    <metric>high-income-avg-spending</metric>
    <metric>middle-income-avg-spending</metric>
    <metric>low-income-avg-spending</metric>
    <metric>high-income-lottery</metric>
    <metric>middle-income-lottery</metric>
    <metric>low-income-lottery</metric>
    <metric>high-participation</metric>
    <metric>middle-participation</metric>
    <metric>low-participation</metric>
    <metric>total-participation</metric>
    <steppedValueSet variable="add_cap" first="-500" step="100" last="3000"/>
  </experiment>
</experiments>
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
0
@#$#@#$#@
