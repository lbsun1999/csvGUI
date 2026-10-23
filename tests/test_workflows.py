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
from PIL import Image

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from csvFIG import csvFIG
from csvPLOT import csvPLOT


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
        tool = 'csvFIG' if isinstance(app, csvFIG.CsvFigApp) else 'csvPLOT'
        with patch("tkinter.filedialog.askopenfilename", return_value=str(ROOT / tool / "examples" / name)):
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

    def test_canvas_resize_cleans_old_image_and_keeps_axes_export_size(self):
        for cls in (csvPLOT.CsvPlotterApp, csvFIG.CsvFigApp):
            app = self.app(cls)
            canvas = app.canvas
            for width, height in ((9, 5.5), (4, 4), (8, 6), (3, 2)):
                with patch.object(app.plot_area, 'winfo_width', return_value=500), patch.object(app.plot_area, 'winfo_height', return_value=350):
                    canvas.set_size_inches(width, height)
                    canvas.draw()
                    actual_axes = app.ax.get_window_extent().size / app.figure.dpi
                    np.testing.assert_allclose(actual_axes, [width, height])
                    self.assertTrue(np.all(app.figure.get_size_inches() > [width, height]))
                    widget = canvas.get_tk_widget()
                    images = [item for item in widget.find_all() if widget.type(item) == 'image']
                    self.assertEqual(len(images), 1)
                    self.assertLessEqual(canvas._tkphoto.width(), 500)
                    self.assertLessEqual(canvas._tkphoto.height(), 350)
                    path = self.tmp / 'resized.png'
                    app.figure.savefig(path)
                    with Image.open(path) as image:
                        self.assertEqual(image.size, tuple(int(size * canvas.base_dpi) for size in canvas.total_inches))
            self.assertEqual(app.plot_area.cget('background'), '#e5e7eb')

    def test_small_axes_grow_figure_to_fit_large_text_and_outside_legends(self):
        for cls in (csvPLOT.CsvPlotterApp, csvFIG.CsvFigApp):
            app = self.app(cls)
            app.font_size.set('24')
            app.plot_title.set('A long experimental comparison title')
            if isinstance(app, csvPLOT.CsvPlotterApp):
                app.width.set('2')
                app.height.set('1')
                app.data = pd.DataFrame({'condition': ['Long condition A', 'Long condition B', 'Long condition C'],
                                         'measurements': [1e9, 2e9, 3e9]})
                app.x_column.set('condition')
                app.y_column.set('measurements')
                app.plot_selected()
                app.ax.set_xlabel('Experimental condition label')
                app.ax.set_ylabel('Measured response label')
            else:
                app.width_fig.set('2')
                app.height_fig.set('1')
                self.load_csv(app, 'distributions.csv')
                for name in ('group_a', 'group_b', 'group_c'):
                    app.column.set(name)
                    app._on_column_changed()
                    app.box_label.set('Long experimental condition ' + name)
                    app.add_box()
                    app.hold.set(True)
                app.x_label_var.set('Experimental condition label')
                app.y_label_var.set('Measured response label')
                app._show_legend.set(True)
            for location in ('best', 'outside lower', 'outside upper', 'outside right'):
                with self.subTest(app=cls.__name__, location=location):
                    app.legend_loc.set(location)
                    if isinstance(app, csvPLOT.CsvPlotterApp):
                        app._update_legend()
                        app._apply_appearance()
                    else:
                        app._redraw()
                    canvas = app.canvas
                    renderer = canvas.get_renderer()
                    bounds = app.ax.get_tightbbox(renderer)
                    figure = app.figure.bbox
                    self.assertGreaterEqual(bounds.x0, 4)
                    self.assertGreaterEqual(bounds.y0, 4)
                    self.assertLessEqual(bounds.x1, figure.width - 4)
                    self.assertLessEqual(bounds.y1, figure.height - 4)
                    np.testing.assert_allclose(app.ax.get_window_extent().size / app.figure.dpi, [2, 1])
                    if location.startswith('outside'):
                        decoration = app.ax.get_tightbbox(renderer, bbox_extra_artists=[])
                        legend = app.ax.get_legend().get_window_extent(renderer)
                        if location == 'outside lower':
                            self.assertLess(legend.y1, decoration.y0)
                        elif location == 'outside upper':
                            self.assertGreater(legend.y0, decoration.y1)
                        else:
                            self.assertGreater(legend.x0, decoration.x1)
                    app.figure.savefig(self.tmp / f'{cls.__name__}-{location}.png')
            large_size = np.array(canvas.total_inches)
            app.font_size.set('10')
            app.plot_title.set('')
            if isinstance(app, csvPLOT.CsvPlotterApp):
                app._apply_appearance()
            else:
                app._redraw()
            self.assertTrue(np.all(np.array(canvas.total_inches) < large_size))

    def test_project_axes_units_and_legacy_figure_conversion(self):
        for cls, extension in ((csvPLOT.CsvPlotterApp, 'cplot'), (csvFIG.CsvFigApp, 'cfig')):
            app = self.app(cls)
            saved = self.roundtrip(app, extension)
            self.assertEqual(saved['settings']['size_mode'], 'axes')
            np.testing.assert_allclose(app.canvas.requested_inches, [9, 5.5])
            saved['settings'].pop('size_mode')
            path = self.tmp / f'legacy.{extension}'
            path.write_text(json.dumps(saved), encoding='utf-8')
            with patch('tkinter.filedialog.askopenfilename', return_value=str(path)):
                app.load_project()
            np.testing.assert_allclose(app.canvas.requested_inches, [9 * .82, 5.5 * .76])

    def test_default_smoothing_and_csv_import_controls(self):
        plot = self.app(csvPLOT.CsvPlotterApp)
        self.assertEqual(plot.smooth_window.get(), '25')
        self.load_csv(plot, 'curves.csv')
        plot.x_column.set('step')
        plot.y_column.set('signal_a')
        plot.plot_selected()
        np.testing.assert_allclose(plot._curves[0]['smooth_line'].get_ydata(),
                                   csvPLOT.trailing_moving_average(plot._curves[0]['raw_y'], 25))
        fig = self.app(csvFIG.CsvFigApp)
        self.assertFalse(fig._show_legend.get())
        self.load_csv(fig, 'distributions.csv')
        fig.column.set('group_a')
        fig.add_box()
        self.assertIsNone(fig.ax.get_legend())
        self.roundtrip(fig, 'cfig')
        self.assertFalse(fig._show_legend.get())
        self.assertIsNone(fig.ax.get_legend())
        for app in (plot, fig):
            top_buttons = [w for w in widgets(app) if isinstance(w, ttk.Button)][:3]
            self.assertEqual([w.cget('text') for w in top_buttons], ['Load CSV', 'Save Project', 'Open Project'])
        self.assertFalse(any(isinstance(w, ttk.Button) and w.cget('text') == 'Load TXT' for w in widgets(fig)))

    def test_figure_dialog_stages_settings_without_sidebar_scrollbars(self):
        for cls in (csvPLOT.CsvPlotterApp, csvFIG.CsvFigApp):
            app = self.app(cls)
            self.assertFalse(any(isinstance(w, ttk.Scrollbar) for w in widgets(app)))
            self.assertFalse(any(isinstance(w, ttk.Label) and str(w.cget('textvariable')) == str(app.status) for w in widgets(app)))
            dialog = app._open_figure_settings()
            self.assertIs(dialog, app._open_figure_settings())
            self.assertIs(dialog, app.canvas.toolbar.configure_subplots())
            self.assertFalse(any(isinstance(w, ttk.Scrollbar) for w in widgets(dialog)))
            values = dialog._settings_values
            original = app.canvas.requested_inches
            values['width'].set('4')
            values['height'].set('3')
            values['plot_title'].set('Updated title')
            values['legend_loc'].set('lower left')
            values['legend_ncol'].set('2')
            self.assertEqual(app.canvas.requested_inches, original)
            apply = next(w for w in widgets(dialog) if isinstance(w, ttk.Button) and w.cget('text') == 'Apply')
            apply.invoke()
            np.testing.assert_allclose(app.canvas.requested_inches, [4, 3])
            self.assertEqual(app.plot_title.get(), 'Updated title')
            self.assertEqual(app.ax.get_title(), 'Updated title')
            self.assertEqual(app.legend_loc.get(), 'lower left')
            values['width'].set('-1')
            with patch.object(messagebox, 'showerror') as error:
                apply.invoke()
                error.assert_called_once()
            np.testing.assert_allclose(app.canvas.requested_inches, [4, 3])
            dialog.destroy()

    def test_long_tick_labels_rotate_and_short_labels_reset(self):
        app = self.app(csvFIG.CsvFigApp)
        self.load_csv(app, 'distributions.csv')
        for name in ('group_a', 'group_b', 'group_c'):
            app.column.set(name)
            app._on_column_changed()
            app.box_label.set('A long descriptive experimental condition ' + name)
            app.add_box()
            app.hold.set(True)
        app.width_fig.set('6')
        app.height_fig.set('4')
        app._apply_appearance()
        self.assertTrue(all(label.get_rotation() == 45 for label in app.ax.get_xticklabels()))
        renderer = app.canvas.get_renderer()
        self.assertGreaterEqual(min(label.get_window_extent(renderer).y0 for label in app.ax.get_xticklabels()), 5)
        for index, item in enumerate(app._boxes):
            item['label'] = f'G{index + 1}'
        app._redraw()
        self.assertTrue(all(label.get_rotation() == 0 for label in app.ax.get_xticklabels()))

    def test_distribution_legend_location_and_groups_roundtrip(self):
        app = self.app(csvFIG.CsvFigApp)
        self.load_csv(app, 'distributions.csv')
        app.column.set('group_a')
        app.add_box()
        app._show_legend.set(True)
        app.legend_loc.set('lower left')
        app.legend_ncol.set(2)
        app._redraw()
        self.assertIn(app._boxes[0]['label'], [text.get_text() for text in app.ax.get_legend().get_texts()])
        saved = self.roundtrip(app, 'cfig')
        self.assertEqual(saved['settings']['legend_loc'], 'lower left')
        self.assertEqual(app.legend_ncol.get(), 2)


if __name__ == "__main__":
    unittest.main()
