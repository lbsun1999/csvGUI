"""Exercise real Tk/Matplotlib workflows without interactive file dialogs."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox, ttk
import unittest
from unittest.mock import patch
import warnings

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import csvFIG
import csvPLOT


def widgets(parent):
    for child in parent.winfo_children():
        yield child
        yield from widgets(child)


class SmoothingTests(unittest.TestCase):
    def test_causal_average_with_missing_samples(self):
        result = csvPLOT.trailing_moving_average([2, 4, np.nan, 8], 2)
        np.testing.assert_allclose(result, [2, 3, 4, 8])
        with self.assertRaises(ValueError):
            csvPLOT.trailing_moving_average([1, 2], 0)


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.tmp = Path(self.directory.name)
        self.apps = []
        self.callbacks = []
        self.warnings = warnings.catch_warnings()
        self.warnings.__enter__()
        self.addCleanup(self.warnings.__exit__, None, None, None)
        warnings.filterwarnings("ignore", category=FutureWarning)
        for name in ("showerror", "showwarning", "showinfo"):
            mock = patch.object(messagebox, name, side_effect=AssertionError)
            mock.start()
            self.addCleanup(mock.stop)

    def tearDown(self):
        for app in reversed(self.apps):
            app.update_idletasks()
            for widget in app.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()
            app.destroy()
        self.assertEqual(self.callbacks, [])

    def app(self, cls):
        app = cls()
        app.withdraw()
        app.report_callback_exception = lambda *args: self.callbacks.append(args)
        self.apps.append(app)
        return app

    def load_csv(self, app, name):
        with patch("tkinter.filedialog.askopenfilename", return_value=str(ROOT / "examples" / name)):
            app.load_csv()

    def roundtrip(self, app, extension):
        path = self.tmp / f"project.{extension}"
        with patch("tkinter.filedialog.asksaveasfilename", return_value=str(path)):
            app.save_project()
        saved = json.loads(path.read_text(encoding="utf-8"))
        with patch("tkinter.filedialog.askopenfilename", return_value=str(path)):
            app.load_project()
        return saved

    def test_curve_overlay_smooth_roundtrip_and_export(self):
        app = self.app(csvPLOT.CsvPlotterApp)
        self.load_csv(app, "curves.csv")
        app.x_column.set("step")
        app.y_column.set("signal_a")
        app.smooth_window.set("3")
        app.plot_selected()
        app.hold.set(True)
        app.y_column.set("signal_b")
        app.plot_selected()
        original = [c["raw_y"].copy() for c in app._curves]
        app._curves[1]["visible"] = False
        app.smooth_window.set("5")
        app.resmooth_all()
        np.testing.assert_allclose(app._curves[0]["smooth_line"].get_ydata()[1], 1.35)
        self.assertFalse(app._curves[1]["smooth_line"].get_visible())
        saved = self.roundtrip(app, "cplot")
        self.assertEqual(len(saved["curves"]), 2)
        self.assertFalse(any(k.startswith("lp_") or k in ("show_lp", "combine") for c in saved["curves"] for k in c))
        for actual, expected in zip(app._curves, original):
            np.testing.assert_allclose(actual["raw_y"], expected)
        app.smooth_window.set("1")
        app.resmooth_all()
        self.assertEqual(len(app.ax.lines), 2)
        self.assertEqual(len(app._line_types), 2)
        for extension in ("png", "svg", "pdf"):
            path = self.tmp / f"curves.{extension}"
            app.figure.savefig(path)
            self.assertGreater(path.stat().st_size, 100)

    def test_date_and_category_axes_survive_project_reload(self):
        app = self.app(csvPLOT.CsvPlotterApp)
        for x in (["2026-01-01", "2026-01-02", "2026-01-03"], ["alpha", "beta", "gamma"]):
            with self.subTest(x=x):
                app.clear_plot()
                app.data = pd.DataFrame({"x": x, "y": [1, 2, 5]})
                app.x_column.set("x")
                app.y_column.set("y")
                app.smooth_window.set("2")
                app.plot_selected()
                expected = app._curves[0]["line"].get_xdata().copy()
                self.roundtrip(app, "cplot")
                np.testing.assert_array_equal(app._curves[0]["line"].get_xdata(), expected)
                app.smooth_window.set("3")
                app.resmooth_all()
                np.testing.assert_allclose(app._curves[0]["smooth_line"].get_ydata(), [1, 1.5, 8 / 3])

    def test_visibility_checkbox_changes_its_own_curve(self):
        app = self.app(csvPLOT.CsvPlotterApp)
        self.load_csv(app, "curves.csv")
        app.x_column.set("step")
        app.smooth_window.set("2")
        for name in ("signal_a", "signal_b"):
            app.y_column.set(name)
            app.plot_selected()
            app.hold.set(True)
        app._open_advanced()
        dialog = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
        checks = [w for w in widgets(dialog) if isinstance(w, ttk.Checkbutton) and w.grid_info().get("column") == 0]
        self.assertEqual(len(checks), 2)
        checks[0].invoke()
        self.assertFalse(app._curves[0]["visible"])
        self.assertTrue(app._curves[1]["visible"])
        next(w for w in widgets(dialog) if isinstance(w, ttk.Button) and w.cget("text") == "Apply").invoke()
        self.assertTrue(app.bind("<MouseWheel>"))

    def test_all_distribution_plots_and_recomputed_statistics(self):
        app = self.app(csvFIG.CsvFigApp)
        self.load_csv(app, "distributions.csv")
        for name in ("group_a", "group_b"):
            app.column.set(name)
            app._on_column_changed()
            app.add_box()
            app.hold.set(True)
        for kind in ("Box (V)", "Box (H)", "Bar+Err", "Violin", "Violin+Box"):
            with self.subTest(kind=kind):
                app.box_orientation.set(kind)
                app._redraw()
                app.figure.savefig(self.tmp / f"{kind.replace('/', '_')}.png")
        expected = app._boxes[0]["data"].copy()
        saved = self.roundtrip(app, "cfig")
        self.assertEqual(len(saved["boxes"]), 2)
        np.testing.assert_allclose(app._boxes[0]["data"], expected)
        saved["boxes"][0]["stats"]["med"] = -999
        path = self.tmp / "edited.cfig"
        path.write_text(json.dumps(saved), encoding="utf-8")
        with patch("tkinter.filedialog.askopenfilename", return_value=str(path)):
            app.load_project()
        self.assertAlmostEqual(app._boxes[0]["stats"]["med"], np.median(expected))
        app._open_advanced()
        dialog = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
        next(w for w in widgets(dialog) if isinstance(w, ttk.Button) and w.cget("text") == "Apply").invoke()
        self.assertTrue(app.bind("<MouseWheel>"))

    def test_txt_distributions(self):
        app = self.app(csvFIG.CsvFigApp)
        path = ROOT / "examples" / "distributions.txt"
        with patch("tkinter.filedialog.askopenfilename", return_value=str(path)):
            app.load_txt()
        self.assertEqual(len(app._boxes), 3)
        self.assertEqual(app.plot_title.get(), "Example distributions")
        self.roundtrip(app, "cfig")
        self.assertEqual(app._boxes[0]["stats"]["n"], 8)

    def test_constant_distribution_can_render_violin(self):
        app = self.app(csvFIG.CsvFigApp)
        app.data = pd.DataFrame({"constant": [3, 3, 3, np.inf]})
        app.column.set("constant")
        app.add_box()
        for kind in ("Violin", "Violin+Box"):
            app.box_orientation.set(kind)
            app._redraw()
        self.assertEqual(app._boxes[0]["stats"]["n"], 3)

    def test_summary_only_project_is_rejected_without_losing_data(self):
        app = self.app(csvFIG.CsvFigApp)
        self.load_csv(app, "distributions.csv")
        app.column.set("group_a")
        app.add_box()
        expected = app._boxes[0]["data"].copy()
        path = self.tmp / "summary.cfig"
        path.write_text(json.dumps({"type": "csvFIG", "boxes": [{"data": None}]}), encoding="utf-8")
        with patch("tkinter.filedialog.askopenfilename", return_value=str(path)), patch.object(messagebox, "showerror") as error:
            app.load_project()
        error.assert_called_once()
        np.testing.assert_array_equal(app._boxes[0]["data"], expected)

    def test_empty_csv_reports_a_read_error(self):
        path = self.tmp / "empty.csv"
        path.touch()
        for cls in (csvPLOT.CsvPlotterApp, csvFIG.CsvFigApp):
            app = self.app(cls)
            with patch("tkinter.filedialog.askopenfilename", return_value=str(path)), patch.object(messagebox, "showerror") as error:
                app.load_csv()
            error.assert_called_once()
            self.assertIsNone(app.data)


if __name__ == "__main__":
    unittest.main()
