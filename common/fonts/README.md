# 本地字体

将有权使用的 `TimesSimSunRegular.ttf`、粗体或斜体文件放入本目录即可。程序启动时自动注册，不需要修改操作系统字体设置；存在 TimesSimSun 时优先作为绘图字体。

字体二进制不纳入公开 Git 仓库，也不适用项目代码的 MIT 许可证。

字体获取与项目说明：[Zhoushijiehqu/Academic-Font-TimesSimSun](https://github.com/Zhoushijiehqu/Academic-Font-TimesSimSun)。该仓库提供 `TimesSimSunRegular.ttf`，其 README 介绍了 Times New Roman 英文与 SimSun 中文的合并用途。

公众号 **阿昆的科研日常** 的[相关文章](https://mp.weixin.qq.com/s/Z--wuiasKW90wUn2dsC5kw)保留为介绍与发现渠道，不作为字体原创或最早发布的署名。这里引用字体仓库，不据此断言其为最早发布者。

上述字体仓库的 README 声明仅供个人学术研究及非商业使用，原字体版权归各自权利人。该说明不同于本项目代码的 MIT 许可证；公开下载链接也不等于字体再分发授权。本仓库继续提供加载方法和来源链接，不打包字体二进制。

当前字体内嵌许可保留了 Times New Roman、SimSun 等原字体的分发限制，并提示合并工具无法为合成字体决定许可证。没有明确的再分发授权时，公开仓库只包含字体加载代码和本说明。参见[微软字体分发说明](https://learn.microsoft.com/en-us/typography/fonts/font-faq)。

未找到 TimesSimSun 时，默认使用 Matplotlib 自带字体。打开保存了 TimesSimSun 设置的项目时，会尝试本机的 Times New Roman、SimSun 字体组合，再回退到 DejaVu Serif。
