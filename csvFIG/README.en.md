# csvFIG

[简体中文](README.md) | **English**

Statistical distribution plots and journal figure layouts. [Series home](../README.en.md) · [Experimental CSV](examples/experiment_distributions.csv)

```powershell
# Launch from the repository root.
python csvFIG/csvFIG.py
```

You can also run `python csvFIG.py` from this directory. Install dependencies as described in the [main README](../README.en.md), and retain the sibling `common/` directory.

## Four plot families and horizontal boxplots

Every example includes a **600 DPI PNG, vector PDF/SVG, and an editable `.cfig` project containing raw observations**. Each image was exported after reopening its corresponding project, so the saved settings match the displayed result.

The examples use **2.6 × 2.05 inch axes and 13 pt text**, short group labels, a white background, few ticks, and no legend. Built-in titles are omitted so manuscript captions and panel labels can be arranged consistently. The complete figure size adjusts to rotated labels and other text; exact dimensions are in the [gallery manifest](../examples/gallery_manifest.json).

| Boxplot: Box (V) | Bar with error bars: Bar+Err |
| --- | --- |
| ![Compact monochrome boxplot](examples/exports/box.png) | ![Bars with mean connections](examples/exports/bar-error.png) |
| [PNG](examples/exports/box.png) · [PDF](examples/exports/box.pdf) · [SVG](examples/exports/box.svg) · [box.cfig](examples/projects/box.cfig) | [PNG](examples/exports/bar-error.png) · [PDF](examples/exports/bar-error.pdf) · [SVG](examples/exports/bar-error.svg) · [bar-error.cfig](examples/projects/bar-error.cfig) |
| Violin | Violin+Box |
| ![Violins with median connections](examples/exports/violin.png) | ![Pale violins with black outlines and inner boxes](examples/exports/violin-box.png) |
| [PNG](examples/exports/violin.png) · [PDF](examples/exports/violin.pdf) · [SVG](examples/exports/violin.svg) · [violin.cfig](examples/projects/violin.cfig) | [PNG](examples/exports/violin-box.png) · [PDF](examples/exports/violin-box.pdf) · [SVG](examples/exports/violin-box.svg) · [violin-box.cfig](examples/projects/violin-box.cfig) |

### Horizontal boxplots: Box (H)

<img src="examples/exports/box-horizontal.png" width="450" alt="Narrow horizontal boxplots with median connections">

[PNG](examples/exports/box-horizontal.png) · [PDF](examples/exports/box-horizontal.pdf) · [SVG](examples/exports/box-horizontal.svg) · [box-horizontal.cfig](examples/projects/box-horizontal.cfig)

This is a horizontal arrangement of the boxplot family. The application therefore provides five Plot Type options representing four plot families. Clustered boxplots are planned for a future version.

### Data and styling conventions

| Label | Data column | Color and distribution |
| --- | --- | --- |
| Uni | `single_peak` | Blue; a mostly single-peaked mixture |
| Bi | `bimodal` | Red; two modes |
| Tri | `trimodal` | Green; three modes |
| Skew | `right_skewed` | Purple; right-skewed |
| Tail | `heavy_tail` | Orange; heavy-tailed |

Every group contains **5000 raw observations**. The five examples deliberately use different opacity, width, outlines, and statistical connections. Edge/line width is 1.2 throughout. DejaVu Serif is bundled with Matplotlib; select TimesSimSun for Chinese text.

| Project | Fill alpha | Relative width | Outlines | Between-group connection | Line style / marker size |
| --- | --- | --- | --- | --- | --- |
| `box.cfig` | 0 | 0.50 | All black | None | No markers |
| `bar-error.cfig` | 0.55 | 0.62 | Black | Means, triangular markers | dashdot / 5 |
| `violin.cfig` | 0.45 | 0.90 | Group colors | Medians, circular markers | dotted / 4 |
| `violin-box.cfig` | 0.25 | 0.95 | Black | None | No markers |
| `box-horizontal.cfig` | 0.65 | 0.40 | Group colors | Medians, line only | solid / 0 |

Connections demonstrate styling only. These synthetic groups are independent populations; the lines do not imply pairing or a time trend. The color table describes the colored examples. All groups in the monochrome boxplot are set to black.

