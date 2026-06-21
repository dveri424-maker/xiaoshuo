#!/usr/bin/env python3
"""Prepare a local Fanqie draft-save ledger from the novel chapter files.

This script does not open a browser and does not publish anything. It scans the
Markdown chapters under 正文/, validates chapter numbering, safely strips a
leading Markdown title line when present, computes content hashes, and creates or
updates data/fanqie_publish_state.json for the browser automation script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHAPTER_RE = re.compile(r"^第(\d{3})章-(.+)\.md$")
DRAFT_SAVED = "draft_saved"
DEFAULT_FORBIDDEN_MARKERS = ("TODO", "待补", "【修改】", "<!--")


@dataclass(frozen=True)
class Chapter:
    chapter_no: int
    chapter_label: str
    title: str
    publish_title: str
    source_file: Path
    raw_hash: str
    content_hash: str
    char_count: int
    line_count: int
    body_preview: str
    removed_heading: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def clean_markdown_body(raw: str) -> tuple[str, str | None]:
    """Return body text and the removed first Markdown heading, if any.

    Only an explicit Markdown level-1 heading (`# ...`) is removed. This avoids
    deleting real first paragraphs in early chapters that do not have headings.
    """
    text = normalize_newlines(raw).strip()
    if not text:
        return "", None

    lines = text.split("\n")
    first_non_empty = None
    for idx, line in enumerate(lines):
        if line.strip():
            first_non_empty = idx
            break

    if first_non_empty is None:
        return "", None

    line = lines[first_non_empty]
    stripped = line.lstrip()
    if stripped.startswith("# ") and not stripped.startswith("## "):
        removed = line.strip()
        del lines[first_non_empty]
        return "\n".join(lines).strip(), removed

    return text, None


def count_effective_chars(text: str) -> int:
    return sum(1 for ch in text if not ch.isspace())


def preview(text: str, limit: int = 80) -> str:
    one_line = " ".join(part.strip() for part in text.splitlines() if part.strip())
    return one_line[:limit]


def parse_chapter(path: Path) -> Chapter:
    match = CHAPTER_RE.match(path.name)
    if not match:
        raise ValueError(f"章节文件名不符合格式 第NNN章-标题.md: {path.name}")

    chapter_no = int(match.group(1))
    chapter_label = f"第{chapter_no:03d}章"
    title = match.group(2).strip()
    if not title:
        raise ValueError(f"章节标题为空: {path.name}")

    raw = read_text(path)
    raw_normalized = normalize_newlines(raw)
    body, removed_heading = clean_markdown_body(raw)
    publish_title = f"{chapter_label}-{title}"

    return Chapter(
        chapter_no=chapter_no,
        chapter_label=chapter_label,
        title=title,
        publish_title=publish_title,
        source_file=path,
        raw_hash=sha256_text(raw_normalized),
        content_hash=sha256_text(body),
        char_count=count_effective_chars(body),
        line_count=len(body.splitlines()) if body else 0,
        body_preview=preview(body),
        removed_heading=removed_heading,
    )


def load_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def existing_chapter_map(state: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not state:
        return {}
    return {int(item["chapter_no"]): item for item in state.get("chapters", [])}


def validate_chapters(
    chapters: list[Chapter],
    *,
    start: int | None,
    end: int | None,
    strict: bool,
    min_char_count: int,
    max_title_chars: int,
    forbidden_markers: tuple[str, ...],
) -> list[str]:
    errors: list[str] = []

    if not chapters:
        return ["未找到任何章节文件"]

    nums = [chapter.chapter_no for chapter in chapters]
    titles = [chapter.publish_title for chapter in chapters]
    hashes = [chapter.content_hash for chapter in chapters]

    duplicate_nums = [num for num, count in Counter(nums).items() if count > 1]
    duplicate_titles = [title for title, count in Counter(titles).items() if count > 1]
    duplicate_hashes = [h for h, count in Counter(hashes).items() if count > 1]

    if duplicate_nums:
        errors.append(f"发现重复章号: {duplicate_nums}")
    if duplicate_titles:
        errors.append(f"发现重复标题: {duplicate_titles[:10]}")
    if duplicate_hashes:
        errors.append(f"发现重复正文 hash: {duplicate_hashes[:5]}")

    expected_start = start if start is not None else min(nums)
    expected_end = end if end is not None else max(nums)
    expected = list(range(expected_start, expected_end + 1))
    if nums != expected:
        missing = sorted(set(expected) - set(nums))
        extra = sorted(set(nums) - set(expected))
        errors.append(f"章号不连续或范围不符；缺失={missing[:20]} 多余={extra[:20]}")

    for chapter in chapters:
        if not chapter.title.strip():
            errors.append(f"第{chapter.chapter_no:03d}章标题为空")
        if len(chapter.publish_title) > max_title_chars:
            errors.append(
                f"{chapter.publish_title} 标题长度 {len(chapter.publish_title)} 超过限制 {max_title_chars}"
            )
        if chapter.char_count == 0:
            errors.append(f"{chapter.publish_title} 正文为空")
        if chapter.char_count < min_char_count:
            errors.append(
                f"{chapter.publish_title} 正文字数偏低: {chapter.char_count} < {min_char_count}"
            )
        body_text = chapter.source_file.read_text(encoding="utf-8-sig")
        cleaned_body, _ = clean_markdown_body(body_text)
        for marker in forbidden_markers:
            if marker and marker in cleaned_body:
                errors.append(f"{chapter.publish_title} 包含禁止标记: {marker}")
                break

    if not strict:
        # In non-strict mode only structural errors should remain fatal.
        return [err for err in errors if "重复" in err or "不连续" in err or "为空" in err]

    return errors


def build_state(
    *,
    project_root: Path,
    chapters_dir: Path,
    state_path: Path,
    chapters: list[Chapter],
    old_state: dict[str, Any] | None,
    force_rebuild: bool,
) -> dict[str, Any]:
    old_by_no = existing_chapter_map(old_state)
    now = utc_now()
    entries: list[dict[str, Any]] = []

    for chapter in chapters:
        old = old_by_no.get(chapter.chapter_no, {})
        old_status = old.get("status")
        old_hash = old.get("content_hash")

        if old_status == DRAFT_SAVED and old_hash and old_hash != chapter.content_hash and not force_rebuild:
            raise RuntimeError(
                f"{chapter.publish_title} 已标记为草稿保存，但本地正文 hash 已变化；"
                "请人工确认远端草稿后再使用 --force-rebuild。"
            )

        status = old_status if old_status == DRAFT_SAVED and old_hash == chapter.content_hash else "pending"
        entry = {
            "chapter_no": chapter.chapter_no,
            "chapter_label": chapter.chapter_label,
            "title": chapter.publish_title,
            "title_text": chapter.title,
            "source_file": str(chapter.source_file.relative_to(project_root)),
            "raw_sha256": chapter.raw_hash,
            "content_sha256": chapter.content_hash,
            "char_count": chapter.char_count,
            "line_count": chapter.line_count,
            "body_preview": chapter.body_preview,
            "removed_heading": chapter.removed_heading,
            "status": status,
            "attempts": old.get("attempts", 0) if status == DRAFT_SAVED else 0,
            "last_attempt_at": old.get("last_attempt_at") if status == DRAFT_SAVED else None,
            "draft_saved_at": old.get("draft_saved_at") if status == DRAFT_SAVED else None,
            "pre_save_screenshot": old.get("pre_save_screenshot") if status == DRAFT_SAVED else None,
            "post_save_screenshot": old.get("post_save_screenshot") if status == DRAFT_SAVED else None,
            "error_type": None,
            "error_message": None,
            "page_url_at_error": None,
            "save_confirmation_text": old.get("save_confirmation_text") if status == DRAFT_SAVED else None,
        }
        entries.append(entry)

    total_chars = sum(chapter.char_count for chapter in chapters)
    shortest = min(chapters, key=lambda item: item.char_count)
    longest = max(chapters, key=lambda item: item.char_count)

    return {
        "schema_version": 1,
        "target_platform": "fanqie",
        "target_action": "save_draft_only",
        "project_root": str(project_root),
        "chapters_dir": str(chapters_dir.relative_to(project_root)),
        "state_file": str(state_path.relative_to(project_root)),
        "created_at": (old_state or {}).get("created_at", now),
        "updated_at": now,
        "summary": {
            "chapter_count": len(chapters),
            "first_chapter": chapters[0].chapter_no,
            "last_chapter": chapters[-1].chapter_no,
            "total_effective_chars": total_chars,
            "shortest_chapter": {"chapter_no": shortest.chapter_no, "title": shortest.publish_title, "char_count": shortest.char_count},
            "longest_chapter": {"chapter_no": longest.chapter_no, "title": longest.publish_title, "char_count": longest.char_count},
        },
        "chapters": entries,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    project_root = resolve_project_root()
    parser = argparse.ArgumentParser(description="Prepare Fanqie draft-save state from Markdown chapters.")
    parser.add_argument("--chapters-dir", default="正文", help="Chapter directory, relative to project root unless absolute.")
    parser.add_argument("--state", default="fanqie_draft_upload/data/fanqie_publish_state.json", help="State JSON path.")
    parser.add_argument("--start", type=int, default=None, help="First chapter number to include.")
    parser.add_argument("--end", type=int, default=None, help="Last chapter number to include.")
    parser.add_argument("--strict", action="store_true", help="Treat quality warnings as fatal.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print summary without writing state.")
    parser.add_argument("--force-rebuild", action="store_true", help="Allow rebuilding entries whose saved hash changed.")
    parser.add_argument("--min-char-count", type=int, default=500)
    parser.add_argument("--max-title-chars", type=int, default=80)
    parser.add_argument("--forbidden-marker", action="append", default=list(DEFAULT_FORBIDDEN_MARKERS))
    args = parser.parse_args(argv)

    chapters_dir = Path(args.chapters_dir)
    if not chapters_dir.is_absolute():
        chapters_dir = project_root / chapters_dir
    state_path = Path(args.state)
    if not state_path.is_absolute():
        state_path = project_root / state_path

    if not chapters_dir.is_dir():
        print(f"正文目录不存在: {chapters_dir}", file=sys.stderr)
        return 2

    chapters: list[Chapter] = []
    bad_names: list[str] = []
    for path in sorted(chapters_dir.glob("*.md")):
        if not CHAPTER_RE.match(path.name):
            bad_names.append(path.name)
            continue
        chapter = parse_chapter(path)
        if args.start is not None and chapter.chapter_no < args.start:
            continue
        if args.end is not None and chapter.chapter_no > args.end:
            continue
        chapters.append(chapter)

    chapters.sort(key=lambda item: item.chapter_no)
    errors = validate_chapters(
        chapters,
        start=args.start,
        end=args.end,
        strict=args.strict,
        min_char_count=args.min_char_count,
        max_title_chars=args.max_title_chars,
        forbidden_markers=tuple(args.forbidden_marker),
    )
    if bad_names:
        errors.append(f"正文目录存在不符合章节命名的 Markdown 文件: {bad_names[:20]}")

    if errors:
        print("质检失败：", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    old_state = load_state(state_path)
    try:
        state = build_state(
            project_root=project_root,
            chapters_dir=chapters_dir,
            state_path=state_path,
            chapters=chapters,
            old_state=old_state,
            force_rebuild=args.force_rebuild,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    summary = state["summary"]
    print("Fanqie 草稿台账准备完成")
    print(f"- 章节数: {summary['chapter_count']}")
    print(f"- 范围: 第{summary['first_chapter']:03d}章 - 第{summary['last_chapter']:03d}章")
    print(f"- 总有效字符: {summary['total_effective_chars']}")
    print(f"- 最短: 第{summary['shortest_chapter']['chapter_no']:03d}章 {summary['shortest_chapter']['char_count']} 字")
    print(f"- 最长: 第{summary['longest_chapter']['chapter_no']:03d}章 {summary['longest_chapter']['char_count']} 字")
    print("- 第001-003章清洗预览：")
    for chapter in chapters[:3]:
        print(f"  {chapter.publish_title}: removed_heading={chapter.removed_heading!r}, preview={chapter.body_preview[:40]}")

    if args.dry_run:
        print(f"dry-run：未写入 {state_path}")
        return 0

    write_json(state_path, state)
    print(f"已写入: {state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
