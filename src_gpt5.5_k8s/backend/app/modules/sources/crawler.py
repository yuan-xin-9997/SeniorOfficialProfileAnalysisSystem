from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import SourceConfig, SourceDocument


USER_AGENT = (
    "SeniorOfficialProfileAnalysisSystem/0.1 "
    "(internal research crawler; contact: local-admin)"
)


def crawl_source_config(db: Session, source_config: SourceConfig) -> SourceDocument:
    url = normalize_url(source_config.base_url)
    validate_url(url)

    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() in {"iso-8859-1", "ascii"}:
        response.encoding = response.apparent_encoding or "utf-8"

    html = response.text
    title, plain_text = extract_title_and_text(html)
    content_hash = hashlib.sha256(plain_text.encode("utf-8")).hexdigest()
    parse_status = "fetched"

    latest = (
        db.query(SourceDocument)
        .filter(SourceDocument.source_config_id == source_config.id)
        .order_by(SourceDocument.fetched_at.desc())
        .first()
    )
    if latest and latest.content_hash == content_hash:
        parse_status = "unchanged"

    document = SourceDocument(
        source_config_id=source_config.id,
        url=url,
        title=title,
        publisher=source_config.name,
        fetched_at=datetime.now(timezone.utc),
        http_status=response.status_code,
        content_hash=content_hash,
        trust_level=source_config.trust_level,
        parse_status=parse_status,
    )
    db.add(document)
    db.flush()

    raw_html_path, plain_text_path = save_snapshots(document.id, html, plain_text)
    document.raw_html_path = str(raw_html_path)
    document.plain_text_path = str(plain_text_path)
    db.commit()
    db.refresh(document)
    return document


def normalize_url(url: str) -> str:
    return url.strip()


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only http/https URLs are supported",
        )
    host = (parsed.hostname or "").lower()
    if host in {"localhost"} or host.startswith("127.") or host == "0.0.0.0":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loopback URLs are not allowed for crawling",
        )


def extract_title_and_text(html: str) -> tuple[str | None, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, text


def save_snapshots(document_id: str, html: str, plain_text: str) -> tuple[Path, Path]:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    directory = settings.RAW_DOCS_DIR / day
    directory.mkdir(parents=True, exist_ok=True)
    raw_html_path = directory / f"{document_id}.html"
    plain_text_path = directory / f"{document_id}.txt"
    raw_html_path.write_text(html, encoding="utf-8")
    plain_text_path.write_text(plain_text, encoding="utf-8")
    return raw_html_path, plain_text_path


def read_excerpt(path: str | None, limit: int = 500) -> str | None:
    if not path:
        return None
    text_path = Path(path)
    if not text_path.exists():
        return None
    text = text_path.read_text(encoding="utf-8", errors="ignore").strip()
    return text[:limit]
