# 文献源接入矩阵 — GNSS 文献调研 Agent

> 目标：能接的源尽量都接上，但按"官方开放 API → 需 Key 商业源 → 爬虫/合规敏感源"分层接入。MVP 只做第一层（免费开放 API），后续层以可选插件扩展。

## 1. 接入优先级总览

| 优先级 | 源 | 官方 API | 需 Key | 费用 | MVP 接入 | 备注 |
|---|---|---|---|---|---|---|
| P0 | **OpenAlex** | ✅ | ❌ | 免费 | ✅ 已接 | 全球最大开放文献图谱，覆盖广、可批量、字段全，做主检索源 |
| P0 | **arXiv** | ✅ | ❌ | 免费 | ✅ 已接 | GNSS/PNT 预印本多（信号处理/组合导航/抗干扰），XML API 稳定 |
| P0 | **Semantic Scholar** | ✅ | ❌(限流) | 免费 | ✅ 已接 | 语义相关检索、引用量、开放 PDF，限流 100 次/5min |
| P0 | **Crossref** | ✅ | ❌ | 免费 | ✅ 已接 | 期刊论文元数据权威，补全 DOI/期刊/引用量 |
| P1 | **CORE** | ✅ | ✅(免费申请) | 免费 | 插件化 | 开放获取全文聚合，需用户申请 API Key |
| P1 | **DOAJ / Europe PMC** | ✅ | ❌ | 免费 | 插件化 | 开放获取期刊/生物医学（GNSS 相关度一般） |
| P2 | **IEEE Xplore API** | ✅ | ✅(机构订阅) | 付费 | 插件化 | GNSS 论文大户（TAES/TITS 等），需机构 Key，正文常付费 |
| P2 | **Springer Nature API** | ✅ | ✅ | 付费 | 插件化 | GPS Solutions / Journal of Navigation 的出版方 |
| P2 | **Elsevier（Scopus/ScienceDirect）** | ✅ | ✅(机构) | 付费 | 插件化 | 覆盖面大但贵，API 配额苛刻 |
| P3 | **Google Scholar** | ❌(反爬) | — | — | ❌ 不做 | 无官方 API，爬取违反 ToS，封禁风险高 |
| P3 | **CNKI / 万方 / 维普** | ❌(无公开 API) | — | — | ⚠️ 谨慎 | 中文库无官方 API；仅能爬虫，有合规风险；且 GNSS 中文文献量有限。列为远期可选，需用户确认合规 |

## 2. MVP 四源详情（已实现）

### 2.1 OpenAlex（主源）
- 接口：`GET https://api.openalex.org/works`
- 关键参数：`search=`（相关性检索）、`filter=from_publication_date:...,type:article|...`、`per-page=100`、`sort=relevance_score:desc`、`mailto=`（礼貌池，建议配置）
- 返回字段：doi、title、publication_year、authorships（作者）、abstract_inverted_index（倒排索引，需重建）、cited_by_count、primary_location.source.display_name（期刊）、open_access、referenced_works（引用网络，供扩展检索）
- 限流：无 Key 礼貌池约 10 rps；失败自动降速
- 价值：覆盖 arXiv/IEEE/Springer/Elsevier 的全部元数据，是去重与引用挖掘的枢纽

### 2.2 arXiv
- 接口：`GET https://export.arxiv.org/api/query`（Atom XML）
- 参数：`search_query=all:"..."`、`start/max_results`、`sortBy=relevance`
- 字段：id、title、summary（摘要）、authors、published、doi、journal_ref、categories
- 限流：3 秒间隔建议；重试 503
- 价值：预印本最新研究（PPP-RTK、LEO-PNT、抗欺骗等前沿主题）

### 2.3 Semantic Scholar
- 接口：`GET https://api.semanticscholar.org/graph/v1/paper/search`
- 参数：`query=`、`fields=title,abstract,authors,year,venue,externalIds,citationCount,url,openAccessPdf`、`limit=100`
- 限流：未认证 100 次/5min（严格退避，429 时等待窗口）
- 价值：语义相关性排序与开放 PDF 链接，与 OpenAlex 交叉验证

### 2.4 Crossref
- 接口：`GET https://api.crossref.org/works`
- 参数：`query.bibliographic=`、`rows=100`、`select=DOI,title,author,issued,abstract,container-title,URL,is-referenced-by-count`、`sort=relevance`
- 限流：礼貌池（加 `mailto`），429 退避
- 价值：DOI 权威解析、期刊名补全、引用量交叉校验

## 3. 统一归一化模型

所有源统一转换为内部 `Paper` 结构再入库（去重键：DOI，缺失则用标题归一化）：

```python
Paper = {
  "source": str,          # openalex | arxiv | semanticscholar | crossref
  "doi": str | None,
  "title": str,
  "authors": [str],
  "year": int | None,
  "venue": str | None,    # 期刊/会议名
  "abstract": str | None,
  "url": str | None,      # 首选可读链接
  "cited_by": int,
  "query_used": str,
}
```

## 4. 插件化扩展（P1/P2 设计）

- 每个源实现 `Source` 接口：`name / enabled / search(query, year_from, year_to, limit) -> list[Paper]`。
- 设置页可开关每个源；P2 商业源统一要求用户在设置页填自己的 Key（复用现有 Key 配置 UI）。
- CORE、IEEE、Springer 等按同样接口编写，插入 `app/sources/` 即可，无需改编排器。

## 5. 检索策略要点

1. **中英双语互补**：英文词打 OpenAlex/arXiv/S2/Crossref；中文词（北斗等）追加进 query 的 OR 组，保证中文文献覆盖。
2. **领域词库交叉**：主题解析出的关键词与内置 GNSS 子领域词库做 AND/OR 组合，提升精确率。
3. **期刊白名单过滤**：对 venue 命中白名单（如 ION GNSS+、GPS Solutions、NAVIGATION、IEEE TAES 等）的论文加权。
4. **时间滑动**：默认近 10 年；扩展阶段向更早年份滑动，覆盖经典文献。
5. **引用网络挖掘**：从 Top 论文的 `referenced_works`（OpenAlex）提取高被引关联文献，作为扩展候选。
