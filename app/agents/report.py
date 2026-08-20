"""中文调研报告生成：概述 + 子领域分布 + 逐篇深读 + 趋势与空白 + 参考文献。

增量更新：趋势与空白分析按"已深读论文集合"缓存（sidecar JSON），
论文集合未变化时直接复用，避免长跑期间重复调用 LLM。"""
import json
import os
import tempfile
from collections import Counter
from datetime import datetime

from ..config import reports_dir
from ..db import DB
from ..domain.terms import SUBFIELD_LABELS

SOURCE_LABELS = {
    "openalex": "OpenAlex",
    "arxiv": "arXiv",
    "semanticscholar": "Semantic Scholar",
    "crossref": "Crossref",
    "upload": "用户上传",
}


def _link(p: dict) -> str:
    doi = p.get("doi")
    if doi:
        return f"https://doi.org/{doi}"
    return p.get("url") or ""


async def generate_report(db: DB, task_id: str, analyst=None) -> str:
    task = await db.get_task(task_id)
    if not task:
        return ""
    read = await db.read_papers(task_id)
    counters = task["counters"]
    cost = task.get("cost") or {}
    queries = await db.list_queries(task_id)

    lines: list[str] = []
    lines.append(f"# {task['topic']} — 文献调研报告\n")
    lines.append(
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} · "
        f"任务状态：{task['status']} · 运行轮次：{task['rounds']}\n")
    lines.append(
        f"> 检索 {counters.get('found', 0)} 篇 → 相关 {counters.get('relevant', 0)} 篇 → "
        f"深读 {counters.get('read', 0)} 篇\n")
    lines.append("> 数据来源：OpenAlex / arXiv / Semantic Scholar / Crossref（官方开放 API）\n")

    # 一、调研概述
    lines.append("## 一、调研概述\n")
    if task.get("direction"):
        lines.append(f"- **调研主题**：{task['topic']}")
        lines.append(f"- **补充说明**：{task['direction']}")
    else:
        lines.append(f"- **调研主题**：{task['topic']}")
    src_counter = Counter(p["source"] for p in read)
    if src_counter:
        lines.append("- **来源分布（已深读）**：" +
                     "；".join(f"{SOURCE_LABELS.get(k, k)} {v} 篇" for k, v in src_counter.most_common()))
    year_counter = Counter(p.get("year") or 0 for p in read)
    if year_counter:
        years = sorted(year_counter.items())
        lines.append("- **年份分布（已深读）**：" +
                     "；".join(f"{y} 年 {v} 篇" for y, v in years))
    lines.append(f"- **检索轮次**：{task['rounds']} 轮，检索式 {len(queries)} 个")
    if cost.get("calls"):
        lines.append(
            f"- **大模型消耗**：调用 {cost['calls']} 次 · 输入 {cost.get('in_tokens', 0):,} tokens · "
            f"输出 {cost.get('out_tokens', 0):,} tokens · 估算成本 "
            f"${cost.get('est_cost_usd', 0):.3f}（按设置单价估算）")
    lines.append("")

    # 二、子领域分布
    lines.append("## 二、子领域分布\n")
    by_cat: dict[str, list] = {}
    for p in read:
        by_cat.setdefault(p.get("category") or "other", []).append(p)
    lines.append("| 子领域 | 深读篇数 | 代表文献 |")
    lines.append("|---|---|---|")
    for cat, papers in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        label = SUBFIELD_LABELS.get(cat, cat)
        top = sorted(papers, key=lambda p: -(p.get("relevance") or 0))[:2]
        reps = "；".join(f"[{t['title'][:40]}]({_link(t)})" for t in top)
        lines.append(f"| {label} | {len(papers)} | {reps} |")
    lines.append("")

    # 三、重点文献深读
    lines.append("## 三、重点文献深读\n")
    if not read:
        lines.append("（尚无深读完成的文献，报告将在任务继续运行中补充）\n")
    for cat, papers in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        label = SUBFIELD_LABELS.get(cat, cat)
        lines.append(f"### 子领域：{label}（{len(papers)} 篇）\n")
        papers_sorted = sorted(papers, key=lambda p: -(p.get("relevance") or 0))
        for i, p in enumerate(papers_sorted, 1):
            lines.append(f"#### {i}. {p['title']}")
            meta = []
            if p.get("year"):
                meta.append(str(p["year"]))
            if p.get("venue"):
                meta.append(p["venue"])
            if p.get("authors"):
                meta.append("、".join((p.get("authors") or [])[:3]) + (" 等" if len(p.get("authors") or []) > 3 else ""))
            if meta:
                lines.append(f"*{(' · ').join(meta)}*\n")
            kp = p.get("key_points") or {}
            lines.append(f"- **中文摘要**：{p.get('summary') or '（无）'}")
            if kp.get("methods"):
                lines.append("- **方法**：" + "；".join(str(m) for m in kp["methods"]))
            if kp.get("findings"):
                lines.append("- **关键结论**：" + "；".join(str(f) for f in kp["findings"]))
            if kp.get("relevance"):
                lines.append(f"- **与 GNSS 测试的相关性**：{kp['relevance']}")
            extra = []
            if p.get("relevance") is not None:
                extra.append(f"相关度 {p['relevance']:.2f}")
            if p.get("cited_by"):
                extra.append(f"被引 {p['cited_by']}")
            extra.append(SOURCE_LABELS.get(p.get("source"), p.get("source")))
            if extra:
                lines.append(f"- *{' · '.join(extra)}*")
            href = _link(p)
            if href:
                lines.append(f"- 链接：{href}")
            lines.append("")

    # 四、研究趋势与空白
    lines.append("## 四、研究趋势与空白\n")
    analysis = await _analysis_section(analyst, task, read)
    lines.append(analysis)
    lines.append("")

    # 五、参考文献
    lines.append("## 五、参考文献\n")
    refs = sorted(read, key=lambda p: -(p.get("cited_by") or 0))
    for i, p in enumerate(refs, 1):
        authors = "、".join((p.get("authors") or [])[:3])
        venue = p.get("venue") or "未知来源"
        line = f"{i}. {p['title']} — {authors}，{p.get('year') or '无年份'}，{venue}"
        href = _link(p)
        if href:
            line += f"。{href}"
        lines.append(line)
    lines.append("")

    md = "\n".join(lines)
    _write_atomic(task_id, md)
    return md


