#!/usr/bin/env python3
"""Save prepared novel chapters to Fanqie drafts via the official web UI.

Safety boundaries:
- This script only saves drafts. It has no publish/schedule mode.
- It does not store passwords and does not bypass verification challenges.
- It uses a persistent browser profile so the user can log in manually.
- It stops on selector failures, duplicate warnings, hash changes, or unclear save confirmation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from fanqie_prepare_manifest import clean_markdown_body, sha256_text
except ImportError:  # pragma: no cover - fallback for unusual invocation paths
    def sha256_text(text: str) -> str:
        import hashlib

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def clean_markdown_body(raw: str) -> tuple[str, str | None]:
        text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
        lines = text.split("\n") if text else []
        for idx, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped:
                if stripped.startswith("# ") and not stripped.startswith("## "):
                    removed = line.strip()
                    del lines[idx]
                    return "\n".join(lines).strip(), removed
                break
        return text, None

DRAFT_SAVED = "draft_saved"
DRAFT_SAVING = "draft_saving"
FAILED_INTERRUPTED = "failed_interrupted"
PENDING = "pending"

try:
    from playwright.async_api import BrowserContext, Locator, Page, TimeoutError as PlaywrightTimeoutError, async_playwright
except ModuleNotFoundError:  # Allow `audit --help`-style local commands before dependencies are installed.
    BrowserContext = Locator = Page = Any  # type: ignore[assignment]
    async_playwright = None  # type: ignore[assignment]

    class PlaywrightTimeoutError(Exception):
        pass


class FanqieError(RuntimeError):
    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise FanqieError("failed_config", f"配置文件格式错误: {path}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FanqieError("failed_state", f"状态文件不存在，请先运行 fanqie_prepare_manifest.py: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def chapters_by_no(state: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(item["chapter_no"]): item for item in state.get("chapters", [])}


def select_chapters(
    state: dict[str, Any],
    *,
    start: int | None,
    end: int | None,
    limit: int | None,
    only_chapter: int | None,
    resume: bool,
) -> list[dict[str, Any]]:
    chapters = sorted(state.get("chapters", []), key=lambda item: int(item["chapter_no"]))
    selected: list[dict[str, Any]] = []
    for item in chapters:
        no = int(item["chapter_no"])
        if only_chapter is not None and no != only_chapter:
            continue
        if start is not None and no < start:
            continue
        if end is not None and no > end:
            continue
        status = item.get("status")
        if status == DRAFT_SAVED:
            continue
        if status == DRAFT_SAVING:
            raise FanqieError(
                "failed_interrupted",
                f"第{no:03d}章遗留 draft_saving 状态。请先人工确认远端草稿，再手动改回 pending 或标记 draft_saved。",
            )
        if resume:
            if status == PENDING or str(status or "").startswith("failed_"):
                selected.append(item)
        elif status == PENDING:
            selected.append(item)
    if limit is not None:
        selected = selected[:limit]
    return selected


def get_configured_selectors(config: dict[str, Any], name: str) -> list[dict[str, Any]]:
    selectors = (config.get("selectors") or {}).get(name) or []
    if not isinstance(selectors, list):
        raise FanqieError("failed_config", f"selectors.{name} 必须是列表")
    return selectors


def locator_from_spec(page: Page, spec: dict[str, Any]) -> Locator:
    kind = spec.get("kind")
    value = str(spec.get("value", ""))
    if not value:
        raise FanqieError("failed_config", f"选择器缺少 value: {spec}")
    if kind == "role":
        role = spec.get("role")
        if not role:
            raise FanqieError("failed_config", f"role 选择器缺少 role: {spec}")
        return page.get_by_role(role, name=value)
    if kind == "text":
        return page.get_by_text(value)
    if kind == "label":
        return page.get_by_label(value)
    if kind == "placeholder":
        return page.get_by_placeholder(value)
    if kind == "css":
        return page.locator(value)
    raise FanqieError("failed_config", f"未知选择器 kind={kind!r}: {spec}")


async def first_visible(page: Page, specs: list[dict[str, Any]], *, name: str, timeout_ms: int = 2000) -> Locator:
    if not specs:
        raise FanqieError("failed_selector", f"未配置选择器: {name}")
    last_error: Exception | None = None
    for spec in specs:
        locator = locator_from_spec(page, spec).first
        try:
            await locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except Exception as exc:  # Playwright can raise strictness/timeout errors here.
            last_error = exc
    raise FanqieError("failed_selector", f"找不到可见元素 {name}: {last_error}")


async def maybe_visible(page: Page, specs: list[dict[str, Any]], *, timeout_ms: int = 800) -> Locator | None:
    for spec in specs:
        locator = locator_from_spec(page, spec).first
        try:
            await locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except Exception:
            continue
    return None


async def click_selector(page: Page, config: dict[str, Any], name: str, *, timeout_ms: int = 3000) -> None:
    locator = await first_visible(page, get_configured_selectors(config, name), name=name, timeout_ms=timeout_ms)
    await locator.click()


async def click_optional_selector(page: Page, config: dict[str, Any], name: str, *, timeout_ms: int = 1200) -> bool:
    specs = get_configured_selectors(config, name)
    if not specs:
        return False
    locator = await maybe_visible(page, specs, timeout_ms=timeout_ms)
    if locator is None:
        return False
    await locator.click()
    return True


async def navigate_to_chapter_manager(page: Page, config: dict[str, Any]) -> None:
    await page.goto(str(config["fanqie_author_url"]), wait_until="domcontentloaded")
    default_timeout = int((config.get("browser") or {}).get("default_timeout_ms", 15000))
    ready = await maybe_visible(page, get_configured_selectors(config, "workbench_ready"), timeout_ms=default_timeout)
    if ready is None:
        print("未检测到后台就绪标记。如页面要求登录/验证码，请在浏览器中人工完成。")
        await prompt_input( "完成后按回车继续...")

    book_specs = get_configured_selectors(config, "book_entry")
    if book_specs:
        await click_selector(page, config, "book_entry", timeout_ms=default_timeout)
    chapter_specs = get_configured_selectors(config, "chapter_manage")
    if chapter_specs:
        await click_selector(page, config, "chapter_manage", timeout_ms=default_timeout)
    await click_optional_selector(page, config, "draft_tab", timeout_ms=2000)
    await click_optional_selector(page, config, "draft_tip_ok", timeout_ms=1200)


async def paste_text(locator: Locator, text: str) -> None:
    page = locator.page
    await locator.click(timeout=5000)
    try:
        await locator.press("Control+A")
    except Exception:
        pass
    try:
        await page.evaluate("async value => await navigator.clipboard.writeText(value)", text)
        await locator.press("Control+V")
        await page.wait_for_timeout(300)
        return
    except Exception:
        # Fallback to keyboard typing. It is slower, but keeps events closer to a
        # real user action than direct DOM value mutation.
        await locator.type(text, delay=1)
        await page.wait_for_timeout(300)


async def fill_editor(locator: Locator, text: str) -> None:
    try:
        await paste_text(locator, text)
        return
    except Exception as exc:
        raise FanqieError("failed_selector", f"无法粘贴编辑器内容: {exc}") from exc


async def read_field_value(locator: Locator) -> str:
    try:
        value = await locator.input_value(timeout=2000)
        return value.strip()
    except Exception:
        return await read_locator_text(locator)


async def fill_title_field(locator: Locator, text: str) -> None:
    """Fill Fanqie title input using real keyboard events.

    The title DOM value can be correct while Fanqie's internal save state remains
    empty. Prefer Playwright keyboard insertion, then force blur/focusout and wait
    before continuing.
    """
    page = locator.page

    await locator.click(timeout=5000)
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await page.keyboard.insert_text(text)
    await page.wait_for_timeout(800)

    actual = await read_field_value(locator)
    if actual != text:
        await locator.click(timeout=5000)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.type(text, delay=35)
        await page.wait_for_timeout(800)
        actual = await read_field_value(locator)

    if actual != text:
        raise FanqieError("failed_field_verify", f"章节标题写入校验失败：期望 {text!r}，实际 {actual!r}")

    await locator.evaluate(
        """
        el => {
          el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText'}));
          el.dispatchEvent(new Event('change', {bubbles: true}));
          el.dispatchEvent(new FocusEvent('focusout', {bubbles: true}));
          el.blur && el.blur();
        }
        """
    )
    await page.wait_for_timeout(1000)
    actual = await read_field_value(locator)
    print(f"标题框键盘输入确认：{actual}")
    if actual != text:
        raise FanqieError("failed_field_verify", f"章节标题 blur 后丢失：期望 {text!r}，实际 {actual!r}")


async def fill_and_verify_field(locator: Locator, text: str, field_name: str) -> None:
    await fill_editor(locator, text)
    await locator.evaluate("el => el.blur && el.blur()")
    await locator.page.wait_for_timeout(300)
    actual = await read_field_value(locator)
    if actual != text:
        await locator.click(timeout=3000)
        try:
            await locator.press("Control+A")
        except Exception:
            pass
        await locator.type(text, delay=8)
        await locator.evaluate("el => el.blur && el.blur()")
        await locator.page.wait_for_timeout(300)
        actual = await read_field_value(locator)
    if actual != text:
        raise FanqieError("failed_field_verify", f"{field_name} 写入校验失败：期望 {text!r}，实际 {actual!r}")


async def read_locator_text(locator: Locator) -> str:
    try:
        return (await locator.inner_text(timeout=2000)).strip()
    except Exception:
        try:
            return (await locator.text_content(timeout=2000) or "").strip()
        except Exception:
            return ""


async def assert_safe_save_button(locator: Locator, config: dict[str, Any]) -> None:
    text = await read_locator_text(locator)
    forbidden = [str(item) for item in ((config.get("safety") or {}).get("forbidden_action_keywords") or [])]
    for word in forbidden:
        if word and word in text and "草稿" not in text:
            raise FanqieError("failed_safety_guard", f"拒绝点击疑似发布按钮: {text}")
    if "草稿" not in text:
        raise FanqieError("failed_safety_guard", f"保存按钮文本未明确包含“草稿”: {text!r}")


async def screenshot(page: Page, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(path), full_page=True)
    return str(path)


def format_body_for_paste(body: str, config: dict[str, Any]) -> str:
    if (config.get("formatting") or {}).get("collapse_blank_lines", True):
        # Manual copy from many editors often normalizes paragraph gaps. The
        # Fanqie editor can render raw blank lines as an extra empty paragraph,
        # so fold multiple newlines to a single newline before pasting.
        body = re.sub(r"\n{2,}", "\n", body.strip())
    return body


def read_current_chapter_body(root: Path, item: dict[str, Any], config: dict[str, Any] | None = None) -> tuple[str, str]:
    source = resolve_path(root, item["source_file"])
    raw = source.read_text(encoding="utf-8-sig")
    body, _ = clean_markdown_body(raw)
    if config is not None:
        body = format_body_for_paste(body, config)
    return body, sha256_text(clean_markdown_body(raw)[0])


def mark_failure(
    state: dict[str, Any],
    item: dict[str, Any],
    *,
    error_type: str,
    error_message: str,
    page_url: str | None = None,
) -> None:
    by_no = chapters_by_no(state)
    target = by_no[int(item["chapter_no"])]
    target["status"] = error_type if error_type.startswith("failed_") else f"failed_{error_type}"
    target["error_type"] = error_type
    target["error_message"] = error_message
    target["page_url_at_error"] = page_url
    target["last_attempt_at"] = utc_now()
    state["updated_at"] = utc_now()


def update_item(state: dict[str, Any], item: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    by_no = chapters_by_no(state)
    target = by_no[int(item["chapter_no"])]
    target.update(updates)
    state["updated_at"] = utc_now()
    return target


async def save_one_chapter(
    page: Page,
    config: dict[str, Any],
    state: dict[str, Any],
    state_path: Path,
    root: Path,
    item: dict[str, Any],
    screenshot_root: Path,
) -> None:
    no = int(item["chapter_no"])
    full_title = str(item["title"])
    title_text = str(item.get("title_text") or full_title)
    body, current_hash = read_current_chapter_body(root, item, config)
    if current_hash != item.get("content_sha256"):
        raise FanqieError("failed_hash_changed", f"{full_title} 本地正文 hash 与台账不一致，停止以避免覆盖远端草稿。")
    if not body.strip():
        raise FanqieError("failed_quality_check", f"{full_title} 正文为空")

    attempts = int(item.get("attempts") or 0) + 1
    update_item(
        state,
        item,
        {
            "status": DRAFT_SAVING,
            "attempts": attempts,
            "last_attempt_at": utc_now(),
            "error_type": None,
            "error_message": None,
            "page_url_at_error": None,
        },
    )
    write_json(state_path, state)

    await navigate_to_chapter_manager(page, config)

    duplicate = await maybe_visible(page, get_configured_selectors(config, "duplicate_title"), timeout_ms=500)
    if duplicate is not None:
        raise FanqieError("failed_duplicate_remote", f"页面已出现重复提示，未创建草稿: {await read_locator_text(duplicate)}")

    new_chapter = await first_visible(page, get_configured_selectors(config, "new_chapter"), name="new_chapter")
    popup_page: Page | None = None
    try:
        async with page.expect_popup(timeout=3000) as popup_info:
            await new_chapter.click()
        popup_page = await popup_info.value
    except Exception:
        # If no popup appears, the click has already happened; some versions may
        # open the editor in the same page. Do not click a second time.
        popup_page = None
    editor_page = popup_page or page
    await editor_page.wait_for_load_state("domcontentloaded")

    chapter_no_input = await first_visible(editor_page, get_configured_selectors(config, "chapter_no_input"), name="chapter_no_input")
    await fill_title_field(chapter_no_input, str(no))
    title_input = await first_visible(editor_page, get_configured_selectors(config, "title_input"), name="title_input")
    await fill_title_field(title_input, title_text)

    await editor_page.wait_for_timeout(1000)
    editor = await first_visible(editor_page, get_configured_selectors(config, "content_editor"), name="content_editor")
    await fill_editor(editor, body)
    await editor_page.wait_for_timeout(1000)

    safe_title = f"{no:03d}"
    pre_path = screenshot_root / f"{safe_title}-before-save.png"
    if (config.get("safety") or {}).get("screenshot_before_save", True):
        pre_saved = await screenshot(editor_page, pre_path)
    else:
        pre_saved = None

    await editor_page.wait_for_timeout(1000)
    no_before_save = await read_field_value(chapter_no_input)
    title_before_save = await read_field_value(title_input)
    print(f"存草稿前章节号框值：{no_before_save!r}")
    print(f"存草稿前标题框值：{title_before_save!r}")
    if no_before_save != str(no):
        raise FanqieError("failed_field_verify", f"存草稿前章节号丢失：期望 {str(no)!r}，实际 {no_before_save!r}")
    if title_before_save != title_text:
        raise FanqieError("failed_field_verify", f"存草稿前标题丢失：期望 {title_text!r}，实际 {title_before_save!r}")

    save_button = await first_visible(editor_page, get_configured_selectors(config, "save_draft"), name="save_draft")
    await assert_safe_save_button(save_button, config)
    await save_button.click()

    duplicate_after = await maybe_visible(editor_page, get_configured_selectors(config, "duplicate_title"), timeout_ms=1200)
    if duplicate_after is not None:
        raise FanqieError("failed_duplicate_remote", f"保存后出现重复提示: {await read_locator_text(duplicate_after)}")

    confirmation_text = ""
    success_specs = get_configured_selectors(config, "save_success")
    try:
        success = await first_visible(editor_page, success_specs, name="save_success", timeout_ms=10000)
        confirmation_text = await read_locator_text(success)
    except FanqieError as exc:
        if (config.get("safety") or {}).get("require_save_confirmation", True):
            raise FanqieError("failed_save_confirm", f"无法确认保存草稿成功: {exc}") from exc

    post_path = screenshot_root / f"{safe_title}-after-save.png"
    if (config.get("safety") or {}).get("screenshot_after_save", True):
        post_saved = await screenshot(editor_page, post_path)
    else:
        post_saved = None

    update_item(
        state,
        item,
        {
            "status": DRAFT_SAVED,
            "draft_saved_at": utc_now(),
            "pre_save_screenshot": pre_saved,
            "post_save_screenshot": post_saved,
            "save_confirmation_text": confirmation_text,
            "error_type": None,
            "error_message": None,
            "page_url_at_error": None,
        },
    )
    write_json(state_path, state)
    print(f"已保存草稿：{full_title}")


async def launch_context(config: dict[str, Any], root: Path) -> BrowserContext:
    if async_playwright is None:
        raise FanqieError("failed_dependency", "缺少依赖 playwright；请先运行 pip install -r requirements.txt")
    browser_cfg = config.get("browser") or {}
    profile_dir = resolve_path(root, browser_cfg.get("profile_dir", ".secrets/fanqie-browser-profile"))
    profile_dir.mkdir(parents=True, exist_ok=True)
    playwright = await async_playwright().start()
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=bool(browser_cfg.get("headless", False)),
        slow_mo=int(browser_cfg.get("slow_mo_ms", 0)),
        viewport={"width": 1400, "height": 900},
        permissions=["clipboard-read", "clipboard-write"],
    )
    # Stash playwright object for shutdown.
    setattr(context, "_fanqie_playwright", playwright)
    context.set_default_timeout(int(browser_cfg.get("default_timeout_ms", 15000)))
    return context


async def close_context(context: BrowserContext) -> None:
    playwright = getattr(context, "_fanqie_playwright", None)
    await context.close()
    if playwright is not None:
        await playwright.stop()


async def get_page(context: BrowserContext) -> Page:
    if context.pages:
        return context.pages[0]
    return await context.new_page()


async def prompt_input(prompt: str) -> str:
    """Python 3.8-compatible async wrapper around input()."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)


