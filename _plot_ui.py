"""Shared font loading, clean canvas resizing, and figure settings dialogs."""
from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib import font_manager
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.transforms import Bbox

PREVIEW_BACKGROUND = "#e5e7eb"
LEGEND_LOCATIONS = [
    "best", "upper right", "upper left", "lower left", "lower right", "right",
    "center left", "center right", "lower center", "upper center", "center",
    "outside upper", "outside lower", "outside right",
]


def register_project_fonts() -> str:
    """Register optional local fonts without installing them in the OS."""
    folder = Path(__file__).resolve().parent / "fonts"
    for path in sorted(folder.glob("*")):
        if path.suffix.lower() in (".ttf", ".otf", ".ttc"):
            try:
                font_manager.fontManager.addfont(str(path))
            except (OSError, RuntimeError, ValueError):
                continue
    families = {entry.name for entry in font_manager.fontManager.ttflist}
    return "TimesSimSun" if "TimesSimSun" in families else "DejaVu Sans"


DEFAULT_FONT = register_project_fonts()
FONT_CHOICES = list(dict.fromkeys([
    DEFAULT_FONT, "TimesSimSun", "Times New Roman", "SimSun", "Microsoft YaHei",
    "SimHei", "STIX", "Cambria", "DejaVu Serif", "DejaVu Sans", "Noto Serif SC",
    "Source Han Serif CN", "Georgia", "Palatino Linotype",
]))


def font_family(name: str) -> list[str]:
    families = {entry.name for entry in font_manager.fontManager.ttflist}
    if name == "TimesSimSun" and name not in families:
        return [f for f in ("Times New Roman", "SimSun", "DejaVu Serif") if f in families]
    return [name or DEFAULT_FONT]


def legend_options(location: str) -> dict:
    locations = {
        "outside upper": ("lower center", (0.5, 1.02)),
        "outside lower": ("upper center", (0.5, -0.15)),
        "outside right": ("center left", (1.02, 0.5)),
    }
    if location in locations:
        loc, anchor = locations[location]
        return {"loc": loc, "bbox_to_anchor": anchor}
    return {"loc": location or "best"}


def project_axes_size(settings: dict, distribution: bool = False) -> tuple[str, str]:
    """Convert legacy whole-figure dimensions to their former axes dimensions."""
    width, height = settings.get("width", "9"), settings.get("height", "5.5")
    if settings.get("size_mode") == "axes":
        return str(width), str(height)
    location = settings.get("legend_loc", "best")
    visible = settings.get("show_legend", False) if distribution else not settings.get("hide_legend", False)
    x_fraction = 0.66 if visible and location == "outside right" else 0.82
    y_fraction = ((0.66 if distribution else 0.68) if visible and location == "outside lower" else
                  0.68 if visible and location == "outside upper" else 0.76)
    return f"{float(width) * x_fraction:.6g}", f"{float(height) * y_fraction:.6g}"


class PlotToolbar(NavigationToolbar2Tk):
    """Route the layout button to the axes settings used by automatic layout."""
    def __init__(self, canvas, master, settings_command, **kwargs):
        self.settings_command = settings_command
        super().__init__(canvas, master, **kwargs)

    def configure_subplots(self):
        return self.settings_command()


