import os
import time
from pathlib import Path
from collections import deque
import ctypes
from ctypes import wintypes
import pyperclip

_COMTYPES_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "comtypes"
_COMTYPES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("COMTYPES_CACHE", str(_COMTYPES_CACHE_DIR))
os.environ.setdefault("COMTYPES_GEN_DIR", str(_COMTYPES_CACHE_DIR))

_LOG_DIR = Path(__file__).resolve().parent.parent / ".logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_DEBUG_LOG_PATH = _LOG_DIR / "realtime_monitor.log"
_ERROR_LOG_PATH = _LOG_DIR / "realtime_monitor_errors.log"
_WORD_LOG_PATH = _LOG_DIR / "word_monitor.log"
_HWP_LOG_PATH = _LOG_DIR / "hwp_monitor.log"
_TEXT_CLASS_HINTS = ("Edit", "RichEdit", "TextArea", "Scintilla")
_TEXT_CONTROL_TYPES = ("EditControl", "DocumentControl")
_BROWSER_PROCESS_NAMES = {
    "chrome.exe",
    "msedge.exe",
    "whale.exe",
    "brave.exe",
    "vivaldi.exe",
    "opera.exe",
    "browser.exe",
}
_WORD_PROCESS_NAMES = {"winword.exe"}
_HWP_VIEWER_PROCESS_NAMES = {"hwpviewer.exe"}
_BROWSER_ADDRESS_HINTS = (
    "address and search bar",
    "주소 및 검색창",
    "search or enter web address",
    "search or type web address",
    "web address",
    "search the web",
    "주소창",
    "검색창",
    "url",
    "omnibox",
    "search box",
    "searchbar",
    "search bar",
    "address bar",
    "navigation",
    "nav bar",
    "toolbar",
    "tab search",
    "search google or type a url",
    "search or type a url",
    "새 탭",
    "new tab",
)
_BROWSER_PASSWORD_HINTS = ("password", "비밀번호", "passcode")
_BROWSER_SENSITIVE_HINTS = (
    "email",
    "e-mail",
    "이메일",
    "메일 주소",
    "username",
    "user name",
    "아이디",
    "id",
    "login",
    "log in",
    "sign in",
    "signin",
    "account",
    "계정",
    "phone",
    "전화번호",
    "휴대폰",
    "mobile",
)
_WORD_EXCLUDED_HINTS = (
    "search",
    "검색",
    "find",
    "replace",
    "tell me",
    "what do you want to do",
    "command",
    "리본",
    "ribbon",
    "toolbar",
    "navigation",
    "nav",
    "menu",
    "file",
    "account",
    "backstage",
    "template",
    "document recovery",
    "recovery",
    "comments",
    "comment",
    "header",
    "footer",
)
_WORD_CLASS_HINTS = ("_WwG", "RichEdit", "Afx", "NetUI")
_HWP_CLASS_HINTS = ("Hwp", "Hnc", "Afx", "RichEdit", "Edit")
_HWP_EXCLUDED_HINTS = (
    "search",
    "find",
    "replace",
    "menu",
    "file",
    "help",
    "toolbar",
    "status",
    "navigation",
    "account",
    "comment",
    "header",
    "footer",
    "page setup",
    "print",
)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_CURRENT_PROCESS_ID = os.getpid()
_OWN_WINDOW_TITLE_HINTS = ("writing assistant",)

try:
    import comtypes.client
    import comtypes.gen
except Exception:  # pragma: no cover - optional dependency fallback
    comtypes = None
else:
    comtypes.client.gen_dir = str(_COMTYPES_CACHE_DIR)
    gen_path = list(getattr(comtypes.gen, "__path__", []))
    if str(_COMTYPES_CACHE_DIR) not in gen_path:
        gen_path.append(str(_COMTYPES_CACHE_DIR))
        comtypes.gen.__path__ = gen_path

try:
    import uiautomation as automation
except Exception:  # pragma: no cover - optional dependency fallback
    automation = None

from input.keyboard_monitor import monitor_typed_text
from input.notepad_monitor import get_active_notepad_snapshot