async def command_login(config: dict[str, Any], root: Path) -> None:
    context = await launch_context(config, root)
    try:
        page = await get_page(context)
        await page.goto(str(config["fanqie_author_url"]), wait_until="domcontentloaded")
        print("浏览器已打开。请在页面中手动登录番茄作者后台；遇到验证码/短信/滑块请人工处理。")
        await prompt_input( "登录完成后按回车关闭浏览器...")
    finally:
        await close_context(context)


async def command_check(config: dict[str, Any], root: Path) -> None:
    context = await launch_context(config, root)
    try:
        page = await get_page(context)
        await navigate_to_chapter_manager(page, config)
        print("后台路径检查完成：已尝试进入作品章节管理页。请在浏览器中确认页面正确。")
        await prompt_input( "确认后按回车关闭浏览器...")
    finally:
        await close_context(context)


def print_audit(state: dict[str, Any]) -> None:
    counts = Counter(str(item.get("status")) for item in state.get("chapters", []))
    print("Fanqie 草稿台账统计：")
    for status, count in sorted(counts.items()):
        print(f"- {status}: {count}")
    summary = state.get("summary") or {}
    if summary:
        print(f"章节范围：第{summary.get('first_chapter', 0):03d}章 - 第{summary.get('last_chapter', 0):03d}章")