class PlotCanvas(FigureCanvasTkAgg):
    """Keep the axes size in inches; grow the figure to enclose its decorations.

    Layout is measured at export DPI. Only the preview DPI is reduced when the
    complete figure is larger than the available gray viewport.
    """
    def __init__(self, figure, master):
        self.requested_inches = tuple(figure.get_size_inches())
        self.total_inches = self.requested_inches
        self.base_dpi = figure.dpi
        self.legend_location = "best"
        self._drawing = False
        super().__init__(figure, master=master)
        self.get_tk_widget().place(x=0, y=0)
        master.bind("<Configure>", self._fit, add="+")

    def set_size_inches(self, width: float, height: float) -> None:
        self.requested_inches = (width, height)
        self.draw_idle()

    def _fit(self, event=None):
        self.draw_idle()

    def resize(self, event):
        # Tk Configure events describe the preview, never the requested axes.
        self.draw_idle()

    def _position_axes(self, ax, margins):
        left, right, bottom, top = margins
        width, height = self.requested_inches
        self.total_inches = (left + width + right, bottom + height + top)
        self.figure.set_size_inches(*self.total_inches, forward=False)
        self.figure.subplots_adjust(
            left=left / self.total_inches[0], right=(left + width) / self.total_inches[0],
            bottom=bottom / self.total_inches[1], top=(bottom + height) / self.total_inches[1])

    def _place_outside_legend(self, ax, renderer):
        legend = ax.get_legend()
        if legend is None or not legend.get_visible():
            return
        location = self.legend_location
        if not location.startswith("outside "):
            return
        # Anchor beyond the tick labels, axis labels and title, not just the spine.
        bounds = ax.get_tightbbox(renderer, bbox_extra_artists=[])
        area = ax.get_window_extent(renderer)
        gap = self.base_dpi * 0.12
        anchors = {
            "outside upper": (0.5, (bounds.y1 - area.y0 + gap) / area.height),
            "outside lower": (0.5, (bounds.y0 - area.y0 - gap) / area.height),
            "outside right": ((bounds.x1 - area.x0 + gap) / area.width, 0.5),
        }
        legend.set_bbox_to_anchor(anchors[location], transform=ax.transAxes)

    def _layout(self):
        self.figure.set_dpi(self.base_dpi)
        if not self.figure.axes:
            return
        ax = self.figure.axes[0]
        padding = 0.12  # inches, also covers small raster/vector font metric differences
        margins = (padding,) * 4
        self._position_axes(ax, margins)
        labels = ax.get_xticklabels()
        for label in labels:
            label.set_rotation(0)
            label.set_ha("center")
            label.set_rotation_mode("anchor")
        FigureCanvasAgg.draw(self)
        renderer = self.get_renderer()
        low, high = sorted(ax.get_xlim())
        visible_labels = [label for label in ax.get_xticklabels()
                          if label.get_visible() and label.get_text()
                          and low <= label.get_position()[0] <= high]
        bounds = sorted((label.get_window_extent(renderer) for label in visible_labels), key=lambda box: box.x0)
        if any(left.x1 + 8 > right.x0 for left, right in zip(bounds, bounds[1:])):
            for label in ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha("right")

        for _ in range(4):
            FigureCanvasAgg.draw(self)
            renderer = self.get_renderer()
            self._place_outside_legend(ax, renderer)
            area = ax.get_window_extent(renderer)
            boxes = [ax.get_tightbbox(renderer)]
            legend = ax.get_legend()
            if legend is not None and legend.get_visible():
                boxes.append(legend.get_window_extent(renderer))
            tight = Bbox.union([box for box in boxes if box is not None])
            margins = (
                padding + max(0, area.x0 - tight.x0) / self.base_dpi,
                padding + max(0, tight.x1 - area.x1) / self.base_dpi,
                padding + max(0, area.y0 - tight.y0) / self.base_dpi,
                padding + max(0, tight.y1 - area.y1) / self.base_dpi,
            )
            self._position_axes(ax, margins)

    def _fit_preview(self):
        width, height = self.total_inches
        parent = self.get_tk_widget().master
        available_w = parent.winfo_width()
        available_h = parent.winfo_height()
        scale = 1.0
        if available_w > 1 and available_h > 1:
            scale = min(1.0, available_w / (width * self.base_dpi), available_h / (height * self.base_dpi))
        self.figure.set_dpi(self.base_dpi * max(scale, 0.01))
        self.figure.set_size_inches(width, height, forward=False)
        pixels_w = max(1, int(width * self.figure.dpi))
        pixels_h = max(1, int(height * self.figure.dpi))
        self.get_tk_widget().place(x=0, y=0, width=pixels_w, height=pixels_h)
        if self._tkphoto.width() != pixels_w or self._tkphoto.height() != pixels_h:
            # The backend replaces the old image instead of stacking new images.
            super().resize(SimpleNamespace(width=pixels_w, height=pixels_h))
            self.figure.set_size_inches(width, height, forward=False)

    def draw(self):
        if self._drawing:
            return
        self._drawing = True
        try:
            self._layout()
            self._fit_preview()
            super().draw()
        finally:
            self._drawing = False

    def print_figure(self, *args, **kwargs):
        # Apply pending settings before the toolbar or Figure.savefig exports.
        self.draw()
        return super().print_figure(*args, **kwargs)