def monitor_realtime_text(callback, poll_interval=0.35):
    with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} monitor_started automation={automation is not None}\n")

    if automation is None:
        monitor_typed_text(callback)
        return

    initializer_factory = getattr(automation, "UIAutomationInitializerInThread", None)

    try:
        if initializer_factory is None:
            _run_realtime_loop(callback, poll_interval)
        else:
            with initializer_factory():
                _run_realtime_loop(callback, poll_interval)
    except Exception as exc:
        _log_error("monitor_realtime_text", exc)
        monitor_typed_text(callback)


def _run_realtime_loop(callback, poll_interval):
    last_signature = ("", None)
    last_debug_key = None

    while True:
        try:
            notepad_snapshot = get_active_notepad_snapshot()
            if notepad_snapshot and notepad_snapshot.get("text", "").strip():
                text = notepad_snapshot["text"]
                window_title = notepad_snapshot.get("window_title", "")
                focused_control = None
                foreground_control = None
            else:
                focused_control = automation.GetFocusedControl()
                foreground_control = automation.GetForegroundControl()
                if _is_own_application_control(foreground_control, focused_control):
                    last_debug_key = None
                    time.sleep(poll_interval)
                    continue
                window_title = _extract_window_title(foreground_control, focused_control)
                browser_snapshot = _extract_browser_snapshot(focused_control, foreground_control, window_title)
                word_snapshot = _extract_word_snapshot(focused_control, foreground_control, window_title)
                hwp_snapshot = _extract_hwp_snapshot(focused_control, foreground_control, window_title)
                if browser_snapshot is not None:
                    text = browser_snapshot.get("text", "")
                    window_title = browser_snapshot.get("window_title", window_title)
                elif word_snapshot is not None:
                    text = word_snapshot.get("text", "")
                    window_title = word_snapshot.get("window_title", window_title)
                elif hwp_snapshot is not None:
                    text = hwp_snapshot.get("text", "")
                    window_title = hwp_snapshot.get("window_title", window_title)
                else:
                    text = _extract_text_from_controls(focused_control, foreground_control)
        except Exception as exc:
            _log_error("realtime_loop_iteration", exc)
            text = ""
            window_title = ""
            focused_control = None
            foreground_control = None

        cleaned = _normalize_text(_remove_window_title_noise(text, window_title))
        signature = (window_title, cleaned)
        if signature != last_signature and (cleaned or window_title):
            last_signature = signature
            callback(
                {
                    "source": "realtime",
                    "window_title": window_title,
                    "text": cleaned,
                }
            )
        elif not cleaned:
            debug_key = _control_identity(foreground_control) or _control_identity(focused_control)
            if debug_key and debug_key != last_debug_key:
                _debug_dump_controls(focused_control, foreground_control)
                last_debug_key = debug_key

        time.sleep(poll_interval)


def _extract_text_from_controls(*controls):
    candidates = []
    seen = set()

    for control in controls:
        if control is None:
            continue

        current = control
        for _ in range(4):
            if current is None:
                break

            handle = getattr(current, "NativeWindowHandle", None)
            key = ("ancestor", handle, getattr(current, "ControlTypeName", ""))
            if key not in seen:
                seen.add(key)
                candidates.extend(_collect_control_text_candidates(current))

            try:
                current = current.GetParentControl()
            except Exception:
                current = None

        candidates.extend(_collect_descendant_text_candidates(control))

    candidates = [value.strip() for value in candidates if isinstance(value, str) and value.strip()]
    if not candidates:
        return ""

    return max(candidates, key=len)


def _extract_browser_snapshot(focused_control, foreground_control, window_title):
    foreground_process = _get_process_name_from_control(foreground_control)
    if foreground_process not in _BROWSER_PROCESS_NAMES:
        return None

    target_control = _find_browser_text_control(focused_control)
    if target_control is None:
        return {
            "window_title": window_title,
            "text": "",
        }

    if _is_excluded_browser_control(target_control):
        return {
            "window_title": window_title,
            "text": "",
        }

    candidates = _collect_control_text_candidates(target_control)
    candidates.extend(_collect_descendant_text_candidates(target_control, max_depth=2, max_nodes=40))
    candidates = [value.strip() for value in candidates if isinstance(value, str) and value.strip()]

    return {
        "window_title": window_title,
        "text": max(candidates, key=len) if candidates else "",
    }


