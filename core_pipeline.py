#!/usr/bin/env python3
"""RSS-Brew core pipeline: fetch feeds, extract clean text, deduplicate.

Outputs a JSON payload of ONLY new, pure-text articles.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import feedparser
import trafilatura
import yaml
from pydantic import BaseModel, ValidationError


class Source(BaseModel):
    name: str
    url: str


class SourcesConfig(BaseModel):
    sources: List[Source]


def load_sources(path: Path) -> List[Source]:
    if not path.exists():
        raise FileNotFoundError(f"sources.yaml not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        config = SourcesConfig(**data)
    except ValidationError as exc:
        raise ValueError(f"Invalid sources.yaml: {exc}") from exc
    return config.sources


def load_dedup(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_dedup(path: Path, index: Dict[str, str]) -> None:
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def entry_datetime(entry) -> Optional[datetime]:
    # feedparser provides published_parsed / updated_parsed as time.struct_time
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct_time:
        return None
    return datetime.fromtimestamp(time.mktime(struct_time), tz=timezone.utc)


def extract_text(url: str) -> Optional[str]:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        include_images=False,
        favor_recall=False,
    )
    if not text:
        return None
    return text.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="RSS-Brew core pipeline")

    default_data_dir = Path(os.getenv("RSS_DATA_DIR", "./data"))

    parser.add_argument(
        "--sources",
        default=str(default_data_dir / "sources.yaml"),
        help="Path to sources.yaml",
    )
    parser.add_argument(
        "--dedup",
        default=str(default_data_dir / "processed-index.json"),
        help="Path to dedup index JSON",
    )
    parser.add_argument(
        "--output",
        default=str(default_data_dir / "new-articles.json"),
        help="Path to output JSON",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=48,
        help="Lookback window in hours",
    )
    args = parser.parse_args()

    sources_path = Path(args.sources)
    dedup_path = Path(args.dedup)
    output_path = Path(args.output)

    sources = load_sources(sources_path)
    dedup_index = load_dedup(dedup_path)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    new_articles = []
    updated_index = dict(dedup_index)

    for source in sources:
        feed = feedparser.parse(source.url)
        for entry in feed.entries:
            url = entry.get("link")
            title = entry.get("title")
            if not url or not title:
                continue

            published_dt = entry_datetime(entry)
            if not published_dt or published_dt < cutoff:
                continue

            url_hash = hash_url(url)
            if url_hash in updated_index:
                continue

            text = extract_text(url)
            if not text:
                continue

            article = {
                "source": source.name,
                "source_url": source.url,
                "title": title,
                "url": url,
                "published": published_dt.isoformat(),
                "text": text,
            }
            new_articles.append(article)
            updated_index[url_hash] = url

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "article_count": len(new_articles),
        "articles": new_articles,
    }

    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    save_dedup(dedup_path, updated_index)


if __name__ == "__main__":
    main()
