---
id: DESIGN-96cabcf0
title: 找点乐子 —— 设计文档
status: approved
req_ref: REQ-96cabcf0
feat_ref: FEAT-96cabcf0
selected_approach: PySide6 自绘卡片
---

# 1. 意图与缘由

上班时间长且枯燥。需要一个常驻后台、以随机间隔、用不打扰的方式推送**单条**趣味内容的 Windows 桌面小工具，为枯燥的工作带来轻量的「小惊喜」。实现语言：Python。

# 2. 目标 / 非目标 / 反目标

**目标**
- 常驻系统托盘，任务栏不出现常驻窗口
- 工作时段内按随机间隔弹出单条趣味卡片，自动消失
- 内容类型：冷笑话 / 脑筋急转弯（先题后答案）/ 冷知识 / 趣闻·新闻
- 本地内容库 + 联网抓取并重，离线时自动降级为纯本地
- 卡片操作：「再来一个」「收藏」「安静一会」；收藏内容可回看
- 不抢键盘焦点；全屏/演示/会议场景自动抑制
- 短时间内不重复推送同一条内容

**非目标（首版不做）**
- 偏好学习（越爱看越推）、「今日乐子」汇总视图
- 账号系统、社交分享、移动端、海量内容库

**反目标（即使能运行也算失败）**
- 抢焦点、打断当前操作、开会时乱弹、刷屏
- 反复推同一条内容；离线直接哑火
- 卡片卡顿或粗糙，反而增添烦躁

# 3. 选定方案

**PySide6 自绘卡片**：单进程 Qt 应用。`QSystemTrayIcon` 常驻托盘；随机定时器到期后弹出**无边框、圆角、半透明**卡片窗口（`QWidget` + `Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint`，并设置 `Qt.WA_ShowWithoutActivating` 以确保不抢焦点），以 200ms 淡入、停留 `card_seconds` 秒、再以 200ms 淡出关闭。

选择理由：本产品的核心价值是「卡片好看且可交互」，只有自绘窗口才能同时满足视觉质感与「脑筋急转弯揭示答案 / 再来一个 / 收藏」等交互；托盘控制与多显示器定位在 Qt 下也最可靠。

**候选方案（已否决）**
- *Tkinter + pystray 极简派*：依赖最少，但卡片视觉朴素、圆角/阴影/淡入淡出难做，削弱「惊喜感」。
- *pystray + Windows 原生 Toast*：实现最轻且天然不打扰，但无法承载卡片内的揭示与按钮交互，内容长度也受限。

# 4. 架构 / 模块

- `app`：程序入口、生命周期、托盘控制器（TrayController）
- `scheduler`：工作时段判断 + 随机间隔
- `content`：内容层——本地库（ContentStore）+ 联网抓取（FeedFetcher）+ 统一模型 `ContentItem`
- `ui`：卡片窗口（CardWindow）、设置窗口（SettingsWindow）、收藏夹窗口（FavoritesWindow）
- `state`：配置与持久化（配置、收藏、已看历史）
- `platform`：平台集成——全屏检测、空闲检测（Windows）

**数据流**：scheduler 触发 → content 取一条未看过的内容（优先联网、否则本地，基于去重窗口）→ ui 渲染卡片 → 用户操作（再来一个 / 收藏 / 安静一会）→ state 持久化。

# 5. 关键接口

- `ContentItem`: {id, type, title, body, answer(可选), source, url, fetched_at}
- `ContentProvider.next_item() -> ContentItem | None`
- `Scheduler.next_delay_seconds() -> float`；`Scheduler.in_work_hours(now) -> bool`
- `CardWindow.show_item(item)`；`build_card_view(item, reveal) -> CardView`
- `FavoritesWindow(items)`；`favorites_to_rows(items) -> list[str]`
- `StateStore`: 加载/保存配置；`add_favorite(item)`；`favorites()`；`mark_seen(id)`；`is_seen(id) -> bool`；`snooze_until()`；`set_snooze(until)`

# 6. 内容来源与流程

- **本地库**：JSON 文件，作为打底内容，便于人工扩充
- **联网**：RSS / 公开接口抓取趣闻与新闻；具体来源清单在计划阶段确定
- **去重**：以 `id` 维护已看历史，短窗口内不重复推送
- **降级**：抓取超时或失败时，退回本地库

# 7. 错误处理

- 无网络 / 超时：捕获异常，降级到本地内容库
- 取内容为空：本轮不弹，等待下一轮
- 卡片渲染异常：记录日志，托盘与调度不受影响

# 8. 测试策略

- **单元测试（pytest）**：调度器的时段与随机间隔逻辑、去重逻辑、内容模型、降级逻辑——均可通过注入**假时钟**与**假数据源**实现确定性测试
- **集成/手动验证**：托盘启动、卡片显示与自动消失、全屏抑制、收藏回看
- 所有涉及时间与网络的逻辑必须可注入替身，避免不确定性

# 9. 配置默认值

- 工作时段：工作日 9:30–18:30
- 推送间隔：40~90 分钟随机
- 卡片停留：约 15 秒
- 「安静一会」：暂停 60 分钟

# 10. 计划阶段已确定

- **联网来源清单**：初版使用可配置 RSS 列表，且**全部为中文来源**：奇客资讯 Solidot（`https://www.solidot.org/index.rss`）、少数派（`https://sspai.com/feed`）、科技爱好者周刊（`https://www.ruanyifeng.com/blog/atom.xml`）；实现阶段已实测可达。曾考虑的 BBC World 因内容为英文、煎蛋（`https://jandan.net/feed`）因返回 403 而未采用；来源可按需增删。
- **卡片视觉**：出现在屏幕**右下角**（距边缘 24px）；深色半透明圆角卡片（圆角 16px）；正文中文字体「微软雅黑」；强调色 `#FFB74D`；淡入/淡出各 200ms。
- **打包**：采用 PyInstaller **目录模式（onedir）+ 无控制台窗口**。配置见仓库根 `lezi.spec`，构建命令 `python -m PyInstaller lezi.spec --noconfirm`，产物 `dist/lezi/lezi.exe`（分发时需带上同目录的 `_internal/`）。运行期 `config.json` / `state.json` 落在 exe 同级目录，本地内容库从 `sys._MEIPASS/resources` 读取（实现见 `app.py` 的 `_base_dir()` / `_resource_path()`）。构建脚本为仓库根 `build.bat`（先清理 `build/` 与 `dist/lezi` 再执行打包），亦可直接运行 `python -m PyInstaller lezi.spec --noconfirm`。打包入口为仓库根 `lezi_entry.py`——`src/lezi/__main__.py` 使用相对导入，只能配合 `python -m lezi`，不能直接作为 PyInstaller 的入口脚本。