"""CSV line plotting GUI with smoothing, styling, and project files."""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
from matplotlib.figure import Figure
from _plot_ui import (DEFAULT_FONT, PREVIEW_BACKGROUND,
                      PlotCanvas, font_family, legend_options, open_figure_settings)
from matplotlib.ticker import FuncFormatter, MaxNLocator, MultipleLocator, ScalarFormatter

COLOR_PALETTE = [
    ("Deep Red",    "#A6232F"),
    ("Red",         "#C0392B"),
    ("Burnt Orange","#D35400"),
    ("Orange",      "#CA6F1E"),
    ("Amber",       "#B7950B"),
    ("Olive",       "#7D8C3A"),
    ("Forest Green","#229954"),
    ("Teal",        "#16A085"),
    ("Ocean Blue",  "#2E86C1"),
    ("Royal Blue",  "#2855A6"),
    ("Indigo",      "#4A235A"),
    ("Purple",      "#7D3C98"),
    ("Plum",        "#9B1B6B"),
]

ORIG_ALPHA = 0.3
DARKEN_FACTOR = 0.80


def darken(hex_color: str, factor: float = DARKEN_FACTOR) -> tuple:
    rgb = mcolors.to_rgb(hex_color)
    return tuple(c * factor for c in rgb)


def trailing_moving_average(values, window: int) -> np.ndarray:
    """Causal moving average: point k uses only current and previous points."""
    if window < 1:
        raise ValueError("Smoothing window must be >= 1.")

    arr = np.asarray(values, dtype=float).reshape(-1)
    if window == 1:
        return arr.copy()

    valid = np.isfinite(arr)
    filled = np.where(valid, arr, 0.0)
    csum = np.concatenate([[0.0], np.cumsum(filled)])
    ccount = np.concatenate([[0], np.cumsum(valid.astype(int))])
    smooth = np.empty(len(arr), dtype=float)

    for k in range(len(arr)):
        lo = max(0, k - window + 1)
        total = csum[k + 1] - csum[lo]
        count = ccount[k + 1] - ccount[lo]
        smooth[k] = total / count if count > 0 else np.nan
    return smooth


def serialize_x(values) -> tuple[str, list]:
    """Keep numeric, date, and category axes editable after reopening a project."""
    arr = np.asarray(values)
    if np.issubdtype(arr.dtype, np.datetime64):
        return "datetime", [pd.Timestamp(v).isoformat() for v in arr]
    if np.issubdtype(arr.dtype, np.number):
        return "numeric", [float(v) if np.isfinite(v) else None for v in arr]
    return "text", [str(v) for v in arr]


def deserialize_x(values, kind: str = "numeric") -> np.ndarray:
    if kind == "datetime":
        return pd.to_datetime(values, errors="raise").to_numpy()
    if kind == "text":
        return np.asarray(values, dtype=str)
    if kind != "numeric":
        raise ValueError(f"Unknown X axis type: {kind}")
    return np.asarray(values, dtype=float)


class CsvPlotterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("csvPLOT")
        self.geometry("1280x820")
        self.minsize(1000, 680)
        self.data: pd.DataFrame | None = None
        self.current_file = ""
        self.plot_title = tk.StringVar()
        self._build_variables()
        self._build_ui()
        self._apply_appearance(redraw=False)

    def _build_variables(self) -> None:
        self.x_column = tk.StringVar()
        self.y_column = tk.StringVar()
        self.curve_color = tk.StringVar(value=COLOR_PALETTE[0][1])
        self.smooth_window = tk.StringVar(value="25")
        self.hold = tk.BooleanVar(value=False)
        self.width = tk.StringVar(value="9")
        self.height = tk.StringVar(value="5.5")
        self.font_name = tk.StringVar(value=DEFAULT_FONT)
        self.font_size = tk.StringVar(value="12")
        self.xmin = tk.StringVar()
        self.xmax = tk.StringVar()
        self.ymin = tk.StringVar()
        self.ymax = tk.StringVar()
        self.x_tick_step = tk.StringVar()
        self.y_tick_step = tk.StringVar()
        self.hide_last_xtick = tk.BooleanVar(value=False)
        self.hide_last_ytick = tk.BooleanVar(value=False)
        self.grid_x = tk.BooleanVar(value=True)
        self.grid_y = tk.BooleanVar(value=True)
        self.legend_ncol = tk.IntVar(value=1)
        self.legend_loc = tk.StringVar(value="best")
        self.hide_legend = tk.BooleanVar(value=False)
        self.hide_original_legend = tk.BooleanVar(value=False)
        self.orig_alpha = tk.DoubleVar(value=ORIG_ALPHA)
        self.darken_factor = tk.DoubleVar(value=DARKEN_FACTOR)
        self.smooth_linewidth = tk.DoubleVar(value=2.4)
        self._line_colors: dict = {}
        self._line_types: dict = {}
        self._curves: list[dict] = []  # tracks curve order, visibility, color, label
        self.status = tk.StringVar(value="Please load a CSV file first.")
        self._orig_x_fmt: object = None
        self._orig_y_fmt: object = None

    def _build_ui(self) -> None:
        sidebar = ttk.Frame(self, width=290)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        controls = ttk.Frame(sidebar, padding=10)
        controls.pack(fill=tk.BOTH, expand=True)

        chart_frame = ttk.Frame(self, padding=(0, 10, 10, 10))
        chart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Button(controls, text="Load CSV", command=self.load_csv).pack(fill=tk.X)
        proj_row = ttk.Frame(controls); proj_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(proj_row, text="Save Project", command=self.save_project).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(proj_row, text="Open Project", command=self.load_project).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        curve = ttk.LabelFrame(controls, text="Curve Data & Style", padding=8)
        curve.pack(fill=tk.X, pady=(8, 8))
        self._combo(curve, "X Column", self.x_column)
        self._combo(curve, "Y Column", self.y_column)
        self._color_combo(curve, "Curve Color", self.curve_color)
        self._entry(curve, "Smoothing Window (blank=off)", self.smooth_window)
        ttk.Checkbutton(curve, text="Hold: keep existing curves", variable=self.hold).pack(anchor=tk.W, pady=(4, 2))
        btn_row = ttk.Frame(curve); btn_row.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_row, text="Plot / Add", command=self.plot_selected).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(btn_row, text="Clear", command=self.clear_plot).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        ttk.Button(curve, text="Re-smooth All Curves (global window)",
                   command=self.resmooth_all).pack(fill=tk.X, pady=(6, 0))

        ttk.Button(controls, text="Figure & Axes...", command=self._open_figure_settings).pack(fill=tk.X, pady=(4, 4))
        ttk.Button(controls, text="Advanced Settings...", command=self._open_advanced).pack(fill=tk.X)

        self.figure = Figure(figsize=(9, 5.5), dpi=100)
        self.figure.set_layout_engine("none")
        self.ax = self.figure.add_subplot(111)
        self.plot_area = tk.Frame(chart_frame, background=PREVIEW_BACKGROUND)
        self.canvas = PlotCanvas(self.figure, master=self.plot_area)
        toolbar = NavigationToolbar2Tk(self.canvas, chart_frame, pack_toolbar=False)
        toolbar.update(); toolbar.pack(side=tk.TOP, fill=tk.X)
        self.plot_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _combo(self, parent: ttk.Widget, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(4, 0))
        combo = ttk.Combobox(parent, textvariable=variable, state="readonly")
        combo.pack(fill=tk.X)
        if label.startswith("X"):
            self.x_combo = combo
        else:
            self.y_combo = combo

    def _open_figure_settings(self):
        return open_figure_settings(self, distribution=False)

    def _color_combo(self, parent: ttk.Widget, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(4, 0))
        values = [f"{name}  {hexv}" for name, hexv in COLOR_PALETTE]
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", height=len(COLOR_PALETTE))
        combo.current(0)
        combo.pack(fill=tk.X)
        self._color_combo_widget = combo

    @staticmethod
    def _entry(parent: ttk.Widget, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(4, 0))
        ttk.Entry(parent, textvariable=variable).pack(fill=tk.X)

    def _slider_row(self, parent: ttk.Widget, label: str, variable: tk.DoubleVar,
                    from_: float, to: float, fmt: str = "{:.2f}") -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(4, 0))
        row = ttk.Frame(parent); row.pack(fill=tk.X)
        val_label = ttk.Label(row, text=fmt.format(variable.get()), width=6)

        def on_move(_=None):
            val_label.config(text=fmt.format(variable.get()))

        ttk.Scale(row, from_=from_, to=to, variable=variable,
                  command=on_move).pack(side=tk.LEFT, fill=tk.X, expand=True)
        val_label.pack(side=tk.LEFT, padx=(4, 0))

    def load_csv(self) -> None:
        path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        data = None
        used_encoding = ""
        for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk", "latin1"):
            try:
                data = pd.read_csv(path, encoding=encoding)
                used_encoding = encoding
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
            except (OSError, pd.errors.EmptyDataError) as exc:
                messagebox.showerror("Load Failed", str(exc))
                return
        if data is None:
            messagebox.showerror("Load Failed", "Cannot parse this CSV. Check encoding and format.")
            return
        if data.empty or not len(data.columns):
            messagebox.showwarning("Empty", "The CSV has no plottable columns.")
            return
        self.data, self.current_file = data, path
        columns = [str(c) for c in data.columns]
        self.x_combo["values"] = columns
        self.y_combo["values"] = columns
        default_x = "episode" if "episode" in columns else columns[0]
        self.x_column.set(default_x)
        self.y_column.set(next((c for c in columns if c != default_x), default_x))
        fname = path.split("/")[-1].split("\\")[-1]
        self.status.set(f"Loaded: {fname}  ({len(data)} rows, {used_encoding})")

    def plot_selected(self) -> None:
        if self.data is None:
            messagebox.showinfo("Info", "Please load a CSV file first.")
            return
        try:
            color = self.curve_color.get().split()[-1]
            smooth_str = self.smooth_window.get().strip()
            window = int(smooth_str) if smooth_str else 1
            if window < 1:
                raise ValueError("Smoothing window must be >= 1.")
            x_name, y_name = self.x_column.get(), self.y_column.get()
            y = pd.to_numeric(self.data[y_name], errors="coerce").replace([np.inf, -np.inf], np.nan)
            valid = y.notna()
            if not valid.any():
                raise ValueError(f"Column '{y_name}' has no numeric values.")
            x_raw = self.data.loc[valid, x_name]
            y = y.loc[valid]

            x_numeric = pd.to_numeric(x_raw, errors="coerce")
            if x_numeric.notna().all():
                x = x_numeric
                numeric_x = True
            else:
                x_datetime = pd.to_datetime(x_raw, errors="coerce")
                if x_datetime.notna().all():
                    x = x_datetime
                    numeric_x = False
                else:
                    valid_x = x_raw.notna()
                    x = x_raw.loc[valid_x]
                    y = y.loc[valid_x]
                    numeric_x = False

            order = np.argsort(np.asarray(x))
            x = x.iloc[order] if isinstance(x, pd.Series) else x[order]
            y = y.iloc[order]
            if not self.hold.get():
                self.ax.clear()
                self._line_colors.clear()
                self._line_types.clear()
                self._curves.clear()
            fname = self.current_file.split("/")[-1].split("\\")[-1]
            label = f"{y_name} ({fname})"
            line = self.ax.plot(x, y, color=color, linewidth=1.5,
                                alpha=self.orig_alpha.get(), label=label)[0]
            self._line_colors[id(line)] = color
            self._line_types[id(line)] = "original"
            sline = None
            if window > 1:
                smooth_arr = trailing_moving_average(y.to_numpy(dtype=float), window)
                smooth = pd.Series(smooth_arr, index=y.index)
                dark = darken(color, self.darken_factor.get())
                sline = self.ax.plot(x, smooth, color=dark,
                                     linewidth=self.smooth_linewidth.get(),
                                     label=label)[0]
                self._line_colors[id(sline)] = color
                self._line_types[id(sline)] = "smooth"
            self._curves.append({
                "line": line,
                "smooth_line": sline,
                "curve_id": self._next_curve_number(),
                "color": color,
                "label": label,
                "visible": True,
                # raw data for global re-smooth
                "raw_x": np.asarray(x),
                "raw_y": y.to_numpy(dtype=float) if isinstance(y, pd.Series) else np.asarray(y, dtype=float),
            })
            self.ax.set_xlabel(x_name)
            self.ax.set_ylabel(y_name)
            if numeric_x:
                self.ax.xaxis.set_major_locator(MaxNLocator(nbins=8, integer=x_name.lower() == "episode"))
                fmt = ScalarFormatter(useOffset=False)
                fmt.set_scientific(False)
                self.ax.xaxis.set_major_formatter(fmt)
            self._update_legend()
            self._apply_appearance()
        except (ValueError, KeyError) as exc:
            messagebox.showerror("Plot Error", str(exc))

    def clear_plot(self) -> None:
        self.ax.clear()
        self._line_colors.clear()
        self._line_types.clear()
        self._curves.clear()
        self.plot_title.set("")
        self._apply_appearance()
        self.status.set("Canvas cleared.")

    def resmooth_all(self) -> None:
        """Recompute smooth lines for all curves using the current smooth window value."""
        try:
            smooth_str = self.smooth_window.get().strip()
            window = int(smooth_str) if smooth_str else 1
            if window < 1:
                raise ValueError("Smoothing window must be >= 1.")
        except ValueError as e:
            messagebox.showerror("Invalid Window", str(e))
            return

        count = 0
        no_raw = 0
        factor = self.darken_factor.get()
        lw = self.smooth_linewidth.get()

        for c in self._curves:
            raw_x = c.get("raw_x")
            raw_y = c.get("raw_y")
            if raw_x is None or raw_y is None:
                no_raw += 1
                continue

            # remove old smooth line if exists
            if c.get("smooth_line") is not None:
                old_line = c["smooth_line"]
                old_line.remove()
                self._line_colors.pop(id(old_line), None)
                self._line_types.pop(id(old_line), None)
                c["smooth_line"] = None

            if window > 1:
                smooth_y = trailing_moving_average(raw_y, window)
                dark = darken(c["color"], factor)
                sline = self.ax.plot(raw_x, smooth_y, color=dark,
                                     linewidth=lw,
                                     label=c["label"])[0]
                self._line_colors[id(sline)] = c["color"]
                self._line_types[id(sline)] = "smooth"
                c["smooth_line"] = sline

            # restore visibility
            if c.get("smooth_line") is not None:
                c["smooth_line"].set_visible(c.get("visible", True))

            count += 1

        self._update_legend()
        self._apply_appearance()

        msg = f"Re-smoothed {count} curves (window={window})"
        if no_raw > 0:
            msg += f", {no_raw} skipped (no raw data)"
        self.status.set(msg)

    def save_project(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Project", defaultextension=".cplot",
            filetypes=[("csvPLOT Project", "*.cplot"), ("All files", "*.*")])
        if not path:
            return
        project = {
            "version": 1,
            "type": "csvPLOT",
            "settings": {
                "plot_title": self.plot_title.get(),
                "width": self.width.get(),
                "height": self.height.get(),
                "font_name": self.font_name.get(),
                "font_size": self.font_size.get(),
                "xmin": self.xmin.get(),
                "xmax": self.xmax.get(),
                "ymin": self.ymin.get(),
                "ymax": self.ymax.get(),
                "x_tick_step": self.x_tick_step.get(),
                "y_tick_step": self.y_tick_step.get(),
                "hide_last_xtick": self.hide_last_xtick.get(),
                "hide_last_ytick": self.hide_last_ytick.get(),
                "grid_x": self.grid_x.get(),
                "grid_y": self.grid_y.get(),
                "legend_ncol": self.legend_ncol.get(),
                "legend_loc": self.legend_loc.get(),
                "hide_legend": self.hide_legend.get(),
                "hide_original_legend": self.hide_original_legend.get(),
                "orig_alpha": self.orig_alpha.get(),
                "darken_factor": self.darken_factor.get(),
                "smooth_linewidth": self.smooth_linewidth.get(),
                "smooth_window": self.smooth_window.get(),
                "x_column": self.x_column.get(),
                "y_column": self.y_column.get(),
                "x_label": self.ax.get_xlabel(),
                "y_label": self.ax.get_ylabel(),
            },
            "curves": [],
        }
        for c in self._curves:
            line = c["line"]
            xd = line.get_xdata()
            yd = line.get_ydata()
            x_kind, x_list = serialize_x(xd)
            y_list = [float(v) if np.isfinite(v) else None for v in yd]
            sline = c.get("smooth_line")
            sx_list, sy_list = [], []
            sx_kind = x_kind
            if sline is not None:
                sxd = sline.get_xdata()
                syd = sline.get_ydata()
                sx_kind, sx_list = serialize_x(sxd)
                sy_list = [float(v) if np.isfinite(v) else None for v in syd]
            project["curves"].append({
                "x_data": x_list,
                "x_kind": x_kind,
                "y_data": y_list,
                "color": c["color"],
                "label": c["label"],
                "curve_id": c.get("curve_id"),
                "visible": c.get("visible", True),
                "smooth_x": sx_list,
                "smooth_x_kind": sx_kind,
                "smooth_y": sy_list,
                "has_smooth": sline is not None,
            })
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(project, f, ensure_ascii=False, indent=2)
            fname = path.split("/")[-1].split("\\")[-1]
            self.status.set(f"Project saved: {fname}")
        except OSError as exc:
            messagebox.showerror("Save Failed", str(exc))

    def load_project(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Project",
            filetypes=[("csvPLOT Project", "*.cplot"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                project = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load Failed", str(exc))
            return
        if project.get("type") != "csvPLOT":
            messagebox.showerror("Wrong Format", "This is not a csvPLOT project file.")
            return
        s = project.get("settings", {})
        self.plot_title.set(s.get("plot_title", ""))
        self.width.set(s.get("width", "9"))
        self.height.set(s.get("height", "5.5"))
        self.font_name.set(s.get("font_name", DEFAULT_FONT))
        self.font_size.set(s.get("font_size", "12"))
        self.xmin.set(s.get("xmin", ""))
        self.xmax.set(s.get("xmax", ""))
        self.ymin.set(s.get("ymin", ""))
        self.ymax.set(s.get("ymax", ""))
        self.x_tick_step.set(s.get("x_tick_step", ""))
        self.y_tick_step.set(s.get("y_tick_step", ""))
        self.hide_last_xtick.set(s.get("hide_last_xtick", False))
        self.hide_last_ytick.set(s.get("hide_last_ytick", False))
        self.grid_x.set(s.get("grid_x", True))
        self.grid_y.set(s.get("grid_y", True))
        self.legend_ncol.set(s.get("legend_ncol", 1))
        self.legend_loc.set(s.get("legend_loc", "best"))
        self.hide_legend.set(s.get("hide_legend", False))
        self.hide_original_legend.set(s.get("hide_original_legend", s.get("hide_original_lines", False)))
        self.orig_alpha.set(s.get("orig_alpha", ORIG_ALPHA))
        self.darken_factor.set(s.get("darken_factor", DARKEN_FACTOR))
        self.smooth_linewidth.set(s.get("smooth_linewidth", 2.4))
        self.smooth_window.set(s.get("smooth_window", "25"))
        self.x_column.set(s.get("x_column", ""))
        self.y_column.set(s.get("y_column", ""))
        x_label = s.get("x_label", "")
        y_label = s.get("y_label", "")
        self.ax.clear()
        self._line_colors.clear()
        self._line_types.clear()
        self._curves.clear()
        alpha = self.orig_alpha.get()
        factor = self.darken_factor.get()
        lw = self.smooth_linewidth.get()
        for c in project.get("curves", []):
            x = deserialize_x(c["x_data"], c.get("x_kind", "numeric"))
            y = np.array(c["y_data"], dtype=float)
            color = c["color"]
            label = c["label"]
            visible = c.get("visible", True)
            line = self.ax.plot(x, y, color=color, linewidth=1.5,
                                alpha=alpha, label=label)[0]
            self._line_colors[id(line)] = color
            self._line_types[id(line)] = "original"
            sline = None
            if c.get("has_smooth"):
                sx = deserialize_x(c["smooth_x"], c.get("smooth_x_kind", c.get("x_kind", "numeric")))
                sy = np.array(c["smooth_y"], dtype=float)
                dark = darken(color, factor)
                sline = self.ax.plot(sx, sy, color=dark,
                                     linewidth=lw,
                                     label=label)[0]
                self._line_colors[id(sline)] = color
                self._line_types[id(sline)] = "smooth"
            line.set_visible(visible)
            if sline is not None:
                sline.set_visible(visible)
            self._curves.append({
                "line": line,
                "smooth_line": sline,
                "curve_id": c.get("curve_id") or self._next_curve_number(),
                "color": color,
                "label": label,
                "visible": visible,
                # raw data for global re-smooth (from v2 or v1 x/y data)
                "raw_x": x,
                "raw_y": y,
            })
        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.ax.set_title(self.plot_title.get().strip())
        self._update_legend()
        self._apply_appearance()
        fname = path.split("/")[-1].split("\\")[-1]
        self.status.set(f"Project loaded: {fname}  ({len(self._curves)} curves)")

    def _apply_curve_visibility(self) -> None:
        for curve in self._curves:
            visible = curve.get("visible", True)
            curve["line"].set_visible(visible)
            sline = curve.get("smooth_line")
            if sline is not None:
                sline.set_visible(visible)
    def _next_curve_number(self) -> int:
        used = []
        for i, curve in enumerate(self._curves, start=1):
            try:
                used.append(int(curve.get("curve_id", i)))
            except (TypeError, ValueError):
                used.append(i)
        return max(used, default=0) + 1


    def _update_legend(self) -> None:
        self._apply_curve_visibility()
        existing = self.ax.get_legend()
        if existing:
            existing.remove()
        if self.hide_legend.get():
            return
        # Build legend from self._curves in order, only visible ones
        legend_handles = []
        legend_labels = []
        for curve in self._curves:
            if not curve.get("visible", True):
                continue
            line = curve["line"]
            label = curve["label"]
            if label.strip() and line.get_visible() and not self.hide_original_legend.get():
                legend_handles.append(line)
                legend_labels.append(label)
            sline = curve.get("smooth_line")
            if sline is not None and sline.get_visible():
                legend_handles.append(sline)
                legend_labels.append(label)
        if legend_handles:
            loc = self.legend_loc.get().strip() or "best"
            ncol = max(1, self.legend_ncol.get())
            kwargs = {"ncol": ncol, **legend_options(loc)}
            self.ax.legend(legend_handles, legend_labels, **kwargs)


    def _open_advanced(self) -> None:
        """Open advanced settings with reorder, color, and hide/show controls."""
        dlg = tk.Toplevel(self)
        dlg.title("Advanced Settings")
        dlg.geometry("560x760")
        dlg.transient(self)
        dlg.grab_set()

        scroll_area = ttk.Frame(dlg)
        scroll_area.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(scroll_area, highlightthickness=0)
        vbar = ttk.Scrollbar(scroll_area, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = ttk.Frame(canvas)
        inner_win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_config(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_config(event):
            canvas.itemconfig(inner_win, width=event.width)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        inner.bind("<Configure>", _on_inner_config)
        canvas.bind("<Configure>", _on_canvas_config)
        dlg.bind("<MouseWheel>", _on_mousewheel)

        ttk.Label(inner, text="Plot Title").pack(anchor=tk.W, pady=(12, 2))
        ttk.Entry(inner, textvariable=self.plot_title, width=60).pack(fill=tk.X, padx=12)

        ttk.Label(inner, text="X-Axis Label").pack(anchor=tk.W, pady=(8, 2))
        x_var = tk.StringVar(value=self.ax.get_xlabel())
        ttk.Entry(inner, textvariable=x_var, width=60).pack(fill=tk.X, padx=12)

        ttk.Label(inner, text="Y-Axis Label").pack(anchor=tk.W, pady=(8, 2))
        y_var = tk.StringVar(value=self.ax.get_ylabel())
        ttk.Entry(inner, textvariable=y_var, width=60).pack(fill=tk.X, padx=12)

        ttk.Label(inner, text="Font Name (manual override)").pack(anchor=tk.W, pady=(8, 2))
        ttk.Entry(inner, textvariable=self.font_name, width=60).pack(fill=tk.X, padx=12)

        grid_frame = ttk.LabelFrame(inner, text="Grid", padding=8)
        grid_frame.pack(fill=tk.X, padx=12, pady=(6, 4))
        ttk.Checkbutton(grid_frame, text="Vertical (X)", variable=self.grid_x).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(grid_frame, text="Horizontal (Y)", variable=self.grid_y).pack(side=tk.LEFT)

        legend_frame = ttk.LabelFrame(inner, text="Legend Layout", padding=8)
        legend_frame.pack(fill=tk.X, padx=12, pady=(6, 4))
        ttk.Label(legend_frame, text="Columns").pack(anchor=tk.W)
        ttk.Spinbox(legend_frame, from_=1, to=10, textvariable=self.legend_ncol, width=8).pack(anchor=tk.W, pady=(1, 6))
        ttk.Label(legend_frame, text="Location").pack(anchor=tk.W)
        loc_values = ["best", "upper right", "upper left", "lower left", "lower right",
                       "right", "center left", "center right", "lower center", "upper center", "center",
                       "outside upper", "outside lower", "outside right"]
        ttk.Combobox(legend_frame, textvariable=self.legend_loc, values=loc_values,
                     state="readonly", width=18).pack(anchor=tk.W, pady=(1, 2))
        ttk.Checkbutton(legend_frame, text="Hide all legends", variable=self.hide_legend).pack(anchor=tk.W, pady=(4, 0))
        ttk.Checkbutton(legend_frame, text="Hide original data legends", variable=self.hide_original_legend).pack(anchor=tk.W, pady=(2, 0))

        # --- Curves list with reorder, color, hide/show ---
        n_curves = len(self._curves)
        ttk.Label(inner, text=f"Curves on Plot  ({n_curves})  — uncheck to hide, ↑↓ to reorder").pack(
            anchor=tk.W, pady=(10, 2))

        curve_frame = ttk.Frame(inner)
        curve_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        curve_vars = []  # list of (visible_var, label_var, color_var)
        if n_curves == 0:
            ttk.Label(curve_frame, text="(no curves on plot)", foreground="#888").pack(anchor=tk.W)
        else:
            for i, curve in enumerate(self._curves):
                kv = tk.BooleanVar(value=curve.get("visible", True))
                lv = tk.StringVar(value=curve["label"])
                cv = tk.StringVar(value=curve["color"])
                curve_vars.append((kv, lv, cv))

                def _make_toggle(idx=i, visible_var=kv):
                    def _on_toggle():
                        vis = visible_var.get()
                        c = self._curves[idx]
                        c["visible"] = vis
                        c["line"].set_visible(vis)
                        sline = c.get("smooth_line")
                        if sline is not None:
                            sline.set_visible(vis)
                        self._update_legend()
                        self._apply_appearance()
                        self.canvas.draw_idle()
                    return _on_toggle

                ttk.Checkbutton(curve_frame, variable=kv, command=_make_toggle(i)).grid(row=i, column=0, sticky=tk.W, pady=2)
                ttk.Label(curve_frame, text=f"#{i+1}", width=4).grid(row=i, column=3, sticky=tk.W, pady=2)
                ttk.Entry(curve_frame, textvariable=lv, width=30).grid(row=i, column=4, sticky=tk.EW, pady=2, padx=(2, 4))

                # Color button
                def _pick_color(idx=i, v=cv):
                    picker = tk.Toplevel(dlg)
                    picker.title("Pick Color")
                    picker.geometry("300x400")
                    picker.transient(dlg)
                    picker.grab_set()
                    ttk.Label(picker, text="Palette", padding=(10, 6)).pack(anchor=tk.W)
                    pal = ttk.Frame(picker, padding=(10, 0))
                    pal.pack(fill=tk.X)
                    COLS = 6
                    for j, (name, hexv) in enumerate(COLOR_PALETTE):
                        r, c = divmod(j, COLS)
                        tk.Button(pal, width=4, height=2, bg=hexv,
                                  command=lambda h=hexv: v.set(h)).grid(row=r, column=c, padx=2, pady=2)
                    ttk.Label(picker, text="Custom", padding=(10, 10)).pack(anchor=tk.W)
                    cf = ttk.Frame(picker, padding=(10, 0))
                    cf.pack(fill=tk.X)
                    ttk.Entry(cf, textvariable=v, width=14).pack(side=tk.LEFT, padx=(0, 6))
                    def _sys_pick():
                        from tkinter import colorchooser
                        r = colorchooser.askcolor(color=v.get(), title="Choose Color")
                        if r and r[1]:
                            v.set(r[1])
                    ttk.Button(cf, text="Picker…", command=_sys_pick).pack(side=tk.LEFT)
                    ttk.Label(picker, text="Preview", padding=(10, 10)).pack(anchor=tk.W)
                    sw = tk.Label(picker, width=28, height=2, bg=v.get(), relief="sunken", bd=1)
                    sw.pack(fill=tk.X, padx=10)
                    def _preview(*_):
                        color = v.get().strip()
                        if mcolors.is_color_like(color):
                            try:
                                sw.config(bg=color)
                            except tk.TclError:
                                pass
                    trace_id = v.trace_add("write", _preview)
                    def _close_picker():
                        v.trace_remove("write", trace_id)
                        picker.destroy()
                        dlg.grab_set()
                    picker.protocol("WM_DELETE_WINDOW", _close_picker)
                    ttk.Button(picker, text="OK", command=_close_picker).pack(pady=10)

                tk.Button(curve_frame, text="", bg=curve["color"], width=2,
                          command=_pick_color).grid(row=i, column=5, padx=(4, 2), pady=2)

                # Up/Down buttons
                btn_col = ttk.Frame(curve_frame)
                btn_col.grid(row=i, column=6, padx=(4, 0), pady=2)
                def _move_up(idx=i):
                    if idx > 0:
                        self._curves[idx - 1], self._curves[idx] = self._curves[idx], self._curves[idx - 1]
                        dlg.grab_release()
                        dlg.destroy()
                        self._open_advanced()
                def _move_down(idx=i):
                    if idx < len(self._curves) - 1:
                        self._curves[idx], self._curves[idx + 1] = self._curves[idx + 1], self._curves[idx]
                        dlg.grab_release()
                        dlg.destroy()
                        self._open_advanced()
                up_btn = ttk.Button(btn_col, text="\u2191", width=2, command=_move_up)
                down_btn = ttk.Button(btn_col, text="\u2193", width=2, command=_move_down)
                up_btn.pack(side=tk.LEFT, padx=(0, 1))
                down_btn.pack(side=tk.LEFT)
                if i == 0:
                    up_btn.config(state=tk.DISABLED)
                if i == n_curves - 1:
                    down_btn.config(state=tk.DISABLED)

                def _delete_curve(idx=i):
                    curve = self._curves.pop(idx)
                    for key in ("line", "smooth_line"):
                        artist = curve.get(key)
                        if artist is not None:
                            artist.remove()
                            self._line_colors.pop(id(artist), None)
                            self._line_types.pop(id(artist), None)
                    self._update_legend()
                    self._apply_appearance()
                    dlg.grab_release()
                    dlg.destroy()
                    self._open_advanced()

                ttk.Button(curve_frame, text="Delete", width=7, command=_delete_curve).grid(
                    row=i, column=7, padx=(6, 0), pady=2)

            curve_frame.columnconfigure(4, weight=1)

        # Curve style sliders
        style = ttk.LabelFrame(inner, text="Curve Style", padding=8)
        style.pack(fill=tk.X, padx=12, pady=(6, 12))
        self._slider_row(style, "Original Line Alpha", self.orig_alpha, 0.0, 1.0)
        self._slider_row(style, "Smooth Darken Factor", self.darken_factor, 0.3, 1.0)
        self._slider_row(style, "Smooth Line Width", self.smooth_linewidth, 0.5, 5.0, "{:.1f}")

        def _sync_curve_metadata() -> bool:
            for _, _, color_var in curve_vars:
                if not mcolors.is_color_like(color_var.get().strip()):
                    messagebox.showerror("Invalid Color", "Please select a valid color.", parent=dlg)
                    return False
            for curve, (kv, lv, cv) in zip(self._curves, curve_vars):
                curve["visible"] = kv.get()
                curve["label"] = lv.get().strip()
                new_color = cv.get().strip()
                if new_color != curve["color"]:
                    curve["color"] = new_color
                    # Update line colors
                    line = curve["line"]
                    self._line_colors[id(line)] = new_color
                    line.set_color(new_color)
                    sline = curve.get("smooth_line")
                    if sline is not None:
                        self._line_colors[id(sline)] = new_color
                        sline.set_color(darken(new_color, self.darken_factor.get()))
            return True

        def apply_settings():
            self.ax.set_title(self.plot_title.get().strip())
            self.ax.set_xlabel(x_var.get().strip())
            self.ax.set_ylabel(y_var.get().strip())
            if not _sync_curve_metadata():
                return

            # Apply visibility
            for curve in self._curves:
                vis = curve.get("visible", True)
                curve["line"].set_visible(vis)
                sline = curve.get("smooth_line")
                if sline is not None:
                    sline.set_visible(vis)
            # Apply labels
            for curve in self._curves:
                curve["line"].set_label(curve["label"])
                sline = curve.get("smooth_line")
                if sline is not None:
                    sline.set_label(curve["label"])
            # Apply style
            alpha = self.orig_alpha.get()
            factor = self.darken_factor.get()
            lw = self.smooth_linewidth.get()
            for curve in self._curves:
                base = curve["color"]
                line = curve["line"]
                line.set_alpha(alpha)
                sline = curve.get("smooth_line")
                if sline is not None:
                    sline.set_color(darken(base, factor))
                    sline.set_linewidth(lw)
            self._update_legend()
            self._apply_appearance()
            dlg.grab_release()
            dlg.destroy()

        def cancel():
            dlg.grab_release()
            dlg.destroy()

        btn_frame = ttk.Frame(dlg); btn_frame.pack(fill=tk.X, pady=12, padx=12)
        ttk.Button(btn_frame, text="Apply", command=apply_settings).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side=tk.RIGHT)

    def _optional_float(self, variable: tk.StringVar, name: str) -> float | None:
        value = variable.get().strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be numeric or blank.") from exc

    def _apply_appearance(self, redraw: bool = True) -> None:
        try:
            self.ax.set_title(self.plot_title.get().strip())
            width, height = float(self.width.get()), float(self.height.get())
            font_size = float(self.font_size.get())
            if width <= 0 or height <= 0 or font_size <= 0:
                raise ValueError("Figure size and font size must be > 0.")
            xmin = self._optional_float(self.xmin, "X range")
            xmax = self._optional_float(self.xmax, "X range")
            ymin = self._optional_float(self.ymin, "Y range")
            ymax = self._optional_float(self.ymax, "Y range")
            if xmin is not None or xmax is not None:
                self.ax.set_xlim(left=xmin, right=xmax)
            else:
                self.ax.autoscale(enable=True, axis="x", tight=False)
            if ymin is not None or ymax is not None:
                self.ax.set_ylim(bottom=ymin, top=ymax)
            else:
                self.ax.autoscale(enable=True, axis="y", tight=False)
            x_step = self._optional_float(self.x_tick_step, "X tick step")
            y_step = self._optional_float(self.y_tick_step, "Y tick step")
            if x_step is not None and x_step > 0:
                self.ax.xaxis.set_major_locator(MultipleLocator(x_step))
            if y_step is not None and y_step > 0:
                self.ax.yaxis.set_major_locator(MultipleLocator(y_step))
            self.ax.grid(False)
            if self.grid_x.get():
                self.ax.grid(True, axis="x", alpha=0.25)
            if self.grid_y.get():
                self.ax.grid(True, axis="y", alpha=0.25)
            self.canvas.set_size_inches(width, height)
            self._reset_axes_layout()
            font = self.font_name.get().strip() or DEFAULT_FONT
            for item in [self.ax.title, self.ax.xaxis.label, self.ax.yaxis.label]:
                item.set_fontfamily(font_family(font)); item.set_fontsize(font_size)
            for lbl in self.ax.get_xticklabels() + self.ax.get_yticklabels():
                lbl.set_fontfamily(font_family(font)); lbl.set_fontsize(font_size)
            legend = self.ax.get_legend()
            if legend:
                for text in legend.get_texts():
                    text.set_fontfamily(font_family(font)); text.set_fontsize(font_size * 0.9)
            if redraw:
                self.canvas.draw()
                if self.hide_last_xtick.get():
                    xticks = self.ax.get_xticks()
                    if len(xticks) > 0:
                        last_x = xticks[-1]
                        cur_fmt = self.ax.xaxis.get_major_formatter()
                        if not isinstance(cur_fmt, FuncFormatter):
                            self._orig_x_fmt = cur_fmt
                        _orig = self._orig_x_fmt if self._orig_x_fmt else cur_fmt
                        def _xfmt(val, pos, _l=last_x, _o=_orig):
                            if abs(val - _l) < 1e-9:
                                return ""
                            if _o:
                                try:
                                    return _o(val, pos)
                                except Exception:
                                    pass
                            return f"{val:g}"
                        self.ax.xaxis.set_major_formatter(FuncFormatter(_xfmt))
                else:
                    if self._orig_x_fmt is not None:
                        self.ax.xaxis.set_major_formatter(self._orig_x_fmt)
                        self._orig_x_fmt = None
                if self.hide_last_ytick.get():
                    yticks = self.ax.get_yticks()
                    if len(yticks) > 0:
                        last_y = yticks[-1]
                        cur_fmt = self.ax.yaxis.get_major_formatter()
                        if not isinstance(cur_fmt, FuncFormatter):
                            self._orig_y_fmt = cur_fmt
                        _orig = self._orig_y_fmt if self._orig_y_fmt else cur_fmt
                        def _yfmt(val, pos, _l=last_y, _o=_orig):
                            if abs(val - _l) < 1e-9:
                                return ""
                            if _o:
                                try:
                                    return _o(val, pos)
                                except Exception:
                                    pass
                            return f"{val:g}"
                        self.ax.yaxis.set_major_formatter(FuncFormatter(_yfmt))
                else:
                    if self._orig_y_fmt is not None:
                        self.ax.yaxis.set_major_formatter(self._orig_y_fmt)
                        self._orig_y_fmt = None
                self.canvas.draw()
        except ValueError as exc:
            if redraw:
                messagebox.showerror("Invalid Setting", str(exc))

    def _reset_axes_layout(self) -> None:
        loc = self.legend_loc.get().strip()
        if not self.hide_legend.get() and loc == "outside right":
            self.figure.subplots_adjust(left=0.12, right=0.78, bottom=0.14, top=0.90)
        elif not self.hide_legend.get() and loc == "outside lower":
            self.figure.subplots_adjust(left=0.12, right=0.94, bottom=0.22, top=0.90)
        elif not self.hide_legend.get() and loc == "outside upper":
            self.figure.subplots_adjust(left=0.12, right=0.94, bottom=0.14, top=0.82)
        else:
            self.figure.subplots_adjust(left=0.12, right=0.94, bottom=0.14, top=0.90)
        self.canvas.base_bottom = self.figure.subplotpars.bottom


if __name__ == "__main__":
    CsvPlotterApp().mainloop()
