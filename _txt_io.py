"""Structured TXT reader for csvFIG distribution data.

Format spec (v1) — see examples/distributions.txt for an example:

  - Lines starting with `#` are comments.
  - Blank lines are ignored.
  - Top-level `KEY: VALUE` defines a setting.
  - A `series:` block introduces one or more named series; each series
    is keyed by `name:` followed by indented fields (color, marker,
    linewidth, linestyle, y, ci_lower, ci_upper, ci_alpha, label).
  - If VALUE is the single character `|`, the following indented lines
    are joined and parsed as a single Python literal (multi-line matrix
    support).

When running `python csvFIG.py` from outside this folder, csvFIG adds its
own directory to sys.path so this module is still available.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


_BOOL_KEYS = {
    "hide_last_ytick", "hide_last_xtick", "show_ci",
    "grid_x", "grid_y", "show_legend", "hide_legend",
    "show_outliers", "black_edges", "connect_medians", "connect_means",
}
_INT_KEYS = {"width", "height", "font_size", "legend_cols"}
_FLOAT_KEYS = {"ymin", "ymax", "y_tick_step",
               "xmin", "xmax", "x_tick_step",
               "linewidth", "marker_size",
               "ci_alpha", "alpha", "edge_lw", "median_marker_size",
               "box_width", "darken_factor", "orig_alpha", "smooth_linewidth"}


def _coerce_scalar(raw: str) -> Any:
    """Best-effort coerce a string into a Python literal / number / str."""
    s = raw.strip()
    if not s:
        return ""
    low = s.lower()
    if low in ("true", "false", "none"):
        return {"true": True, "false": False, "none": None}[low]
    if s.startswith(("[", "(", "{")):
        try:
            return ast.literal_eval(s)
        except (SyntaxError, ValueError):
            return s
    try:
        if "." in s or "e" in low:
            return float(s)
        return int(s)
    except ValueError:
        return s


def _coerce(target: dict, key: str, value: str) -> None:
    if value == "|":
        return  # handled by caller
    parsed = _coerce_scalar(value)
    if key in _BOOL_KEYS and isinstance(parsed, str):
        parsed = parsed.lower() in ("true", "1", "yes")
    if key in _INT_KEYS and isinstance(parsed, float):
        parsed = int(parsed)
    if key in _FLOAT_KEYS and isinstance(parsed, int):
        parsed = float(parsed)
    target[key] = parsed


_KV_RE = re.compile(r"^(?P<key>[A-Za-z_][\w]*)\s*:\s*(?P<value>.*)$")
_NAME_RE = re.compile(r"^\s*([^:#\s][^:]*?)\s*:\s*$")


def parse_txt(text: str) -> dict:
    """Parse a TXT payload.

    Returns
    -------
    dict
        ``{"settings": {...}, "series": [{...}, ...]}``.
        Each series dict contains at least ``name`` and ``label``.
    """
    settings: dict = {}
    series: list[dict] = []
    current_series: dict | None = None

    ml_target: tuple | None = None   # ("settings", key) or ("series", key)
    ml_buf: list[str] = []
    ml_indent: int = 0

    def flush_ml() -> None:
        nonlocal ml_target, ml_buf, ml_indent
        if ml_target is None:
            return
        joined = "\n".join(ml_buf).strip()
        parsed: Any = None
        if joined:
            # 1) try the raw content as-is
            try:
                parsed = ast.literal_eval(joined)
            except (SyntaxError, ValueError):
                # 2) try wrapping in [...] after stripping trailing commas
                stripped = joined.rstrip(",").rstrip()
                if not (stripped.startswith("[") and stripped.endswith("]")):
                    try:
                        parsed = ast.literal_eval(f"[{stripped}]")
                    except (SyntaxError, ValueError) as exc:
                        raise ValueError(
                            f"Multi-line value for {ml_target[1]} is not a valid Python literal:\n{joined}\n{exc}"
                        ) from exc
                else:
                    raise ValueError(
                        f"Multi-line value for {ml_target[1]} is not a valid Python literal:\n{joined}"
                    )
        if ml_target[0] == "settings":
            settings[ml_target[1]] = parsed
        else:
            assert current_series is not None
            current_series[ml_target[1]] = parsed
        ml_target = None
        ml_buf = []
        ml_indent = 0

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if ml_target is not None:
            leading = len(raw) - len(raw.lstrip(" \t"))
            if not stripped:
                ml_buf.append("")
                i += 1
                continue
            if stripped.startswith("#"):
                ml_buf.append(raw)
                i += 1
                continue
            if leading >= ml_indent and ml_indent > 0:
                ml_buf.append(raw[ml_indent:])
                i += 1
                continue
            flush_ml()
            continue

        leading = len(raw) - len(raw.lstrip(" "))

        # Top-level KEY: VALUE
        if leading == 0:
            if stripped == "series:":
                i += 1
                continue
            m = _KV_RE.match(stripped)
            if not m:
                raise ValueError(f"Cannot parse line {i + 1}: {raw!r}")
            key = m.group("key")
            value = m.group("value").strip()
            if value == "|":
                ml_target = ("settings", key)
                ml_buf = []
                ml_indent = 0
                i += 1
                continue
            _coerce(settings, key, value)
            i += 1
            continue

        # Indented: must be inside a series block
        m_name = _NAME_RE.match(raw)
        if leading >= 2 and m_name:
            flush_ml()
            current_series = {"name": m_name.group(1).strip(), "label": m_name.group(1).strip()}
            series.append(current_series)
            i += 1
            continue

        m_field = _KV_RE.match(stripped)
        if leading >= 4 and current_series is not None and m_field:
            key = m_field.group("key")
            value = m_field.group("value").strip()
            if value == "|":
                ml_target = ("series", key)
                ml_buf = []
                ml_indent = leading
                i += 1
                continue
            _coerce(current_series, key, value)
            i += 1
            continue

        raise ValueError(f"Unexpected indented line {i + 1}: {raw!r}")

    flush_ml()
    return {"settings": settings, "series": series}


def read_txt(path: str | Path) -> dict:
    """Read and parse a TXT file."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_txt(text)


def postprocess_csvfig(parsed: dict) -> dict:
    """Convert raw parsed dict into a csvFIG-friendly payload.

    For csvFIG each series is a 1-D distribution (raw observations).
    A 2-D `y` is flattened row-major into a single distribution.
    """
    import numpy as np

    settings = dict(parsed["settings"])
    out_series: list[dict] = []
    for s in parsed["series"]:
        y_raw = s.get("y")
        if y_raw is None:
            continue
        if isinstance(y_raw, (list, tuple)) and len(y_raw) > 0 and isinstance(y_raw[0], (list, tuple, np.ndarray)):
            arr = np.asarray(y_raw, dtype=float)
            data = arr.flatten().astype(float)
        else:
            data = np.asarray([float(v) for v in y_raw], dtype=float)
        data = data[np.isfinite(data)]
        if not data.size:
            raise ValueError("Each series must contain finite numeric observations.")
        out_series.append({
            "label": s.get("label", s.get("name", "data")),
            "color": s.get("color", "#2E86C1"),
            "alpha": float(s.get("alpha", 0.6)) if s.get("alpha") is not None else 0.6,
            "width": float(s.get("width", 0.8)) if s.get("width") is not None else 0.8,
            "data": data,
        })
    return {"settings": settings, "series": out_series}
