# GNSS 领域知识库 — 文献检索策略内置词库（中英双语）

> 用途：GNSS 测试厂商文献调研 Agent 的内置领域知识（关键词词库 / 期刊会议白名单 / 调研主题示例 / 检索策略）。
> 本文档面向产品经理与算法工程师，所有术语均经过 web 检索交叉验证（验证来源见文末附录）。
> 对接目标：`app/domain/terms.py`（见 §6 数据结构建议，与架构文档 `docs/ARCHITECTURE.md` 中 `app/domain/terms.py` 一致）。

---

## 1. GNSS 子领域关键词词库（英文）

> 通用约定：
> - 主流学术检索引擎（OpenAlex、Scopus、Web of Science、Semantic Scholar、IEEE Xplore）默认**大小写不敏感**，故本词库不重复大小写变体；仅在检索 API 大小写敏感或需精确短语匹配时，才提示变体。
> - 连字符/斜杠变体需显式列出，因为各引擎分词规则不同：如 `PPP-RTK` vs `PPP RTK` vs `PPP/RTK`、`GNSS/INS` vs `GNSS-INS` vs `INS/GNSS`。
> - 每个子领域给出 **8–20 个**核心检索词，含同义词/变体；标注 `[ph]` 的词建议加英文引号做短语精确匹配。

### 1.1 Receiver Testing & Conformance（接收机测试与认证）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | GNSS receiver testing | 通用主题词 |
| 2 | receiver conformance testing | 一致性/符合性测试 |
| 3 | GNSS test standard | 配合具体标准号检索更佳 |
| 4 | RF interference testing | 射频干扰测试 |
| 5 | PVT accuracy | Position-Velocity-Time 精度 |
| 6 | positioning accuracy | 定位精度（通用） |
| 7 | time to first fix (TTFF) | 首次定位时间；变体：`TTFF`、`time-to-first-fix` |
| 8 | cold start / warm start / hot start | 冷/温/热启动（TTFF 测试场景） |
| 9 | acquisition sensitivity | 捕获灵敏度 |
| 10 | tracking sensitivity | 跟踪灵敏度 |
| 11 | carrier-to-noise ratio (C/N0) | 载噪比；变体：`C/N0`、`CN0`、`carrier-to-noise` |
| 12 | dilution of precision (DOP) | 精度因子；变体：`PDOP`、`HDOP`、`VDOP`、`GDOP` |
| 13 | timing accuracy | 授时精度（见 §1.7） |
| 14 | 1PPS | one-pulse-per-second 秒脉冲 |
| 15 | assisted GNSS (A-GNSS) | 辅助定位测试 |
| 16 | conformance test scenario | 一致性测试场景 |
| 17 | 3GPP TS 37.571 | 蜂窝终端 GNSS 一致性测试标准（搜索时建议短语匹配） |
| 18 | EN 16803 / ETSI EN 303 413 | 道路 ITS / 接收设备欧洲标准 |
| 19 | IEC 61108 | 海事 GNSS 接收机性能标准 |
| 20 | field testing / drive test | 外场测试/路测（可归入 §1.11 仿真验证） |

**检索提示**：测试类主题在学术库中命中偏少，大量内容在标准文本（3GPP/ETSI/RTCM）与厂商白皮书（Spirent/Keysight、u-blox、Septentrio）中，建议检索时额外开启"标准/技术报告"类型过滤，或搭配 `verification`、`characterization`、`benchmark` 等词。