To avoid crowding compact panels with many heavy-tail outliers, boxplot and combination examples disable **Show outliers**. All samples remain in the project and can be displayed again. Violin densities use every sample. Boxplots/bars use numeric limits 0–100, while violins/combinations use 0–120; check scales when comparing panels. **Bar+Err error bars span the boxplot whisker endpoints, not standard deviation, standard error, or a confidence interval.**

## Continue editing from a project

1. Click **Open Project** and select a `.cfig` in `examples/projects/`.
2. The project restores raw data, plot type, labels, fonts, colors, and the disabled legend.
3. Switch **Plot Type** to reuse the same data in another representation. Adjust axis labels when switching to Box (H).
4. Use **Figure & Axes** for axes dimensions and numeric limits. Use **Advanced Settings** for labels, colors, opacity, order, and statistical connections.
5. Toolbar **Save** exports an image; **Save Project** saves an editable project.

## Actual window and controls

![csvFIG main window with adjustable width and no legend](../docs/screenshots/csvfig-style-window.jpg)

The left panel contains CSV import, project save/open, data-column selection, labels, colors, width, and plot type. Hold retains multiple groups. **Figure & Axes** opens layout settings; **Advanced Settings** opens data-item and statistical-style controls. There is no status paragraph above the controls, and the main sidebar needs no scrolling.

## Advanced settings: screenshots and procedures

### 1. Connections, line styles, markers, outlines, and opacity

![Statistical connections, outlines, and opacity controls](../docs/screenshots/csvfig-advanced-style.jpg)

This screenshot loads `bar-error.cfig`: Connect means is enabled, line style is dashdot, marker size is 5, outlines are black, and alpha is 0.55. The advanced window scrolls and also includes titles, axis labels, fonts, and grids. Apply and Cancel remain at the bottom.

| Control | Effect | When applied |
| --- | --- | --- |
| **Connect medians** | Connect group medians with circular markers | Redraw immediately |
| **Connect means** | Connect group means with triangular markers | Redraw immediately |
| **Connection Line Style** | solid, dashed, dashdot, dotted, or none; shared by mean and median connections | Redraw on selection |
| **Connection Marker Size** | 0–15; zero hides markers while allowing a line | Redraw while dragging |
| **Edge / Line Width** | 0.5–5; outline, whisker, and statistical-connection thickness | Redraw while dragging |
| **Edges: Color / Black** | Toggle outlines; the button text shows the current mode | Redraw on click |
| **Global Box Alpha** | 0 means no fill; 1 means opaque fill; outlines remain visible | Change the slider, then Apply to all groups |

`solid` is continuous, `dashed` uses dashes, `dashdot` alternates dashes and dots, and `dotted` uses dots. Choose `none` with a nonzero marker size for **statistical points without lines**. Choose a non-none style with marker size 0 for **lines without markers**. Setting both line style to none and marker size to zero hides the between-group connection. The median line inside each box remains visible regardless of the connection switch.

**Connection Line Style / Marker Size** were previously named Median Line Style / Marker Size. Existing project fields remain compatible. These controls style the connections between group means/medians; they do not turn individual whiskers or box outlines into dashed lines.

On opening, Alpha displays the first group's current value. If groups have different values, clicking Apply without changing this slider preserves them. Changing it and applying makes their alpha values uniform. Connections, line styles, and outlines take effect immediately: Cancel does not roll those changes back. Unapplied alpha, label, and visibility edits are discarded when the dialog closes.

### 2. Group labels, visibility, order, and color

![Group labels, visibility switches, color swatches, and ordering](../docs/screenshots/csvfig-advanced-items.jpg)

Each row contains a visibility switch, group number, label field, color swatch, and up/down buttons. Labels and visibility take effect on Apply. Hidden groups are removed from the displayed sequence and remaining groups are repositioned. Reordering redraws the plot and reopens the dialog; apply pending edits before reordering if they should be retained.

![Group color selector](../docs/screenshots/csvfig-color-picker.jpg)

Click a **color swatch for an existing group**. Select a Palette color or enter `#RRGGBB` under Custom, such as black `#000000`. Preview shows the selected color; **OK** applies it to that group. **Picker…** opens the system color picker. Main-panel Color applies to the next **Add Data** action; use the advanced swatches to recolor existing groups.

### 3. Adjusting width

Main-panel **Relative Width** ranges from 0.1 to 1.0. Dragging immediately applies the value to every current group; newly added groups also use it. Smaller values produce narrower boxes, bars, or violins. Group centers remain fixed.

