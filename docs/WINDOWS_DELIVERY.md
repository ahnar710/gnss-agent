# Windows 交付指南 — GNSS 文献调研 Agent

> 目标用户：GNSS 测试厂商产品经理（零编程背景，Windows 10/11）。
> 交付形态：**一键安装包**（Inno Setup 生成的 .exe），用户双击安装即可使用，无需安装 Python。
> 应用图标：雷达/卫星主题（`packaging/assets/app.ico` / `app.icns`，由 `make_icon.py` 生成）。

---

## 1. 交付物清单

| 交付物 | 生成方式 | 说明 |
|---|---|---|
| `GNSS文献调研Agent_Setup_0.1.0.exe` | Windows 上运行打包脚本 | 最终分发给用户的安装器（含 PyInstaller 应用 + 桌面快捷方式） |
| `GNSS文献调研Agent.app`（macOS） | `packaging/build.py`（mac 上） | Mac 用户双击即用（无终端、Dock 图标） |
| `dist/GNSS文献调研Agent/` | PyInstaller | 免安装绿色目录版（可整目录拷给用户，双击 GNSSAgent.exe） |
| 源码运行版 | — | 开发/调试用：`python start.py` |

## 2. Windows 打包步骤（打包机：Windows 10/11 x64）

前置：安装 [Python 3.10+](https://www.python.org/downloads/)（勾选 Add to PATH）、[Inno Setup 6](https://jrsoftware.org/isinfo.php)（安装时勾选 Add ISCC to PATH）。

```bat
:: 一键打包（在项目根目录）
packaging\build_windows.bat
```

脚本自动完成：创建构建环境 → 装依赖 → PyInstaller 打包 → 检测 iscc → 生成安装器。
产物：
- 安装器：`dist_installer\GNSS文献调研Agent_Setup_0.1.0.exe`
- 绿色版：`dist\GNSS文献调研Agent\`

> 说明：PyInstaller 不支持交叉编译，**必须在 Windows 上构建 Windows 安装包**。
> macOS/Linux 可用 `python3 packaging/build.py` 验证 spec 与构建流程（产物为当前平台版本，仅供自测）。

### 2.1 没有 Windows 机器？用 GitHub Actions 自动打包（推荐）

仓库已配置 `.github/workflows/build-windows.yml`，把项目推到任意 GitHub 仓库后：

1. 手动触发：仓库页 **Actions → Build Windows Installer → Run workflow**
2. 或发版触发：`git tag v0.1.0 && git push origin v0.1.0`
3. 构建完成后，在该运行页底部 **Artifacts** 下载：
   - `gnss-agent-windows-installer.zip` → 安装器（分发给最终用户）
   - `gnss-agent-windows-portable.zip` → 绿色目录版

> 私有仓库也能用（免费额度内），只有你在 Actions 运行页能看到产物。

## 3. 打包产物结构

```
GNSS文献调研Agent/          ← 双击 GNSSAgent.exe 即启动（无黑窗口）
├── GNSSAgent.exe
├── _internal/              ← 运行库与资源（app/web/static 在其中）
└── ...（依赖库）
```

用户数据（任务库/报告/日志）存放在 `%USERPROFILE%\.gnss_agent\`：
```
.gnss_agent/
├── tasks.db                ← 全部任务与论文数据（SQLite）
├── reports/                ← 中文调研报告（.md）+ 分析缓存
└── app.log                 ← 运行日志（排障用）
```

## 4. Windows 验收测试清单（每次发版必须全过）

### 4.1 安装/启动
- [ ] 普通用户（非管理员）双击安装器，无 UAC 弹窗，默认安装到 `%LOCALAPPDATA%`
- [ ] 静默安装：`GNSS...Setup.exe /VERYSILENT /SUPPRESSMSGBOXES` 成功且无界面
- [ ] 桌面快捷方式（勾选"附加任务"时）与开始菜单快捷方式正常
- [ ] 双击 GNSSAgent.exe：**无黑窗口**，浏览器自动打开 `http://127.0.0.1:8765`
- [ ] 已运行一个实例时再双击：不启动第二个实例，仅唤起浏览器
- [ ] 端口 8765 被其他程序占用：自动换端口并正常打开浏览器
- [ ] 安装到含空格/中文路径（如用户名"张三"）：一切正常

### 4.2 功能
- [ ] 设置页配置 API Key → 测试连接成功 → 保存（Key 只存本机）
- [ ] 新建调研 → 自动跑完 检索/打分/深读/报告 → 达标后持续扩展
- [ ] 点"停止调研"→ 优雅收尾生成最终报告；报告可复制/下载
- [ ] 关闭应用（托盘无，直接结束进程）→ 重启后任务自动恢复继续
- [ ] 重启电脑后双击启动：进行中的任务恢复，不重复已做工作

### 4.3 稳定性/安全
- [ ] 杀毒软件（Windows Defender / 360 / 火绒）不误报或已加入白名单
- [ ] 连续运行 ≥ 2 小时无内存异常增长（观察任务管理器）
- [ ] 卸载后用户数据（`.gnss_agent`）保留；确认无残留进程/自启动项

### 4.4 离线/弱网
- [ ] 断网启动：能打开页面、能查看历史任务与报告；新建任务给出明确提示

## 5. 分发渠道与更新

### 5.1 分发
1. **推荐**：GitHub Actions 自动构建（见 §2.1），下载安装器后上传到团队共享盘 / 微信文件 / 私有网盘。
2. 附 `安装说明.txt`（1 页：双击安装 → 打开后右上角设置里填 Key → 提问）。

### 5.2 自动更新（可选，建议 M4 再上）
- **方案**：GitHub Release 或自建静态服务器，放 `latest.json`（版本号 + 安装包 URL + 变更日志）。
- 客户端启动时（网络可用）拉取 `latest.json`，发现新版本提示用户下载新安装包。
- **注意**：本地数据在 `%USERPROFILE%\.gnss_agent`，升级安装包**不影响数据**（安装器不覆盖用户目录）。

## 6. 常见故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 双击无反应 | 杀软拦截 / 缺 VC 运行库 | 查看 `%USERPROFILE%\.gnss_agent\app.log`；加入杀软白名单 |
| 浏览器没自动打开 | 系统默认浏览器被改 | 手动访问 `http://127.0.0.1:8765` |
| 端口冲突 | 其他软件占用 | 已自动换端口，看 app.log 中的实际地址 |
| 任务一直"运行中"无进展 | 网络不通 / API Key 失效 | 看运行日志中的警告；设置页重新测试连接 |
| 电脑重启后任务没了 | 未正常关闭？ | 重启后自动恢复；若状态异常可在页面删除重建 |

## 7. 发版检查单（打包前）

- [ ] `app/__init__.py` 版本号、`packaging/version_info.txt`、`packaging/installer.iss` 三处版本号一致
- [ ] `packaging/gnss_agent.spec` 中 icon 已替换为品牌图标（可选但推荐）
- [ ] `scripts/smoke_test.py` 与 `scripts/stress_test.py` 在打包机上通过
- [ ] 按 §4 清单全量验收