def _extract_word_snapshot(focused_control, foreground_control, window_title):
    foreground_process = _get_process_name_from_control(foreground_control)
    if foreground_process not in _WORD_PROCESS_NAMES:
        return None

    target_control = _find_word_text_control(focused_control)
    if target_control is None:
        return {
            "window_title": window_title,
            "text": "",
        }

    if _is_excluded_word_control(target_control):
        return {
            "window_title": window_title,
            "text": "",
        }

    candidates = _collect_control_text_candidates(target_control)
    candidates.extend(_collect_descendant_text_candidates(target_control, max_depth=2, max_nodes=40))
    candidates = [value.strip() for value in candidates if isinstance(value, str) and value.strip()]
    if not candidates:
        com_text = _read_word_text_via_com(window_title)
        if com_text.strip():
            candidates.append(com_text.strip())
    if not candidates:
        clipboard_text = _read_word_text_via_clipboard_snapshot(target_control)
        if clipboard_text.strip():
            candidates.append(clipboard_text.strip())
    candidates = _filter_word_candidates(candidates, window_title)
    _log_word_state(focused_control, foreground_control, target_control, window_title, candidates)

    return {
        "window_title": window_title,
        "text": max(candidates, key=len) if candidates else "",
    }


def _extract_hwp_snapshot(focused_control, foreground_control, window_title):
    foreground_process = _get_process_name_from_control(foreground_control)
    if foreground_process not in _HWP_VIEWER_PROCESS_NAMES:
        return None

    target_control = _find_hwp_text_control(focused_control) or _find_hwp_text_control(foreground_control)
    if target_control is None:
        target_control = foreground_control

    if _is_excluded_hwp_control(target_control):
        _log_hwp_message(f"excluded target={_describe_control(target_control)}")
        return {
            "window_title": window_title,
            "text": "",
        }

    candidates = _collect_control_text_candidates(target_control)
    candidates.extend(_collect_descendant_text_candidates(target_control, max_depth=4, max_nodes=120))
    candidates = [value.strip() for value in candidates if isinstance(value, str) and value.strip()]
    if not candidates:
        _log_hwp_control_tree(target_control, "target_tree")
        clipboard_text = _read_hwp_text_via_clipboard_snapshot(target_control)
        if clipboard_text.strip():
            candidates.append(clipboard_text.strip())

    candidates = _filter_hwp_candidates(candidates, window_title)
    _log_hwp_state(focused_control, foreground_control, target_control, window_title, candidates)

    return {
        "window_title": window_title,
        "text": max(candidates, key=len) if candidates else "",
    }


def _find_browser_text_control(control):
    current = control
    for _ in range(6):
        if current is None:
            break
        control_type = getattr(current, "ControlTypeName", "")
        class_name = getattr(current, "ClassName", "")
        if (
            control_type in _TEXT_CONTROL_TYPES
            or "Chrome_RenderWidgetHostHWND" in class_name
            or "RenderWidgetHostHWND" in class_name
        ):
            return current
        try:
            current = current.GetParentControl()
        except Exception:
            current = None
    return None


def _find_word_text_control(control):
    current = control
    for _ in range(8):
        if current is None:
            break

        control_type = getattr(current, "ControlTypeName", "")
        class_name = getattr(current, "ClassName", "")
        if (
            control_type in _TEXT_CONTROL_TYPES
            or any(hint in class_name for hint in _WORD_CLASS_HINTS)
        ):
            return current

        try:
            current = current.GetParentControl()
        except Exception:
            current = None
    return None


def _find_hwp_text_control(control):
    current = control
    for _ in range(10):
        if current is None:
            break

        control_type = getattr(current, "ControlTypeName", "")
        class_name = getattr(current, "ClassName", "")
        if (
            control_type in _TEXT_CONTROL_TYPES
            or any(hint.lower() in class_name.lower() for hint in _HWP_CLASS_HINTS)
        ):
            return current

        try:
            current = current.GetParentControl()
        except Exception:
            current = None
    return None


