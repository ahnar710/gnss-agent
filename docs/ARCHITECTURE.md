# 架构设计文档 — GNSS 文献调研 Agent

> 版本：v0.1（MVP） · 配套 PRD：docs/PRD.md

## 1. 总体架构

```
┌────────────────────────────── 用户电脑（Windows / macOS） ──────────────────────────────┐
│                                                                                          │
│  ┌─────────────────┐   HTTP/JSON    ┌──────────────────────────────────────────────┐    │
│  │   浏览器 (UI)    │◄──────────────►│           本地后端 (FastAPI)                   │    │
│  │  index.html      │   localhost    │                                              │    │
│  │  设置/新建/进度/  │                │  ┌────────────┐  ┌────────────────────────┐  │    │
│  │  论文/报告        │                │  │ 任务编排器  │  │ 固定工作流 Orchestrator │  │    │
│  └─────────────────┘                │  │ (asyncio)  │  │ 解析→检索→打分→深读→     │  │    │
│                                     │  └────────────┘  │ 扩展→报告 (状态机)        │  │    │
│                                     │  ┌────────────┐  └────────────────────────┘  │    │
│                                     │  │ 文献源适配层 │  OpenAlex/arXiv/S2/Crossref  │    │
│                                     │  └────────────┘                               │    │
│                                     │  ┌────────────┐  ┌────────────┐  ┌─────────┐ │    │
│                                     │  │ LLM 客户端  │  │ SQLite 持久化│ │ 报告引擎 │ │    │
│                                     │  └────────────┘  └────────────┘  └─────────┘ │    │
│                                     └──────────────────────────────────────────────┘    │
│                                                                                          │
│   ┌────────────┐      ┌──────────────┐      ┌───────────────┐      ┌──────────────┐      │
│   │ OpenAlex   │      │ arXiv API    │      │ Semantic      │      │ Crossref API │      │
│   │ (免费无key) │      │ (免费)        │      │ Scholar API   │      │ (免费)        │      │
│   └────────────┘      └──────────────┘      └───────────────┘      └──────────────┘      │
│                                                                                          │
│   ┌─────────────────────┐   HTTPS (用户自己的 Key)                                        │
│   │ 大模型 API           │◄────────────────────────────────────┐                          │
│   │ DeepSeek/OpenAI/     │  OpenAI 兼容 /chat/completions       │                          │
│   │ 通义/Ollama(本机)     │                                     │                          │
│   └─────────────────────┘                                     │                          │
└────────────────────────────────────────────────────────────────┴──────────────────────────┘
```

**关键原则**：
1. **无云端**：整个产品 = 用户电脑上的一个进程 + 浏览器。后端不向任何自有服务器上报数据。
2. **自带 Key**：大模型调用走 OpenAI 兼容协议，用户自己配置 base_url / api_key / model。
3. **一切可恢复**：所有状态落 SQLite；启动时自动恢复未完成任务。

## 2. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 后端框架 | Python 3.13 + FastAPI + uvicorn | 学术 API 生态好、asyncio 适合并发检索、单文件打包成熟 |
| HTTP 客户端 | httpx（async） | 并发 + 超时 + 重试控制 |
| 持久化 | SQLite（aiosqlite） | 零运维、单文件、跨平台，天然适合本地应用 |
| 前端 | 原生 HTML/CSS/JS（无构建步骤） | 离线可用、打包简单、无 node 依赖 |
| 大模型协议 | OpenAI 兼容 Chat Completions | DeepSeek/OpenAI/通义/Ollama 全兼容 |
| 打包 | PyInstaller（Windows 单目录/单文件） | 用户无需装 Python；Mac 开发直接跑源码 |
| 任务调度 | asyncio 后台任务（每任务一个协程） | 简单可控，天然支持并发任务与优雅停止 |

## 3. 数据模型（SQLite）

```
settings(key PK, value)                     -- api_base, api_key, model, 默认参数、单价、成本上限
tasks(id PK, topic, direction, status,      -- running/stopped/completed/error
      created_at, updated_at, started_at, stopped_at,
      rounds, target_count, time_limit_hours, config JSON,
      counters JSON, cost JSON, error)      -- cost: {calls, in_tokens, out_tokens, est_cost_usd}
queries(id PK, task_id FK, text, source, searched_at)  -- 幂等：不重复检索
papers(id PK, task_id FK, source, doi, title, authors JSON, year, venue,
       abstract, url, cited_by, query_used,
       status pending/scored/reading/read/failed,
       relevance REAL, category, summary, key_points JSON, extras JSON)
task_logs(id PK, task_id FK, ts, level, message)
```

