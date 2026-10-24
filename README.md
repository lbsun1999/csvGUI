# csvGUI

面向科研绘图的轻量桌面工具系列。使用 CSV 原始数据绘图，调整样式，保存可编辑项目，并导出期刊插图。

| 工具 | 用途 | 文档与图集 | 可编辑项目 |
| --- | --- | --- | --- |
| **csvPLOT** | 多曲线叠加、移动平均平滑、局部视图 | [完整说明、紧凑图集与手工样式](csvPLOT/README.md) | [4 个 .cplot](csvPLOT/examples/projects/) |
| **csvFIG** | 黑白箱线图、均值/中位数连线、彩色分布图 | [完整说明与 5 个示例](csvFIG/README.md) | [5 个 .cfig](csvFIG/examples/projects/) |

## 紧凑期刊插图

| csvPLOT · 多曲线与平滑 | csvFIG · 小提琴与箱线 |
| --- | --- |
| ![紧凑多曲线图](csvPLOT/examples/exports/curves.png) | ![紧凑小提琴箱线图](csvFIG/examples/exports/violin-box.png) |
| [PNG](csvPLOT/examples/exports/curves.png) · [PDF](csvPLOT/examples/exports/curves.pdf) · [SVG](csvPLOT/examples/exports/curves.svg) · [项目](csvPLOT/examples/projects/curves.cplot) | [PNG](csvFIG/examples/exports/violin-box.png) · [PDF](csvFIG/examples/exports/violin-box.pdf) · [SVG](csvFIG/examples/exports/violin-box.svg) · [项目](csvFIG/examples/projects/violin-box.cfig) |

示例采用约 **2.6–2.8 英寸宽的坐标区与 13 pt 字体**，适合组合成多子图。PNG 为 **600 DPI**，PDF/SVG 为矢量图。标题交给论文图注；画布随文字自动扩展，csvFIG 默认无图例。具体尺寸、绘图约定、全部图片下载和控件截图见各子项目 README。

项目文件已经准备好：启动对应工具，点击 **Open Project** 即可恢复数据与样式，继续编辑。图片由项目重开后导出，使用仓库内的合成实验数据，不代表真实实验结果。

## 安装与启动

需要 **Python 3.10+**、Tkinter 与桌面显示环境。

```powershell
git clone https://github.com/lbsun1999/csvGUI.git
cd csvGUI
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python csvPLOT/csvPLOT.py
# 或者
python csvFIG/csvFIG.py
```

`requirementLists.txt` 为兼容安装入口。macOS/Linux 可使用 `python3` 和 `source .venv/bin/activate`；Linux 需有系统 Tkinter 包。运行 `python -m tkinter` 可检查桌面支持。

两个工具各有依赖入口、README、CSV、导出图和项目目录，共用 `common/` 中的画布与字体支持。可从工具目录运行相应脚本，请保留仓库整体结构。

## 数据、样式与导出

- csvPLOT：5000 行 × 6 列，[实验 CSV](csvPLOT/examples/experiment_curves.csv)，首列为行号，其余列含趋势、谐波与噪声；平滑窗口默认 **25**。
- csvFIG：5000 行 × 5 列，[实验 CSV](csvFIG/examples/experiment_distributions.csv)，包含单峰、双峰、三峰、右偏与厚尾的原始观测。
- 两者均支持坐标范围、刻度、标签、画布、字体、图例、颜色、透明度和多种图片格式。宽高表示**坐标区尺寸**，外围画布自动容纳文字。
- TimesSimSun 字体获取与项目说明见 [Zhoushijiehqu/Academic-Font-TimesSimSun](https://github.com/Zhoushijiehqu/Academic-Font-TimesSimSun)，本地加载方法见 [common/fonts](common/fonts/README.md)。字体二进制不包含在公开仓库中。

## 复现图集

```powershell
# 重建合成 CSV 与数值元数据
python examples/generate_examples.py
# 通过 GUI 的绘图、保存、重开流程生成 8 个项目和 24 份图片
python examples/render_gallery.py
# 检查程序工作流
python -m unittest discover -s tests -v
```

图集导出需要桌面环境。每张图的尺寸与输出参数见[图集清单](examples/gallery_manifest.json)，数据生成参数见[数据元信息](examples/dataset_metadata.json)。具体数据模型在各子项目 README 中说明。

## 目录与后续扩展

```text
csvPLOT/                    折线图工具、详细 README、依赖入口
  examples/                 CSV、exports/ 插图、projects/ 可编辑项目
csvFIG/                     分布图工具、详细 README、依赖入口
  examples/                 CSV、exports/ 插图、projects/ 可编辑项目
common/                     共享界面与可选本地字体
docs/screenshots/           真实应用窗口与控件截图
examples/                   数据与图集生成器、元数据
tests/                      数值及 GUI 工作流检查
requirements.txt            系列依赖清单
requirementLists.txt         兼容依赖入口
LICENSE                     MIT 许可证
```

后续工具沿用独立子目录。分簇箱线图计划后续加入，当前版本尚不支持。当前系列保留绘图、平滑、样式与项目保存，不含数据变换功能。

采用 [MIT 许可证](LICENSE)。