def require_confirmation(args: argparse.Namespace, chapters: list[dict[str, Any]]) -> None:
    if not getattr(args, "confirm_save_drafts", False):
        raise FanqieError("failed_safety_guard", "保存草稿必须显式传入 --confirm-save-drafts")
    if not chapters:
        print("没有需要保存的章节。")
        return
    first = int(chapters[0]["chapter_no"])
    last = int(chapters[-1]["chapter_no"])
    phrase = f"SAVE FANQIE DRAFTS {first}-{last}"
    print("即将通过浏览器保存番茄草稿。不会发布，但会写入远端草稿箱。")
    print(f"章节范围：第{first:03d}章 - 第{last:03d}章，共 {len(chapters)} 章。")
    typed = input(f"请输入确认语：{phrase}\n> ").strip()
    if typed != phrase:
        raise FanqieError("failed_safety_guard", "确认语不匹配，已取消。")


async def command_save(config: dict[str, Any], root: Path, args: argparse.Namespace, *, resume: bool) -> None:
    state_path = resolve_path(root, config.get("state_file", "data/fanqie_publish_state.json"))
    state = load_json(state_path)
    selected = select_chapters(
        state,
        start=args.start,
        end=args.end,
        limit=args.limit,
        only_chapter=args.only_chapter,
        resume=resume,
    )
    require_confirmation(args, selected)
    if not selected:
        return

    rid = run_id()
    screenshot_dir = resolve_path(root, (config.get("browser") or {}).get("screenshot_dir", "logs/fanqie/screenshots")) / rid
    context = await launch_context(config, root)
    try:
        page = await get_page(context)
        for item in selected:
            try:
                await save_one_chapter(page, config, state, state_path, root, item, screenshot_dir)
            except Exception as exc:
                error_type = exc.error_type if isinstance(exc, FanqieError) else "failed_browser"
                mark_failure(state, item, error_type=error_type, error_message=str(exc), page_url=page.url)
                write_json(state_path, state)
                err_shot = screenshot_dir / f"{int(item['chapter_no']):03d}-error.png"
                try:
                    await screenshot(page, err_shot)
                    print(f"错误截图：{err_shot}", file=sys.stderr)
                except Exception:
                    pass
                raise

            delay = float((config.get("batch") or {}).get("delay_between_chapters_sec", 3))
            jitter = float((config.get("batch") or {}).get("jitter_sec", 2))
            await asyncio.sleep(delay + random.uniform(0, max(0.0, jitter)))
    finally:
        await close_context(context)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Save Fanqie novel chapters to drafts via Playwright.")
    parser.add_argument("command", choices=("login", "check", "audit", "save-drafts", "resume"))
    parser.add_argument("--config", default="fanqie_draft_upload/fanqie_publish.yaml")
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only-chapter", type=int, default=None)
    parser.add_argument("--confirm-save-drafts", action="store_true")
    return parser


async def async_main(argv: list[str] | None = None) -> int:
    root = project_root()
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = resolve_path(root, args.config)
    config = load_yaml(config_path)

    # Resolve a relative project_root override if provided, while keeping script
    # defaults useful when invoked from anywhere.
    cfg_root = config.get("project_root")
    if cfg_root:
        root = resolve_path(root, cfg_root).resolve()

    if args.command == "login":
        await command_login(config, root)
    elif args.command == "check":
        await command_check(config, root)
    elif args.command == "audit":
        state = load_json(resolve_path(root, config.get("state_file", "data/fanqie_publish_state.json")))
        print_audit(state)
    elif args.command == "save-drafts":
        await command_save(config, root, args, resume=False)
    elif args.command == "resume":
        await command_save(config, root, args, resume=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(async_main(argv))
    except KeyboardInterrupt:
        print("用户中断。若有章节停在 draft_saving，请先人工确认远端草稿状态。", file=sys.stderr)
        return 130
    except (FanqieError, PlaywrightTimeoutError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
