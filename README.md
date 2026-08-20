# GNSS 文献调研 Agent

一款**完全本地运行**的文献调研 Agent（网页应用）。GNSS 测试行业的产品经理输入一句调研主题，Agent 自动完成「检索 → 深读 → 分析 → 报告」全流程，24 小时内交付 ≥100 篇文献的中文调研报告；**用户不点停止，Agent 不停止工作**。

- 🖥️ **网页应用**：浏览器界面，零编程门槛；也可打包为桌面应用（Windows exe / macOS .app，双击启动免终端）
- 🔒 **完全本地**：无任何云端组件，API Key 只存本机
- 🔑 **自带 Key**：兼容 DeepSeek / OpenAI / 通义千问 / Ollama 等 OpenAI 兼容接口
- 📚 **多源检索**：OpenAlex / arXiv / Semantic Scholar / Crossref（免费开放 API）
- 📄 **PDF 上传分析**：上传论文 PDF，自动提取文本并进入深读队列，与检索文献一起进报告
- 🛰️ **GNSS 领域定制**：内置 11 个子领域中英文词库、期刊/会议白名单、15 个示例主题
- ⏱️ **持续运行**：不点停止不停工；断点续跑，关浏览器/重启电脑任务不丢
- 💻 **跨平台**：同一套代码在 macOS 与 Windows 10/11 交付（桌面应用或源码运行）

---

## 快速开始

### 方式一：Windows 用户（安装包，无需 Python）
- 拿到 `GNSS文献调研Agent_Setup_0.1.0.exe` → 双击安装 → 桌面图标启动 → 浏览器自动打开
- 首次使用：设置页填 API Key → 测试连接 → 保存 → 新建调研
- 打包流程与验收清单见 [docs/WINDOWS_DELIVERY.md](docs/WINDOWS_DELIVERY.md)

### 方式二：源码运行（开发 / Mac）

```bash
# 1. 安装（需要 Python 3.10+）
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip install -r requirements.txt

# 2. 启动
.venv/bin/python start.py                        # Windows: .venv\Scripts\python start.py

# 3. 使用
# 浏览器自动打开 http://127.0.0.1:8765
# ① 点右上角「设置」→ 填入你的 API Base URL / Key / 模型 → 测试连接 → 保存
# ② 点「新建调研」→ 输入主题（或用示例一键填入）→ 开始调研
# ③ 实时查看进度；随时点「停止调研」→ 生成最终报告；报告可复制 / 下载 .md
# ④ （可选）任务详情页点「📄 上传论文(PDF)」→ 选择论文 PDF → 自动提取文本并加入深读队列
```

> 💡 **无 Key 想先体验**：`GNSS_AGENT_MOCK_LLM=1 .venv/bin/python start.py` 进入演示模式（假模型，不调用任何 API）。

## PDF 论文上传分析

- 在任意任务详情页点「📄 上传论文(PDF)」，选择论文 PDF（≤50MB，文本型）
- 系统自动：提取标题与正文 → 直接进入该任务的深读队列（视为高相关，跳过打分）→ 深读员用**全文**（而非仅摘要）生成中文分析 → 与其他检索文献一起进入最终报告
- 报告与论文列表中标记来源为「📄 用户上传」
- 扫描版/图片型 PDF（无文本层）会提示暂不支持 OCR

## 模型配置参考

| 服务商 | API Base URL | 模型示例 |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| Ollama（本机） | `http://localhost:11434/v1` | `qwen2.5:14b`（Key 留空） |

## 固定工作流

```
用户输入主题 → ① 主题解析（LLM 拆解为中英文关键词×子领域×时间范围，合并内置词库）
  → ② 多源检索（OpenAlex/arXiv/S2/Crossref 并行）→ ③ 去重归一
  → ④ 相关性打分（LLM 批量）→ ⑤ 逐篇深读（中文结构化摘要）
  → ⑥ 达标检查：未达标 → 扩展检索（LLM 新角度 / 引用网络挖掘）回到 ②
              已达标 → 持续扩展模式（不点停止不停工）
  → ⑦ 报告持续更新（每积累一批深读自动刷新）→ 用户停止/超时 → 最终报告
```

## 目录结构

```
passage/
├── start.py                  # 启动入口（单实例/自检/自动打开浏览器）
├── requirements.txt
├── docs/                     # PRD / 架构 / 源矩阵 / 路线图 / 领域知识库 / Windows 交付指南
├── app/
│   ├── main.py               # FastAPI 路由（含 PDF 上传接口）
│   ├── db.py                 # SQLite 持久化（断点续跑/幂等）
│   ├── config.py             # 路径/端口/默认设置（含打包 frozen 感知）
│   ├── pdf_extract.py        # PDF 论文文本提取（pypdf）
│   ├── domain/terms.py       # GNSS 内置词库（中英）+ 期刊白名单 + 示例主题
│   ├── llm/client.py         # OpenAI 兼容客户端（重试/JSON 提取）
│   ├── sources/              # OpenAlex / arXiv / Semantic Scholar / Crossref
│   ├── agents/orchestrator.py# 协调器（路由到角色、断点续跑、成本上限）
│   ├── agents/roles/         # 多 Agent：策略官/评审员/深读员/分析师/主编
│   ├── agents/pool.py        # 深读员并行 Worker 池（原子认领）
│   ├── agents/report.py      # 中文报告生成（分析章节增量缓存）
│   └── web/static/           # 前端（原生 HTML/CSS/JS，无构建步骤）
├── scripts/                  # 冒烟测试 / 24h 压测
├── packaging/                # PyInstaller spec / 图标 / Inno Setup / 构建脚本
└── data/                     # 运行时数据（任务库/报告/上传 PDF，自动生成，勿提交）
```

