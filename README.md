# csvGUI

两个轻量的桌面绘图工具，使用 Tkinter 和 Matplotlib，可从 CSV 数据生成图表并保存绘图项目。

| 工具 | 用途 | 输入 | 项目文件 |
| --- | --- | --- | --- |
| `csvPLOT.py` | 多曲线折线图、移动平均平滑 | CSV | `.cplot` |
| `csvFIG.py` | 纵向/横向箱线图、柱状误差图、小提琴图、组合图 | CSV、结构化 TXT | `.cfig` |

## 安装与运行

需要 Python 3.10 或更高版本，并安装 Tkinter。推荐在虚拟环境中安装依赖：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python csvPLOT.py
# 或运行统计图工具
python csvFIG.py
```

macOS/Linux 可以使用 `python3`，虚拟环境激活命令为 `source .venv/bin/activate`。Linux 如缺少 Tkinter，需要安装对应 Python 版本的 Tk 包。可以用 `python -m tkinter` 检查。

## 快速试用

**折线图：** 启动 `csvPLOT.py`，选择 **Load CSV** 并打开 `examples/curves.csv`，设置 X 为 `step`、Y 为 `signal_a`，点击 **Plot / Add**。勾选 **Hold** 后可以添加 `signal_b`，也可以从其他 CSV 添加曲线。

平滑使用当前点及前面若干点的移动平均。窗口留空或设为 `1` 时关闭平滑；修改窗口后点击 **Re-smooth All Curves**，即可统一更新已添加的曲线。

**分布图：** 启动 `csvFIG.py`，打开 `examples/distributions.csv`，选择 `group_a` 并点击 **Add Data**。勾选 **Hold** 后可以添加其他列，再通过 **Plot Type** 切换图形。也可用 **Load TXT** 打开 `examples/distributions.txt`，一次导入多个分布。

**调整样式：** 侧栏可设置颜色、尺寸、字体、字号和坐标范围。**Advanced Settings** 中可设置标题、坐标标签、网格和数据项的显示顺序等。默认字体使用 Matplotlib 自带的 DejaVu Sans；绘制中文时请选择本机安装的中文字体。

**保存：** 图表上方工具栏的保存按钮用于导出 PNG、SVG、PDF 等图片；**Save Project** 保存数据和样式，**Open Project** 可继续编辑。项目文件包含已绘制数据，无需依赖原 CSV 路径。

柱状误差图的柱高是均值，误差范围使用箱线图的上下须，并非置信区间。所有示例数据均为人工构造的演示数据。

## 本版本的范围

此版本以原 `csvPLOT.py` 和 `csvFIG.py` 为基础整理。

- 保留 CSV 导入、多组叠加、平滑、样式设置、图例、项目保存和图片导出。
- 保留 csvFIG 的五种图形及结构化 TXT 导入。
- 移除 LP 曲线变换、曲线加权合成、分布线性映射和统计值手工编辑。
- 移除根据汇总统计值自动生成替代观测数据的逻辑。
- 不包含 `csvPLOT_v2.py` 的批量导入界面，也不包含 `seqPLOT.py`。

普通 v1 `.cplot` 项目可以继续打开。旧文件中的 LP 配置不再执行；已经保存在曲线数组中的数据会作为普通曲线读取。日期和文本 X 轴会在新项目中记录轴类型。

`.cfig` 项目必须包含原始观测数组，载入时会重新计算统计值。仅有汇总统计值的旧项目需要重新导入 CSV/TXT；手工修改过的汇总统计值不会覆盖原始观测。项目里已经保存的映射结果会作为普通观测数据读取。

## 文件

```text
csvPLOT.py          折线图工具
csvFIG.py           分布图工具
_txt_io.py          csvFIG 的 TXT 读取模块，需要与脚本放在一起
requirements.txt    Python 依赖
examples/           演示数据
tests/              绘图与项目保存/重开测试
```

## 检查

在有桌面环境的电脑中运行：

```powershell
python -m unittest discover -s tests -v
```

测试会创建临时 Tk 窗口，并使用临时目录验证项目保存和图片导出。无显示服务器的 Linux 环境需使用虚拟显示服务器运行 GUI 测试。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。源代码仓库：[lbsun1999/csvGUI](https://github.com/lbsun1999/csvGUI)。
