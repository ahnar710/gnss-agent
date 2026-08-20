"""PDF 论文文本提取：上传的论文进入深读流水线前的预处理。

- 提取标题：优先 PDF 元数据 title，其次文件名（去扩展名）
- 提取正文文本：pypdf 逐页提取；论文多为文本型 PDF，可正常解析
- 扫描版 PDF（无文本层）：抛出 PDFTextError，前端提示用户
"""
import logging
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger("pdf_extract")

MAX_TEXT_CHARS = 15000  # 存库上限（深读时再截断取用）


class PDFTextError(Exception):
    pass


def extract_pdf(path: Path, fallback_title: str = "") -> tuple[str, str]:
    """返回 (标题, 全文文本前 MAX_TEXT_CHARS 字符)。
    标题优先级：PDF 元数据 title > fallback_title（原始文件名）> 文件 basename。"""
    try:
        reader = PdfReader(str(path))
    except Exception as e:  # noqa: BLE001
        raise PDFTextError(f"无法读取 PDF：{e}") from e

    # 标题：元数据优先，其次原始文件名，最后文件 basename
    title = ""
    try:
        meta_title = (reader.metadata or {}).get("title")
        if meta_title and str(meta_title).strip():
            title = str(meta_title).strip()
    except Exception:  # noqa: BLE001
        pass
    if not title:
        title = (fallback_title or Path(path).stem).strip()

    pages_text = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            t = ""
        if t.strip():
            pages_text.append(t.strip())
    text = "\n\n".join(pages_text)
    if len(text) < 200:
        raise PDFTextError("未能从 PDF 提取到足够文本（可能是扫描版/图片型 PDF，暂不支持 OCR）")
    return title, text[:MAX_TEXT_CHARS]
