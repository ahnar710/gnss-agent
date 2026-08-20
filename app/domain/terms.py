"""内置 GNSS 领域知识：子领域词库（中英）、期刊白名单、示例调研主题。

这是"固定工作流"的领域底座：主题解析出的关键词会与这里的词库合并，
打分时用于分类，期刊白名单用于加权。
"""

SUBFIELDS = {
    "receiver_testing": {
        "label": "接收机测试与认证",
        "en": [
            "GNSS receiver testing", "receiver conformance testing",
            "GNSS receiver performance", "receiver sensitivity",
            "time to first fix", "GNSS simulator", "receiver characterization",
            "PVT accuracy", "GNSS receiver certification",
            "conformance test scenario", "GNSS test standard",
            "RF interference testing", "carrier-to-noise ratio",
            "dilution of precision", "acquisition sensitivity",
            "tracking sensitivity", "3GPP TS 37.571", "ETSI EN 303 413",
            "RTCM standard",
        ],
        "zh": [
            "接收机测试", "接收机性能测试", "灵敏度测试", "首次定位时间",
            "GNSS模拟器", "定位精度测试", "接收机认证", "接收机校准",
            "一致性测试", "符合性测试", "测试标准", "载噪比", "精度因子",
        ],
        "phrase": "GNSS receiver conformance testing",
    },
    "high_precision": {
        "label": "高精度定位（RTK/PPP）",
        "en": [
            "RTK", "PPP", "PPP-RTK", "precise point positioning",
            "real-time kinematic", "integer ambiguity resolution",
            "network RTK", "virtual reference station", "ambiguity resolution",
            "PPK", "state space representation", "SSR",
            "convergence time", "carrier phase measurement",
        ],
        "zh": [
            "实时动态差分", "RTK定位", "精密单点定位", "PPP-RTK",
            "整周模糊度", "网络RTK", "虚拟参考站", "高精度定位",
            "状态空间表示", "收敛时间", "载波相位",
        ],
        "phrase": "RTK PPP precise positioning",
    },
    "integrity": {
        "label": "完好性（RAIM/ARAIM）",
        "en": [
            "RAIM", "ARAIM", "receiver autonomous integrity monitoring",
            "integrity monitoring", "protection level",
            "fault detection and exclusion", "GBAS", "GNSS integrity",
        ],
        "zh": [
            "完好性监测", "接收机自主完好性监测", "RAIM", "ARAIM",
            "保护级别", "故障检测与排除", "地基增强完好性",
        ],
        "phrase": "GNSS integrity monitoring RAIM",
    },
    "multipath": {
        "label": "多路径与城市环境",
        "en": [
            "multipath", "multipath mitigation", "NLOS",
            "urban canyon", "non-line-of-sight", "multipath rejection",
            "3D mapping aided GNSS", "multipath estimation",
        ],
        "zh": [
            "多路径", "多径效应", "多径抑制", "城市峡谷",
            "非视距", "NLOS", "三维地图辅助定位",
        ],
        "phrase": "GNSS multipath mitigation urban",
    },
    "ionosphere": {
        "label": "电离层与对流层",
        "en": [
            "ionospheric scintillation", "ionospheric delay", "TEC",
            "total electron content", "tropospheric delay",
            "ionospheric error", "scintillation monitoring",
        ],
        "zh": [
            "电离层闪烁", "电离层延迟", "对流层延迟",
            "总电子含量", "TEC", "电离层改正",
        ],
        "phrase": "ionospheric scintillation GNSS",
    },
    "interference": {
        "label": "干扰与抗干扰",
        "en": [
            "GNSS spoofing", "GNSS jamming", "anti-jamming",
            "anti-spoofing", "GNSS interference detection", "meaconing",
            "GNSS security", "interference mitigation", "RFI",
        ],
        "zh": [
            "欺骗干扰", "压制干扰", "抗干扰", "反欺骗",
            "干扰检测", "GNSS安全", "干扰抑制", "射频干扰",
        ],
        "phrase": "GNSS spoofing jamming detection",
    },
    "timing": {
        "label": "授时与同步",
        "en": [
            "GNSS timing", "time synchronization", "disciplined oscillator",
            "GNSS clock", "PTP", "network timing", "UTC dissemination",
            "timing receiver",
        ],
        "zh": [
            "授时", "时间同步", "授时接收机", "驯服振荡器",
            "GNSS授时", "时间基准", "时间传递",
        ],
        "phrase": "GNSS timing synchronization",
    },
    "integrated_navigation": {
        "label": "组合导航（GNSS/INS）",
        "en": [
            "GNSS INS integration", "loosely coupled", "tightly coupled",
            "factor graph", "sensor fusion", "GNSS/INS",
            "visual inertial navigation", "integrated navigation",
        ],
        "zh": [
            "组合导航", "GNSS/INS组合", "松耦合", "紧耦合",
            "深耦合", "因子图", "传感器融合", "惯性导航",
        ],
        "phrase": "GNSS INS integrated navigation",
    },
    "sbass": {
        "label": "星基增强（SBAS）",
        "en": [
            "SBAS", "WAAS", "EGNOS", "GAGAN", "BDSBAS", "QZSS",
            "dual frequency SBAS", "DFMC SBAS", "satellite based augmentation",
        ],
        "zh": [
            "星基增强", "广域增强", "北斗星基增强", "BDSBAS",
            "QZSS", "双频星基增强",
        ],
        "phrase": "satellite based augmentation system SBAS",
    },
    "new_signals": {
        "label": "新信号与新体制",
        "en": [
            "dual frequency GNSS", "multi frequency", "L5", "E5a",
            "B1C", "B2a", "Galileo HAS", "QZSS CLAS",
            "LEO PNT", "low earth orbit augmentation", "GNSS modernization",
        ],
        "zh": [
            "双频", "多频", "北斗三号新信号", "B1C", "B2a",
            "低轨增强", "LEO-PNT", "信号体制",
        ],
        "phrase": "multi frequency GNSS signals",
    },
    "simulation": {
        "label": "仿真与测试方法",
        "en": [
            "GNSS simulator", "hardware in the loop", "RF constellation simulator",
            "GNSS testing scenarios", "field testing", "record and replay",
            "scenario simulation", "multipath simulation",
        ],
        "zh": [
            "仿真测试", "硬件在环", "GNSS模拟器", "场景仿真",
            "外场测试", "回放测试", "高精度仿真",
        ],
        "phrase": "GNSS simulator testing",
    },
}