def _is_excluded_browser_control(control):
    try:
        if getattr(control, "IsPassword", False):
            return True
    except Exception:
        pass

    hints = " ".join(
        [
            str(getattr(control, "Name", "")),
            str(getattr(control, "AutomationId", "")),
            str(getattr(control, "LocalizedControlType", "")),
            str(getattr(control, "HelpText", "")),
            str(getattr(control, "AriaRole", "")),
            str(getattr(control, "AriaProperties", "")),
            str(getattr(control, "ClassName", "")),
            str(getattr(control, "FrameworkId", "")),
        ]
    ).lower()

    if any(hint in hints for hint in _BROWSER_ADDRESS_HINTS):
        return True
    if any(hint in hints for hint in _BROWSER_PASSWORD_HINTS):
        return True
    if any(hint in hints for hint in _BROWSER_SENSITIVE_HINTS):
        return True

    current = control
    for _ in range(5):
        if current is None:
            break
        parent_hints = " ".join(
            [
                str(getattr(current, "Name", "")),
                str(getattr(current, "AutomationId", "")),
                str(getattr(current, "LocalizedControlType", "")),
                str(getattr(current, "ClassName", "")),
            ]
        ).lower()
        if any(hint in parent_hints for hint in _BROWSER_ADDRESS_HINTS):
            return True
        if any(hint in parent_hints for hint in _BROWSER_SENSITIVE_HINTS):
            return True
        try:
            current = current.GetParentControl()
        except Exception:
            current = None
    return False


def _is_excluded_word_control(control):
    hints = " ".join(
        [
            str(getattr(control, "Name", "")),
            str(getattr(control, "AutomationId", "")),
            str(getattr(control, "LocalizedControlType", "")),
            str(getattr(control, "HelpText", "")),
            str(getattr(control, "AriaRole", "")),
            str(getattr(control, "AriaProperties", "")),
            str(getattr(control, "ClassName", "")),
            str(getattr(control, "FrameworkId", "")),
        ]
    ).lower()

    if any(hint in hints for hint in _WORD_EXCLUDED_HINTS):
        return True

    current = control
    for _ in range(6):
        if current is None:
            break
        parent_hints = " ".join(
            [
                str(getattr(current, "Name", "")),
                str(getattr(current, "AutomationId", "")),
                str(getattr(current, "LocalizedControlType", "")),
                str(getattr(current, "ClassName", "")),
            ]
        ).lower()
        if any(hint in parent_hints for hint in _WORD_EXCLUDED_HINTS):
            return True
        try:
            current = current.GetParentControl()
        except Exception:
            current = None
    return False


def _is_excluded_hwp_control(control):
    hints = " ".join(
        [
            str(getattr(control, "Name", "")),
            str(getattr(control, "AutomationId", "")),
            str(getattr(control, "LocalizedControlType", "")),
            str(getattr(control, "HelpText", "")),
            str(getattr(control, "ClassName", "")),
            str(getattr(control, "FrameworkId", "")),
        ]
    ).lower()

    if any(hint in hints for hint in _HWP_EXCLUDED_HINTS):
        return True

    current = control
    for _ in range(6):
        if current is None:
            break
        parent_hints = " ".join(
            [
                str(getattr(current, "Name", "")),
                str(getattr(current, "AutomationId", "")),
                str(getattr(current, "LocalizedControlType", "")),
                str(getattr(current, "ClassName", "")),
            ]
        ).lower()
        if any(hint in parent_hints for hint in _HWP_EXCLUDED_HINTS):
            return True
        try:
            current = current.GetParentControl()
        except Exception:
            current = None
    return False


def _filter_word_candidates(candidates, window_title):
    cleaned_title = _normalize_text(window_title).lower()
    filtered = []

    for value in candidates:
        normalized = _normalize_text(value)
        lowered = normalized.lower()
        if not normalized:
            continue
        if cleaned_title and lowered == cleaned_title:
            continue
        if cleaned_title and cleaned_title in lowered and len(normalized) <= len(cleaned_title) + 8:
            continue
        if lowered in {"microsoft word", "microsoft word 문서", "word 문서"}:
            continue
        filtered.append(normalized)

    return filtered


def _filter_hwp_candidates(candidates, window_title):
    cleaned_title = _normalize_text(window_title).lower()
    filtered = []

    for value in candidates:
        normalized = _normalize_text(value)
        lowered = normalized.lower()
        if not normalized:
            continue
        if cleaned_title and lowered == cleaned_title:
            continue
        if cleaned_title and cleaned_title in lowered and len(normalized) <= len(cleaned_title) + 12:
            continue
        if lowered in {"한글 viewer", "hwp viewer", "viewer", "한글 뷰어"}:
            continue
        filtered.append(normalized)

    return filtered


