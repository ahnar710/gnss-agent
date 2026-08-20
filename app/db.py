"""SQLite 持久化层（aiosqlite）。所有任务状态、论文、日志、设置落盘，支撑断点续跑。"""
import hashlib
import json
import re
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  topic TEXT NOT NULL,
  direction TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'running',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  started_at TEXT,
  stopped_at TEXT,
  rounds INTEGER NOT NULL DEFAULT 0,
  target_count INTEGER NOT NULL DEFAULT 100,
  time_limit_hours REAL NOT NULL DEFAULT 24,
  config TEXT NOT NULL DEFAULT '{}',
  counters TEXT NOT NULL DEFAULT '{}',
  cost TEXT NOT NULL DEFAULT '{}',
  error TEXT
);

CREATE TABLE IF NOT EXISTS queries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  text TEXT NOT NULL,
  source TEXT NOT NULL,
  searched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_queries_task ON queries(task_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_queries_unique ON queries(task_id, text, source);

CREATE TABLE IF NOT EXISTS papers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  source TEXT NOT NULL,
  doi TEXT,
  title TEXT NOT NULL,
  authors TEXT NOT NULL DEFAULT '[]',
  year INTEGER,
  venue TEXT,
  abstract TEXT,
  url TEXT,
  cited_by INTEGER NOT NULL DEFAULT 0,
  query_used TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  relevance REAL,
  category TEXT,
  summary TEXT,
  key_points TEXT,
  extras TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_papers_task ON papers(task_id);
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(task_id, status);

CREATE TABLE IF NOT EXISTS task_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  level TEXT NOT NULL DEFAULT 'info',
  message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_task ON task_logs(task_id);
"""


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def title_key(title: str) -> str:
    """标题归一化，用于去重。"""
    t = (title or "").lower()
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def paper_key(doi: Optional[str], title: str) -> str:
    if doi:
        return "doi:" + doi.lower().strip()
    return "title:" + hashlib.sha1(title_key(title).encode("utf-8")).hexdigest()[:16]


class DB:
    def __init__(self, path):
        self.path = str(path)
        self._conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        import os
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.executescript(SCHEMA)
        await self._migrate()
        await self._conn.commit()

    async def _migrate(self):
        """轻量列迁移：旧库补新列（cost）。"""
        rows = await self._fetchall("PRAGMA table_info(tasks)")
        names = {r["name"] for r in rows}
        if "cost" not in names:
            await self._execute(
                "ALTER TABLE tasks ADD COLUMN cost TEXT NOT NULL DEFAULT '{}'")

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def _execute(self, sql: str, params: tuple = ()):
        cur = await self._conn.execute(sql, params)
        await self._conn.commit()
        return cur

    async def _fetchall(self, sql: str, params: tuple = ()) -> list:
        cur = await self._conn.execute(sql, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def _fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        rows = await self._fetchall(sql, params)
        return rows[0] if rows else None

    # ---------- settings ----------
    async def get_settings(self) -> dict:
        rows = await self._fetchall("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in rows}

    async def set_settings(self, kv: dict):
        for k, v in kv.items():
            await self._execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (k, str(v)),
            )

    # ---------- tasks ----------
    async def create_task(self, topic: str, direction: str, target_count: int,
                          time_limit_hours: float, config: dict) -> dict:
        tid = uuid.uuid4().hex[:12]
        ts = now_iso()
        await self._execute(
            "INSERT INTO tasks(id, topic, direction, status, created_at, updated_at, "
            "started_at, target_count, time_limit_hours, config, counters) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (tid, topic, direction, "running", ts, ts, ts, target_count,
             time_limit_hours, json.dumps(config, ensure_ascii=False),
             json.dumps({"found": 0, "relevant": 0, "read": 0, "queries": 0})),
        )
        return await self.get_task(tid)

    async def get_task(self, tid: str) -> Optional[dict]:
        t = await self._fetchone("SELECT * FROM tasks WHERE id=?", (tid,))
        if t:
            t["config"] = json.loads(t["config"] or "{}")
            t["counters"] = json.loads(t["counters"] or "{}")
            t["cost"] = json.loads(t["cost"] or "{}")
        return t

    async def list_tasks(self) -> list:
        rows = await self._fetchall("SELECT * FROM tasks ORDER BY created_at DESC")
        for r in rows:
            r["config"] = json.loads(r["config"] or "{}")
            r["counters"] = json.loads(r["counters"] or "{}")
            r["cost"] = json.loads(r["cost"] or "{}")
        return rows

    async def update_task(self, tid: str, **fields):
        if not fields:
            return
        fields["updated_at"] = now_iso()
        if "config" in fields:
            fields["config"] = json.dumps(fields["config"], ensure_ascii=False)
        if "counters" in fields:
            fields["counters"] = json.dumps(fields["counters"], ensure_ascii=False)
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values())
        await self._execute(
            f"UPDATE tasks SET {sets} WHERE id=?",
            tuple(vals) + (tid,),
        )

    # ---------- queries（幂等） ----------
    async def add_query(self, task_id: str, text: str, source: str):
        await self._execute(
            "INSERT OR IGNORE INTO queries(task_id, text, source, searched_at) VALUES(?,?,?,?)",
            (task_id, text, source, now_iso()),
        )

    async def has_query(self, task_id: str, text: str, source: str) -> bool:
        r = await self._fetchone(
            "SELECT 1 AS x FROM queries WHERE task_id=? AND text=? AND source=?",
            (task_id, text, source),
        )
        return r is not None

    async def has_query_text(self, task_id: str, text: str) -> bool:
        """该检索式是否已在任一源检索过（用于任务恢复时的幂等判断）。"""
        r = await self._fetchone(
            "SELECT 1 AS x FROM queries WHERE task_id=? AND text=?", (task_id, text))
        return r is not None

    async def list_queries(self, task_id: str) -> list:
        return await self._fetchall(
            "SELECT text, source FROM queries WHERE task_id=?", (task_id,))

    # ---------- papers ----------
    async def insert_papers(self, task_id: str, papers: list) -> int:
        """批量插入并去重（DOI 优先，其次标题归一化），返回新增数量。"""
        existing = await self._fetchall(
            "SELECT doi, title FROM papers WHERE task_id=?", (task_id,))
        seen = {paper_key(r.get("doi"), r.get("title") or "") for r in existing}
        added = 0
        for p in papers:
            title = (p.get("title") or "").strip()
            if not title:
                continue
            key = paper_key(p.get("doi"), title)
            if key in seen:
                continue
            seen.add(key)
            ts = now_iso()
            extras = {k: v for k, v in p.items() if k.startswith("_")}
            await self._execute(
                "INSERT INTO papers(task_id, source, doi, title, authors, year, venue, "
                "abstract, url, cited_by, query_used, status, extras, created_at, updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (task_id, p.get("source", ""), p.get("doi"), title,
                 json.dumps(p.get("authors", []), ensure_ascii=False),
                 p.get("year"), p.get("venue"), p.get("abstract"),
                 p.get("url"), int(p.get("cited_by") or 0),
                 p.get("query_used"), "pending",
                 json.dumps(extras, ensure_ascii=False), ts, ts),
            )
            added += 1
        return added

    async def get_papers(self, task_id: str, status: Optional[str] = None,
                         category: Optional[str] = None, limit: int = 200,
                         offset: int = 0, order: str = "created_at DESC") -> list:
        sql = "SELECT * FROM papers WHERE task_id=?"
        params: list = [task_id]
        if status:
            sql += " AND status=?"
            params.append(status)
        if category:
            sql += " AND category=?"
            params.append(category)
        sql += f" ORDER BY {order} LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = await self._fetchall(sql, tuple(params))
        for r in rows:
            r["authors"] = json.loads(r["authors"] or "[]")
            r["key_points"] = json.loads(r["key_points"] or "null")
            r["extras"] = json.loads(r["extras"] or "{}")
        return rows

    async def count_papers(self, task_id: str, status: Optional[str] = None) -> int:
        sql = "SELECT COUNT(*) AS n FROM papers WHERE task_id=?"
        params: list = [task_id]
        if status:
            sql += " AND status=?"
            params.append(status)
        r = await self._fetchone(sql, tuple(params))
        return r["n"] if r else 0

    async def pending_papers(self, task_id: str, limit: int = 100) -> list:
        return await self.get_papers(task_id, status="pending", limit=limit,
                                     order="cited_by DESC")

    async def relevant_papers(self, task_id: str, limit: int = 50) -> list:
        return await self.get_papers(task_id, status="relevant", limit=limit,
                                     order="relevance DESC")

    async def read_papers(self, task_id: str) -> list:
        return await self.get_papers(task_id, status="read", limit=10000,
                                     order="relevance DESC")

    async def update_paper(self, pid: int, **fields):
        fields["updated_at"] = now_iso()
        if "authors" in fields:
            fields["authors"] = json.dumps(fields["authors"], ensure_ascii=False)
        if "key_points" in fields:
            fields["key_points"] = json.dumps(fields["key_points"], ensure_ascii=False)
        if "extras" in fields:
            fields["extras"] = json.dumps(fields["extras"], ensure_ascii=False)
        sets = ", ".join(f"{k}=?" for k in fields)
        await self._execute(
            f"UPDATE papers SET {sets} WHERE id=?", tuple(fields.values()) + (pid,))

    # ---------- 深读认领（多 Worker 协作） ----------
    async def claim_next_relevant(self, task_id: str) -> Optional[dict]:
        """原子认领一条优先级最高的相关论文（置 reading），无则返回 None。

        并发安全：不显式开事务（aiosqlite 共享连接不支持嵌套事务），
        用「条件 UPDATE + rowcount 校验」保证同一篇论文只有一个 worker 认领成功。
        优先级：relevance × log(引用+2) × 白名单 × 近3年时效。
        """
        rows = await self._fetchall(
            "SELECT * FROM papers WHERE task_id=? AND status='relevant' "
            "ORDER BY relevance DESC, cited_by DESC LIMIT 30", (task_id,))
        if not rows:
            return None
        year_now = datetime.now().year
        best = max(rows, key=lambda p: self._read_priority(p, year_now))
        extras = json.loads(best.get("extras") or "{}")
        extras["attempts"] = int(extras.get("attempts", 0)) + 1
        cur = await self._execute(
            "UPDATE papers SET status='reading', extras=?, updated_at=? "
            "WHERE id=? AND status='relevant'",
            (json.dumps(extras, ensure_ascii=False), now_iso(), best["id"]))
        if not cur.rowcount:
            return None  # 已被其他 worker 认领，放弃本次
        best["extras"] = extras
        best["authors"] = json.loads(best.get("authors") or "[]")
        best["key_points"] = json.loads(best.get("key_points") or "null")
        return best

    @staticmethod
    def _read_priority(p: dict, year_now: int) -> float:
        import math
        score = float(p.get("relevance") or 0.5)
        cited = int(p.get("cited_by") or 0)
        base = score * (1.0 + math.log(cited + 2))
        venue = (p.get("venue") or "").lower()
        from .domain.terms import JOURNAL_WHITELIST
        if any(w in venue for w in JOURNAL_WHITELIST):
            base *= 1.2
        year = p.get("year")
        if year and year_now - int(year) <= 3:
            base *= 1.15
        return base

    async def release_paper(self, pid: int):
        """深读失败：释放回相关队列（保留 attempts 计数）。"""
        await self._execute(
            "UPDATE papers SET status='relevant', updated_at=? WHERE id=?",
            (now_iso(), pid))

    async def release_if_reading(self, pid: int):
        """取消时：仅当论文仍在 reading 状态才释放（避免已完成的重复读）。"""
        await self._execute(
            "UPDATE papers SET status='relevant', updated_at=? "
            "WHERE id=? AND status='reading'",
            (now_iso(), pid))

    async def mark_failed(self, pid: int):
        await self._execute(
            "UPDATE papers SET status='failed', updated_at=? WHERE id=?",
            (now_iso(), pid))

    async def reset_reading(self, task_id: str):
        """恢复崩溃遗留的 reading 论文：重试未超限回队列，超限标失败。"""
        await self._execute(
            "UPDATE papers SET status='relevant', updated_at=? "
            "WHERE task_id=? AND status='reading' "
            "AND COALESCE(json_extract(extras,'$.attempts'),0) < 3",
            (now_iso(), task_id))
        await self._execute(
            "UPDATE papers SET status='failed', updated_at=? "
            "WHERE task_id=? AND status='reading'",
            (now_iso(), task_id))

    async def recent_read_papers(self, task_id: str, after_id: int = 0,
                                 limit: int = 20) -> list:
        """质控用：拉取新近深读、且未被质控标记的论文。"""
        rows = await self._fetchall(
            "SELECT * FROM papers WHERE task_id=? AND status='read' AND id>? "
            "AND COALESCE(json_extract(extras,'$.qc'),0)!=1 ORDER BY id LIMIT ?",
            (task_id, after_id, limit))
        for r in rows:
            r["authors"] = json.loads(r["authors"] or "[]")
            r["key_points"] = json.loads(r["key_points"] or "null")
            r["extras"] = json.loads(r["extras"] or "{}")
        return rows

    async def inc_counter(self, task_id: str, key: str, delta: int = 1):
        """原子自增任务计数（并发安全）。"""
        await self._execute(
            "UPDATE tasks SET counters=json_set(COALESCE(counters,'{}'), ?, "
            "COALESCE(json_extract(counters, ?),0)+?), updated_at=? WHERE id=?",
            (f"$.{key}", f"$.{key}", delta, now_iso(), task_id))

    async def get_paper_by_key(self, task_id: str, doi: Optional[str], title: str):
        key = paper_key(doi, title)
        if doi:
            return await self._fetchone(
                "SELECT * FROM papers WHERE task_id=? AND doi=?", (task_id, doi))
        rows = await self._fetchall("SELECT * FROM papers WHERE task_id=?", (task_id,))
        for r in rows:
            if paper_key(r.get("doi"), r.get("title") or "") == key:
                r["authors"] = json.loads(r["authors"] or "[]")
                return r
        return None

    # ---------- logs ----------
    async def add_log(self, task_id: str, message: str, level: str = "info"):
        await self._execute(
            "INSERT INTO task_logs(task_id, ts, level, message) VALUES(?,?,?,?)",
            (task_id, now_iso(), level, message),
        )

    async def get_logs(self, task_id: str, after_id: int = 0, limit: int = 200) -> list:
        return await self._fetchall(
            "SELECT * FROM task_logs WHERE task_id=? AND id>? ORDER BY id LIMIT ?",
            (task_id, after_id, limit),
        )

    async def prune_logs(self, task_id: str, keep: int = 2000):
        """日志滚动：每个任务只保留最近 keep 条，防止长跑磁盘膨胀。"""
        await self._execute(
            "DELETE FROM task_logs WHERE task_id=? AND id NOT IN "
            "(SELECT id FROM task_logs WHERE task_id=? ORDER BY id DESC LIMIT ?)",
            (task_id, task_id, keep),
        )

    async def checkpoint(self):
        """WAL 压缩，保持 DB 文件紧凑（长跑定期调用）。"""
        try:
            await self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            await self._conn.commit()
        except Exception:  # noqa: BLE001
            pass

    # ---------- 成本 ----------
    async def add_cost(self, task_id: str, prompt_tokens: int = 0,
                       completion_tokens: int = 0, est_cost_usd: float = 0.0):
        t = await self._fetchone("SELECT cost FROM tasks WHERE id=?", (task_id,))
        if not t:
            return
        c = json.loads(t["cost"] or "{}")
        c["calls"] = int(c.get("calls", 0)) + 1
        c["in_tokens"] = int(c.get("in_tokens", 0)) + int(prompt_tokens or 0)
        c["out_tokens"] = int(c.get("out_tokens", 0)) + int(completion_tokens or 0)
        c["est_cost_usd"] = round(float(c.get("est_cost_usd", 0.0))
                                  + float(est_cost_usd or 0.0), 6)
        await self._execute(
            "UPDATE tasks SET cost=?, updated_at=? WHERE id=?",
            (json.dumps(c, ensure_ascii=False), now_iso(), task_id),
        )

    # ---------- 任务清理 ----------
    async def delete_task(self, task_id: str) -> bool:
        """级联删除任务及其论文/检索式/日志。"""
        await self._execute("DELETE FROM papers WHERE task_id=?", (task_id,))
        await self._execute("DELETE FROM queries WHERE task_id=?", (task_id,))
        await self._execute("DELETE FROM task_logs WHERE task_id=?", (task_id,))
        cur = await self._execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return cur.rowcount > 0
