"""Resume refresh job (runs in the background worker).

For every official with a ``source_url`` the job fetches the page through the
centralized WebFetch service, extracts the resume with the configured LLM and
replaces the official's career rows. Officials whose page text is unchanged
(same sha256) are skipped in ``incremental`` mode, so repeated runs only do
work for pages that actually changed.
"""
from __future__ import annotations

import hashlib
import json

from bs4 import BeautifulSoup
from pydantic import ValidationError
from sqlalchemy.orm import selectinload

from ...core.database import SessionLocal
from ...core.logging import get_logger
from ...core.timeutil import utcnow
from ...models.official import Career, Official
from ...models.task import TaskLog, TaskRun
from ...schemas.official import CareerData
from ..analysis.llm_client import LLMClient, LLMError
from ..info_source.webfetch_client import WebFetchClient, WebFetchError

_logger = get_logger("resume_refresh")

# 送入 LLM 前的最大页面文本长度，避免超出上下文与无谓的 token 消耗。
MAX_PAGE_CHARS = 12000

_SYSTEM_PROMPT = (
    "你是严谨的中文人物履历数据抽取助手。只依据给定网页文本抽取该人物的任职经历，"
    "不得虚构文本中没有的事实。只返回 JSON 对象，不要使用 Markdown。"
)


def _user_prompt(name: str, page_text: str) -> str:
    return (
        f"从下面的网页文本中抽取「{name}」的任职经历（履历），按时间从早到晚排序，"
        '返回 JSON：{"careers": [{"start_date": "YYYY.MM 或空字符串", '
        '"end_date": "YYYY.MM 或 至今", "organization": "机构或空字符串", '
        '"position": "职务", "location": "地点或空字符串", '
        '"administrative_rank": "行政级别或空字符串", "description": "一句话说明或空字符串"}]}。'
        "日期尽量用 YYYY.MM 格式；在任的写「至今」。只抽取该人物本人的经历。\n\n"
        f"网页文本：\n{page_text}"
    )


def _log(db, run_id: int, level: str, message: str) -> None:
    db.add(TaskLog(run_id=run_id, level=level, message=message))
    db.commit()


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _html_to_text(html: str) -> str:
    """把抓取到的 HTML 归一化为纯文本（供哈希比较与 LLM 抽取）。"""
    soup = BeautifulSoup(html or "", "html.parser")
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    text = "\n".join(line for line in lines if line)
    return text[:MAX_PAGE_CHARS]


def _parse_llm_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("模型返回的不是 JSON 对象")
    return data


def _apply_careers(db, official: Official, careers: list[CareerData]) -> None:
    official.careers.clear()
    for index, item in enumerate(careers):
        data = item.model_dump(exclude={"id"})
        data["sort_order"] = index
        official.careers.append(Career(**data))
    official.resume_refreshed_at = utcnow()


def _refresh_one(client: WebFetchClient, llm: LLMClient, db, official: Official, mode: str) -> tuple[str, int]:
    """刷新单个官员。返回 (动作, 条目数)，动作取值 updated | skipped。"""
    html = client.fetch_html(official.source_url)
    text = _html_to_text(html)
    digest = _content_hash(text)
    if mode == "incremental" and official.resume_hash == digest:
        return "skipped", 0

    raw = llm.chat(_SYSTEM_PROMPT, _user_prompt(official.name, text))
    data = _parse_llm_json(raw)
    items = data.get("careers") or []
    if not isinstance(items, list) or not items:
        raise ValueError("模型未解析出任何履历条目")
    try:
        careers = [CareerData.model_validate(item) for item in items]
    except ValidationError as exc:
        raise ValueError(f"模型返回的履历条目格式无效: {exc}") from exc

    _apply_careers(db, official, careers)
    official.resume_hash = digest
    return "updated", len(careers)


def run_resume_refresh(run_id: int, mode: str = "incremental") -> None:
    """Refresh resumes for all officials and update the TaskRun."""
    with SessionLocal() as db:
        run = db.get(TaskRun, run_id)
        if run is None:
            return

        run.status = "running"
        run.started_at = utcnow()
        db.commit()
        _log(db, run_id, "INFO", f"开始履历刷新（模式: {mode}），正在准备抓取与解析服务…")

        try:
            client = WebFetchClient()
            llm = LLMClient()
        except (WebFetchError, LLMError) as exc:
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = utcnow()
            _log(db, run_id, "ERROR", f"履历刷新无法启动: {exc}")
            db.commit()
            return

        try:
            officials = (
                db.query(Official)
                .options(selectinload(Official.careers))
                .order_by(Official.id.asc())
                .all()
            )
            total = len(officials)
            _log(db, run_id, "INFO", f"共 {total} 位官员待刷新")

            updated = skipped = failed = no_source = 0
            for official in officials:
                # 事务回滚后 ORM 对象会过期，循环开头先取出循环体需要的字段。
                name = official.name
                if not official.source_url:
                    no_source += 1
                    _log(db, run_id, "WARNING", f"{name}: 未配置来源链接（source_url），跳过")
                    continue
                try:
                    action, count = _refresh_one(client, llm, db, official, mode)
                    if action == "skipped":
                        skipped += 1
                        _log(db, run_id, "INFO", f"{name}: 来源页面内容未变化，跳过")
                    else:
                        updated += 1
                        _log(db, run_id, "INFO", f"{name}: 已更新 {count} 条任职经历")
                    db.commit()
                except Exception as exc:  # noqa: BLE001  单人失败不阻断整体
                    db.rollback()
                    failed += 1
                    _logger.exception("履历刷新失败: %s", name)
                    _log(db, run_id, "ERROR", f"{name}: 刷新失败: {exc}")

            summary = (
                f"履历刷新完成: 共 {total} 人, 更新 {updated}, 跳过 {skipped}, "
                f"无来源 {no_source}, 失败 {failed}"
            )
            run.finished_at = utcnow()
            if total and updated == 0 and skipped == 0 and failed == total:
                run.status = "failed"
                run.error = f"全部 {total} 位官员刷新失败，请检查抓取服务与 LLM 配置"
                _log(db, run_id, "ERROR", run.error)
            else:
                run.status = "succeeded"
            run.summary = summary
            _log(db, run_id, "INFO", summary)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            _logger.exception("履历刷新任务异常")
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = utcnow()
            _log(db, run_id, "ERROR", f"履历刷新失败: {exc}")
            db.commit()