- **Box (V)** changes horizontal box width; **Box (H)** changes vertical box thickness.
- **Bar+Err** changes bar width. Error-bar cap size is fixed by the plotting code and is not separately controlled by this slider.
- **Violin** changes maximum width along the category axis, without changing observations or the KDE bandwidth.
- **Violin+Box** scales both layers; the inner box remains approximately 30% of the outer violin width.

### 4. Making a traditional unfilled monochrome boxplot

Open [box.cfig](examples/projects/box.cfig) directly, or start from another distribution project:

1. Select **Box (V)** or **Box (H)** under Plot Type.
2. Set each group's color swatch to `#000000`, or simply switch to **Edges: Black** to preserve the group colors for later reuse.
3. Set **Global Box Alpha** to **0** and click **Apply**. Fill disappears while outlines, whiskers, caps, and median lines remain.
4. Disable **Connect medians / Connect means** and adjust Relative Width; this example uses 0.50.
5. Enable **Show outliers (Box)** if you want whisker-exceeding observations. Outliers use fixed gray circular markers; fill alpha does not control them.

Alpha=0 removes box fill; it does not make the exported image background transparent. The outline toggle mainly affects boxes, bars, and violin contours. Whiskers/caps are dark gray, and medians/statistical connections are black. Combination plots use a fixed white fill for their inner boxes; choose a Box type for a traditional unfilled boxplot.

## csvFIG features

### Input and grouping

**Load CSV** reads a header-based CSV. **Data Column** selects raw observations; nonnumeric values, missing values, and infinities are filtered out. **Add Data** adds a group, **Hold** retains existing groups, and **Clear** clears the plot.

The import area matches csvPLOT: a full-width **Load CSV** button above **Save Project / Open Project**.

**Label (display name)** sets a new group's label. Edit existing labels/colors in advanced settings. The application prevents consecutive duplicate additions of the current column; select another column or clear the plot before restarting.

### Plot types

| Plot Type | Representation |
| --- | --- |
| **Box (V)** | Vertical boxplot: Q1–Q3 box, black median, whiskers determined by the `1.5×IQR` rule, and optional outliers |
| **Box (H)** | Horizontal boxplot; the numeric axis becomes X |
| **Bar+Err** | Mean-height bars with errors extending to boxplot whisker endpoints; **not SD, SE, or confidence intervals** |
| **Violin** | Gaussian KDE of raw observations, with a median segment |
| **Violin+Box** | Violin contours overlaid with narrower white boxes, showing density and quartiles |

Switching types reuses the data. Each violin is normalized to its own maximum density to compare shape; violin widths cannot be interpreted as sample-size comparisons.

### Styling and item management

| Control | Behavior |
| --- | --- |
| **Relative Width** | `0.1–1.0`; controls new items and updates existing items when dragged |
| **Show outliers (Box)** | Show/hide outliers in boxplots and combination plots |
| **Connect medians / Connect means** | Connect medians with circles or means with triangles |
| **Connection Line Style** | Shared line style for statistical connections |
| **Connection Marker Size** | `0–15`; zero hides markers |
| **Edge / Line Width** | `0.5–5`; box, whisker, violin-outline, and connection thickness |
| **Edges: Color / Black** | Group-colored or black outlines |
| **Show legend** | Show group colors/names and enabled statistical elements |
| **Global Box Alpha** | Fill opacity `0–1`; change it and Apply to update all items |

csvFIG **hides the legend by default**, because axis labels identify groups. Enable **Show legend** when needed. Opening a project restores its saved legend switch. **Figure & Axes → Legend** supports `best`, explicit inside/outside locations, and column counts, all saved in `.cfig` projects. Clustered boxplots are planned, not currently implemented.

Connections, marker styles, and outline details are in **Advanced Settings → Distribution Style**. **Data Items on Plot** provides visibility, labels, colors, and **↑ / ↓** ordering. Hidden items are omitted and visible groups repositioned. Click Apply for staged changes.

## Figure, axes, fonts, and toolbar

The main sidebar has no scrollbar. The initial application window is `1280×820` and can be resized. **Figure & Axes...** opens a tabbed settings dialog. The advanced data list can scroll when many items are present.

### Figure & Axes