async def _analysis_section(analyst, task: dict, read: list) -> str:
    """分析师角色生成趋势与空白分析；论文集合未变时复用缓存；失败降级。"""
    if not read:
        return "（暂无数据，无法生成分析）\n"
    task_id = task["id"]
    ids = sorted(p["id"] for p in read)
    cache_file = reports_dir() / f"{task_id}.analysis.json"

    # 命中缓存：已深读论文集合与上次一致 → 直接复用
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if data.get("ids") == ids and data.get("text"):
                return data["text"]
        except (json.JSONDecodeError, OSError):
            pass

    grouped: dict[str, list[str]] = {}
    for p in read:
        cat = p.get("category") or "other"
        grouped.setdefault(cat, []).append(f"- {p['title']}：{(p.get('summary') or '')[:180]}")
    block = "\n".join(
        f"### {SUBFIELD_LABELS.get(cat, cat)}\n" + "\n".join(items)
        for cat, items in list(grouped.items())[:8])
    if analyst is None:
        return ("（未配置分析师角色，跳过趋势分析。可参考上方逐篇深读内容自行归纳。）\n")
    text = await analyst.analyze(len(read), block)
    text = (text or "").strip()
    if text and "模型未返回" not in text and "LLM 分析生成失败" not in text:
        _write_analysis_cache(task_id, ids, text)
        return text
    return text or "（模型未返回分析内容）\n"


def _write_analysis_cache(task_id: str, ids: list, text: str):
    cache_file = reports_dir() / f"{task_id}.analysis.json"
    fd, tmp = tempfile.mkstemp(dir=str(reports_dir()), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"ids": ids, "text": text}, f, ensure_ascii=False)
        os.replace(tmp, str(cache_file))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _write_atomic(task_id: str, md: str):
    d = reports_dir()
    path = d / f"{task_id}.md"
    fd, tmp = tempfile.mkstemp(dir=str(d), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(md)
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
