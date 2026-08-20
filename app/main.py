"""FastAPI 本地服务：API 路由 + 静态网页。仅监听 127.0.0.1。"""
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .agents.mock import MockLLM
from .agents.orchestrator import Orchestrator
from .config import (APP_NAME, DEFAULT_SETTINGS, STATIC_DIR, db_path,
                     reports_dir, uploads_dir)
from .db import DB
from .domain.terms import EXAMPLE_TOPICS
from .llm.client import LLMClient, LLMError
from .pdf_extract import PDFTextError, extract_pdf
from .sources import source_info

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("main")

db = DB(db_path())
# 演示模式：GNSS_AGENT_MOCK_LLM=1 时使用假模型（无需 API Key）
if os.environ.get("GNSS_AGENT_MOCK_LLM") == "1":
    logger.warning("演示模式：使用 Mock LLM，未连接真实大模型")
    orch = Orchestrator(db, llm_factory=lambda _s, _m=None: MockLLM())
else:
    orch = Orchestrator(db)


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await db.init()
    current = await db.get_settings()
    missing = {k: v for k, v in DEFAULT_SETTINGS.items() if k not in current}
    if missing:
        await db.set_settings(missing)
    await orch.resume_running()
    logger.info("GNSS 文献调研 Agent 已就绪，数据目录: %s", db_path().parent)
    yield
    await orch.shutdown()
    await db.close()


app = FastAPI(title=APP_NAME, version=__version__, lifespan=lifespan)


# ---------------- 模型 ----------------
class SettingsIn(BaseModel):
    api_base: str = ""
    api_key: str = ""
    model: str = ""
    mailto: str = ""
    sources_enabled: list[str] = []
    year_back: int = 10
    relevance_threshold: float = 0.6
    max_concurrent_tasks: int = 3
    target_count: int = 100
    time_limit_hours: float = 24.0
    price_in_per_m: float = 0.27
    price_out_per_m: float = 1.10
    max_task_cost_usd: float = 10.0
    reader_pool_size: int = 3
    qc_enabled: bool = True
    model_strategist: str = ""
    model_reviewer: str = ""
    model_reader: str = ""
    model_analyst: str = ""
    model_editor: str = ""


class TaskIn(BaseModel):
    topic: str
    direction: str = ""
    target_count: int | None = None
    time_limit_hours: float | None = None
    year_back: int | None = None
    max_task_cost_usd: float | None = None


# ---------------- 页面 ----------------
@app.get("/", include_in_schema=False)
async def index():
    resp = FileResponse(STATIC_DIR / "index.html")
    resp.headers["Cache-Control"] = "no-cache"  # 防止浏览器缓存旧界面
    return resp


class NoCacheStaticFiles(StaticFiles):
    """静态资源禁用缓存，避免前端更新后浏览器仍加载旧 JS/CSS。"""

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


