"""CSV and TXT distribution plots with styling and project files."""
from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.cbook import boxplot_stats
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator
from scipy.stats import gaussian_kde

# Pull in the shared TXT parser from this folder. We add the script's own
# directory to sys.path first so that running `python csvFIG.py` from any
# working directory still picks up _txt_io.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    from _txt_io import (
        read_txt as _read_txt,
        postprocess_csvfig as _pp_csvfig,
    )
    _HAS_TXT = True
except Exception:  # noqa: BLE001
    _HAS_TXT = False

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

def compute_box_stats(data: np.ndarray) -> dict:
    """Compute boxplot statistics from raw data."""
    arr = np.asarray(data, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        raise ValueError("A distribution must contain finite numeric observations.")
    stats = boxplot_stats(arr)[0]
    return {
        "mean": float(stats["mean"]),
        "med": float(stats["med"]),
        "q1": float(stats["q1"]),
        "q3": float(stats["q3"]),
        "cilo": float(stats["cilo"]),
        "cihi": float(stats["cihi"]),
        "whislo": float(stats["whislo"]),
        "whishi": float(stats["whishi"]),
        "iqr": float(stats["q3"] - stats["q1"]),
        "n": len(arr),
        "fliers": stats.get("fliers", []).tolist() if stats.get("fliers") is not None else [],
    }


class CsvFigApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("csvFIG")
        self.geometry("1280x820")
        self.minsize(1000, 680)
        self.data: pd.DataFrame | None = None
        self.current_file = ""
        self.plot_title = tk.StringVar()
        self.x_label_var = tk.StringVar()
        self.y_label_var = tk.StringVar()
        self._build_variables()
        self._build_ui()
        self._apply_appearance(redraw=False)

    def _build_variables(self) -> None:
        self.column = tk.StringVar()
        self.box_label = tk.StringVar()
        self.box_color = tk.StringVar(value=COLOR_PALETTE[0][1])
        self.box_width = tk.DoubleVar(value=0.8)
        self.hold = tk.BooleanVar(value=False)
        self.width_fig = tk.StringVar(value="9")
        self.height_fig = tk.StringVar(value="5.5")
        self.font_name = tk.StringVar(value="DejaVu Sans")
        self.font_size = tk.StringVar(value="12")
        self.ymin = tk.StringVar()
        self.ymax = tk.StringVar()
        self.y_tick_step = tk.StringVar()
        self.hide_last_ytick = tk.BooleanVar(value=False)
        self.grid_x = tk.BooleanVar(value=True)
        self.grid_y = tk.BooleanVar(value=True)
        self.box_orientation = tk.StringVar(value="Box (V)")
        self.show_outliers = tk.BooleanVar(value=True)
        self._connect_medians = tk.BooleanVar(value=False)
        self._connect_means = tk.BooleanVar(value=False)
        self._edge_lw = tk.DoubleVar(value=1.5)
        self._black_edges = tk.BooleanVar(value=False)
        self._median_linestyle = tk.StringVar(value="solid")
        self._median_marker_size = tk.DoubleVar(value=6.0)
        self._show_legend = tk.BooleanVar(value=False)
        self._boxes: list[dict] = []
        self._added_key: str | None = None
        if _HAS_TXT:
            self.status = tk.StringVar(
                value="Load CSV for one column, or Load TXT for a multi-series distribution set."
            )
        else:
            self.status = tk.StringVar(value="Please load a CSV file first.")
        self._orig_y_fmt: object = None
        self.box_width.trace_add("write", self._on_width_changed)
        self._edge_lw.trace_add("write", lambda *_: self._redraw() if self._boxes else None)
        self._median_linestyle.trace_add("write", lambda *_: self._redraw() if self._boxes else None)
        self._median_marker_size.trace_add("write", lambda *_: self._redraw() if self._boxes else None)

    def _build_ui(self) -> None:
        # Left sidebar with scroll
        sidebar = ttk.Frame(self, width=310)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        scroll_canvas = tk.Canvas(sidebar, highlightthickness=0)
        vbar = ttk.Scrollbar(sidebar, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        controls = ttk.Frame(scroll_canvas, padding=10)
        controls_win = scroll_canvas.create_window((0, 0), window=controls, anchor="nw")

        def _on_inner(_=None):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        def _on_canvas(event):
            scroll_canvas.itemconfig(controls_win, width=event.width)
        def _on_wheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        controls.bind("<Configure>", _on_inner)
        scroll_canvas.bind("<Configure>", _on_canvas)
        self.bind("<MouseWheel>", _on_wheel)

        chart_frame = ttk.Frame(self, padding=(0, 10, 10, 10))
        chart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        row1 = ttk.Frame(controls); row1.pack(fill=tk.X, pady=(0, 2))
        ttk.Button(row1, text="Load CSV", command=self.load_csv).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(row1, text="Load TXT", command=self.load_txt).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        row2 = ttk.Frame(controls); row2.pack(fill=tk.X)
        ttk.Button(row2, text="Save Project", command=self.save_project).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(row2, text="Open Project", command=self.load_project).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))
        ttk.Label(controls, textvariable=self.status, wraplength=260, foreground="#555").pack(fill=tk.X, pady=(5, 12))

        box_frame = ttk.LabelFrame(controls, text="Data & Style", padding=8)
        box_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(box_frame, text="Data Column").pack(anchor=tk.W, pady=(4, 0))
        self.col_combo = ttk.Combobox(box_frame, textvariable=self.column, state="readonly")
        self.col_combo.pack(fill=tk.X)
        self.col_combo.bind("<<ComboboxSelected>>", lambda e: self._on_column_changed())
        ttk.Label(box_frame, text="Label (display name)").pack(anchor=tk.W, pady=(4, 0))
        self.label_entry = ttk.Entry(box_frame, textvariable=self.box_label)
        self.label_entry.pack(fill=tk.X)
        self._color_combo(box_frame, "Color", self.box_color)
        self._slider_row(box_frame, "Relative Width", self.box_width, 0.1, 1.0)
        ttk.Label(box_frame, text="Plot Type").pack(anchor=tk.W, pady=(4, 0))
        pt_combo = ttk.Combobox(box_frame, textvariable=self.box_orientation,
                     values=["Box (V)", "Box (H)", "Bar+Err", "Violin", "Violin+Box"],
                     state="readonly")
        pt_combo.pack(fill=tk.X)
        pt_combo.bind("<<ComboboxSelected>>", lambda e: self._redraw())
        ttk.Checkbutton(box_frame, text="Show outliers (Box)", variable=self.show_outliers).pack(anchor=tk.W, pady=(4, 0))
        ttk.Checkbutton(box_frame, text="Show legend", variable=self._show_legend,
                        command=self._redraw).pack(anchor=tk.W, pady=(2, 0))
        ttk.Checkbutton(box_frame, text="Connect medians", variable=self._connect_medians,
                        command=self._redraw).pack(anchor=tk.W, pady=(4, 0))
        ttk.Checkbutton(box_frame, text="Connect means", variable=self._connect_means,
                        command=self._redraw).pack(anchor=tk.W, pady=(2, 0))
        ttk.Label(box_frame, text="Median Line Style").pack(anchor=tk.W, pady=(4, 0))
        ttk.Combobox(box_frame, textvariable=self._median_linestyle,
                     values=["solid", "dashed", "dashdot", "dotted", "none"],
                     state="readonly").pack(fill=tk.X)
        self._slider_row(box_frame, "Median Marker Size", self._median_marker_size, 0, 15, "{:.0f}")
        self._slider_row(box_frame, "Edge / Line Width", self._edge_lw, 0.5, 5.0, "{:.1f}")
        self._black_edges_btn = ttk.Button(box_frame, text="Edges: Color",
                                           command=self._toggle_black_edges)
        self._black_edges_btn.pack(fill=tk.X, pady=(2, 4))
        ttk.Checkbutton(box_frame, text="Hold: keep existing data", variable=self.hold).pack(anchor=tk.W, pady=(4, 2))
        btn_row = ttk.Frame(box_frame)
        btn_row.pack(fill=tk.X, pady=(5, 0))
        self.add_btn = ttk.Button(btn_row, text="Add Data", command=self.add_box)
        self.add_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(btn_row, text="Clear", command=self.clear_plot).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(3, 0))

        appearance = ttk.LabelFrame(controls, text="Figure & Axes", padding=8)
        appearance.pack(fill=tk.X)
        self._entry(appearance, "Width (inches)", self.width_fig)
        self._entry(appearance, "Height (inches)", self.height_fig)
        ttk.Label(appearance, text="Font").pack(anchor=tk.W, pady=(4, 0))
        ttk.Combobox(appearance, textvariable=self.font_name,
                     values=["DejaVu Sans", "Times New Roman", "STIX", "Cambria",
                             "XITS Math", "cmr10", "Palatino Linotype", "Georgia",
                             "DejaVu Serif", "Microsoft YaHei",
                             "SimHei", "SimSun", "Noto Serif SC", "Source Han Serif CN"],
                     state="readonly").pack(fill=tk.X)
        self._entry(appearance, "Font Size", self.font_size)
        ttk.Label(appearance, text="Y Axis  (min — step — max, blank=auto)").pack(anchor=tk.W, pady=(5, 0))
        row = ttk.Frame(appearance)
        row.pack(fill=tk.X, pady=(1, 2))
        ttk.Entry(row, textvariable=self.ymin, width=8).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Label(row, text=" — ").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.y_tick_step, width=8).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Label(row, text=" — ").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=self.ymax, width=8).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Checkbutton(appearance, text="Hide last Y tick", variable=self.hide_last_ytick).pack(anchor=tk.W, pady=(0, 7))
        ttk.Button(appearance, text="Apply Figure Settings",
                   command=lambda: self._apply_appearance(from_user=True)).pack(fill=tk.X, pady=(0, 4))
        ttk.Button(appearance, text="Advanced Settings…", command=self._open_advanced).pack(fill=tk.X)

        self.figure = Figure(figsize=(9, 5.5), dpi=100)
        self.figure.set_tight_layout(False)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        toolbar = NavigationToolbar2Tk(self.canvas, chart_frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.X)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _color_combo(self, parent: ttk.Widget, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(4, 0))
        values = [f"{name}  {hexv}" for name, hexv in COLOR_PALETTE]
        combo = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", height=len(COLOR_PALETTE))
        combo.current(0)
        combo.pack(fill=tk.X)

    @staticmethod
    def _entry(parent: ttk.Widget, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(4, 0))
        ttk.Entry(parent, textvariable=variable).pack(fill=tk.X)

    def _slider_row(self, parent: ttk.Widget, label: str, variable: tk.DoubleVar,
                    from_: float, to: float, fmt: str = "{:.2f}") -> None:
        ttk.Label(parent, text=label).pack(anchor=tk.W, pady=(4, 0))
        row = ttk.Frame(parent)
        row.pack(fill=tk.X)
        val_label = ttk.Label(row, text=fmt.format(variable.get()), width=6)

        def on_move(_=None):
            val_label.config(text=fmt.format(variable.get()))

        ttk.Scale(row, from_=from_, to=to, variable=variable, command=on_move).pack(side=tk.LEFT, fill=tk.X, expand=True)
        val_label.pack(side=tk.LEFT, padx=(4, 0))

    def _on_width_changed(self, *_args) -> None:
        w = self.box_width.get()
        for b in self._boxes:
            b["width"] = w
        if self._boxes:
            self._redraw()

    def _toggle_black_edges(self) -> None:
        cur = not self._black_edges.get()
        self._black_edges.set(cur)
        self._black_edges_btn.config(text="Edges: Black" if cur else "Edges: Color")
        self._redraw()

    def _edge_color(self, b: dict) -> str:
        return "#000000" if self._black_edges.get() else b["color"]

    def _current_key(self) -> str:
        return f"{self.current_file}::{self.column.get()}"

    def _on_column_changed(self) -> None:
        self.box_label.set(self.column.get())
        if self._added_key is not None and self._current_key() != self._added_key:
            self._added_key = None
            self.add_btn.config(state=tk.NORMAL)

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
            messagebox.showerror("Load Failed", "Cannot parse this CSV.")
            return
        if data.empty or not len(data.columns):
            messagebox.showwarning("Empty", "CSV has no columns.")
            return
        self.data, self.current_file = data, path
        columns = [str(c) for c in data.columns]
        self.col_combo["values"] = columns
        default_col = next((c for c in columns if c in ("F_Q", "FQ", "Q_cov", "S_surv")), columns[0])
        self.column.set(default_col)
        self.box_label.set(default_col)
        self._added_key = None
        self.add_btn.config(state=tk.NORMAL)
        fname = path.split("/")[-1].split("\\")[-1]
        self.status.set(f"Loaded: {fname}  ({len(data)} rows, {used_encoding})")

    def add_box(self) -> None:
        if self.data is None:
            messagebox.showinfo("Info", "Please load a CSV first.")
            return
        col = self.column.get()
        if not col:
            messagebox.showinfo("Info", "Please select a column.")
            return
        key = self._current_key()
        if self._added_key == key:
            messagebox.showinfo("Duplicate", "This column has already been added.")
            return
        y = pd.to_numeric(self.data[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if y.empty:
            messagebox.showerror("Error", f"Column '{col}' has no numeric data.")
            return
        label = self.box_label.get().strip() or col
        color = self.box_color.get().split()[-1]
        width = self.box_width.get()
        stats = compute_box_stats(y.values)

        if not self.hold.get():
            self._boxes.clear()

        self._boxes.append({
            "kind": "distribution",
            "data": y.values,
            "label": label,
            "color": color,
            "alpha": 0.6,
            "width": width,
            "visible": True,
            "source_key": key,
            "stats": stats,
        })
        self._added_key = key
        self.add_btn.config(state=tk.DISABLED)
        self._redraw()
        fname = self.current_file.split("/")[-1].split("\\")[-1]
        self.status.set(f"Added '{label}' from {fname}  (N={stats['n']}, median={stats['med']:.4f})")

    def load_txt(self) -> None:
        """Load a structured TXT project with multiple distribution series."""
        if not _HAS_TXT:
            messagebox.showerror(
                "Unavailable",
                "The shared _txt_io module is missing from this folder.\n"
                "Please copy _txt_io.py alongside csvFIG.py.",
            )
            return
        path = filedialog.askopenfilename(
            title="Load TXT Project",
            filetypes=[("csvFIG TXT", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            payload = _pp_csvfig(_read_txt(path))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("TXT Load Failed", str(exc))
            return

        s = payload.get("settings", {})
        # Apply UI settings
        if "title" in s:
            self.plot_title.set(str(s["title"]))
        if "x_label" in s:
            self.x_label_var.set(str(s["x_label"]))
        if "y_label" in s:
            self.y_label_var.set(str(s["y_label"]))
        if "width" in s:
            try:
                self.width_fig.set(str(s["width"]))
            except Exception:
                pass
        if "height" in s:
            try:
                self.height_fig.set(str(s["height"]))
            except Exception:
                pass
        if "ymin" in s:
            self.ymin.set(str(s["ymin"]))
        if "ymax" in s:
            self.ymax.set(str(s["ymax"]))
        if "y_tick_step" in s:
            self.y_tick_step.set(str(s["y_tick_step"]))
        if "plot_type" in s:
            self.box_orientation.set(str(s["plot_type"]))
        if "show_outliers" in s:
            self.show_outliers.set(bool(s["show_outliers"]))

        # Replace data
        self._boxes.clear()
        for item in payload.get("series", []):
            data_arr = item["data"]
            stats = compute_box_stats(data_arr)
            self._boxes.append({
                "kind": "distribution",
                "data": data_arr,
                "label": item["label"],
                "color": item.get("color", COLOR_PALETTE[0][1]),
                "alpha": float(item.get("alpha", 0.6)),
                "width": float(item.get("width", 0.8)),
                "visible": True,
                "source_key": path + "::" + item["label"],
                "stats": stats,
            })
        self._added_key = None
        self.add_btn.config(state=tk.NORMAL)
        self._redraw()
        fname = path.split("/")[-1].split("\\")[-1]
        self.status.set(f"Loaded TXT: {fname}  ({len(self._boxes)} items)")


    def clear_plot(self) -> None:
        self._boxes.clear()
        self.ax.clear()
        self.plot_title.set("")
        self.x_label_var.set("")
        self.y_label_var.set("")
        self._added_key = None
        self.add_btn.config(state=tk.NORMAL)
        self._apply_appearance()
        self.status.set("Canvas cleared.")

    def save_project(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save Project", defaultextension=".cfig",
            filetypes=[("csvFIG Project", "*.cfig"), ("All files", "*.*")])
        if not path:
            return
        project = {
            "version": 1,
            "type": "csvFIG",
            "settings": {
                "plot_title": self.plot_title.get(),
                "x_label": self.x_label_var.get(),
                "y_label": self.y_label_var.get(),
                "width": self.width_fig.get(),
                "height": self.height_fig.get(),
                "font_name": self.font_name.get(),
                "font_size": self.font_size.get(),
                "ymin": self.ymin.get(),
                "ymax": self.ymax.get(),
                "y_tick_step": self.y_tick_step.get(),
                "hide_last_ytick": self.hide_last_ytick.get(),
                "grid_x": self.grid_x.get(),
                "grid_y": self.grid_y.get(),
                "plot_type": self.box_orientation.get(),
                "show_outliers": self.show_outliers.get(),
                "connect_medians": self._connect_medians.get(),
                "connect_means": self._connect_means.get(),
                "edge_lw": self._edge_lw.get(),
                "black_edges": self._black_edges.get(),
                "median_linestyle": self._median_linestyle.get(),
                "median_marker_size": self._median_marker_size.get(),
                "show_legend": self._show_legend.get(),
                "box_width": self.box_width.get(),
            },
            "boxes": [],
        }
        for b in self._boxes:
            raw = b.get("data")
            item = {
                "kind": "distribution",
                "label": b["label"],
                "color": b["color"],
                "visible": b.get("visible", True),
                "alpha": b.get("alpha", 0.6),
                "width": b.get("width", 0.8),
                "source_key": b.get("source_key", ""),
                "stats": b["stats"],
                "data": raw.tolist() if raw is not None else None,
            }
            project["boxes"].append(item)
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
            filetypes=[("csvFIG Project", "*.cfig"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                project = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load Failed", str(exc))
            return
        if project.get("type") != "csvFIG":
            messagebox.showerror("Wrong Format", "This is not a csvFIG project file.")
            return
        try:
            boxes = []
            for b in project.get("boxes", []):
                if b.get("data") is None:
                    raise ValueError("This project has no raw observations. Reload the original CSV or TXT file.")
                raw = np.asarray(b["data"], dtype=float)
                if raw.ndim != 1:
                    raise ValueError("Each distribution must be one-dimensional.")
                raw = raw[np.isfinite(raw)]
                if not raw.size:
                    raise ValueError("Each distribution must contain finite numeric observations.")
                boxes.append({**b, "data": raw, "stats": compute_box_stats(raw)})
        except (TypeError, ValueError, KeyError) as exc:
            messagebox.showerror("Load Failed", str(exc))
            return
        s = project.get("settings", {})
        self.plot_title.set(s.get("plot_title", ""))
        self.x_label_var.set(s.get("x_label", ""))
        self.y_label_var.set(s.get("y_label", ""))
        self.width_fig.set(s.get("width", "9"))
        self.height_fig.set(s.get("height", "5.5"))
        self.font_name.set(s.get("font_name", "DejaVu Sans"))
        self.font_size.set(s.get("font_size", "12"))
        self.ymin.set(s.get("ymin", ""))
        self.ymax.set(s.get("ymax", ""))
        self.y_tick_step.set(s.get("y_tick_step", ""))
        self.hide_last_ytick.set(s.get("hide_last_ytick", False))
        self.grid_x.set(s.get("grid_x", True))
        self.grid_y.set(s.get("grid_y", True))
        self.box_orientation.set(s.get("plot_type", "Box (V)"))
        self.show_outliers.set(s.get("show_outliers", True))
        self._connect_medians.set(s.get("connect_medians", False))
        self._connect_means.set(s.get("connect_means", False))
        self._edge_lw.set(s.get("edge_lw", 1.5))
        self._black_edges.set(s.get("black_edges", False))
        self._black_edges_btn.config(text="Edges: Black" if self._black_edges.get() else "Edges: Color")
        self._median_linestyle.set(s.get("median_linestyle", "solid"))
        self._median_marker_size.set(s.get("median_marker_size", 6.0))
        self._show_legend.set(s.get("show_legend", False))
        self.box_width.set(s.get("box_width", 0.8))
        self._boxes.clear()
        for b in boxes:
            raw = b["data"]
            self._boxes.append({
                "kind": "distribution",
                "data": raw,
                "label": b["label"],
                "color": b["color"],
                "alpha": b.get("alpha", 0.6),
                "width": b.get("width", 0.8),
                "visible": b.get("visible", True),
                "source_key": b.get("source_key", ""),
                "stats": b["stats"],
            })
        self._added_key = None
        self.add_btn.config(state=tk.NORMAL)
        self._redraw()
        fname = path.split("/")[-1].split("\\")[-1]
        self.status.set(f"Project loaded: {fname}  ({len(self._boxes)} items)")

    def _redraw(self) -> None:
        self.ax.clear()
        plot_type = self.box_orientation.get()
        visible = [b for b in self._boxes if b.get("visible", True)]
        if not visible:
            self.canvas.draw()
            return
        positions = list(range(1, len(visible) + 1))
        labels = [b["label"] for b in visible]

        if plot_type in ("Box (V)", "Box (H)"):
            self._draw_boxplot(visible, positions, labels, plot_type == "Box (V)")
        elif plot_type == "Bar+Err":
            self._draw_bar_err(visible, positions, labels)
        elif plot_type == "Violin":
            self._draw_violin(visible, positions, labels)
        elif plot_type == "Violin+Box":
            self._draw_violin_box(visible, positions, labels)

        if self._connect_medians.get() and len(visible) > 1:
            meds = [b["stats"]["med"] for b in visible]
            self._draw_stat_connection(positions, meds, "o", plot_type == "Box (H)")

        if self._connect_means.get() and len(visible) > 1:
            means = [b["stats"]["mean"] for b in visible]
            self._draw_stat_connection(positions, means, "^", plot_type == "Box (H)")

        if self._show_legend.get():
            handles = []
            ms = self._median_marker_size.get()
            ls = self._median_linestyle.get()
            if self._connect_medians.get() and len(visible) > 1:
                handles.append(Line2D([0], [0], color="#000000",
                                      linestyle="none" if ls == "none" else ls,
                                      linewidth=self._edge_lw.get(),
                                      marker="o" if ms > 0 else "",
                                      markersize=ms,
                                      markerfacecolor="#000000",
                                      markeredgecolor="#000000",
                                      label="Median"))
            if self._connect_means.get() and len(visible) > 1:
                handles.append(Line2D([0], [0], color="#000000",
                                      linestyle="none" if ls == "none" else ls,
                                      linewidth=self._edge_lw.get(),
                                      marker="^" if ms > 0 else "",
                                      markersize=ms,
                                      markerfacecolor="#000000",
                                      markeredgecolor="#000000",
                                      label="Mean"))
            if self.show_outliers.get() and plot_type in ("Box (V)", "Box (H)", "Violin+Box"):
                handles.append(Line2D([0], [0], color="none",
                                      linestyle="none",
                                      marker="o", markersize=4,
                                      markerfacecolor="#888888",
                                      markeredgecolor="#555555",
                                      label="Outliers"))
            if handles:
                self.ax.legend(handles=handles, loc="upper right",
                               framealpha=0.9, fontsize=int(self.font_size.get()))

        if self.plot_title.get().strip():
            self.ax.set_title(self.plot_title.get().strip())
        if self.x_label_var.get().strip():
            self.ax.set_xlabel(self.x_label_var.get().strip())
        if self.y_label_var.get().strip():
            self.ax.set_ylabel(self.y_label_var.get().strip())
        self._apply_appearance()

    def _draw_stat_connection(self, positions, values, marker: str, horizontal: bool) -> None:
        ms = self._median_marker_size.get()
        linestyle = self._median_linestyle.get()
        x_data, y_data = (values, positions) if horizontal else (positions, values)
        line = Line2D(
            x_data, y_data,
            color="#000000",
            linewidth=self._edge_lw.get(),
            linestyle="none" if linestyle == "none" else linestyle,
            marker=marker if ms > 0 else "",
            markersize=ms,
            markerfacecolor="#000000",
            markeredgecolor="#000000",
            zorder=10,
        )
        self.ax.add_line(line)

    def _draw_boxplot(self, visible, positions, labels, vertical) -> None:
        bp_stats = []
        for b in visible:
            s = b["stats"]
            bp_stats.append({
                "med": s["med"], "q1": s["q1"], "q3": s["q3"],
                "whislo": s["whislo"], "whishi": s["whishi"],
                "fliers": s.get("fliers", []), "mean": s["mean"],
            })
        widths = [b["width"] for b in visible]
        showflier = bool(self.show_outliers.get())
        bp = self.ax.bxp(bp_stats, vert=vertical, patch_artist=True,
                         widths=widths, showfliers=showflier)
        if vertical:
            self.ax.set_xticks(positions)
            self.ax.set_xticklabels(labels)
        else:
            self.ax.set_yticks(positions)
            self.ax.set_yticklabels(labels)
        for patch, box in zip(bp["boxes"], visible):
            a = box.get("alpha", 0.6)
            patch.set_facecolor(mcolors.to_rgba(box["color"], alpha=a))
            patch.set_edgecolor(self._edge_color(box))
            patch.set_linewidth(self._edge_lw.get())
        for element in ["whiskers", "caps"]:
            for line in bp.get(element, []):
                line.set_color("#333333")
                line.set_linewidth(self._edge_lw.get())
        for med in bp.get("medians", []):
            med.set_color("#000000")
            med.set_linewidth(self._edge_lw.get())
        for flier in bp.get("fliers", []):
            flier.set_marker("o")
            flier.set_markerfacecolor("#888888")
            flier.set_markeredgecolor("#555555")
            flier.set_markersize(4)
            flier.set_alpha(0.5)

    def _draw_bar_err(self, visible, positions, labels) -> None:
        means = [b["stats"]["mean"] for b in visible]
        whislo = [b["stats"]["whislo"] for b in visible]
        whishi = [b["stats"]["whishi"] for b in visible]
        err_lo = [m - lo for m, lo in zip(means, whislo)]
        err_hi = [hi - m for m, hi in zip(means, whishi)]
        widths = [b["width"] for b in visible]
        colors = [mcolors.to_rgba(b["color"], alpha=b.get("alpha", 0.6)) for b in visible]
        edge_colors = [self._edge_color(b) for b in visible]
        lw = self._edge_lw.get()

        self.ax.bar(positions, means, width=widths, color=colors,
                     edgecolor=edge_colors, linewidth=lw, zorder=2)
        self.ax.errorbar(positions, means, yerr=[err_lo, err_hi],
                          fmt="none", ecolor="#333333", capsize=5,
                          linewidth=lw, zorder=3)
        self.ax.set_xticks(positions)
        self.ax.set_xticklabels(labels)

    def _draw_violin_body(self, data, pos, width, color, alpha,
                          edge_color, lw, zorder=1) -> None:
        """Draw a single violin using custom KDE."""
        n = len(data)
        if n < 2:
            return
        if np.ptp(data) == 0:
            self.ax.plot([pos - width * 0.5, pos + width * 0.5], [data[0], data[0]],
                         color=edge_color, linewidth=lw, zorder=zorder)
            return
        kde = gaussian_kde(data)
        d_min, d_max = float(data.min()), float(data.max())
        data_range = d_max - d_min
        if data_range <= 0:
            data_range = max(abs(d_min) * 0.02, 1e-6)
        bandwidth = float(kde.factor * np.std(data, ddof=1))
        pad = max(data_range * 0.08, bandwidth * 3.0, 1e-9)
        y_eval = np.linspace(d_min - pad, d_max + pad, 600)
        density = kde(y_eval)
        density[0] = 0.0
        density[-1] = 0.0
        max_d = density.max()
        if max_d > 0:
            hw = width * 0.5 * (density / max_d)
        else:
            hw = np.zeros_like(density)
        self.ax.fill_betweenx(y_eval, pos - hw, pos + hw,
                               facecolor=mcolors.to_rgba(color, alpha=alpha),
                               edgecolor=edge_color,
                               linewidth=lw, zorder=zorder)

    def _draw_violin(self, visible, positions, labels) -> None:
        lw = self._edge_lw.get()
        widths = [b["width"] for b in visible]
        for i, b in enumerate(visible):
            data = self._get_data(b)
            self._draw_violin_body(data, positions[i], widths[i],
                                   b["color"], b.get("alpha", 0.6),
                                   self._edge_color(b), lw)
        for i, b in enumerate(visible):
            med = b["stats"]["med"]
            pos = positions[i]
            hw = widths[i] * 0.45
            self.ax.plot([pos - hw, pos + hw], [med, med],
                         color="#000000", linewidth=lw, zorder=5)
        self.ax.set_xticks(positions)
        self.ax.set_xticklabels(labels)

    def _draw_violin_box(self, visible, positions, labels) -> None:
        lw = self._edge_lw.get()
        widths = [b["width"] for b in visible]
        for i, b in enumerate(visible):
            data = self._get_data(b)
            self._draw_violin_body(data, positions[i], widths[i],
                                   b["color"], b.get("alpha", 0.3),
                                   self._edge_color(b), lw * 0.7, zorder=1)
        # Box layer on top (narrower)
        bp_stats = []
        for b in visible:
            s = b["stats"]
            bp_stats.append({
                "med": s["med"], "q1": s["q1"], "q3": s["q3"],
                "whislo": s["whislo"], "whishi": s["whishi"],
                "fliers": s.get("fliers", []), "mean": s["mean"],
            })
        box_widths = [b["width"] * 0.3 for b in visible]
        showflier = bool(self.show_outliers.get())
        bp = self.ax.bxp(bp_stats, vert=True, patch_artist=True,
                         positions=positions, widths=box_widths, showfliers=showflier)
        for patch, box in zip(bp["boxes"], visible):
            patch.set_facecolor("white")
            patch.set_edgecolor(self._edge_color(box))
            patch.set_linewidth(lw)
        for element in ["whiskers", "caps"]:
            for line in bp.get(element, []):
                line.set_color("#333333")
                line.set_linewidth(lw)
        for med in bp.get("medians", []):
            med.set_color("#000000")
            med.set_linewidth(lw)
        for flier in bp.get("fliers", []):
            flier.set_marker("o")
            flier.set_markerfacecolor("#888888")
            flier.set_markeredgecolor("#555555")
            flier.set_markersize(4)
            flier.set_alpha(0.5)
        self.ax.set_xticks(positions)
        self.ax.set_xticklabels(labels)

    @staticmethod
    def _get_data(b: dict) -> np.ndarray:
        """Return recorded observations without generating replacement data."""
        return np.asarray(b["data"], dtype=float)

    # ---- Advanced Settings ----

    def _open_advanced(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Advanced Settings")
        dlg.geometry("560x760")
        dlg.transient(self)
        dlg.grab_set()

        # Scrolled area
        scroll_canvas = tk.Canvas(dlg, highlightthickness=0)
        vbar = ttk.Scrollbar(dlg, orient=tk.VERTICAL, command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = ttk.Frame(scroll_canvas)
        inner_win = scroll_canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner(_=None):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        def _on_canvas(event):
            scroll_canvas.itemconfig(inner_win, width=event.width)
        def _on_wheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        inner.bind("<Configure>", _on_inner)
        scroll_canvas.bind("<Configure>", _on_canvas)
        dlg.bind("<MouseWheel>", _on_wheel)

        # Title
        ttk.Label(inner, text="Plot Title").pack(anchor=tk.W, pady=(12, 2))
        ttk.Entry(inner, textvariable=self.plot_title, width=60).pack(fill=tk.X, padx=12)

        # Axis labels
        ttk.Label(inner, text="X-Axis Label").pack(anchor=tk.W, pady=(8, 2))
        x_var = tk.StringVar(value=self.x_label_var.get())
        ttk.Entry(inner, textvariable=x_var, width=60).pack(fill=tk.X, padx=12)

        ttk.Label(inner, text="Y-Axis Label").pack(anchor=tk.W, pady=(8, 2))
        y_var = tk.StringVar(value=self.y_label_var.get())
        ttk.Entry(inner, textvariable=y_var, width=60).pack(fill=tk.X, padx=12)

        # Font
        ttk.Label(inner, text="Font Name").pack(anchor=tk.W, pady=(8, 2))
        ttk.Entry(inner, textvariable=self.font_name, width=60).pack(fill=tk.X, padx=12)

        # Grid
        grid_frame = ttk.LabelFrame(inner, text="Grid", padding=8)
        grid_frame.pack(fill=tk.X, padx=12, pady=(6, 4))
        ttk.Checkbutton(grid_frame, text="Vertical (X)", variable=self.grid_x).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Checkbutton(grid_frame, text="Horizontal (Y)", variable=self.grid_y).pack(side=tk.LEFT)

        # Global alpha
        ttk.Label(inner, text="Global Box Alpha (0 = transparent, 1 = opaque)").pack(anchor=tk.W, pady=(6, 2))
        alpha_row = ttk.Frame(inner)
        alpha_row.pack(fill=tk.X, padx=12, pady=(0, 4))
        alpha_val = tk.DoubleVar(value=0.6)
        alpha_label = ttk.Label(alpha_row, text="0.60", width=5)
        def _on_alpha(_=None):
            alpha_label.config(text=f"{alpha_val.get():.2f}")
        ttk.Scale(alpha_row, from_=0.0, to=1.0, variable=alpha_val, command=_on_alpha).pack(side=tk.LEFT, fill=tk.X, expand=True)
        alpha_label.pack(side=tk.LEFT, padx=(4, 0))

        # Data list with visibility, labels, colors, and reordering
        ttk.Label(inner, text=f"Data Items on Plot  ({len(self._boxes)})").pack(anchor=tk.W, pady=(10, 2))
        list_frame = ttk.Frame(inner)
        list_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        box_vars = []  # list of (visible_var, label_var)
        for i, box in enumerate(self._boxes):
            kv = tk.BooleanVar(value=box.get("visible", True))
            lv = tk.StringVar(value=box["label"])
            box_vars.append((kv, lv))

            ttk.Checkbutton(list_frame, variable=kv).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Label(list_frame, text=f"#{i+1}", width=4).grid(row=i, column=1, sticky=tk.W, pady=2)
            entry = ttk.Entry(list_frame, textvariable=lv, width=28)
            entry.grid(row=i, column=2, sticky=tk.EW, pady=2)

            # Color swatch
            color_btn = tk.Button(list_frame, text="", bg=box["color"], width=2)
            color_btn.config(command=lambda idx=i, btn=color_btn: self._pick_color_for(idx, btn))
            color_btn.grid(row=i, column=3, padx=(4, 2), pady=2)

            # Up/Down buttons
            btn_col = ttk.Frame(list_frame)
            btn_col.grid(row=i, column=4, padx=(4, 0), pady=2)
            up_btn = ttk.Button(btn_col, text="↑", width=2,
                                command=lambda idx=i: self._move_box_up(idx, dlg))
            down_btn = ttk.Button(btn_col, text="↓", width=2,
                                  command=lambda idx=i: self._move_box_down(idx, dlg))
            up_btn.pack(side=tk.LEFT, padx=(0, 1))
            down_btn.pack(side=tk.LEFT)
            if i == 0:
                up_btn.config(state=tk.DISABLED)
            if i == len(self._boxes) - 1:
                down_btn.config(state=tk.DISABLED)

        list_frame.columnconfigure(2, weight=1)

        if not self._boxes:
            ttk.Label(list_frame, text="(no data on plot - add some first)", foreground="#888").grid(
                row=0, column=0, columnspan=5, pady=8)

        def apply_settings():
            self.x_label_var.set(x_var.get().strip())
            self.y_label_var.set(y_var.get().strip())
            # Apply global alpha to all boxes
            ga = alpha_val.get()
            for box in self._boxes:
                box["alpha"] = ga
            # Update visibility and labels
            for box, (kv, lv) in zip(self._boxes, box_vars):
                box["visible"] = kv.get()
                box["label"] = lv.get().strip()
            dlg.destroy()
            self._redraw()

        def cancel():
            dlg.destroy()

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, pady=12, padx=12)
        ttk.Button(btn_frame, text="Apply", command=apply_settings).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side=tk.RIGHT)

    def _pick_color_for(self, idx: int, btn_widget: tk.Button) -> None:
        """Open a color picker dialog with palette swatches + custom color."""
        current = self._boxes[idx]["color"]
        picker = tk.Toplevel(self)
        picker.title("Pick Color")
        picker.geometry("320x420")
        picker.transient(self)
        picker.grab_set()

        selected = tk.StringVar(value=current)

        # Palette swatches
        ttk.Label(picker, text="Palette", padding=(10, 6)).pack(anchor=tk.W)
        pal_frame = ttk.Frame(picker, padding=(10, 0))
        pal_frame.pack(fill=tk.X)

        COLS = 6
        for i, (name, hexv) in enumerate(COLOR_PALETTE):
            row, col = divmod(i, COLS)
            btn = tk.Button(pal_frame, width=4, height=2, bg=hexv,
                            command=lambda h=hexv: selected.set(h))
            btn.grid(row=row, column=col, padx=2, pady=2)
            if hexv == current:
                btn.config(relief="solid", bd=3)

        # Custom color entry
        ttk.Label(picker, text="Custom", padding=(10, 10)).pack(anchor=tk.W)
        custom_frame = ttk.Frame(picker, padding=(10, 0))
        custom_frame.pack(fill=tk.X)
        custom_entry = ttk.Entry(custom_frame, textvariable=selected, width=14)
        custom_entry.pack(side=tk.LEFT, padx=(0, 6))

        def _open_system_picker():
            result = colorchooser.askcolor(color=selected.get(), title="Choose Color")
            if result and result[1]:
                selected.set(result[1])

        ttk.Button(custom_frame, text="Picker…", command=_open_system_picker).pack(side=tk.LEFT)

        # Preview
        ttk.Label(picker, text="Preview", padding=(10, 10)).pack(anchor=tk.W)
        preview_frame = ttk.Frame(picker, padding=(10, 0))
        preview_frame.pack(fill=tk.X)
        preview_swatch = tk.Label(preview_frame, width=30, height=2, bg=current,
                                  relief="sunken", bd=1)
        preview_swatch.pack(fill=tk.X)

        def _update_preview(*_):
            try:
                c = selected.get()
                # validate hex color
                if c.startswith("#") and len(c) in (4, 7, 9):
                    preview_swatch.config(bg=c)
            except Exception:
                pass
        selected.trace_add("write", _update_preview)

        def _ok():
            c = selected.get().strip()
            if not c:
                return
            try:
                mcolors.to_rgba(c)
            except ValueError:
                messagebox.showerror("Invalid Color", f"'{c}' is not a valid color.", parent=picker)
                return
            self._boxes[idx]["color"] = c
            btn_widget.config(bg=c)
            picker.destroy()
            self._redraw()

        btn_frame = ttk.Frame(picker)
        btn_frame.pack(fill=tk.X, pady=16, padx=10, side=tk.BOTTOM)
        ttk.Button(btn_frame, text="OK", command=_ok).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_frame, text="Cancel", command=picker.destroy).pack(side=tk.RIGHT)

    def _move_box_up(self, idx: int, dlg: tk.Toplevel) -> None:
        if idx <= 0:
            return
        self._boxes[idx - 1], self._boxes[idx] = self._boxes[idx], self._boxes[idx - 1]
        self._redraw()
        # Rebuild the dialog
        dlg.destroy()
        self._open_advanced()

    def _move_box_down(self, idx: int, dlg: tk.Toplevel) -> None:
        if idx >= len(self._boxes) - 1:
            return
        self._boxes[idx], self._boxes[idx + 1] = self._boxes[idx + 1], self._boxes[idx]
        self._redraw()
        dlg.destroy()
        self._open_advanced()


    def _optional_float(self, variable: tk.StringVar, name: str) -> float | None:
        value = variable.get().strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be numeric or blank.") from exc

    def _apply_appearance(self, redraw: bool = True, from_user: bool = False) -> None:
        try:
            # Only update last-box label when user explicitly clicks Apply from main panel
            if from_user and self._boxes:
                new_label = self.box_label.get().strip()
                if new_label and new_label != self._boxes[-1]["label"]:
                    self._boxes[-1]["label"] = new_label
                    self._redraw()
                    return
            width, height = float(self.width_fig.get()), float(self.height_fig.get())
            font_size = float(self.font_size.get())
            if width <= 0 or height <= 0 or font_size <= 0:
                raise ValueError("Figure size and font size must be > 0.")
            ymin = self._optional_float(self.ymin, "Y range")
            ymax = self._optional_float(self.ymax, "Y range")
            vertical = self.box_orientation.get() != "Box (H)"
            if ymin is not None or ymax is not None:
                if vertical:
                    self.ax.set_ylim(bottom=ymin, top=ymax)
                else:
                    self.ax.set_xlim(left=ymin, right=ymax)
            else:
                if vertical:
                    self.ax.autoscale(enable=True, axis="y", tight=False)
                else:
                    self.ax.autoscale(enable=True, axis="x", tight=False)
            y_step = self._optional_float(self.y_tick_step, "Y tick step")
            if y_step is not None and y_step > 0:
                if vertical:
                    self.ax.yaxis.set_major_locator(MultipleLocator(y_step))
                else:
                    self.ax.xaxis.set_major_locator(MultipleLocator(y_step))
            self.ax.grid(False)
            if self.grid_x.get():
                self.ax.grid(True, axis="x", alpha=0.25)
            if self.grid_y.get():
                self.ax.grid(True, axis="y", alpha=0.25)
            self.figure.set_size_inches(width, height, forward=True)
            self._reset_axes_layout()
            font = self.font_name.get().strip() or "DejaVu Sans"
            for item in [self.ax.title, self.ax.xaxis.label, self.ax.yaxis.label]:
                item.set_fontname(font)
                item.set_fontsize(font_size)
            for lbl in self.ax.get_xticklabels() + self.ax.get_yticklabels():
                lbl.set_fontname(font)
                lbl.set_fontsize(font_size)
            legend = self.ax.get_legend()
            if legend:
                for text in legend.get_texts():
                    text.set_fontname(font)
                    text.set_fontsize(font_size * 0.9)
            if redraw:
                self.canvas.draw()
                if self.hide_last_ytick.get():
                    axis = self.ax.yaxis if vertical else self.ax.xaxis
                    ticks = axis.get_majorticklocs()
                    if len(ticks) > 0:
                        last_t = ticks[-1]
                        cur_fmt = axis.get_major_formatter()
                        if not isinstance(cur_fmt, FuncFormatter):
                            self._orig_y_fmt = cur_fmt
                        _orig = self._orig_y_fmt if self._orig_y_fmt else cur_fmt
                        def _tfmt(val, pos, _l=last_t, _o=_orig):
                            if abs(val - _l) < 1e-9:
                                return ""
                            if _o:
                                try:
                                    return _o(val, pos)
                                except Exception:
                                    pass
                            return f"{val:g}"
                        axis.set_major_formatter(FuncFormatter(_tfmt))
                else:
                    if self._orig_y_fmt is not None:
                        if vertical:
                            self.ax.yaxis.set_major_formatter(self._orig_y_fmt)
                        else:
                            self.ax.xaxis.set_major_formatter(self._orig_y_fmt)
                        self._orig_y_fmt = None
                self.canvas.draw()
        except ValueError as exc:
            if redraw:
                messagebox.showerror("Invalid Setting", str(exc))

    def _reset_axes_layout(self) -> None:
        self.figure.subplots_adjust(left=0.12, right=0.94, bottom=0.14, top=0.90)


if __name__ == "__main__":
    CsvFigApp().mainloop()