def open_figure_settings(app, distribution: bool = False):
    existing = getattr(app, "_figure_dialog", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        return existing
    dialog = tk.Toplevel(app)
    app._figure_dialog = dialog
    dialog.title("Figure & Axes")
    app.update_idletasks()
    left = max(0, app.winfo_rootx() + (app.winfo_width() - 510) // 2)
    top = max(0, app.winfo_rooty() + (app.winfo_height() - 540) // 2)
    dialog.geometry(f"510x540+{left}+{top}")
    dialog.resizable(False, False)
    dialog.transient(app)
    dialog.grab_set()
    book = ttk.Notebook(dialog)
    book.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
    tabs = {}
    for title in ("Plot Area & Font", "Axes & Labels", "Legend"):
        tab = ttk.Frame(book, padding=14)
        tab.columnconfigure(1, weight=1)
        book.add(tab, text=title)
        tabs[title] = tab

    names = {
        "width": "width_fig" if distribution else "width",
        "height": "height_fig" if distribution else "height",
        "font_name": "font_name", "font_size": "font_size", "plot_title": "plot_title",
        "ymin": "ymin", "ymax": "ymax", "y_tick_step": "y_tick_step",
        "hide_last_ytick": "hide_last_ytick", "grid_x": "grid_x", "grid_y": "grid_y",
        "legend_loc": "legend_loc", "legend_ncol": "legend_ncol",
    }
    if not distribution:
        for name in ("xmin", "xmax", "x_tick_step", "hide_last_xtick", "hide_legend", "hide_original_legend"):
            names[name] = name
    values = {}
    for key, attribute in names.items():
        current = getattr(app, attribute).get()
        values[key] = tk.BooleanVar(dialog, current) if isinstance(current, bool) else tk.StringVar(dialog, str(current))
    values["x_label"] = tk.StringVar(dialog, app.x_label_var.get() if distribution else app.ax.get_xlabel())
    values["y_label"] = tk.StringVar(dialog, app.y_label_var.get() if distribution else app.ax.get_ylabel())
    if distribution:
        values["show_legend"] = tk.BooleanVar(dialog, app._show_legend.get())

    def entry(tab, row, label, key):
        ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=7)
        ttk.Entry(tab, textvariable=values[key]).grid(row=row, column=1, sticky="ew", pady=7)

    canvas = tabs["Plot Area & Font"]
    entry(canvas, 0, "Axes Width (inches)", "width")
    entry(canvas, 1, "Axes Height (inches)", "height")
    ttk.Label(canvas, text="Font").grid(row=2, column=0, sticky="w", pady=7)
    ttk.Combobox(canvas, textvariable=values["font_name"], values=FONT_CHOICES).grid(row=2, column=1, sticky="ew", pady=7)
    entry(canvas, 3, "Font Size", "font_size")
    ttk.Label(canvas, text="Figure margins automatically fit labels and legends.",
              wraplength=400).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))
    axes = tabs["Axes & Labels"]
    entry(axes, 0, "Plot Title", "plot_title")
    entry(axes, 1, "X-Axis Label", "x_label")
    entry(axes, 2, "Y-Axis Label", "y_label")
    row = 3
    for axis in (("y",) if distribution else ("x", "y")):
        title = "Value axis" if distribution else f"{axis.upper()} Axis"
        ttk.Label(axes, text=f"{title}: min / step / max").grid(row=row, column=0, columnspan=2, sticky="w", pady=(9, 3))
        line = ttk.Frame(axes)
        line.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
        for column, key in enumerate((f"{axis}min", f"{axis}_tick_step", f"{axis}max")):
            line.columnconfigure(column, weight=1)
            ttk.Entry(line, textvariable=values[key], width=10).grid(row=0, column=column, sticky="ew", padx=(0, 6))
        ttk.Checkbutton(axes, text=f"Hide last {title.lower()} tick", variable=values[f"hide_last_{axis}tick"]).grid(row=row + 2, column=0, columnspan=2, sticky="w", pady=3)
        row += 3
    grids = ttk.Frame(axes)
    grids.grid(row=row, column=0, columnspan=2, sticky="w", pady=8)
    ttk.Checkbutton(grids, text="X grid", variable=values["grid_x"]).pack(side=tk.LEFT, padx=(0, 20))
    ttk.Checkbutton(grids, text="Y grid", variable=values["grid_y"]).pack(side=tk.LEFT)
    legend = tabs["Legend"]
    ttk.Label(legend, text="Location").grid(row=0, column=0, sticky="w", pady=7)
    ttk.Combobox(legend, textvariable=values["legend_loc"], values=LEGEND_LOCATIONS, state="readonly").grid(row=0, column=1, sticky="ew", pady=7)
    ttk.Label(legend, text="Columns").grid(row=1, column=0, sticky="w", pady=7)
    ttk.Spinbox(legend, from_=1, to=10, textvariable=values["legend_ncol"], width=8).grid(row=1, column=1, sticky="w", pady=7)
    if distribution:
        ttk.Checkbutton(legend, text="Show legend", variable=values["show_legend"]).grid(row=2, column=0, columnspan=2, sticky="w", pady=7)
    else:
        ttk.Checkbutton(legend, text="Hide all legends", variable=values["hide_legend"]).grid(row=2, column=0, columnspan=2, sticky="w", pady=7)
        ttk.Checkbutton(legend, text="Hide original data legends", variable=values["hide_original_legend"]).grid(row=3, column=0, columnspan=2, sticky="w", pady=7)

    def apply(close=False):
        try:
            for key in ("width", "height", "font_size"):
                number = float(values[key].get())
                if not math.isfinite(number) or number <= 0:
                    raise ValueError("Axes dimensions and font size must be finite and positive.")
            for axis in (("y",) if distribution else ("x", "y")):
                low, high = values[f"{axis}min"].get().strip(), values[f"{axis}max"].get().strip()
                step = values[f"{axis}_tick_step"].get().strip()
                for value in (low, high, step):
                    if value and not math.isfinite(float(value)):
                        raise ValueError("Axis settings must be finite numbers or blank.")
                if low and high and float(low) >= float(high):
                    raise ValueError("Axis minimum must be smaller than its maximum.")
                if step and float(step) <= 0:
                    raise ValueError("Tick step must be positive or blank.")
            columns = int(values["legend_ncol"].get())
            if not 1 <= columns <= 10:
                raise ValueError("Legend columns must be between 1 and 10.")
        except ValueError as exc:
            messagebox.showerror("Invalid Setting", str(exc), parent=dialog)
            return
        for key, attribute in names.items():
            getattr(app, attribute).set(int(values[key].get()) if key == "legend_ncol" else values[key].get())
        if distribution:
            app.x_label_var.set(values["x_label"].get())
            app.y_label_var.set(values["y_label"].get())
            app._show_legend.set(values["show_legend"].get())
            app._redraw()
        else:
            app.ax.set_xlabel(values["x_label"].get())
            app.ax.set_ylabel(values["y_label"].get())
            app._update_legend()
            app._apply_appearance()
        if close:
            dialog.destroy()

    buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
    buttons.pack(fill=tk.X)
    ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)
    ttk.Button(buttons, text="OK", command=lambda: apply(True)).pack(side=tk.RIGHT, padx=6)
    ttk.Button(buttons, text="Apply", command=apply).pack(side=tk.RIGHT)
    dialog._settings_values = values
    dialog._settings_tabs = book
    return dialog