### 1.2 High-Precision Positioning（高精度定位）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | RTK / real-time kinematic | 实时动态定位；变体：`real-time kinematic (RTK)` |
| 2 | precise point positioning (PPP) | 精密单点定位；变体：`precise point positioning` |
| 3 | PPP-RTK `[ph]` | 变体：`PPP RTK`、`PPP/RTK`；近年热点（见 [PPP-RTK: a review and recent developments](https://cemse.kaust.edu.sa/events/by-type/seminar/2023/05/01/ppp-rtk-review-and-recent-developments#1)） |
| 4 | PPK / post-processed kinematic | 动态后处理 |
| 5 | integer ambiguity resolution | 整周模糊度解算 |
| 6 | ambiguity resolution (AR) | 变体：`ambiguity fixing`、`ambiguity-fixed solution` |
| 7 | network RTK | 网络 RTK |
| 8 | virtual reference station (VRS) | 虚拟参考站；变体：`VRS` |
| 9 | master-auxiliary concept (MAC) | 主辅站技术 |
| 10 | FKP | 区域改正参数（德语 Flächenkorrekturparameter） |
| 11 | state space representation (SSR) | 状态空间表示（PPP-RTK/精密服务核心） |
| 12 | observation space representation (OSR) | 观测值空间表示 |
| 13 | convergence time | 收敛时间（PPP/PPP-RTK 关键指标） |
| 14 | carrier phase measurement | 载波相位观测 |
| 15 | wide-lane / narrow-lane | 宽巷/窄巷组合；变体：`WL`、`NL` |
| 16 | ionosphere-free combination | 无电离层组合 |
| 17 | LAMBDA | 模糊度最小二乘去相关算法 |
| 18 | ambiguity dilution of precision (ADOP) | 模糊度精度因子 |
| 19 | PPP-B2b | 北斗星基 PPP 服务（可归 §1.10） |
| 20 | differential GNSS (DGNSS) | 差分定位 |

### 1.3 Integrity（完好性）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | RAIM | receiver autonomous integrity monitoring |
| 2 | ARAIM | advanced RAIM（多星座高级 RAIM） |
| 3 | integrity monitoring | 完好性监测 |
| 4 | protection level (PL) | 保护级；变体：`HPL`（水平）、`VPL`（垂直）、`protection level calculation` |
| 5 | alert limit (AL) | 告警限值；变体：`HAL`、`VAL` |
| 6 | fault detection and exclusion (FDE) | 故障检测与排除；变体：`fault detection`、`FDE` |
| 7 | integrity risk | 完好性风险（完好性预算的量化指标） |
| 8 | continuity risk | 连续性风险 |
| 9 | availability | 可用性（完好性性能指标之一） |
| 10 | solution separation | 解分离法（ARAIM/FDE 主流算法，见 [Blanch 2021 ION GNSS+ FDE 论文](https://web.stanford.edu/group/scpnt/gpslab/pubs/papers/Blanch_IONGNSS_2021_FDE.pdf)） |
| 11 | integrity support message (ISM) | 完好性支持信息（ARAIM 地面段播发） |
| 12 | time to alert (TTA) | 告警时间 |
| 13 | GBAS / ground-based augmentation system | 地基增强系统 |
| 14 | LAAS | 局域增强系统（GBAS 的 FAA 版本） |
| 15 | SBAS | 星基增强（与 §1.9 交叉，见 [Navipedia SBAS Systems](https://www.navipedia.org/navipedia/index.php?title=SBAS_Systems)） |
| 16 | integrity for autonomous driving | 自动驾驶完好性（应用向） |

### 1.4 Multipath & Urban Environment（多路径与城市环境）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | multipath | 多路径；变体：`multipath effect`、`multipath error`、`multipath mitigation` |
| 2 | NLOS / non-line-of-sight | 非视距信号；变体：`NLOS reception`、`NLOS signal` |
| 3 | urban canyon | 城市峡谷；变体：`urban canyons`、`dense urban`、`deep urban` |
| 4 | 3D mapping aided (3DMA) | 三维地图辅助定位（见 [3D-Mapping-Aided GNSS Navigation in Urban Canyons](https://core.ac.uk/works/160450514/)） |
| 5 | 3D building model | 三维建筑模型 |
| 6 | GNSS shadow matching | 阴影匹配（3DMA 代表算法） |
| 7 | sky visibility / skyplot | 天空可见性/天空图 |
| 8 | pseudorange multipath | 伪距多径 |
| 9 | carrier phase multipath | 载波相位多径 |
| 10 | code multipath | 码多径 |
| 11 | signal reflection / diffraction | 信号反射/衍射（城市传播机理） |
| 12 | elevation mask angle | 仰角截止角 |
| 13 | ray tracing | 射线追踪（多径建模） |
| 14 | smartphone positioning | 智能手机定位（城市场景热点） |
| 15 | multipath rejection / multipath estimator | 多径抑制算法（如 MEE、DP、MEDLL） |
| 16 | NLOS exclusion / NLOS correction | 非视距剔除/改正 |

### 1.5 Ionosphere & Troposphere（电离层与对流层）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | ionospheric scintillation | 电离层闪烁（低纬/赤道地区重点） |
| 2 | total electron content (TEC) | 电子总含量；变体：`TEC`、`VTEC` |
| 3 | TEC map / global ionosphere map (GIM) | 电离层 TEC 图/全球电离层图 |
| 4 | ionospheric delay | 电离层延迟 |
| 5 | ionospheric error correction | 电离层误差改正 |
| 6 | Klobuchar model | 广播电离层模型 |
| 7 | NeQuick model | 欧洲电离层模型（Galileo 广播使用） |
| 8 | ionospheric gradient | 电离层梯度（GBAS 完好性关注） |
| 9 | phase scintillation / amplitude scintillation | 相位/振幅闪烁 |
| 10 | S4 index | 振幅闪烁指数 |
| 11 | sigma-phi (σφ) index | 相位闪烁指数 |
| 12 | tropospheric delay | 对流层延迟 |
| 13 | zenith tropospheric delay (ZTD) | 天顶对流层延迟；变体：`ZTD`、`zenith wet delay (ZWD)` |
| 14 | tropospheric mapping function | 对流层映射函数（如 VMF3、GPT3） |
| 15 | wet delay / hydrostatic delay | 湿延迟/干延迟 |
| 16 | scintillation mitigation | 闪烁抑制（如 [Geodetic Detrending 技术](https://ieeexplore.ieee.org/document/9262461)） |

### 1.6 Interference & Anti-Interference（干扰与抗干扰）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | GNSS spoofing / spoofing attack | 欺骗干扰；变体：`spoofing detection`、`anti-spoofing` |
| 2 | GNSS jamming / jamming attack | 压制干扰；变体：`anti-jamming`、`jamming mitigation` |
| 3 | interference detection | 干扰检测 |
| 4 | interference mitigation | 干扰抑制 |
| 5 | radio frequency interference (RFI) | 射频干扰 |
| 6 | meaconing | 转发式欺骗/中继欺骗 |
| 7 | GNSS security | GNSS 安全（泛指） |
| 8 | navigation message authentication (NMA) | 导航电文认证 |
| 9 | signal authentication | 信号认证（含 SCA/spreading code authentication） |
| 10 | jamming-to-noise ratio (J/N) | 干噪比 |
| 11 | continuous wave interference (CWI) | 连续波干扰 |
| 12 | chirp jamming | 线性调频干扰（常见 PPD 干扰源） |
| 13 | array antenna / anti-jamming array | 阵列天线抗干扰 |
| 14 | null steering / adaptive beamforming | 调零/自适应波束形成 |
| 15 | space-time adaptive processing (STAP) | 空时自适应处理 |
| 16 | personal privacy device (PPD) | 个人隐私设备（干扰机） |
| 17 | C/N0 monitoring | 载噪比监测（干扰检测手段） |
| 18 | spoofing detection survey / comprehensive review | 综述检索用词（见 [GNSS Spoofing and Jamming Mitigation: A Comprehensive Review](https://ieeexplore.ieee.org/document/11165996)） |

### 1.7 Timing & Synchronization（授时与同步）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | GNSS timing | GNSS 授时 |
| 2 | time synchronization | 时间同步 |
| 3 | disciplined oscillator | 驯服振荡器；变体：`GNSS-disciplined oscillator (GNSSDO)`、`rubidium discipline` |
| 4 | PTP / IEEE 1588 | 精密时间协议；变体：`PTP grandmaster`、`IEEE 1588` |
| 5 | NTP / network time protocol | 网络时间协议 |
| 6 | coordinated universal time (UTC) | 协调世界时 |
| 7 | GNSS common-view time transfer | 共视时间比对 |
| 8 | two-way satellite time and frequency transfer (TWSTFT) | 卫星双向时间频率比对 |
| 9 | time transfer | 时间传递（通用） |
| 10 | time interval measurement | 时间间隔测量 |
| 11 | holdover | 保持能力（授时接收机失锁后维持精度） |
| 12 | 1PPS / pulse per second | 秒脉冲（授时接口） |
| 13 | frequency accuracy / frequency stability | 频率准确度/稳定度 |
| 14 | Allan deviation | Allan 方差（频率稳定度度量） |
| 15 | 5G timing / time synchronization for 5G | 5G 网络授时（3GPP 同步要求） |
| 16 | time-sensitive networking (TSN) | 时间敏感网络 |
| 17 | leap second | 闰秒 |
| 18 | White Rabbit | 亚纳秒级同步协议 |

### 1.8 Integrated Navigation（组合导航）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | GNSS/INS integration | 组合导航；变体：`INS/GNSS`、`GNSS-INS`、`GNSS/INS` |
| 2 | loosely coupled / tightly coupled | 松耦合/紧耦合；变体：`loosely-coupled`、`tightly-coupled` |
| 3 | deeply coupled / ultra-tight coupling | 深耦合/超紧耦合 |
| 4 | factor graph | 因子图（优化框架） |
| 5 | factor graph optimization / graph optimization | 因子图优化（见 [GNSS/IMU 紧-松耦合因子图融合](http://ch.whu.edu.cn/cn/article/doi/10.13203/j.whugis20220321)） |
| 6 | sensor fusion | 传感器融合 |
| 7 | Kalman filter / extended Kalman filter (EKF) | 卡尔曼滤波/扩展卡尔曼滤波 |
| 8 | error state Kalman filter (ESKF) | 误差状态卡尔曼滤波 |
| 9 | inertial navigation system (INS) | 惯性导航系统 |
| 10 | MEMS IMU | 微机械惯性测量单元 |
| 11 | visual-inertial navigation | 视觉惯性导航 |
| 12 | visual-inertial odometry (VIO) | 视觉惯性里程计 |
| 13 | visual-inertial-wheel odometry (VIWO) | 视觉-惯性-轮速里程计（见 [Robust optimization-based fusion of GNSS and Visual-Inertial-Wheel Odometry](https://ieeexplore.ieee.org/abstract/document/10011839)） |
| 14 | SLAM | 同步定位与建图 |
| 15 | LiDAR-GNSS fusion | 激光雷达-GNSS 融合 |
| 16 | dead reckoning | 航位推算 |
| 17 | zero velocity update (ZUPT) | 零速修正 |
| 18 | state estimation | 状态估计（通用） |

### 1.9 SBAS & Regional Augmentation（星基增强与区域增强）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | SBAS / satellite-based augmentation system | 星基增强系统（见 [Navipedia SBAS Systems](https://www.navipedia.org/navipedia/index.php?title=SBAS_Systems)） |
| 2 | WAAS | 美国广域增强系统 |
| 3 | EGNOS | 欧洲静地导航重叠服务 |
| 4 | GAGAN | 印度 GPS 辅助静地增强导航 |
| 5 | MSAS | 日本多功能卫星增强系统 |
| 6 | SDCM | 俄罗斯差分改正监测系统 |
| 7 | BDSBAS | 北斗星基增强系统 |
| 8 | QZSS / Michibiki | 日本准天顶卫星系统 |
| 9 | KASS | 韩国增强卫星系统 |
| 10 | dual-frequency SBAS / DFMC SBAS | 双频多星座 SBAS（L1/L5 时代方向） |
| 11 | L1/L5 dual frequency | L1/L5 双频（SBAS/接收机通用词，亦属 §1.10） |
| 12 | ionospheric grid point (IGP) | 电离层格网点（SBAS 改正播发） |
| 13 | SBAS corrections / augmentation message | SBAS 改正/增强信息 |
| 14 | integrity broadcast | 完好性信息播发 |
| 15 | regional augmentation system | 区域增强系统（泛称） |

### 1.10 New Signals & New Paradigms（新信号与新体制）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | dual-frequency / multi-frequency GNSS | 双频/多频接收机 |
| 2 | L5 / E5a / B1C / B2a | 各系统新民用信号（BDS-3、Galileo、GPS 现代化） |
| 3 | Galileo High Accuracy Service (HAS) | Galileo 高精度服务 |
| 4 | QZSS CLAS | 厘米级增强服务（centimeter-level augmentation service） |
| 5 | PPP-B2b | 北斗星基 PPP 服务（见 [PPP-B2b、HAS、CLAS 性能对比](https://www.sciencedirect.com/science/article/abs/pii/S0273117724003764)） |
| 6 | LEO PNT / LEO navigation | 低轨卫星导航增强（见 [LEO PNT 系统发展与关键技术问题](https://dhdwyss.spacejournal.cn/article/doi/10.19306/j.cnki.2095-8110.2026.03.001)） |
| 7 | LEO augmentation | 低轨增强 |
| 8 | low Earth orbit positioning | 低轨定位 |
| 9 | BDS-3 / BeiDou-3 | 北斗三号 |
| 10 | GPS modernization / modernized GPS | GPS 现代化（L2C/L5/L1C） |
| 11 | new GNSS signals | 新体制信号（泛称） |
| 12 | signals of opportunity | 机会信号（导航增强前沿） |
| 13 | GNSS-R / reflectometry | 反射测量（遥感向，可选） |
| 14 | L6 band | QZSS L6（CLAS 载波） |
| 15 | multi-constellation | 多星座（与多频常组合检索） |

### 1.11 Simulation & Verification（仿真与验证）

| # | 关键词 | 说明/变体 |
|---|---|---|
| 1 | GNSS simulator | GNSS 信号模拟器 |
| 2 | RF constellation simulator | 射频星座模拟器（厂商术语，如 [Spirent（现 Keysight）PNT 模拟器](https://www.keysight.com/se/en/cmp/2026/spirent.html)） |
| 3 | hardware-in-the-loop (HIL) | 硬件在环测试 |
| 4 | GNSS signal simulation | 信号级仿真 |
| 5 | scenario simulation | 场景仿真 |
| 6 | record and replay | 信号采集回放；变体：`signal replay`、`record & replay` |
| 7 | field testing / road testing | 外场/道路测试 |
| 8 | static test / kinematic test | 静态/动态测试 |
| 9 | test repeatability | 测试可重复性（模拟器核心价值） |
| 10 | interference scenario simulation | 干扰场景仿真 |
| 11 | multipath simulation | 多径仿真（城市峡谷场景建模） |
| 12 | high-fidelity simulation | 高保真仿真 |
| 13 | GNSS test bench | 测试平台/测试台 |
| 14 | emulator | 仿真器（与 simulator 常互换） |
| 15 | lab testing vs field testing | 室内外测试对比 |
| 16 | verification and validation (V&V) | 验证与确认（GNSS 系统工程） |

---

## 2. 中文关键词词库（按同一子领域分组）

> 中文检索主要面向 CNKI/万方/维普（无官方 API，产品内做人工/爬虫扩展或转引英文库）；北斗语境下注意与官方术语一致（中国卫星导航系统管理办公室 CSNO 白皮书、《北斗卫星导航系统术语》标准）。

### 2.1 接收机测试与认证
接收机测试、接收机性能测试、一致性测试、符合性测试、卫星导航信号模拟器、信号模拟器、射频干扰测试、PVT 精度、定位精度、测速精度、授时精度、首次定位时间（TTFF）、冷启动、热启动、温启动、捕获灵敏度、跟踪灵敏度、载噪比（C/N0）、精度因子（DOP）、水平精度因子、垂直精度因子、1PPS、测试场景、路测、外场测试、标准符合性、计量检定、北斗用户设备测试

### 2.2 高精度定位
RTK 定位、实时动态定位、精密单点定位（PPP）、PPP-RTK、动态后处理（PPK）、整周模糊度、模糊度固定、模糊度解算、LAMBDA、网络 RTK、虚拟参考站（VRS）、主辅站技术（MAC）、区域改正参数（FKP）、状态空间表示（SSR）、观测值空间表示（OSR）、收敛时间、载波相位、双差观测、宽巷、窄巷、无电离层组合、差分定位、精密定位

### 2.3 完好性
完好性、完好性监测、接收机自主完好性监测（RAIM）、高级 RAIM（ARAIM）、保护级、保护水平、水平保护级、垂直保护级、告警限值、故障检测与排除（FDE）、故障检测、完好性风险、连续性风险、可用性、解分离法、完好性支持信息、告警时间、地基增强系统（GBAS）、局域增强系统（LAAS）、星基增强系统（SBAS）、完好性监测技术、导航完好性

### 2.4 多路径与城市环境
多路径、多径效应、多径误差、多径抑制、非视距（NLOS）、非视距信号、城市峡谷、密集城区、三维地图辅助定位（3DMA）、三维建筑模型、阴影匹配、信号反射、信号衍射、伪距多径、载波相位多径、仰角截止角、射线追踪、智能手机定位、城市环境定位、遮挡

### 2.5 电离层与对流层
电离层、电离层延迟、电离层闪烁、电离层闪烁监测、闪烁指数、S4 指数、电子总含量（TEC）、TEC 图、全球电离层图、电离层改正、Klobuchar 模型、NeQuick 模型、电离层梯度、对流层延迟、天顶对流层延迟（ZTD）、对流层映射函数、湿延迟、干延迟、大气延迟改正、闪烁抑制

### 2.6 干扰与抗干扰
欺骗干扰、欺骗检测、抗欺骗、转发欺骗、中继欺骗、诱骗、压制干扰、干扰检测、干扰抑制、抗干扰、射频干扰（RFI）、导航电文认证、信号认证、干信比、干噪比、连续波干扰、线性调频干扰、阵列天线抗干扰、自适应调零、波束形成、空时自适应处理（STAP）、干扰监测、个人隐私设备、卫星导航抗干扰

### 2.7 授时与同步
授时、卫星授时、北斗授时、时间同步、时间传递、共视时间比对、共视比对、卫星双向时间比对（TWSTFT）、驯服晶振、驯服铷钟、守时、保持能力（holdover）、1PPS、时间间隔测量、频率准确度、频率稳定度、Allan 方差、PTP（IEEE 1588）、NTP、5G 授时、同步以太网、时钟比对、UTC

### 2.8 组合导航
组合导航、GNSS/INS 组合、惯性导航、惯性/卫星组合、松耦合、紧耦合、深耦合、超紧耦合、因子图、因子图优化、传感器融合、卡尔曼滤波、扩展卡尔曼滤波、误差状态卡尔曼滤波、MEMS 惯导、视觉惯性导航、视觉惯性里程计（VIO）、轮速里程计、SLAM、激光雷达融合、航位推算、零速修正（ZUPT）、状态估计

### 2.9 星基增强与区域增强
星基增强、星基增强系统（SBAS）、广域增强、WAAS、EGNOS、GAGAN、MSAS、SDCM、北斗星基增强（BDSBAS）、准天顶卫星系统（QZSS）、区域增强、增强系统、双频增强、电离层格网点（IGP）、增强信息播发、完好性信息播发

### 2.10 新信号与新体制
双频、多频、双频接收机、多频接收机、L1/L5、B1C、B2a、北斗三号（BDS-3）、Galileo 高精度服务（HAS）、QZSS CLAS、厘米级增强服务、PPP-B2b、星基 PPP、低轨增强、低轨卫星导航增强（LEO PNT）、低轨导航、低轨星座、GPS 现代化、新体制信号、多星座

### 2.11 仿真与验证
信号模拟器、卫星导航模拟器、星座模拟器、硬件在环（HIL）、场景仿真、信号回放、采集回放、外场测试、路测、动态测试、静态测试、测试平台、可重复性、高保真仿真、干扰场景仿真、多径仿真、验证与确认（V&V）、测试评估

---

## 3. GNSS 期刊与会议白名单（venue 白名单）

> 使用方式：在 OpenAlex 的 `primary_location.source.display_name`、Semantic Scholar 的 `venue`、Crossref 的 `container-title`、WoS 的 `SO` 字段做**归一化后精确匹配**（需先小写 + 去标点/去空格归一化）。匹配命中即加权（建议白名单命中 +0.15~0.3 相关分）。**注意同一期刊的中英文名都要收录**（如 测绘学报 / Acta Geodaetica et Cartographica Sinica）。

### 3.1 英文期刊（权威性从高到低分组）

| 期刊名 | 出版方 | 影响力说明（检索验证） |
|---|---|---|
| **NAVIGATION** (Journal of the Institute of Navigation) | Institute of Navigation (ION)，开放获取 | GNSS 领域旗舰期刊；JIF ≈ 2.7（Q2 SCIE），见 [ION 官网](https://www.ion.org/navi/) |
| **GPS Solutions** | Springer | 高精度定位（PPP/RTK/多星座）核心期刊，见 [Springer 期刊页](https://link.springer.com/journal/10291) |
| **Journal of Geodesy** | Springer | 大地测量与卫星定位理论核心期刊 |
| **Journal of Navigation** | Cambridge University Press / Royal Institute of Navigation (RIN) | 导航学会老牌期刊，覆盖 GNSS/航海/航空 |
| **IEEE Transactions on Aerospace and Electronic Systems** | IEEE | 航空航天电子系统旗舰（完好性/信号处理/抗干扰大户） |
| **IEEE Transactions on Intelligent Transportation Systems** | IEEE | 智能交通定位（自动驾驶 GNSS 应用） |
| **IEEE Transactions on Vehicular Technology** | IEEE | 车载定位与通信 |
| **Sensors** | MDPI | 开放获取量大，GNSS 定位/多径/融合论文多 |
| **Remote Sensing** | MDPI | 开放获取，电离层/TEC/GNSS-R 遥感向 |
| **Measurement Science and Technology** | IOP | 测量方法与仪器测试方法学（接收机计量） |
| **IET Radar, Sonar & Navigation** | IET | 雷达/声呐/导航（信号处理向） |
| **Advances in Space Research** | Elsevier / COSPAR | 空间研究（LEO PNT、电离层、轨道） |
| **GPS World / Inside GNSS** | (industry magazines) | 非同行评议的行业杂志，适合趋势扫描，**不建议**纳入学术白名单过滤，可单列"行业媒体"分组 |

### 3.2 中文期刊

| 期刊名（中/英） | 出版方/主办 | 影响力说明 |
|---|---|---|
| **测绘学报** / Acta Geodaetica et Cartographica Sinica | 中国测绘学会 | 国内测绘地信权威期刊（EI、CSCD 核心），影响因子常年居测绘类榜首 |
| **武汉大学学报（信息科学版）** / Geomatics and Information Science of Wuhan University | 武汉大学 | EI 核心，卫星定位/北斗论文大户（见 [因子图融合定位论文](http://ch.whu.edu.cn/cn/article/doi/10.13203/j.whugis20220321)） |
| **中国惯性技术学报** / Journal of Chinese Inertial Technology | 中国惯性技术学会 | 惯性/组合导航权威期刊 |
| **导航定位学报** / Journal of Navigation and Positioning | 中国卫星导航定位协会 | 导航定位应用型期刊 |
| **导航定位与授时** / Navigation Positioning and Timing | 北京航天控制仪器研究所 | 覆盖导航/定位/授时三方向（见 [期刊官网](https://dhdwyss.spacejournal.cn)） |
| **全球定位系统** / GNSS World of China | 中国电子科技集团第 22 研究所 | GNSS 应用技术期刊 |
| **测绘科学技术学报** / Journal of Geomatics Science and Technology | 信息工程大学 | 测绘导航技术 |
| **大地测量与地球动力学** / Journal of Geodesy and Geodynamics | 中国地震局地震研究所 | 地学与 GNSS 交叉 |
| **电子测量与仪器学报** / Journal of Electronic Measurement and Instrumentation | 中国电子学会 | 测量仪器（接收机计量测试向） |
| **宇航计测技术** / Journal of Astronautic Metrology and Measurement | 北京航天计量测试技术研究所 | 航天计量测试（授时/频率校准向） |
| **无线电工程** / Radio Engineering | 中国电子科技集团第 54 研究所 | 干扰监测综述等工程论文（见 [低空卫星导航干扰监测综述](https://wxdg.cbpt.cnki.net/portal/journal/portal/client/paper/753f8b8193c995fc03673ab8b95bc054)） |
| **航空学报** / Acta Aeronautica et Astronautica Sinica | 中国航空学会 | 无人机抗干扰等航空导航论文（见 [无人机卫星导航抗干扰综述](https://hkxb.buaa.edu.cn/CN/abstract/abstract20684.shtml)） |
| **天文学进展** / Progress in Astronomy | 中国科学院上海天文台 | 电离层闪烁检测方法等（见 [基于 GNSS 的电离层闪烁检测方法进展](https://qikan.cqvip.com/Qikan/Article/Detail?id=7202626158)） |

### 3.3 会议（Proceedings 白名单）

| 会议名（中/英） | 主办方 | 说明 |
|---|---|---|
| **ION GNSS+**（原 ION GNSS） | Institute of Navigation (ION) | GNSS 领域影响力最大的年度会议；论文在 [ION 出版物库](https://www.ion.org/publications/browse.cfm?proceedingsID=167) 可查 |
| **ION ITM** (International Technical Meeting) | ION | ION 年度国际技术会议 |
| **ION PNT**（原 PTTI） | ION | 导航/授时会议（授时主题重点） |
| **IEEE/ION PLANS** (Position, Location and Navigation Symposium) | IEEE + ION | 定位导航顶级联合会议 |
| **European Navigation Conference (ENC)** | EURINET | 欧洲导航会议 |
| **Munich Satellite Navigation Summit** | 慕尼黑 | 行业峰会（趋势报告向，论文少） |
| **China Satellite Navigation Conference (CSNC 中国卫星导航年会)** | 中国卫星导航系统管理办公室等 | 国内北斗领域最高级别学术会议；论文集由 Springer (Lecture Notes in Electrical Engineering) 出版，见 [CSNC 2020 Proceedings](https://franklin.library.upenn.edu/catalog/FRANKLIN_9977848542703681) |
| **中国卫星导航学术年会**（旧称） | 同上 | CSNC 早期名称，检索历史文献时注意 |
| **ISGNSS** (International Symposium on GNSS) | 各国轮流 | 亚太 GNSS 学术会议 |
| **ITSNT** (International Technical Symposium on Navigation and Timing) | CNES/ENAC 等 | 导航与授时技术研讨会 |

### 3.4 白名单落地建议（供工程参考）

```python
VENUE_WHITELIST = {
  "en": ["navigation", "gps solutions", "journal of geodesy", "journal of navigation",
         "ieee transactions on aerospace and electronic systems",
         "ieee transactions on intelligent transportation systems", "sensors", "remote sensing",
         "measurement science and technology", "iet radar, sonar & navigation",
         "advances in space research", "proceedings of ion gnss+"],
  "zh": ["测绘学报", "武汉大学学报（信息科学版）", "中国惯性技术学报", "导航定位学报",
         "全球定位系统", "导航定位与授时", "无线电工程", "航空学报", "宇航计测技术"],
  "normalize": "lowercase + strip spaces/punct/hyphens before match",  # 例如 "IET Radar, Sonar & Navigation" → "ietradarsonarnavigation"
  "weight_boost": 0.2,   # venue 命中的相关分加成
}
```

---

## 4. 典型调研主题示例（15 个，中英双语）

> 可直接作为产品 UI 的"示例主题"按钮文案；每条标注其覆盖的调研类型（技术趋势 / 竞品对比 / 标准合规 / 算法选型 / 测试方法学）与关联子领域。

| # | 中文主题（UI 示例） | English Topic | 类型 | 关联子领域 |
|---|---|---|---|---|
| 1 | 城市峡谷环境下 RTK 接收机多路径抑制算法的研究进展 | Research progress on multipath mitigation algorithms for RTK receivers in urban canyon environments | 算法选型 | 1.2/1.4 |
| 2 | GNSS 欺骗干扰检测与抗欺骗技术的研究现状与趋势 | State of the art and trends in GNSS spoofing detection and anti-spoofing techniques | 技术趋势 | 1.6 |
| 3 | 电离层闪烁对双频/多频 GNSS 接收机定位性能的影响与缓解方法 | Impact of ionospheric scintillation on dual-/multi-frequency GNSS receiver positioning and mitigation approaches | 算法选型 | 1.5/1.10 |
| 4 | RTK 与 PPP-RTK 定位精度与收敛时间的技术对比 | Technical comparison of RTK and PPP-RTK: accuracy and convergence time | 竞品对比 | 1.2 |
| 5 | GNSS/INS 紧耦合与深耦合组合导航在汽车定位中的应用进展 | Progress of tightly- and deeply-coupled GNSS/INS integration for automotive positioning | 算法选型 | 1.8 |
| 6 | RAIM/ARAIM 完好性监测技术在自动驾驶高精度定位中的可用性研究 | Availability of RAIM/ARAIM integrity monitoring for high-precision positioning in autonomous driving | 技术趋势 | 1.3 |
| 7 | 基于 GNSS 信号模拟器的接收机一致性测试标准与场景设计 | Conformance testing standards and scenario design for GNSS receivers using signal simulators | 标准合规/测试方法学 | 1.1/1.11 |
| 8 | 低轨卫星导航增强（LEO PNT）技术研究现状与商业化前景 | Current status and commercialization prospects of LEO satellite navigation augmentation (LEO PNT) | 技术趋势 | 1.10 |
| 9 | 5G 网络授时与 GNSS 授时技术对比及融合方案 | Comparison and fusion of 5G network timing and GNSS timing technologies | 竞品对比 | 1.7 |
| 10 | 城市峡谷场景下 GNSS 多路径与 NLOS 信号的检测与剔除方法 | Detection and exclusion of GNSS multipath and NLOS signals in urban canyon scenarios | 算法选型 | 1.4 |
| 11 | 压制式干扰对 GNSS 接收机的影响评估与阵列天线抗干扰技术 | Impact assessment of jamming on GNSS receivers and array-antenna anti-jamming techniques | 技术趋势 | 1.6 |
| 12 | Galileo HAS、QZSS CLAS 与北斗 PPP-B2b 高精度服务对比分析 | Comparative analysis of Galileo HAS, QZSS CLAS and BeiDou PPP-B2b high-accuracy services | 竞品对比 | 1.10 |
| 13 | GNSS 接收机一致性测试相关标准（3GPP TS 37.571 / ETSI EN 303 413）的要求梳理 | Review of conformance test requirements in 3GPP TS 37.571 and ETSI EN 303 413 for GNSS receivers | 标准合规 | 1.1 |
| 14 | 智能驾驶场景下 GNSS 定位性能评估方法与测试工具链 | GNSS positioning performance evaluation methodology and test toolchains for intelligent driving | 测试方法学 | 1.1/1.11 |
| 15 | GNSS 授时接收机时间同步精度与保持能力的测试方法 | Test methods for time synchronization accuracy and holdover of GNSS timing receivers | 测试方法学 | 1.7 |

---

## 5. 检索策略建议

### 5.1 每个主题的 query 组合方式

**公式：`(主题核心词) AND (子领域词 OR 组) [AND (venue 白名单)]`**

1. **主题拆词**：LLM 将用户主题解析为 2–4 个核心概念（如"城市峡谷 RTK 多路径抑制" → {RTK, multipath, urban}），每个概念取 1–3 个同义词组成 OR 组。
2. **领域词交叉**：将核心概念与 §1 内置子领域词库做 AND 组合；例如：
   - 英文：`(multipath OR NLOS OR "non-line-of-sight") AND (RTK OR "real-time kinematic") AND ("urban canyon" OR urban)`
   - 中文：`(多路径 OR NLOS OR 非视距) AND (RTK OR 实时动态) AND (城市峡谷 OR 城市环境)`
3. **短语精确匹配**：`PPP-RTK`、`time to first fix`、`integer ambiguity resolution` 等专有组合用引号（OpenAlex `search=` 与 Semantic Scholar 均支持）。
4. **子领域锚定**：query 追加子领域锚词提高精确率，如完好性主题锚定 `(integrity OR RAIM OR ARAIM)`；组合导航锚定 `(GNSS/INS OR "factor graph" OR "sensor fusion")`。
5. **venue 过滤**：命中 §3 白名单的论文加权，不硬过滤（避免漏掉非白名单期刊的优质论文）。
6. **变体展开**：对每个核心词展开连字符/斜杠变体（`PPP-RTK|PPP RTK|PPP/RTK`、`GNSS/INS|INS/GNSS`）。

### 5.2 时间范围与引用量过滤建议

| 调研类型 | 时间范围 | 引用量过滤 | 理由 |
|---|---|---|---|
| 技术趋势（如 LEO PNT、HAS/CLAS） | 近 3–5 年（2020+） | 近 3 年引用 ≥ 5，或 5 年 ≥ 20 | 新方向文献少，按年引用率排序更合理 |
| 算法选型（如多路径抑制、RAIM） | 近 10 年 + 经典回溯 | 经典文献引用 ≥ 100（如 2000–2015 奠基论文）；近期 ≥ 10 | 需同时看经典方法与最新改进 |
| 竞品/服务对比（RTK vs PPP-RTK） | 近 5 年 | ≥ 10 | 对比类综述多为近作 |
| 标准合规（3GPP/ETSI/RTCM） | 只看最新版本 | 不设引用门槛 | 标准文本不按引用排序，按发布时间取最新 |
| 测试方法学（模拟器/HIL） | 近 10 年 | ≥ 5 | 方法类论文更新慢，放宽引用 |

- **通用默认**：`year >= 2015`（近 10 年），排序 `relevance_score`；引用量仅作排序因子（`relevance × log(cited_by)`），不作硬过滤。
- **滑动扩展**：结果不足时向更早年份滑动（如每轮 -3 年），配合经典文献挖掘。

### 5.3 中英文检索结果的互补策略

| 维度 | 英文检索（OpenAlex/arXiv/S2/Crossref） | 中文检索（CNKI/万方/维普，人工或合规扩展） |
|---|---|---|
| 覆盖侧重 | 国际算法源头、标准制定（RTCM/3GPP）、厂商（u-blox/Septentrio/Spirent） | 北斗（BDS-3）专属技术、国内产业动态、国产接收机（和芯星通/华测/中海达/司南） |
| 术语对应 | 用 §1 英文词 | 用 §2 中文词，且注意中文文献常用英文缩写（RTK、RAIM 直接保留） |
| 互补策略 1 | 中文论文的参考文献列表是英文经典文献的"导流"入口 | 英文综述的"Chinese contributions"章节反查中文原文 |
| 互补策略 2 | 用英文词查全球趋势 → 再用中文词查国内落地（如 LEO PNT → 低轨增强） | 中文综述常引用英文奠基论文，可回溯英文原文补全方法细节 |
| 合并去重 | 统一按 DOI/标题归一化入库（见 `docs/SOURCES.md` §3） | 中文文献大多无 DOI，用"标题 + 作者 + 年份"做归一化键 |
| 语言输出 | 报告以中文呈现，英文论文摘要由 LLM 翻译 | 中文论文直接引用原文 |

- **官方术语源**：北斗语境优先核对中国卫星导航系统管理办公室（CSNO）白皮书与《北斗卫星导航系统术语》标准，避免中英术语混用（如"星基增强"=SBAS、"授时"=timing、"共视比对"=common-view time transfer）。

---

## 6. 数据结构建议（可直接转 Python 模块）

建议按"子领域"分组，键为子领域英文名（snake_case），值为含 `en`/`zh` 关键词列表的 dict；另设 `venue` 白名单与 `topics` 示例两个独立结构。**与架构文档中 `app/domain/terms.py` 对齐**：

```python
# app/domain/terms.py
GNSS_SUBFIELDS = {
    "receiver_testing": {
        "en": ["GNSS receiver testing", "receiver conformance testing", "RF interference testing",
               "PVT accuracy", "time to first fix (TTFF)", "cold start", "acquisition sensitivity",
               "tracking sensitivity", "carrier-to-noise ratio", "dilution of precision (DOP)",
               "1PPS", "assisted GNSS", "3GPP TS 37.571", "EN 16803"],
        "zh": ["接收机测试", "一致性测试", "符合性测试", "信号模拟器", "射频干扰测试",
               "PVT 精度", "定位精度", "首次定位时间", "冷启动", "捕获灵敏度", "跟踪灵敏度",
               "载噪比", "精度因子", "授时精度", "1PPS"],
    },
    "high_precision": {
        "en": ["RTK", "real-time kinematic", "precise point positioning (PPP)", "PPP-RTK",
               "post-processed kinematic (PPK)", "integer ambiguity resolution", "network RTK",
               "virtual reference station (VRS)", "master-auxiliary concept", "FKP", "SSR", "OSR",
               "convergence time", "wide-lane", "narrow-lane", "ionosphere-free combination", "LAMBDA"],
        "zh": ["RTK 定位", "实时动态定位", "精密单点定位", "PPP-RTK", "动态后处理", "整周模糊度",
               "模糊度固定", "网络 RTK", "虚拟参考站", "主辅站技术", "状态空间表示", "观测值空间表示",
               "收敛时间", "宽巷", "窄巷", "无电离层组合", "LAMBDA"],
    },
    # ... 其余子领域同构：
    # "integrity", "multipath_urban", "ionosphere_troposphere", "interference",
    # "timing_sync", "integrated_navigation", "sbas_regional", "new_signals", "simulation_verification"
}

VENUE_WHITELIST = {
    "en": [...],      # 见 §3.4
    "zh": [...],
    "normalize": "lowercase + strip spaces/punct/hyphens",
    "weight_boost": 0.2,
}

TOPIC_EXAMPLES = [
    {"id": 1, "zh": "城市峡谷环境下 RTK 接收机多路径抑制算法的研究进展",
     "en": "Research progress on multipath mitigation algorithms for RTK receivers in urban canyon environments",
     "type": "algorithm", "subfields": ["high_precision", "multipath_urban"]},
    # ... 共 15 条，见 §4
]
```

补充说明：
- 若用 YAML/JSON 存储，结构完全一致，Python 侧 `json.load` 即可；键名建议全小写 snake_case，便于检索系统直接拼 query。
- 每个子领域词条可追加可选字段：`aliases`（连字符/斜杠变体）、`case_variants`（如产品对接大小写敏感的检索 API 时使用）。
- `TOPIC_EXAMPLES` 直接供 UI 渲染"示例主题"按钮；点击后 `zh` 作为默认输入，`en` 作为解析阶段的种子词。

---

## 附录：术语检索验证来源（节选）

以下链接为本词库术语/期刊信息检索验证的关键来源：

- 接收机测试标准：[3GPP TS 37.571-1 GNSS 测试场景（TTA 镜像）](https://committee.tta.or.kr/include/Download.jsp?filename=choan%2FTTAT.3G-37.571-1%28R15-15.2.0%29_%5B1%5D.pdf)、[EN 16803-2 道路 ITS GNSS 终端性能评估](https://standards.globalspec.com/std/14489880/)、[SIST EN 61108-3 Galileo 接收机性能测试](https://www.standards.iteh.ai/catalog/standards/sist/b5324c27-f8cc-44ac-9907-6d76a67ddbdd/sist-en-61108-3-2010)
- 高精度定位：[PPP-RTK: a review and recent developments（KAUST 讲座）](https://cemse.kaust.edu.sa/events/by-type/seminar/2023/05/01/ppp-rtk-review-and-recent-developments)、[Recent advances and perspectives in GNSS PPP-RTK（Semantic Scholar）](https://www.semanticscholar.org/paper/Recent-advances-and-perspectives-in-GNSS-PPP-RTK-Hou-Zha/48a2d9d2b33afb83d700885dca3a64fda2b6fe4f)
- 完好性：[Advanced RAIM 用户算法（ION）](https://www.ion.org/publications/abstract.cfm?articleID=10462)、[Blanch 2021 ION GNSS+ FDE 论文（Stanford）](https://web.stanford.edu/group/scpnt/gpslab/pubs/papers/Blanch_IONGNSS_2021_FDE.pdf)
- 多路径/城市：[Investigation of 3D-Mapping-Aided GNSS Navigation in Urban Canyons（CORE）](https://core.ac.uk/works/160450514/)、[3D LiDAR aided GNSS-RTK with NLOS correction（PolyU）](https://theses.lib.polyu.edu.hk/handle/200/14383)
- 电离层：[基于 GNSS 的电离层闪烁检测方法进展（上海天文台）](https://qikan.cqvip.com/Qikan/Article/Detail?id=7202626158)、[Geodetic Detrending 闪烁抑制（IEEE）](https://ieeexplore.ieee.org/document/9262461)
- 干扰：[GNSS Spoofing and Jamming Mitigation: A Comprehensive Review（IEEE）](https://ieeexplore.ieee.org/document/11165996)、[低空场景卫星导航信号干扰监测综述（无线电工程）](https://wxdg.cbpt.cnki.net/portal/journal/portal/client/paper/753f8b8193c995fc03673ab8b95bc054)、[无人机卫星导航系统抗干扰技术综述（航空学报）](https://hkxb.buaa.edu.cn/CN/abstract/abstract20684.shtml)
- 授时：[北斗共视比对技术发展（维普）](https://www.cqvip.com/doc/journal/7204052691)、[基于北斗/GNSS 精密时频量值传递综述](https://yhjcjs.spacejournal.cn/cn/article/pdf/preview/10.12060/j.issn.1000-7202.2012.01.10.pdf)
- 组合导航：[GNSS/IMU 与里程计紧-松耦合因子图融合（武大学报）](http://ch.whu.edu.cn/cn/article/doi/10.13203/j.whugis20220321)、[GNSS + Visual-Inertial-Wheel Odometry 鲁棒融合（IEEE）](https://ieeexplore.ieee.org/abstract/document/10011839)
- 星基增强/新体制：[Navipedia SBAS Systems](https://www.navipedia.org/navipedia/index.php?title=SBAS_Systems)、[PPP-B2b、HAS、CLAS 性能对比（ScienceDirect）](https://www.sciencedirect.com/science/article/abs/pii/S0273117724003764)、[低轨 PNT 系统发展与关键技术（导航定位与授时）](https://dhdwyss.spacejournal.cn/article/doi/10.19306/j.cnki.2095-8110.2026.03.001)
- 仿真验证：[Spirent/Keysight PNT 模拟器与自动化测试](https://www.keysight.com/se/en/cmp/2026/spirent.html)、[Spirent PNT Xe 平台（GPS World）](https://www.gpsworld.com/spirent-launches-pnt-xe-to-expand-gnss-testing-access/)
- 期刊信息：[NAVIGATION（ION）](https://www.ion.org/navi/)、[NAVIGATION JIF 2.7 Q2](https://dizin.docent.com.tr/en/dergiler/00281522)、[GPS Solutions（Springer）](https://link.springer.com/journal/10291)、[测绘学报](https://read.cnki.net/web/Journal/Info/CHXB.html)
- 会议：[ION GNSS+ 2024 论文集](https://www.ion.org/publications/browse.cfm?proceedingsID=167)、[CSNC 2020 Proceedings（Springer 出版）](https://franklin.library.upenn.edu/catalog/FRANKLIN_9977848542703681)