## 桌面应用（双击启动，免终端）

| 平台 | 形态 | 说明 |
|---|---|---|
| macOS | `GNSS文献调研Agent.app`（约 46MB） | 双击启动，无终端窗口，自动打开浏览器 |
| Windows | `GNSSAgent.exe`（windowed）+ Inno Setup 安装器 | 双击启动，无黑窗口，自动打开浏览器 |

- 图标：雷达/卫星主题（`packaging/assets/app.ico` + `app.icns`，`make_icon.py` 自动生成）
- 构建：`packaging/build.py`（macOS/Windows 通用）或 `packaging/build_windows.bat`（Windows）
- macOS 首次双击若提示"无法验证开发者"：右键 → 打开（本机自用）；正式分发需 Apple 开发者签名

## Windows 交付（M3）

- 打包：Windows 上运行 `packaging\build_windows.bat` → 产出安装器 `dist_installer\GNSS文献调研Agent_Setup_*.exe`
- **没有 Windows 机器？** 内置 GitHub Actions（`.github/workflows/build-windows.yml`）：推到 GitHub 仓库后，Actions 页手动 Run 或打 tag，自动产出 Windows 安装包
- 用户侧：双击安装（免 Python、无黑窗口、自动打开浏览器、单实例）
- 完整流程 / 验收清单 / 故障排查：[docs/WINDOWS_DELIVERY.md](docs/WINDOWS_DELIVERY.md)

## 多 Agent 协作（M2.5 新增）

固定工作流由 5 个专职 Agent 协作完成（黑板模式，通过本地数据库共享状态，不互相聊天）：

| 角色 | 职责 | 独立模型配置 |
|---|---|---|
| 策略官 Strategist | 主题解析、检索角度扩展 | `model_strategist` |
| 评审员 Reviewer | 相关性打分与子领域分类 | `model_reviewer` |
| 深读员池 Reader×N | 并行深读（默认 3 并发，可调 1~6） | `model_reader` |
| 分析师 Analyst | 研究趋势与空白分析 | `model_analyst` |
| 主编 Editor | 深读摘要忠实性质控，不符打回重读 | `model_editor` |

- 设置页可给每个角色指定不同模型（留空 = 全局模型），实现**成本分层**（便宜模型打分、好模型分析）。
- 并行深读显著提升 24h 吞吐；Worker 原子认领、失败重试、崩溃自动恢复。
- 主编质控默认开启（`qc_enabled`），可在设置页关闭。

## 成本控制（M2 新增）

- **实时成本显示**：任务详情页与最终报告都会显示 LLM 调用次数、输入/输出 token 和按单价估算的费用。
- **单价可配**：设置页填写你的模型"输入/输出价格（USD/百万 token）"，默认按 DeepSeek 计价（0.27 / 1.10）。
- **成本上限保险丝**：设置页可设"单任务成本上限"，任务累计费用达到上限后**自动结束并生成最终报告**（0=不限）；新建任务时也可单独为某个任务设更严的上限。防止 24h 连续运行烧钱失控。
- **日志滚动**：每个任务日志自动保留最近 2000 条，长跑不撑爆磁盘；任务完成后可一键删除（论文/日志/报告级联清理）。

## 测试

```bash
# 端到端冒烟测试（真实检索 + 假 LLM，无需 Key）
.venv/bin/python scripts/smoke_test.py

# 24h 级压测（成本上限/日志裁剪/资源增长观测与 24h 外推）
.venv/bin/python scripts/stress_test.py --minutes 5
```

## 文档

- [产品需求文档 PRD](docs/PRD.md)
- [架构设计](docs/ARCHITECTURE.md)
- [文献源接入矩阵](docs/SOURCES.md)
- [路线图](docs/ROADMAP.md)
- [GNSS 领域知识库（词库/白名单/示例主题研究）](docs/GNSS_DOMAIN_KNOWLEDGE.md)
- [Windows 交付指南（打包/验收清单/排障）](docs/WINDOWS_DELIVERY.md)

## 常见问题

- **任务能一直跑多久？** 默认上限 24 小时（新建任务时或设置页可调）；达标后进入持续扩展模式，只有「停止」、超时或达到成本上限才结束。
- **关掉浏览器任务会丢吗？** 不会。任务在本地后端运行并落盘，重开页面自动恢复进度。
- **S2 偶尔限流？** 系统自动暂停该源 5 分钟并继续用其他源，不影响任务。
- **Key 安全吗？** 只存本机 SQLite，接口返回时脱敏；产品无任何云端组件。
- **费用怎么算？** 每次 LLM 调用都记录 token，按你在设置页填的单价实时估算；详情页和报告里都能看到。
- **双击图标没反应？** 查看 `%USERPROFILE%\.gnss_agent\app.log`；多半是杀软拦截，加入白名单即可。