| Control | Behavior |
| --- | --- |
| **Axes Width / Axes Height (inches)** | Interior plotting dimensions; default `9×5.5`, positive values only; exclude ticks, labels, title, and legend |
| **Font / Font Size** | Font family and positive point size for titles, axis labels, and tick labels |
| **X Axis: min / step / max** | csvPLOT X limits and major-tick spacing |
| **Y Axis: min / step / max** | Numeric-axis limits and major-tick spacing |
| **Hide last X / Y tick** | Hide the last major-tick label without removing data; csvFIG offers this for its numeric axis |
| **Apply / OK** | Apply the staged figure, font, axes, and legend settings |

Either limit can be specified independently. Blank limits use automatic scaling; a fixed tick step must be positive. In csvFIG's **Box (H)** mode, controls named **Y Axis** apply to the horizontal numeric axis.

The **Axes & Labels** tab edits **Plot Title**, **X-Axis Label**, **Y-Axis Label**, and X/Y grids. Overlapping horizontal tick labels automatically rotate 45° and return to horizontal when space permits.

TimesSimSun is preferred when available for mixed Chinese/English text. Put font files you are entitled to use in `../common/fonts/` and restart; no system-wide installation is needed. Without it, the application uses Matplotlib's bundled font. You may select an installed Chinese font or type a font family name in the field.