def _read_word_text_via_clipboard_snapshot(control):
    if automation is None or control is None:
        return ""

    original_clipboard = _safe_paste()

    try:
        try:
            control.SetFocus()
        except Exception:
            pass

        time.sleep(0.05)
        automation.SendKeys("{Ctrl}a", waitTime=0.05)
        automation.SendKeys("{Ctrl}c", waitTime=0.08)
        time.sleep(0.08)
        return _safe_paste()
    except Exception as exc:
        _log_error("word_clipboard_snapshot", exc)
        return ""
    finally:
        _safe_copy(original_clipboard)


def _read_word_text_via_com(window_title):
    if comtypes is None:
        _log_word_message("comtypes unavailable")
        return ""

    try:
        co_initialize = getattr(comtypes, "CoInitialize", None)
        if callable(co_initialize):
            co_initialize()
        app = comtypes.client.GetActiveObject("Word.Application")
    except Exception as exc:
        _log_error("word_com_get_active", exc)
        return ""

    try:
        document = getattr(app, "ActiveDocument", None)
        if document is None:
            _log_word_message("word_com: no active document")
            return ""

        document_name = _normalize_text(getattr(document, "Name", ""))
        cleaned_title = _normalize_text(window_title)
        if cleaned_title and document_name and document_name not in cleaned_title:
            active_window = getattr(app, "ActiveWindow", None)
            caption = _normalize_text(getattr(active_window, "Caption", "")) if active_window else ""
            if caption and document_name not in caption and caption not in cleaned_title:
                _log_word_message(
                    f"word_com: title mismatch document={document_name!r} caption={caption!r} window={cleaned_title!r}"
                )
                return ""

        candidate_map = {}

        content = getattr(document, "Content", None)
        if content is not None:
            candidate_map["content"] = getattr(content, "Text", "")

        document_range = getattr(document, "Range", None)
        if callable(document_range):
            try:
                candidate_map["range"] = document_range().Text
            except Exception as range_exc:
                _log_error("word_com_range", range_exc)

        selection = getattr(app, "Selection", None)
        if selection is not None:
            try:
                selection_range = getattr(selection, "Range", None)
                candidate_map["selection"] = getattr(selection_range, "Text", "") if selection_range is not None else ""
            except Exception as selection_exc:
                _log_error("word_com_selection", selection_exc)

        debug_parts = []
        best_text = ""
        for source_name, raw_text in candidate_map.items():
            normalized = _normalize_text(raw_text)
            debug_parts.append(f"{source_name}={len(normalized)}")
            if len(normalized) > len(best_text):
                best_text = normalized

        _log_word_message(
            "word_com candidates "
            + " ".join(debug_parts)
            + (f" best_preview={best_text[:120]!r}" if best_text else " best_preview=''")
        )
        return best_text
    except Exception as exc:
        _log_error("word_com_read", exc)
        return ""


def _read_hwp_text_via_clipboard_snapshot(control):
    if automation is None or control is None:
        return ""

    original_clipboard = _safe_paste()
    _log_hwp_message(f"clipboard_before length={len(_normalize_text(original_clipboard))}")

    try:
        try:
            control.SetFocus()
        except Exception:
            pass

        time.sleep(0.08)
        automation.SendKeys("{Ctrl}a", waitTime=0.08)
        automation.SendKeys("{Ctrl}c", waitTime=0.1)
        time.sleep(0.12)
        pasted = _safe_paste()
        normalized = _normalize_text(pasted)
        _log_hwp_message(f"clipboard_after_ctrl_a_ctrl_c length={len(normalized)} preview={normalized[:120]!r}")
        if normalized:
            return pasted

        automation.SendKeys("{Ctrl}c", waitTime=0.1)
        time.sleep(0.12)
        pasted = _safe_paste()
        normalized = _normalize_text(pasted)
        _log_hwp_message(f"clipboard_after_ctrl_c length={len(normalized)} preview={normalized[:120]!r}")
        return pasted
    except Exception as exc:
        _log_error("hwp_clipboard_snapshot", exc)
        return ""
    finally:
        _safe_copy(original_clipboard)


