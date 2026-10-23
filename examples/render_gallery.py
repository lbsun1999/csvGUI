"""Render compact journal examples through the actual GUI and project workflow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from csvFIG.csvFIG import CsvFigApp
from csvPLOT.csvPLOT import CsvPlotterApp

COLORS = ['#2855A6', '#A6232F', '#229954', '#7D3C98', '#D35400']
FIG_TYPES = [('box', 'Box (V)'), ('bar-error', 'Bar+Err'),
             ('violin', 'Violin'), ('violin-box', 'Violin+Box'), ('box-horizontal', 'Box (H)')]


def open_csv(app, tool, filename):
    with patch('tkinter.filedialog.askopenfilename', return_value=str(ROOT / tool / 'examples' / filename)):
        app.load_csv()
    app.current_file = filename


def compact(app):
    app.withdraw()
    app.font_name.set('DejaVu Serif')
    app.font_size.set('13')
    app.plot_title.set('')
    app.grid_x.set(False)
    app.grid_y.set(False)


def build_curves(mode):
    app = CsvPlotterApp()
    compact(app)
    app.width.set('2.8')
    app.height.set('2.0')
    app.orig_alpha.set(0.14)
    app.darken_factor.set(0.92)
    app.smooth_linewidth.set(1.6)
    app.hide_original_legend.set(True)
    app.x_column.set('row')
    open_csv(app, 'csvPLOT', 'experiment_curves.csv')
    app.x_column.set('row')
    if mode == 'curves':
        series = list(zip(app.data.columns[1:], COLORS,
                          ['Rise A', 'Rise B', 'Fall', 'Flat', 'Rise C'], [25] * 5))
    elif mode == 'detail':
        series = [('falling_snr6', COLORS[0], 'W = 25', 25)]
    else:
        series = [('falling_snr6', color, f'W{window}', window)
                  for color, window in zip((COLORS[0], COLORS[2], COLORS[1]), (25, 100, 300))]
    for column, color, label, window in series:
        app.y_column.set(column)
        app.curve_color.set(color)
        app.smooth_window.set(str(window))
        app.plot_selected()
        app._curves[-1]['label'] = label
        app.hold.set(True)
    if mode == 'curves':
        app.xmin.set('0'); app.xmax.set('5000'); app.x_tick_step.set('2500')
        app.ymin.set('0'); app.ymax.set('100'); app.y_tick_step.set('25')
        app.legend_loc.set('outside upper'); app.legend_ncol.set(3)
    else:
        app.xmin.set('1000'); app.xmax.set('1800'); app.x_tick_step.set('400')
        app.ymin.set('35'); app.ymax.set('65'); app.y_tick_step.set('15')
        app.legend_loc.set('outside upper'); app.legend_ncol.set(3)
    app.smooth_window.set('25')
    app.ax.set_xlabel('Row')
    app.ax.set_ylabel('Response')
    app._update_legend()
    app._apply_appearance()
    return app


def build_distribution(kind):
    app = CsvFigApp()
    compact(app)
    app.width_fig.set('2.6'); app.height_fig.set('2.05')
    app.box_width.set(0.68)
    app._edge_lw.set(1.2)
    app._show_legend.set(False)
    app.show_outliers.set(False)
    open_csv(app, 'csvFIG', 'experiment_distributions.csv')
    for column, color, label in zip(app.data.columns, COLORS, ['Uni', 'Bi', 'Tri', 'Skew', 'Tail']):
        app.column.set(column)
        app._on_column_changed()
        app.box_label.set(label)
        app.box_color.set(color)
        app.add_box()
        app._boxes[-1]['alpha'] = 0.75
        app._boxes[-1]['source_key'] = f'experiment_distributions.csv::{column}'
        app.hold.set(True)
    app.box_orientation.set(kind)
    app.ymin.set('0')
    app.ymax.set('120' if kind in ('Violin', 'Violin+Box') else '100')
    app.y_tick_step.set('40' if kind in ('Violin', 'Violin+Box') else '25')
    app.x_label_var.set('Response' if kind == 'Box (H)' else '')
    app.y_label_var.set('' if kind == 'Box (H)' else 'Response')
    app._redraw()
    return app


def save_and_export(app, tool, stem):
    """Save, reopen in the real application, then export the reopened figure."""
    folder = ROOT / tool / 'examples'
    projects, exports = folder / 'projects', folder / 'exports'
    projects.mkdir(exist_ok=True); exports.mkdir(exist_ok=True)
    extension = 'cplot' if tool == 'csvPLOT' else 'cfig'
    project = projects / f'{stem}.{extension}'
    with patch('tkinter.filedialog.asksaveasfilename', return_value=str(project)):
        app.save_project()
    with patch('tkinter.filedialog.askopenfilename', return_value=str(project)):
        app.load_project()
    app.canvas.draw()
    bounds = app.ax.get_tightbbox(app.canvas.get_renderer())
    frame = app.figure.bbox
    assert bounds.x0 >= 4 and bounds.y0 >= 4
    assert bounds.x1 <= frame.width - 4 and bounds.y1 <= frame.height - 4
    if tool == 'csvFIG':
        assert app.ax.get_legend() is None
        assert all(item['stats']['n'] == 5000 for item in app._boxes)
    for extension in ('png', 'pdf', 'svg'):
        app.figure.savefig(exports / f'{stem}.{extension}', dpi=600, facecolor='white')
    svg = exports / f'{stem}.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n',
                   encoding='utf-8', newline='\n')
    settings = json.loads(project.read_text(encoding='utf-8'))['settings']
    entry = {'tool': tool, 'name': stem, 'project': str(project.relative_to(ROOT)).replace('\\', '/'),
             'axes_inches': list(app.canvas.requested_inches),
             'figure_inches': list(app.canvas.total_inches), 'font_size_pt': 13,
             'font_family': settings['font_name'], 'png_dpi': 600}
    app.update_idletasks()
    app.destroy()
    print(f'Exported {tool}/{stem}', flush=True)
    return entry


def preview(kind, settings):
    app = CsvPlotterApp() if kind == 'plot' else CsvFigApp()
    app.withdraw()
    path = ROOT / ('csvPLOT/examples/projects/curves.cplot' if kind == 'plot'
                   else 'csvFIG/examples/projects/violin-box.cfig')
    with patch('tkinter.filedialog.askopenfilename', return_value=str(path)):
        app.load_project()
    app.title(f'csv{ "PLOT" if kind == "plot" else "FIG"} - compact gallery')
    app.geometry('1080x730+60+40')
    if settings:
        dialog = app._open_figure_settings()
        dialog.transient(''); dialog.deiconify()
        dialog.title(f'Gallery settings {settings}')
        dialog._settings_tabs.select({'area': 0, 'axes': 1, 'legend': 2}[settings])
        dialog.focus_set()
    else:
        app.deiconify()
    app.after(600000, app.destroy)
    app.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', choices=['plot', 'fig'])
    parser.add_argument('--settings', choices=['area', 'axes', 'legend'])
    args = parser.parse_args()
    warnings.filterwarnings('ignore', category=PendingDeprecationWarning)
    if args.preview:
        preview(args.preview, args.settings)
        return
    entries = [save_and_export(build_curves(mode), 'csvPLOT', mode)
               for mode in ('curves', 'detail', 'smoothing')]
    entries += [save_and_export(build_distribution(kind), 'csvFIG', stem)
                for stem, kind in FIG_TYPES]
    (ROOT / 'examples' / 'gallery_manifest.json').write_text(
        json.dumps(entries, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
