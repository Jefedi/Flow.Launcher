# -*- coding: utf-8 -*-
"""Read/manage the Windows OS clipboard history via WinRT (winsdk).

Windows itself keeps the clipboard history (Win+V) when the feature is enabled in
Settings → System → Clipboard. This module just reads it on demand — there is no
background daemon and nothing is persisted by the plugin.

Public API (all synchronous wrappers over the WinRT async calls):
    is_enabled() -> bool
    get_items(limit=50) -> (ok: bool, items: list[ClipItem])
    delete(item_id) -> bool
    clear() -> bool
"""

import asyncio
from collections import namedtuple

ClipItem = namedtuple("ClipItem", ["id", "text", "timestamp"])

try:
    from winsdk.windows.applicationmodel.datatransfer import (
        Clipboard,
        ClipboardHistoryItemsResultStatus,
        StandardDataFormats,
    )
    _AVAILABLE = True
except Exception:  # winsdk missing or not on Windows
    _AVAILABLE = False


def is_available():
    """True if the winsdk clipboard API could be imported."""
    return _AVAILABLE


def is_enabled():
    if not _AVAILABLE:
        return False
    try:
        return bool(Clipboard.is_history_enabled())
    except Exception:
        return False


async def _read_items(limit):
    result = await Clipboard.get_history_items_async()
    if result.status != ClipboardHistoryItemsResultStatus.SUCCESS:
        return False, []
    text_format = StandardDataFormats.text
    items = []
    for item in result.items:
        if len(items) >= limit:
            break
        view = item.content
        try:
            if not view.contains(text_format):
                continue  # skip images / non-text entries
            text = await view.get_text_async()
        except Exception:
            continue
        if text:
            items.append(ClipItem(item.id, text, item.timestamp))
    return True, items


def get_items(limit=50):
    """Return (ok, items). ``ok`` is False if history is disabled/unavailable."""
    if not _AVAILABLE:
        return False, []
    try:
        return asyncio.run(_read_items(limit))
    except Exception:
        return False, []


def _find_item(item_id):
    """Return the raw WinRT history item with ``item_id`` (or None)."""
    async def _run():
        result = await Clipboard.get_history_items_async()
        if result.status != ClipboardHistoryItemsResultStatus.SUCCESS:
            return None
        for item in result.items:
            if item.id == item_id:
                return item
        return None
    return asyncio.run(_run())


def delete(item_id):
    """Delete a single entry from the OS clipboard history."""
    if not _AVAILABLE:
        return False
    try:
        item = _find_item(item_id)
        if item is None:
            return False
        return bool(Clipboard.delete_item_from_history(item))
    except Exception:
        return False


def clear():
    """Clear the entire OS clipboard history."""
    if not _AVAILABLE:
        return False
    try:
        return bool(Clipboard.clear_history())
    except Exception:
        return False