# 期刊/会议白名单（venue 命中则加权；小写包含匹配）
JOURNAL_WHITELIST = [
    # 英文期刊
    "navigation",
    "gps solutions",
    "journal of geodesy",
    "journal of navigation",
    "ieee transactions on aerospace and electronic systems",
    "ieee transactions on intelligent transportation systems",
    "ieee transactions on vehicular technology",
    "ieee transactions on instrumentation and measurement",
    "sensors",
    "remote sensing",
    "measurement science and technology",
    "iet radar, sonar & navigation",
    "advances in space research",
    # 会议（Proceedings）
    "proceedings of the ion gnss",
    "ion gnss",
    "ion international technical meeting",
    "ion pnt",
    "ieee/ion position, location and navigation symposium",
    "european navigation conference",
    "china satellite navigation conference",
    "lecture notes in electrical engineering",  # CSNC 论文集出版渠道
    # 中文期刊
    "acta geodaetica et cartographica sinica",
    "geomatics and information science of wuhan university",
    "journal of chinese inertial technology",
    "journal of navigation and positioning",
    "gnss world of china",
    "导航定位与授时",
    "测绘科学技术学报",
    "大地测量与地球动力学",
    "电子测量与仪器学报",
    "宇航计测技术",
    "无线电工程",
    "航空学报",
    "天文学进展",
]

# 示例调研主题（UI 一键填入；来源 docs/GNSS_DOMAIN_KNOWLEDGE.md §4）
EXAMPLE_TOPICS = [
    {"zh": "城市峡谷环境下 RTK 接收机多路径抑制算法的研究进展",
     "en": "Research progress on multipath mitigation algorithms for RTK receivers in urban canyon environments"},
    {"zh": "GNSS 欺骗干扰检测与抗欺骗技术的研究现状与趋势",
     "en": "State of the art and trends in GNSS spoofing detection and anti-spoofing techniques"},
    {"zh": "电离层闪烁对双频/多频 GNSS 接收机定位性能的影响与缓解方法",
     "en": "Impact of ionospheric scintillation on dual-/multi-frequency GNSS receiver positioning and mitigation approaches"},
    {"zh": "RTK 与 PPP-RTK 定位精度与收敛时间的技术对比",
     "en": "Technical comparison of RTK and PPP-RTK: accuracy and convergence time"},
    {"zh": "GNSS/INS 紧耦合与深耦合组合导航在汽车定位中的应用进展",
     "en": "Progress of tightly- and deeply-coupled GNSS/INS integration for automotive positioning"},
    {"zh": "RAIM/ARAIM 完好性监测技术在自动驾驶高精度定位中的可用性研究",
     "en": "Availability of RAIM/ARAIM integrity monitoring for high-precision positioning in autonomous driving"},
    {"zh": "基于 GNSS 信号模拟器的接收机一致性测试标准与场景设计",
     "en": "Conformance testing standards and scenario design for GNSS receivers using signal simulators"},
    {"zh": "低轨卫星导航增强（LEO PNT）技术研究现状与商业化前景",
     "en": "Current status and commercialization prospects of LEO satellite navigation augmentation (LEO PNT)"},
    {"zh": "5G 网络授时与 GNSS 授时技术对比及融合方案",
     "en": "Comparison and fusion of 5G network timing and GNSS timing technologies"},
    {"zh": "城市峡谷场景下 GNSS 多路径与 NLOS 信号的检测与剔除方法",
     "en": "Detection and exclusion of GNSS multipath and NLOS signals in urban canyon scenarios"},
    {"zh": "压制式干扰对 GNSS 接收机的影响评估与阵列天线抗干扰技术",
     "en": "Impact assessment of jamming on GNSS receivers and array-antenna anti-jamming techniques"},
    {"zh": "Galileo HAS、QZSS CLAS 与北斗 PPP-B2b 高精度服务对比分析",
     "en": "Comparative analysis of Galileo HAS, QZSS CLAS and BeiDou PPP-B2b high-accuracy services"},
    {"zh": "GNSS 接收机一致性测试标准（3GPP TS 37.571 / ETSI EN 303 413）要求梳理",
     "en": "Review of conformance test requirements in 3GPP TS 37.571 and ETSI EN 303 413 for GNSS receivers"},
    {"zh": "智能驾驶场景下 GNSS 定位性能评估方法与测试工具链",
     "en": "GNSS positioning performance evaluation methodology and test toolchains for intelligent driving"},
    {"zh": "GNSS 授时接收机时间同步精度与保持能力的测试方法",
     "en": "Test methods for time synchronization accuracy and holdover of GNSS timing receivers"},
]

SUBFIELD_LABELS = {k: v["label"] for k, v in SUBFIELDS.items()}