- 任务进度 = `counters`（found/relevant/read）+ `task_logs`（滚动日志流，每任务保留最近 2000 条）。
- 任务成本 = `cost`（LLM 调用次数、输入/输出 token、按可配单价估算的美元费用）。
- 断点续跑 = 启动时把 `status='running'` 的任务重新入队；编排器对 `queries` 已检索项、`papers` 已处理项全部幂等跳过。

## 4. 多 Agent 协作（M2.5）

**协作模式**：角色流水线 + 并行深读 + 主编质控（黑板模式）。角色之间**不对话**，
通过 SQLite 共享状态协作——这是长跑本地系统最稳的协作方式（记忆 = 数据库，而非上下文窗口）。

```
策略官 Strategist   主题解析 / 检索角度扩展（app/agents/roles/strategist.py）
评审员 Reviewer     批量相关性打分 + 子领域分类（roles/reviewer.py）
深读员池 Reader×N   并行深读 Worker（roles/reader.py + pool.py，N=reader_pool_size 默认 3）
分析师 Analyst      研究趋势与空白分析（roles/analyst.py，报告章节增量缓存）
主编 Editor         深读摘要忠实性核验，不符打回重读（roles/editor.py，qc_enabled 开关）
协调器 Coordinator  路由、并发控制、断点续跑、成本上限（orchestrator.py）
```

- **独立模型配置**：每个角色可配独立模型（`model_strategist/reviewer/reader/analyst/editor`），
  留空用全局模型——实现成本分层（如打分用便宜模型、分析用最强模型）。
- **并行深读**：Worker 通过 `db.claim_next_relevant`（条件 UPDATE + rowcount 校验的原子认领，
  优先级 = 相关性×log(引用+2)×白名单×近3年时效）从黑板取论文；失败自动重试（3 次上限），
  优雅停池（等当前论文读完再停，取消时释放认领），崩溃遗留的 reading 状态自动恢复。
- **主编质控**：每积累 10 篇深读，Editor 批量核验"深读摘要是否忠实于原文摘要"，
  发现编造/张冠李戴/夸大即打回重读（带 qc 标记防循环）。
- **成本追踪**：每个角色每次 LLM 调用都记录 token 与估算费用（单价可配），
  累计到 `tasks.cost`；达到任务/全局成本上限自动结束并生成最终报告（保险丝）。

## 5. 固定工作流实现（Orchestrator）

每个任务一个 asyncio 协程，按阶段推进：

```
parse ─► [search_round × N] ─► score ─► deep_read(优先队列) ─► check_target
              ▲                                                    │
              └────── expand（新关键词/引用挖掘/时间滑动）◄─────────┘
                                                        │ 达标后
                                                        ▼
                                              overdrive（持续扩展+刷新报告）
                                                        │ 用户停止 / 超时
                                                        ▼
                                              final_report ─► status=stopped/completed
```