def _log_word_state(focused_control, foreground_control, target_control, window_title, candidates):
    lines = [
        "=" * 80,
        time.strftime("%Y-%m-%d %H:%M:%S"),
        f"window_title={window_title!r}",
        f"focused={_describe_control(focused_control)}",
        f"foreground={_describe_control(foreground_control)}",
        f"target={_describe_control(target_control)}",
        "candidates:",
    ]

    for value in candidates[:20]:
        preview = value[:200].replace("\r", "\\r").replace("\n", "\\n")
        lines.append(f"- {preview!r}")

    with _WORD_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write("\n".join(lines) + "\n")


def _log_word_message(message):
    with _WORD_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def _log_hwp_state(focused_control, foreground_control, target_control, window_title, candidates):
    lines = [
        "=" * 80,
        time.strftime("%Y-%m-%d %H:%M:%S"),
        f"window_title={window_title!r}",
        f"focused={_describe_control(focused_control)}",
        f"foreground={_describe_control(foreground_control)}",
        f"target={_describe_control(target_control)}",
        "candidates:",
    ]

    for value in candidates[:20]:
        preview = value[:200].replace("\r", "\\r").replace("\n", "\\n")
        lines.append(f"- {preview!r}")

    with _HWP_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write("\n".join(lines) + "\n")


def _log_hwp_message(message):
    with _HWP_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def _log_hwp_control_tree(control, label, max_depth=4, max_nodes=80):
    lines = [
        "=" * 80,
        time.strftime("%Y-%m-%d %H:%M:%S"),
        f"{label}:",
    ]

    if control is not None:
        queue = deque([(control, 0)])
        visited = set()
        count = 0
        while queue and count < max_nodes:
            current, depth = queue.popleft()
            if current is None:
                continue

            key = _control_identity(current)
            if key in visited:
                continue
            visited.add(key)
            count += 1

            lines.append(f"{'  ' * depth}- {_describe_control(current)}")
            if depth >= max_depth:
                continue

            try:
                children = current.GetChildren()
            except Exception:
                children = []
            for child in children:
                queue.append((child, depth + 1))
    else:
        lines.append("- no control available")

    with _HWP_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write("\n".join(lines) + "\n")


def _safe_paste():
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def _safe_copy(text):
    try:
        pyperclip.copy(text or "")
    except Exception:
        pass


def _get_process_name_from_control(control):
    if control is None:
        return ""

    process_id = _get_process_id_from_control(control)
    if not process_id:
        return ""

    process_handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
    if not process_handle:
        return ""

    try:
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(size)):
            return ""
        return Path(buffer.value).name.lower()
    finally:
        kernel32.CloseHandle(process_handle)


def _get_process_id_from_control(control):
    if control is None:
        return 0

    handle = getattr(control, "NativeWindowHandle", 0)
    if not handle:
        current = control
        for _ in range(5):
            if current is None:
                break
            handle = getattr(current, "NativeWindowHandle", 0)
            if handle:
                break
            try:
                current = current.GetParentControl()
            except Exception:
                current = None

    if not handle:
        return 0

    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(handle, ctypes.byref(process_id))
    return process_id.value


def _is_own_application_control(*controls):
    for control in controls:
        if control is None:
            continue

        process_id = _get_process_id_from_control(control)
        if process_id and process_id == _CURRENT_PROCESS_ID:
            return True

        title_hints = " ".join(
            [
                str(getattr(control, "Name", "")),
                str(getattr(control, "ClassName", "")),
                str(getattr(control, "AutomationId", "")),
            ]
        ).lower()
        if any(hint in title_hints for hint in _OWN_WINDOW_TITLE_HINTS):
            return True

    return False


def _collect_descendant_text_candidates(control, max_depth=6, max_nodes=160):
    results = []
    queue = deque([(control, 0)])
    visited = set()
    visited_count = 0

    while queue and visited_count < max_nodes:
        current, depth = queue.popleft()
        if current is None:
            continue

        handle = getattr(current, "NativeWindowHandle", None)
        key = (handle, getattr(current, "AutomationId", ""), getattr(current, "ControlTypeName", ""))
        if key in visited:
            continue
        visited.add(key)
        visited_count += 1

        control_type = getattr(current, "ControlTypeName", "")
        class_name = getattr(current, "ClassName", "")
        if control_type in _TEXT_CONTROL_TYPES or any(hint in class_name for hint in _TEXT_CLASS_HINTS):
            results.extend(_collect_control_text_candidates(current))

        if depth >= max_depth:
            continue

        try:
            children = current.GetChildren()
        except Exception:
            children = []

        for child in children:
            queue.append((child, depth + 1))

    return results


