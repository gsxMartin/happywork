# 找点乐子（happywork）

常驻 Windows 系统托盘的小工具：在工作时段以随机间隔弹出**单条中文趣味内容卡片**（冷笑话 / 脑筋急转弯 / 冷知识 / 妙语），以「不打扰、一眼看完」为原则，给枯燥的上班时光一点小惊喜。只推乐子，不推新闻。

## 特性

- 常驻托盘，不占任务栏；卡片无边框、屏幕右下角淡入淡出，**不抢键盘焦点**
- 工作时段（默认工作日 9:30–18:30）内按随机间隔（默认 40~90 分钟）弹出
- 内容来源：本地内容库（36 条打底）+ **中文趣味接口**（一言 · 抖机灵 / 毒鸡汤 / 趣味一言），两者混池随机；断网自动降级为纯本地。**不含任何资讯/新闻来源**
- 卡片操作：「再来一个」「收藏」「安静一会」；收藏内容可从托盘「收藏夹」回看
- 全屏、或空闲超过 2 分钟时自动抑制，不打扰
- 短时间内不重复推送同一条内容

## 环境要求

- Windows
- Python >= 3.14

## 安装与运行

### 方式一：源码运行（开发用）

```powershell
python -m pip install -e .
lezi
```

### 方式二：不安装，临时运行

```powershell
$env:PYTHONPATH="src"; python -m lezi
```

> 方式一、二都会附带一个黑色控制台窗口，关掉它程序即退出。要真正后台常驻、不出现控制台窗口，用方式三或方式四。

### 方式三：无控制台后台运行（本机常驻）

```powershell
pythonw -m lezi
```

需要开机自启时：`Win+R` 输入 `shell:startup` 打开启动文件夹，把上面命令做成快捷方式放进去。

### 方式四：打包成 exe（分发用，目标机器无需 Python 环境）

首次需安装打包依赖：

```powershell
python -m pip install "pyinstaller>=6.10"
```

之后双击 `build.bat`（或在命令行执行 `.\build.bat`）即可，它会先清理旧产物再打包：

```powershell
.\build.bat
```

也可以跳过脚本直接调 PyInstaller：

```powershell
python -m PyInstaller lezi.spec --noconfirm
```

产物：`dist/lezi/lezi.exe`（连 **同目录的 `_internal/` 一起**拷贝分发；整个文件夹约 20MB）。

- 双击 `lezi.exe` 即启动，**无控制台窗口**
- `config.json`、`state.json` 生成在 `lezi.exe` 同级目录，可直接编辑
- 把整个 `dist/lezi` 文件夹拷到其他 Windows 机器即可运行，无需安装 Python 与任何依赖

## 配置

`config.json` 缺失或损坏时回退为默认值。字段含义：

| 字段 | 含义 | 默认值 |
| --- | --- | --- |
| `work_start` / `work_end` | 工作时段 | `09:30` / `18:30` |
| `work_days` | 生效星期（0 = 周一） | `[0, 1, 2, 3, 4]` |
| `interval_min_minutes` / `interval_max_minutes` | 推送间隔随机区间（分钟） | `40` / `90` |
| `card_seconds` | 卡片停留秒数 | `15` |
| `snooze_minutes` | 「安静一会」时长（分钟） | `60` |

也可从托盘右键菜单 →「设置」修改。

## 开发

```powershell
python -m pip install -e ".[test]"
$env:PYTHONPATH="src"; python -m pytest -q
```

## 许可证

见 [LICENSE](LICENSE)。