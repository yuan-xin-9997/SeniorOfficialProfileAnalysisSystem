"""Resume refresh job (runs in the background worker).

For every official with a ``source_url`` the job fetches the page through the
centralized WebFetch service and extracts the resume with a dedicated parser
(no LLM involved): zh.wikipedia.org pages go through the Wikipedia DOM parser,
everything else through the generic Chinese official-resume line parser.
Officials whose page text is unchanged (same sha256) are skipped in
``incremental`` mode, so repeated runs only do work for pages that changed.
"""
from __future__ import annotations

import hashlib

from sqlalchemy.orm import selectinload

from ...core.database import SessionLocal
from ...core.logging import get_logger
from ...core.timeutil import utcnow
from ...models.official import Career, Official
from ...models.task import TaskLog, TaskRun
from ...schemas.official import CareerData
from ..info_source.webfetch_client import WebFetchClient, WebFetchError
from .resume_parsers import is_wikipedia_url, parse_resume, parser_label_for

_logger = get_logger("resume_refresh")

# 哈希基准文本的最大长度，避免超长页面拖慢增量比对。
MAX_PAGE_CHARS = 12000


def _log(db, run_id: int, level: str, message: str) -> None:
    db.add(TaskLog(run_id=run_id, level=level, message=message))
    db.commit()


def _content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _html_to_text(html: str) -> str:
    """把抓取到的 HTML 归一化为纯文本（仅作增量哈希基准）。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html or "", "html.parser")
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    text = "\n".join(line for line in lines if line)
    return text[:MAX_PAGE_CHARS]


def _apply_careers(db, official: Official, careers: list[CareerData]) -> None:
    official.careers.clear()
    for index, item in enumerate(careers):
        data = item.model_dump(exclude={"id"})
        data["sort_order"] = index
        official.careers.append(Career(**data))
    official.resume_refreshed_at = utcnow()


def _refresh_one(client: WebFetchClient, db, official: Official, mode: str) -> tuple[str, int]:
    """刷新单个官员。返回 (动作, 条目数)，动作取值 updated | skipped。"""
    url = official.source_url
    # 维基百科域名在国内被 DNS 污染，需经集中抓取服务的代理策略出网。
    html = client.fetch_html(url, proxy_policy="proxy" if is_wikipedia_url(url) else None)
    text = _html_to_text(html)
    digest = _content_hash(text)
    if mode == "incremental" and official.resume_hash == digest:
        return "skipped", 0

    items = parse_resume(html, url, official.name)
    if not items:
        raise ValueError(f"{parser_label_for(url)}未能从页面解析出任何履历条目")
    try:
        careers = [CareerData.model_validate(item) for item in items]
    except Exception as exc:  # noqa: BLE001  解析器字段异常按单官员失败处理
        raise ValueError(f"解析结果字段无效: {exc}") from exc

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
        try:
            client = WebFetchClient()
        except WebFetchError as exc:
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
            _log(db, run_id, "INFO", f"共 {total} 位官员待刷新（专用解析器，不调用 LLM）")

            updated = skipped = failed = no_source = 0
            for official in officials:
                # 事务回滚后 ORM 对象会过期，循环开头先取出循环体需要的字段。
                name = official.name
                if not official.source_url:
                    no_source += 1
                    _log(db, run_id, "WARNING", f"{name}: 未配置来源链接（source_url），跳过")
                    continue
                try:
                    action, count = _refresh_one(client, db, official, mode)
                    if action == "skipped":
                        skipped += 1
                        _log(db, run_id, "INFO", f"{name}: 来源页面内容未变化，跳过")
                    else:
                        updated += 1
                        _log(db, run_id, "INFO", f"{name}: {parser_label_for(official.source_url)}已更新 {count} 条任职经历")
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
                run.error = f"全部 {total} 位官员刷新失败，请检查抓取服务与来源页面可达性"
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