def _collect_control_text_candidates(control):
    results = []

    for attr_name in ("Name", "Value"):
        value = getattr(control, attr_name, None)
        if isinstance(value, str) and value.strip():
            results.append(value)

    for method_name in ("GetWindowText",):
        method = getattr(control, method_name, None)
        if callable(method):
            try:
                value = method()
            except Exception:
                value = ""
            if isinstance(value, str) and value.strip():
                results.append(value)

    for pattern_name, reader_name in (
        ("GetValuePattern", "Value"),
        ("GetLegacyIAccessiblePattern", "Value"),
    ):
        getter = getattr(control, pattern_name, None)
        if callable(getter):
            try:
                pattern = getter()
                value = getattr(pattern, reader_name, "")
            except Exception:
                value = ""
            if isinstance(value, str) and value.strip():
                results.append(value)

    text_pattern_getter = getattr(control, "GetTextPattern", None)
    if callable(text_pattern_getter):
        try:
            text_pattern = text_pattern_getter()
            document_range = getattr(text_pattern, "DocumentRange", None)
            if document_range:
                value = document_range.GetText(-1)
                if isinstance(value, str) and value.strip():
                    results.append(value)
        except Exception:
            pass

    return results


def _normalize_text(text):
    if not isinstance(text, str):
        return ""

    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _extract_window_title(*controls):
    for control in controls:
        if control is None:
            continue
        name = getattr(control, "Name", "")
        normalized = _normalize_text(name)
        if normalized:
            return normalized
    return ""


def _remove_window_title_noise(text, window_title):
    if not isinstance(text, str):
        return ""

    cleaned_title = _normalize_text(window_title)
    if not cleaned_title:
        return text

    lines = [line for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    filtered_lines = [line for line in lines if _normalize_text(line) != cleaned_title]
    if not filtered_lines and _normalize_text(text) == cleaned_title:
        return ""
    return "\n".join(filtered_lines).strip()


def _control_identity(control):
    if control is None:
        return ""
    return "|".join(
        [
            str(getattr(control, "NativeWindowHandle", "")),
            getattr(control, "ClassName", ""),
            getattr(control, "AutomationId", ""),
            getattr(control, "ControlTypeName", ""),
            getattr(control, "Name", ""),
        ]
    )


def _debug_dump_controls(focused_control, foreground_control, max_depth=4, max_nodes=80):
    lines = [
        "=" * 80,
        time.strftime("%Y-%m-%d %H:%M:%S"),
        f"focused: {_describe_control(focused_control)}",
        f"foreground: {_describe_control(foreground_control)}",
        "tree:",
    ]

    root = foreground_control or focused_control
    if root is not None:
        queue = deque([(root, 0)])
        visited = set()
        count = 0
        while queue and count < max_nodes:
            current, depth = queue.popleft()
            if current is None:
                continue

            key = _control_identity(current)
            if key in visited:
                continue
            visited.add(key)
            count += 1

            lines.append(f"{'  ' * depth}- {_describe_control(current)}")
            if depth >= max_depth:
                continue

            try:
                children = current.GetChildren()
            except Exception:
                children = []
            for child in children:
                queue.append((child, depth + 1))
    else:
        lines.append("- no control available")

    with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write("\n".join(lines) + "\n")


def _log_error(stage, exc):
    with _ERROR_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{stage}] {type(exc).__name__}: {exc}\n")


def _describe_control(control):
    if control is None:
        return "None"

    try:
        values = {
            "type": getattr(control, "ControlTypeName", ""),
            "class": getattr(control, "ClassName", ""),
            "id": getattr(control, "AutomationId", ""),
            "name": getattr(control, "Name", ""),
            "handle": getattr(control, "NativeWindowHandle", ""),
        }
        text_candidates = _collect_control_text_candidates(control)
        if text_candidates:
            values["text"] = max(text_candidates, key=len)[:120].replace("\n", "\\n")
        return (
            f"{values['type']} class={values['class']!r} id={values['id']!r} "
            f"name={values['name']!r} handle={values['handle']!r}"
            + (f" text={values['text']!r}" if 'text' in values else "")
        )
    except Exception as exc:
        return f"<unavailable control: {exc}>"