Font source and information: [Zhoushijiehqu/Academic-Font-TimesSimSun](https://github.com/Zhoushijiehqu/Academic-Font-TimesSimSun). The [article](https://mp.weixin.qq.com/s/Z--wuiasKW90wUn2dsC5kw) from **A Kun's Research Notes (阿昆的科研日常)** is retained as an introduction, not an authorship credit. The font repository states personal academic research and non-commercial use only. The font is not covered by this project's MIT license, and its binaries are not bundled here. See the [font source/loading notes](../common/fonts/README.md).

The axes area is the data rectangle inside the axis frame. The application measures tick labels, axis labels, titles, and legends and adds outer margins while preserving the requested axes size. Larger text or smaller axes can increase total figure size; shorter labels or smaller text release excess margins. Long tick labels rotate automatically when needed.

For example, `Axes Width=4` and `Axes Height=3` produce a **4×3 inch data rectangle**, with a larger complete image whose size depends on the surrounding text. Outside legends sit beyond the axis labels and title. Very dense labels may still overlap each other; widen the axes, shorten the labels, or reduce the font size.

Only the current figure remains after resizing, with clean gray space around it. Oversized figures are scaled down for preview; exports retain the requested axes dimensions and original DPI.

### Toolbar

| Tool | Behavior |
| --- | --- |
| **Home** | Return to the initial view |
| **Back / Forward** | Navigate view history |
| **Pan** | Drag to pan |
| **Zoom** | Select a rectangle to zoom |
| **Subplots** | Open the same Figure & Axes dialog for dimensions, text, and legends |
| **Save** | Export the current figure |

Pan and zoom do not modify CSV data. Margins are recalculated after navigation or settings changes; exports use the current layout.

## Palette and custom colors

Both tools share these 13 colors. Main-panel colors apply to the next item; advanced color swatches edit existing items.

| Name | Value | Name | Value |
| --- | --- | --- | --- |
| Deep Red | `#A6232F` | Red | `#C0392B` |
| Burnt Orange | `#D35400` | Orange | `#CA6F1E` |
| Amber | `#B7950B` | Olive | `#7D8C3A` |
| Forest Green | `#229954` | Teal | `#16A085` |
| Ocean Blue | `#2E86C1` | Royal Blue | `#2855A6` |
| Indigo | `#4A235A` | Purple | `#7D3C98` |
| Plum | `#9B1B6B` | | |

Color dialogs provide presets, a value field, **Picker…** for the system color picker, and a preview. Use `#RRGGBB` for consistent Tkinter swatches and plotted colors. Alpha ranges from `0` (transparent) to `1` (opaque).

## Image export and project persistence

The generated gallery PNGs are exported at 600 DPI by `../examples/render_gallery.py`, alongside PDF and SVG. The 100 DPI mentioned below is the GUI toolbar's default raster-export DPI. The supplied PDF/SVG files can be used directly in journal layouts.

### Image formats

Click toolbar **Save**. Available formats depend on the environment:

| Type | Formats | Typical use |
| --- | --- | --- |
| Raster | PNG, JPEG/JPG, TIFF/TIF, WebP | Documents, websites, image viewers |
| Vector | PDF, SVG/SVGZ | Papers and subsequent layout work |
| PostScript | EPS, PS | Workflows requiring these formats |

There is no separate export-DPI field. Default raster export uses the initial 100 DPI; pixel dimensions depend on axes size plus measured margins. Preview scaling does not reduce export dimensions. JPEG has no transparent background, and EPS/PS do not fully support transparency. Use PNG, PDF, or SVG when transparency matters. The toolbar may also offer PGF or RAW/RGBA; PGF usually requires a local TeX installation.

### Editable projects

**Save Project** saves embedded data and supported settings; **Open Project** reloads them.

| Content | `.cplot` | `.cfig` |
| --- | --- | --- |
| Data | Raw curves and stored moving averages | Raw observations for every group |
| Appearance | Labels, colors, visibility, order, opacity, smoothed-line styles | Labels, colors, visibility, order, opacity, width, plot type |
| Settings | Titles, axis labels/limits/steps, fonts, grids, legend layout | Titles, axis labels, numeric-axis settings, fonts, grids, statistical elements |
| Further editing | Recalculate curves with another smoothing window | Recompute statistics and switch plot types |

Projects use JSON and contain the plotted data, so the original CSV path is not required. Temporary toolbar navigation history is not persisted; enter limits in **Figure & Axes** when they must be saved. Exported images cannot be reopened as editable projects. Use lowercase `.cplot` and `.cfig` extensions.


## Five experimental distributions

Load [experiment_distributions.csv](examples/experiment_distributions.csv). There is **no row-index column**; all five columns contain observations.

| Data column | Distribution | Suggested color |
| --- | --- | --- |
| `single_peak` | Two nearby Gaussian components forming one main peak | Royal Blue |
| `bimodal` | Two separated peaks | Deep Red |
| `trimodal` | Three peaks | Forest Green |
| `right_skewed` | Main population with a longer right tail | Purple |
| `heavy_tail` | Narrow population with a small broad component | Burnt Orange |

1. Select the first column, enter a **Label (display name)**, choose a color, and click **Add Data**.
2. Enable **Hold: keep existing data** and add the other four columns with different colors.
3. Compare **Box (V)**, **Box (H)**, **Bar+Err**, **Violin**, and **Violin+Box**.
4. Inspect boxes, medians, whiskers, outliers, and the single/multiple peaks and tails of the violins.
5. Try median or mean connections, line widths, black outlines, fill opacity, labels, and ordering.

These columns contain raw samples. Statistics are calculated by the application. Columns represent independent populations; rows do not identify paired subjects.

### Distribution model

The random seed is **20261024**. Each column mixes normal components `N(mean, standard_deviation^2)` with exact component counts determined by the weights, totaling 5000 observations. Each column is shuffled independently.

| Column | Weights | Component means | Component standard deviations |
| --- | --- | --- | --- |
| `single_peak` | 0.7 / 0.3 | 20 / 22 | 2 / 3 |
| `bimodal` | 0.55 / 0.45 | 30 / 39 | 1.8 / 2.4 |
| `trimodal` | 0.30 / 0.45 / 0.25 | 44 / 51 / 58 | 1.4 / 1.8 / 1.6 |
| `right_skewed` | 0.8 / 0.2 | 64 / 73 | 1.8 / 3.0 |
| `heavy_tail` | 0.9 / 0.1 | 83 / 83 | 1.8 / 7.0 |

Metadata also records sample count, mean, sample standard deviation, minimum, Q1, median, Q3, and maximum for each column.

## Reproduction and compatibility

From the repository root, run `python examples/render_gallery.py` to regenerate both tools' compact projects and PNG/PDF/SVG through the actual plotting, save, and reopen workflow. Tkinter and a desktop environment are required. Other project filenames are not overwritten. To rebuild only the distribution gallery, use `python examples/render_gallery.py --tool csvFIG`.

`python examples/generate_examples.py` rebuilds synthetic CSVs; seeds and summaries are in the [metadata](../examples/dataset_metadata.json). The data demonstrate features and do not represent real experiments.

Projects embed raw data and do not require absolute CSV paths. Legacy whole-figure dimensions are converted to axes dimensions using the former layout proportions; new projects record `size_mode: axes`. Older `.cfig` files containing summary statistics without raw observations require the original CSV to be reimported.

[MIT license](../LICENSE) ? [Back to csvGUI](../README.en.md)