app.mount("/static", NoCacheStaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------- 健康检查 ----------------
@app.get("/api/health")
async def health():
    settings = await db.get_settings()
    return {
        "ok": True,
        "app": APP_NAME,
        "version": __version__,
        "llm_configured": bool(settings.get("api_base") and settings.get("model")),
        "sources": source_info(),
    }


# ---------------- 设置 ----------------
@app.get("/api/settings")
async def get_settings():
    s = await db.get_settings()
    s["api_key"] = _mask_key(s.get("api_key", ""))
    try:
        s["sources_enabled"] = json.loads(s.get("sources_enabled") or "[]")
    except json.JSONDecodeError:
        s["sources_enabled"] = []
    return s


@app.put("/api/settings")
async def put_settings(body: SettingsIn):
    kv = body.model_dump(exclude_none=True)
    if kv.get("sources_enabled") is not None:
        kv["sources_enabled"] = json.dumps(kv["sources_enabled"], ensure_ascii=False)
    await db.set_settings(kv)
    return {"ok": True}


@app.post("/api/settings/test")
async def test_settings(body: SettingsIn):
    llm = LLMClient(body.api_base, body.api_key, body.model)
    try:
        reply = await llm.test()
        return {"ok": True, "reply": reply}
    except LLMError as e:
        return {"ok": False, "error": str(e)}


# ---------------- 示例与源 ----------------
@app.get("/api/example-topics")
async def example_topics():
    return {"topics": EXAMPLE_TOPICS}


@app.get("/api/sources")
async def sources():
    return {"sources": source_info()}


# ---------------- 任务 ----------------
@app.post("/api/tasks")
async def create_task(body: TaskIn):
    topic = (body.topic or "").strip()
    if not topic:
        raise HTTPException(400, "调研主题不能为空")
    settings = await db.get_settings()
    cfg = {
        "year_back": body.year_back or int(settings.get("year_back") or 10),
        "relevance_threshold": float(settings.get("relevance_threshold") or 0.6),
    }
    if body.max_task_cost_usd is not None:
        cfg["max_task_cost_usd"] = body.max_task_cost_usd
    task = await db.create_task(
        topic=topic,
        direction=(body.direction or "").strip(),
        target_count=body.target_count or int(settings.get("target_count") or 100),
        time_limit_hours=body.time_limit_hours or float(settings.get("time_limit_hours") or 24),
        config=cfg,
    )
    await db.add_log(task["id"], "任务已创建，开始自动工作")
    await orch.start(task["id"])
    return task


@app.get("/api/tasks")
async def list_tasks():
    return {"tasks": await db.list_tasks()}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    t = await db.get_task(task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    return t


@app.get("/api/tasks/{task_id}/papers")
async def list_papers(task_id: str,
                      status: str | None = Query(default=None),
                      category: str | None = Query(default=None),
                      offset: int = Query(default=0, ge=0),
                      limit: int = Query(default=200, ge=1, le=1000),
                      order: str = Query(default="relevance DESC")):
    papers = await db.get_papers(task_id, status=status, category=category,
                                 offset=offset, limit=limit, order=order)
    return {"papers": papers, "total": len(papers)}


@app.get("/api/tasks/{task_id}/logs")
async def get_logs(task_id: str, after_id: int = Query(default=0, ge=0),
                   limit: int = Query(default=200, ge=1, le=500)):
    return {"logs": await db.get_logs(task_id, after_id=after_id, limit=limit)}


@app.post("/api/tasks/{task_id}/upload")
async def upload_pdf(task_id: str, file: UploadFile = File(...)):
    """上传 PDF 论文：提取文本 → 直接进入该任务的深读队列（不再打分，视为高相关）。"""
    t = await db.get_task(task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件内容为空")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(400, "文件过大（上限 50MB）")

    task_uploads = uploads_dir() / task_id
    task_uploads.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex[:12]}.pdf"
    path = task_uploads / fname
    path.write_bytes(content)

    try:
        title, text = extract_pdf(path, fallback_title=Path(file.filename).stem)
    except PDFTextError as e:
        path.unlink(missing_ok=True)
        raise HTTPException(422, str(e)) from e

    papers = [{
        "source": "upload",
        "doi": None,
        "title": title[:300],
        "authors": [],
        "year": None,
        "venue": "用户上传",
        "abstract": text,
        "url": None,
        "cited_by": 0,
        "query_used": "upload",
        "_upload_file": str(path),
    }]
    added = await db.insert_papers(task_id, papers)
    if not added:
        raise HTTPException(409, "该论文已存在（标题重复）")
    # 上传论文直接视为相关，交给深读员池
    paper = await db.get_paper_by_key(task_id, None, title)
    await db.update_paper(paper["id"], status="relevant", relevance=1.0, category="other")
    counters = (await db.get_task(task_id))["counters"]
    counters["found"] = await db.count_papers(task_id)
    counters["relevant"] = await db.count_papers(task_id, status="relevant")
    await db.update_task(task_id, counters=counters)
    await db.add_log(task_id, f"已上传论文并加入深读队列：{title[:60]}…", "success")
    return {"ok": True, "paper": paper, "title": title}


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    t = await db.get_task(task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    if t["status"] not in ("running", "stopping"):
        return {"ok": True, "status": t["status"]}
    await db.update_task(task_id, status="stopping")
    await db.add_log(task_id, "用户请求停止：完成当前步骤后将生成最终报告")
    await orch.stop(task_id)
    return {"ok": True, "status": "stopping"}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务及其全部数据（仅允许非运行中任务）。"""
    t = await db.get_task(task_id)
    if not t:
        raise HTTPException(404, "任务不存在")
    if t["status"] in ("running", "stopping"):
        raise HTTPException(400, "任务正在运行，请先停止后再删除")
    ok = await db.delete_task(task_id)
    if not ok:
        raise HTTPException(404, "任务不存在")
    # 清理报告与分析缓存文件
    for suffix in (".md", ".analysis.json"):
        p = reports_dir() / f"{task_id}{suffix}"
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    return {"ok": True}


@app.get("/api/tasks/{task_id}/report")
async def get_report(task_id: str):
    path = reports_dir() / f"{task_id}.md"
    if not path.exists():
        raise HTTPException(404, "报告尚未生成（任务运行中会持续更新）")
    return {"content": path.read_text(encoding="utf-8"), "updated_at": path.stat().st_mtime}