- **parse**：LLM 将主题解析为 `{en_terms[], zh_terms[], subfields[], years}`，与内置 GNSS 词库（app/domain/terms.py）合并去重。
- **search_round**：每个未检索过的 query × 每个启用源，**多源并行**抓取（Semaphore 6 并发），归一化入库。
- **score**：LLM 批量打分（10 篇/批，输出 JSON），保留 `relevance ≥ 阈值`（默认 0.6）。
- **deep_read**：深读员并行池（N 个 Worker）从黑板原子认领论文（优先级 = 相关性×log(引用+2)×白名单×近3年时效），并发生成中文结构化摘要；失败重试 3 次，主编质控可打回重读。
- **check_target / expand**：`read < target` 时生成下一轮 query（LLM 组合新词 + 从 Top 论文的引用网络挖新词）；`rounds` 递增。
- **overdrive**：达标后不停，继续 expand + deep_read + 每积累 10 篇重生成报告。
- **成本追踪**：每次 LLM 调用记录 token 与估算费用（单价可配），累计到 `tasks.cost`；达到任务/全局成本上限时自动结束并生成最终报告（保险丝）。
- **报告增量**：趋势与空白分析按"已深读论文集合"缓存（reports/*.analysis.json），集合未变直接复用，避免重复调用 LLM。
- **stop**：置 `stopping` 标记 → 当前步骤完成后生成最终报告 → `stopped`。进程重启 = 自动恢复。

**错误处理**：单源失败不影响整体（降级跳过 + 限流冷却 5 分钟）；LLM 调用指数退避重试（3 次）；单篇解析失败标记 `failed` 不阻断。

## 6. 可靠性设计

| 场景 | 机制 |
|---|---|
| API 限流（429） | 按源 Semaphore + 退避重试；命中限流的源冷却 5 分钟自动跳过；Semantic Scholar 严格遵守 5min 窗口 |
| 单源宕机 | 多源冗余，失败源自动跳过并在日志提示 |
| LLM 超时/断网 | 重试 3 次 + 退避；仍失败则任务暂停等待，不丢状态 |
| 进程被杀 | 每步落库；重启自动恢复 running 任务 |
| 重复检索 | `queries` 表唯一索引 + 幂等；重启不重跑已完成 query |
| 磁盘/报告损坏 | 报告写临时文件后原子替换 |
| 长跑磁盘膨胀 | 每任务日志保留最近 2000 条（滚动裁剪）；任务可一键删除（级联清理） |
| 成本失控 | 每次 LLM 调用记录 token/费用；达到成本上限自动结束并出报告 |

## 7. 安全与隐私

- API Key 仅存本机 SQLite（README 提示可加密扩展）；接口返回时脱敏（只显示末 4 位）。
- 服务只监听 `127.0.0.1`（默认），不对外暴露端口。
- 无账号、无遥测、无外部回调。
- 文献源仅使用官方开放 API，遵守 ToS；不做反爬绕过。

## 8. 打包与分发（M3）+ 桌面化（v0.2）

- **开发**（Mac）：`python start.py`，自动打开浏览器。
- **桌面应用（双击启动，免终端）**：
  - Windows：`GNSSAgent.exe`（windowed 无黑窗口）+ Inno Setup 安装器（用户目录安装免 UAC、快捷方式、静默安装、卸载保留数据）
  - macOS：PyInstaller BUNDLE 产出 `GNSS文献调研Agent.app`（双击启动、无终端、Dock 图标，Info.plist 含版本与 bundle id）
  - 图标：`packaging/make_icon.py`（Pillow 绘制雷达/卫星主题）→ `assets/app.ico`（Windows）+ `app.icns`（macOS，iconutil 转换）
- **构建**：`packaging/build.py`（跨平台：图标 → PyInstaller → [Windows] Inno Setup）或 `build_windows.bat`
- **启动自检与单实例**（start.py）：
  - 单实例：默认端口返回本应用 `/api/health` 即视为已有实例，只唤起浏览器
  - 端口占用自动换端口；数据目录可写检查；网络连通性探测（仅警告）
  - windowed 模式（无 stdout）信息写 `data/app.log`，致命错误用系统弹窗提示
- **打包感知路径**：frozen 时数据目录 = `~/.gnss_agent`（config.py），升级安装包不影响用户数据。
- 跨平台差异点收敛在：端口占用检测、浏览器自动打开、路径处理（`pathlib` + 应用数据目录）。
- 详细交付流程与 Windows 验收清单见 `docs/WINDOWS_DELIVERY.md`。

## 8.1 PDF 论文上传（v0.2）

- 接口：`POST /api/tasks/{task_id}/upload`（multipart，≤50MB）；保存到 `data/uploads/{task_id}/`
- 提取：`app/pdf_extract.py`（pypdf）——标题优先元数据、其次原文件名；正文存 `abstract`（截断 15000 字符）
- 入队：上传论文**跳过相关性打分**，直接 `status=relevant, relevance=1.0` → 深读员池处理；深读员对上传论文使用**全文前 6000 字符**（普通文献仅摘要 1200）
- 标记：`source='upload'`，报告与论文列表显示「📄 用户上传」
- 扫描版（无文本层）PDF 返回 422 提示暂不支持 OCR

## 9. 目录结构

```
passage/
├── start.py                  # 入口：启动服务 + 单实例/自检 + 打开浏览器
├── requirements.txt
├── docs/                     # PRD / 架构 / 文献源矩阵 / 路线图 / 领域知识库 / Windows 交付指南
├── app/
│   ├── main.py               # FastAPI 路由（含 PDF 上传接口）
│   ├── config.py             # 路径/端口/默认值（含 frozen 打包感知）
│   ├── db.py                 # SQLite 访问层
│   ├── pdf_extract.py        # PDF 文本提取（pypdf）
│   ├── domain/terms.py       # GNSS 内置词库（中英）
│   ├── llm/client.py         # OpenAI 兼容客户端
│   ├── sources/              # base + openalex/arxiv/semanticscholar/crossref
│   ├── agents/               # 协调器 + 多 Agent 角色 + 深读池 + 报告生成
│   └── web/static/           # index.html / app.js / style.css
├── scripts/                  # 冒烟测试 / 24h 压测
├── data/                     # 运行时：tasks.db、reports/、uploads/（gitignore）
└── packaging/                # PyInstaller spec / 图标 / version_info / Inno Setup / 构建脚本
```
