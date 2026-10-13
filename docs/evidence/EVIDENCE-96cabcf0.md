---
id: EVIDENCE-96cabcf0
feature: 找点乐子
date: 2026-10-12
---

# 验收证据 · REQ-96cabcf0「找点乐子」

本文件记录 REQ-96cabcf0 共 11 条 Acceptance Criteria 的逐条核验证据。所有输出均为命令的原始、未经改写的输出；仅当存在自动化代理证据（单元测试 / 离屏断言 / 命令行输出）时才判定 PASS，凡只能靠真实桌面或人工观察确认的项目一律标注「需人工确认」，并给出精确的人工验证步骤。

## 证据摘要

| 项目 | 数值 |
| --- | --- |
| 总 AC 数 | 11 |
| 自动化判定为 PASS 的 AC 数 | 4（AC-6、AC-8、AC-9、AC-11） |
| 需人工确认的 AC 数 | 7（AC-1、AC-2、AC-3、AC-4、AC-5、AC-7、AC-10） |
| 测试用例总数 | 47（验收阶段）；后续打包新增 4 条、缺陷修复新增 3 条，现为 54 条，见文末补记 |

> 2026-10-13 更正：AC-7 原被判定为「自动化 PASS」，复查发现其真实探测路径（`is_fullscreen()`）因常量引用错误恒返回 `False`，属于「用替身测通过、真实路径失效」的假 PASS，现改列为需人工确认并已修复，详见文末「补记：人工验证发现的缺陷与修复」。

关键命令执行情况：

- `python -m pytest -v`：成功，`47 passed in 0.30s`（原始输出见文末附录，为验收阶段所录；中文化修正后复跑仍为 47 passed）。
- `python -m lezi --version`：直接运行**失败**（`No module named lezi`，因包在 `src/` 下且未安装）；补 `PYTHONPATH=src` 后成功输出 `lezi 0.1.0`。
- 离屏冒烟脚本 `$env:TEMP\lezi_smoke.py`：成功，退出码 0，全部断言输出见 AC-3/AC-5/AC-6/AC-7 各节。
- `git log --oneline`：17 个提交，提交信息**全部为中文**，覆盖模型/调度/状态/内容库/抓取/提供者/界面/装配。
- `git status --short`：无输出，工作区干净。

---

## AC-1: 程序启动后常驻系统托盘，任务栏不出现常驻窗口

**命令：** `$env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="src"; python $env:TEMP\lezi_smoke.py`（片段）

**输出：**
```
tray_setup_ok: True
```

**判定：** 需人工确认

说明：离屏代理证据仅证明托盘控制器可无异常构造并调用 `setup()`（`src/lezi/ui/tray.py` 中创建 `QSystemTrayIcon` 并 `show()`）；代码层面主窗口为 `CardWindow`（`Qt.Tool` 标志，不进入任务栏）。但「托盘图标真实出现在 Windows 通知区域」「任务栏无常驻窗口」只能靠真实桌面观察确认，故不谎报 PASS。

---

## AC-2: 在工作时段内按随机间隔（默认 40~90 分钟，可配置）自动弹出内容卡片

**命令：** `python -m pytest -v`（片段）+ `$env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="src"; python $env:TEMP\lezi_smoke.py`（片段）

**输出：**
```
tests/test_scheduler.py::test_weekday_boundaries PASSED                  [ 63%]
tests/test_scheduler.py::test_weekend_is_not_work_hours PASSED           [ 65%]
tests/test_scheduler.py::test_next_delay_seconds_range_and_reproducible PASSED [ 68%]
tests/test_scheduler.py::test_overnight_and_malformed_time PASSED        [ 70%]
tests/test_app.py::test_should_pop_true_in_work_hours PASSED             [  2%]
tests/test_app.py::test_should_pop_false_outside_hours PASSED            [  4%]
```
```
pop_in_hours: True
pop_out_hours: False
```

**判定：** 需人工确认

说明：默认随机间隔 40~90 分钟（`Config.interval_min_minutes=40` / `interval_max_minutes=90`）、工作时段判定与「时段内应弹、时段外不应弹」的逻辑已由单元测试与离屏断言自动化 PASS（`test_next_delay_seconds_range_and_reproducible` 断言 2400s≤delay≤5400s）。但「到点自动弹出内容卡片」这一真实运行行为依赖真实桌面长时运行观察，故整体判定为需人工确认。

---

## AC-3: 弹出的卡片不抢占键盘焦点、不阻塞用户当前操作

**命令：** `$env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="src"; python $env:TEMP\lezi_smoke.py`（片段）

**输出：**
```
card_flags_int: 264203
has_FramelessWindowHint: True
has_Tool: True
has_WindowStaysOnTop: True
WA_ShowWithoutActivating: True
```

**判定：** 需人工确认

说明：离屏断言证明卡片实设了无边框（`FramelessWindowHint`）、工具窗口（`Tool`，不占任务栏、不抢激活）、置顶（`WindowStaysOnTopHint`）窗口标志与 `WA_ShowWithoutActivating` 属性，与「不抢焦点」的实现意图一致（`src/lezi/ui/card.py`）。但「真实不抢占键盘焦点、不阻塞当前操作」必须在真实桌面以键盘输入实测确认，故不谎报 PASS。

---

## AC-4: 卡片在若干秒后自动消失，无需用户操作

**命令：** 代码核查 `src/lezi/ui/card.py`（无对应自动化测试）

**输出：**
```
119	        self._timer = QTimer(self)
120	        self._timer.setSingleShot(True)
121	        self._timer.timeout.connect(self._close_with_fade)
...
165	    def show_item(self, item: ContentItem) -> None:
...
172	        self._timer.start(self.cfg.card_seconds * 1000)
```
```
Config 默认值：card_seconds: int = 15
```

**判定：** 需人工确认

说明：代码显示 `show_item` 会以 `cfg.card_seconds`（默认 15 秒）启动单次定时器，超时后淡出关闭。但该「真实自动消失」行为未有任何自动化测试覆盖，只能靠真实桌面观察，故标注需人工确认。

---

## AC-5: 卡片提供「再来一个」「收藏」「安静一会」三个操作

**命令：** `$env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="src"; python $env:TEMP\lezi_smoke.py`（片段）

**输出：**
```
card_signals: True True True
```

**判定：** 需人工确认

说明：离屏断言证明卡片具备 `next_requested`、`favorite_requested`、`snooze_requested` 三个信号（分别对应「再来一个」「收藏」「安静一会」按钮，见 `src/lezi/ui/card.py`）。但「真实按钮点击并触发对应行为」属于人工交互，故整体标注需人工确认。

---

## AC-6: 内容类型至少覆盖：冷笑话、脑筋急转弯（先题后答案，可点击揭示）、冷知识、趣闻/新闻

**命令：** `python -m pytest -v`（片段）+ 冒烟脚本（片段）+ 本地内容库核查

**输出：**
```
tests/test_card_view.py::test_riddle_hides_answer_before_reveal PASSED   [ 12%]
tests/test_card_view.py::test_riddle_shows_answer_after_reveal PASSED    [ 14%]
tests/test_card_view.py::test_joke_never_shows_answer PASSED             [ 17%]
```
```
riddle_hidden_answer: None
riddle_shown_answer: 答
joke_show_answer: False
```
```
src/lezi/models.py 中 ContentType = { JOKE, RIDDLE, TRIVIA, NEWS }
resources/content_local.json 覆盖类型：joke×2、riddle×2、trivia×2
app.py FEEDS 抓取来源条目类型为 NEWS
```

**判定：** PASS

说明：四类内容类型（冷笑话 JOKE / 脑筋急转弯 RIDDLE / 冷知识 TRIVIA / 趣闻·新闻 NEWS）在枚举、本地内容库与在线抓取（NEWS）中均已覆盖；「先题后答案」的揭示语义由 `test_riddle_hides_answer_before_reveal`、`test_riddle_shows_answer_after_reveal` 及离屏断言自动化验证。附注：真实的「点击『看答案』按钮揭示」交互仍需人工确认。

---

## AC-7: 检测到全屏应用/演示/会议场景时，自动推迟或不弹出

**命令：** `python -m pytest -v`（片段）+ 冒烟脚本（片段）

**输出：**
```
tests/test_app.py::test_should_pop_false_when_fullscreen PASSED          [  6%]
tests/test_win.py::test_rect_covers_equal_is_true PASSED                 [ 93%]
tests/test_win.py::test_rect_covers_slightly_smaller_is_false PASSED     [ 95%]
tests/test_win.py::test_rect_covers_larger_is_true PASSED                [ 97%]
tests/test_win.py::test_rect_covers_negative_and_slightly_smaller PASSED [ 99%]
```
```
pop_fullscreen: False
```

**判定：** 代码级 PASS，真实全屏应用下需人工确认

说明：本项在验收阶段曾被误判为 PASS。复查发现 `is_fullscreen()` 中引用了不存在的 `win32api.MONITOR_DEFAULTTONEAREST`（该常量实际位于 `win32con`），该行必然抛 `AttributeError` 并被 `except Exception` 吞掉，导致函数**恒返回 False**——真实的全屏探测从未生效，仅在注入替身的单元测试中显示「通过」。已修复为 `win32con.MONITOR_DEFAULTTONEAREST`，并新增 2 条直接覆盖真实 `is_fullscreen()` 的测试（注入 `GetForegroundWindow`/`GetWindowRect`/`MonitorFromWindow`/`GetMonitorInfo`）。`_rect_covers` 仍由原有 4 条单元测试覆盖。仍未实测的部分：真实全屏应用（视频播放 / F11 全屏 / 放映）下是否确实抑制。

---

## AC-8: 短时间内不重复推送同一条内容

**命令：** `python -m pytest -v`（片段）

**输出：**
```
tests/test_state.py::test_mark_seen_then_is_seen PASSED                  [ 78%]
tests/test_provider.py::test_skips_seen_online_in_favor_of_fresh_online PASSED [ 55%]
tests/test_provider.py::test_all_seen_falls_back_to_any_local PASSED     [ 51%]
```

**判定：** PASS

说明：`StateStore` 的已见集合（seen）与 `ContentProvider.next_item` 优先挑选未见过内容、仅在全部见过时才从本地兜底，均由自动化测试覆盖，证明短时间内不会重复推送同一条内容。

---

## AC-9: 无网络时仍可从本地内容库正常推送

**命令：** `python -m pytest -v`（片段）

**输出：**
```
tests/test_provider.py::test_falls_back_to_local_when_online_empty PASSED [ 48%]
tests/test_provider.py::test_falls_back_to_local_when_fetcher_is_none PASSED [ 57%]
tests/test_provider.py::test_falls_back_to_local_when_fetch_raises PASSED [ 59%]
tests/test_store.py::test_load_count PASSED                              [ 87%]
tests/test_store.py::test_missing_file_returns_empty PASSED              [ 91%]
```

**判定：** PASS

说明：当在线抓取为空、无 fetcher、或抓取抛异常（模拟断网）时，提供者均回退到本地内容库并成功取到条目；本地库加载亦有测试覆盖。

---

## AC-10: 有网络时能抓取外部来源的趣闻/新闻，无网络时自动降级到本地内容库

**命令：** `python -m pytest -v`（片段）+ 代码核查 `src/lezi/content/fetcher.py` + 真实联网抓取

**输出：**
```
tests/test_fetcher.py::test_fetch_parses_entries PASSED                  [ 31%]
tests/test_fetcher.py::test_fetch_respects_limit PASSED                  [ 34%]
tests/test_fetcher.py::test_fetch_skips_garbage_source PASSED            [ 36%]
tests/test_fetcher.py::test_fetch_skips_garbage_bytes_returns_empty PASSED [ 38%]
```
```
provider.py next_item(): 先在线、无新鲜在线再回退本地；fetcher.fetch() 抛异常则 online=[]
```
```
$env:PYTHONPATH="src"; python -c "from lezi.app import FEEDS; from lezi.content.fetcher import FeedFetcher; ..."
FEEDS = ['https://www.solidot.org/index.rss', 'https://sspai.com/feed', 'https://www.ruanyifeng.com/blog/atom.xml']
fetched = 6
 - 趣闻 | rss | 固态硬盘价格一年翻了两番
 - 趣闻 | rss | 全球汽油汽车销量首次低于五成
 - 趣闻 | rss | 微软在 Qwen 模型基础上推出决策模型 Microsoft-Decision-
 - 趣闻 | rss | FAST 发现一个脉冲星三星系统
 - 趣闻 | rss | 英国水果蔬菜营养价值下降最高五成
 - 趣闻 | rss | LineageOS 24 释出
```

**判定：** 需人工确认

说明：RSS 解析与按源容错（单源失败不影响其它源）已由单元测试自动化 PASS（使用注入的 `fetch_fn`）；**真实联网抓取**已用真实代码路径（`FeedFetcher` + `app.FEEDS`）实测三个**中文**来源，均成功返回条目，`source="rss"`、类型为「趣闻」；「无网络降级」逻辑由 AC-9 覆盖。仍待人工确认的部分：程序实际运行时，托盘环境下是否真的弹出这类 RSS 条目。

---

## AC-11: 被收藏的内容可再次查看

**命令：** `python -m pytest -v`（片段）+ 冒烟脚本（片段）

**输出：**
```
tests/test_state.py::test_favorites_roundtrip PASSED                     [ 80%]
tests/test_favorites.py::test_favorites_to_rows_labels_type_and_title PASSED [ 27%]
tests/test_favorites.py::test_favorites_to_rows_empty PASSED             [ 29%]
```
```
favorites_rows: ['[冷笑话] 笑话', '[脑筋急转弯] 题']
```

**判定：** PASS

说明：收藏内容可持久化并重新加载（`test_favorites_roundtrip`），且能渲染为收藏夹列表行（`favorites_to_rows` + `FavoritesWindow`，由 2 条测试与离屏断言覆盖），证明被收藏内容可再次查看。附注：从托盘菜单真实打开收藏夹窗口并肉眼查看仍需人工确认。

---

## 附：`python -m pytest -v` 完整原始输出

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\guoshixuan\AppData\Local\Programs\Python\Python314\python.exe
cachedir: .pytest_cache
rootdir: D:\Python工具\找点乐子
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.12.1, langsmith-0.12.1
collecting ... collected 47 items

tests/test_app.py::test_should_pop_true_in_work_hours PASSED             [  2%]
tests/test_app.py::test_should_pop_false_outside_hours PASSED            [  4%]
tests/test_app.py::test_should_pop_false_when_fullscreen PASSED          [  6%]
tests/test_app.py::test_should_pop_false_when_idle PASSED                [  8%]
tests/test_app.py::test_should_pop_snooze_boundary PASSED                [ 10%]
tests/test_card_view.py::test_riddle_hides_answer_before_reveal PASSED   [ 12%]
tests/test_card_view.py::test_riddle_shows_answer_after_reveal PASSED    [ 14%]
tests/test_card_view.py::test_joke_never_shows_answer PASSED             [ 17%]
tests/test_config.py::test_default_config_values PASSED                  [ 19%]
tests/test_config.py::test_load_missing_file_returns_default PASSED      [ 21%]
tests/test_config.py::test_save_then_load_roundtrip PASSED               [ 23%]
tests/test_config.py::test_load_corrupt_json_returns_default PASSED      [ 25%]
tests/test_favorites.py::test_favorites_to_rows_labels_type_and_title PASSED [ 27%]
tests/test_favorites.py::test_favorites_to_rows_empty PASSED             [ 29%]
tests/test_fetcher.py::test_fetch_parses_entries PASSED                  [ 31%]
tests/test_fetcher.py::test_fetch_respects_limit PASSED                  [ 34%]
tests/test_fetcher.py::test_fetch_skips_garbage_source PASSED            [ 36%]
tests/test_fetcher.py::test_fetch_skips_garbage_bytes_returns_empty PASSED [ 38%]
tests/test_models.py::test_make_id_is_stable_and_normalizes_whitespace PASSED [ 40%]
tests/test_models.py::test_to_dict_from_dict_roundtrip PASSED            [ 42%]
tests/test_models.py::test_from_dict_restores_enum_from_string PASSED    [ 44%]
tests/test_provider.py::test_prefers_fresh_online PASSED                 [ 46%]
tests/test_provider.py::test_falls_back_to_local_when_online_empty PASSED [ 48%]
tests/test_provider.py::test_all_seen_falls_back_to_any_local PASSED     [ 51%]
tests/test_provider.py::test_empty_everything_returns_none PASSED        [ 53%]
tests/test_provider.py::test_skips_seen_online_in_favor_of_fresh_online PASSED [ 55%]
tests/test_provider.py::test_falls_back_to_local_when_fetcher_is_none PASSED [ 57%]
tests/test_provider.py::test_falls_back_to_local_when_fetch_raises PASSED [ 59%]
tests/test_provider.py::test_next_item_does_not_mark_seen PASSED         [ 61%]
tests/test_scheduler.py::test_weekday_boundaries PASSED                  [ 63%]
tests/test_scheduler.py::test_weekend_is_not_work_hours PASSED           [ 65%]
tests/test_scheduler.py::test_next_delay_seconds_range_and_reproducible PASSED [ 68%]
tests/test_scheduler.py::test_overnight_and_malformed_time PASSED        [ 70%]
tests/test_settings.py::test_config_to_form_fields PASSED                [ 72%]
tests/test_settings.py::test_form_to_config_roundtrip PASSED             [ 74%]
tests/test_settings.py::test_form_to_config_casts_strings PASSED         [ 76%]
tests/test_state.py::test_mark_seen_then_is_seen PASSED                  [ 78%]
tests/test_state.py::test_favorites_roundtrip PASSED                     [ 80%]
tests/test_state.py::test_snooze_roundtrip_and_persist PASSED            [ 82%]
tests/test_state.py::test_load_corrupt_state_resets PASSED               [ 85%]
tests/test_store.py::test_load_count PASSED                              [ 87%]
tests/test_store.py::test_by_type_filters PASSED                         [ 89%]
tests/test_store.py::test_missing_file_returns_empty PASSED              [ 91%]
tests/test_win.py::test_rect_covers_equal_is_true PASSED                 [ 93%]
tests/test_win.py::test_rect_covers_slightly_smaller_is_false PASSED     [ 95%]
tests/test_win.py::test_rect_covers_larger_is_true PASSED                [ 97%]
tests/test_win.py::test_rect_covers_negative_and_slightly_smaller PASSED [ 99%]

============================= 47 passed in 0.30s ==============================
```

## 附：其他命令的完整原始输出

**`python -m lezi --version`（未设 PYTHONPATH，原始失败输出）**
```
C:\Users\guoshixuan\AppData\Local\Programs\Python\Python314\python.exe: No module named lezi
```
（退出码 1；原因：包位于 `src/` 下且未 `pip install`。）

**`$env:PYTHONPATH="src"; python -m lezi --version`（补充运行，成功输出）**
```
lezi 0.1.0
```
（退出码 0。）

**`$env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="src"; python $env:TEMP\lezi_smoke.py`（离屏冒烟脚本完整输出）**
```
card_flags_int: 264203
has_FramelessWindowHint: True
has_Tool: True
has_WindowStaysOnTop: True
WA_ShowWithoutActivating: True
card_signals: True True True
riddle_hidden_answer: None
riddle_shown_answer: 答
joke_show_answer: False
tray_setup_ok: True
favorites_rows: ['[冷笑话] 笑话', '[脑筋急转弯] 题']
pop_in_hours: True
pop_out_hours: False
pop_fullscreen: False
pop_idle: False
```
（退出码 0。）

**`git log --oneline`**
```
a340305 修复：界面文案、文档与联网来源统一改为中文
3385d67 合并：合并远程 main 分支
0c0d739 文档：补充 REQ-96cabcf0 的验收证据
6dfcc2d 修复：托盘图标改用 QApplication 样式并保持子窗口引用
114af25 功能：应用装配、调度循环与命令行入口
7d9d29b 功能：内容提供器（优先联网、回落本地）
1a909e9 功能：托盘控制器、设置与收藏夹窗口
1d2b5a4 功能：卡片视图与无边框不抢焦点窗口
5ecae7e 功能：RSS 抓取与逐源容错
f81e699 功能：本地内容库
8794418 功能：已看/收藏/暂停的持久化状态存储
7db28a7 功能：工作时段与随机间隔调度
9156191 功能：内容模型与稳定标识
4a9e27f 功能：项目骨架与配置读写
37aa497 功能：Windows 全屏与空闲检测
ad3bc79 维护：初始化仓库与 devflow/superpowers 流程文档
6b6feac 首次提交
```

**`git status --short`**
```
（无任何输出，工作区干净）
```

---

## 人工验证清单

以下项目需在真实 Windows 桌面上运行 `python -m lezi`（先安装依赖并设 `$env:PYTHONPATH="src"`）后人工观察：

1. **AC-1 常驻托盘 / 无任务栏窗口**
   启动后查看 Windows 通知区域是否出现「找点乐子」托盘图标；确认任务栏**未**出现常驻应用窗口；右键托盘图标应弹出菜单（暂停 1 小时 / 收藏夹 / 设置 / 退出）。
2. **AC-2 随机间隔自动弹出**
   为缩短验证时间，可临时用「设置」把 `work_start` 改为当前时间之前、`interval_min`/`interval_max` 改为 1 分钟；确认工作时间段内到点自动弹出卡片，非工作时段不弹。
3. **AC-3 不抢焦点 / 不阻塞**
   弹出卡片时继续在当前应用（如记事本/浏览器）中打字，确认光标与输入焦点不被卡片夺走、操作不受阻。
4. **AC-4 自动消失**
   卡片弹出后不做任何操作，等待约 15 秒（`card_seconds`），确认卡片自动淡出消失。
5. **AC-5 三个操作**
   逐一点击「再来一个」（应切换下一条）、「收藏」（应写入收藏、可在收藏夹中看到）、「安静一会」（应暂停推送一段时间，默认 60 分钟）。
6. **AC-6 脑筋急转弯交互**
   遇到脑筋急转弯卡片时，确认默认只显示题面；点击「看答案」按钮后答案才出现。
7. **AC-7 全屏不打扰**
   让某应用进入全屏（如视频播放/F11 全屏），确认该期间不弹出卡片；退出全屏后恢复。
8. **AC-10 真实联网抓取**
   在有网络环境下观察是否推送来自 RSS 来源（`source="rss"`）的新闻条目；断网后确认仍能推送本地内容库条目而不报错。

---

## 补记：打包（PyInstaller）验证

本节记录验收之后追加的打包工作，不属于 REQ 的 11 条 AC，仅作交付方式的证据记录。

**新增测试 4 条**（`tests/test_app.py`，TDD：先失败后通过；覆盖冻结模式的路径解析）

```
$env:PYTHONPATH="src"; python -m pytest -q
51 passed in 0.27s
```

**安装构建依赖**

```
python -m pip install "pyinstaller>=6.10"
Successfully installed altgraph-0.17.5 pefile-2024.8.26 pyinstaller-6.22.3 pyinstaller-hooks-contrib-2026.8 pywin32-ctypes-0.2.3 setuptools-84.0.0
```

**构建**

```
python -m PyInstaller lezi.spec --noconfirm
Build complete! The results are available in: D:\Python工具\找点乐子\dist
```

**产物核对**

```
dist/lezi/ 下内容：lezi.exe、_internal
dist/lezi/_internal/resources/content_local.json 存在：True
整个 dist/lezi 体积：19.3 MB
```

**可启动性**

```
lezi.exe --version                 → 退出码 0
lezi.exe（启动后观察 6 秒）        → 进程存活，未提前退出
```

**过程中发现并修复的问题**

- 首次构建产物启动即退出（退出码 1）。因 spec 原以 `src/lezi/__main__.py` 为入口，而该文件使用相对导入（`from .app import main`），仅适用于 `python -m lezi`；被 PyInstaller 当作顶层脚本执行时报
  `ImportError: attempted relative import with no known parent package`（用带控制台的临时构建复现得到）。
  修复：新增仓库根 `lezi_entry.py` 作为绝对导入的打包入口，spec 的 Analysis 指向它。

- 打包脚本 `build.bat` 首次运行时中文行导致 cmd 解析错位（`if exist` 被读成 `xist`，报 `'xist' is not recognized`）。原因是文件为 LF 换行，而 cmd.exe 解析批处理需要 CRLF，按字节偏移读取时错位。修复：转为 CRLF 换行，并新增 `.gitattributes` 固定 `*.bat text eol=crlf`，避免检出后再次变成 LF。修复后脚本一次跑通，`exit=0`，中文输出无乱码。

**打包脚本验证**

```
.\build.bat        → exit=0
[1/3] 清理旧产物...
[2/3] 打包中（目录模式 + 无控制台窗口）...
[3/3] 打包完成。
产物：dist\lezi\lezi.exe
```

```
dist/lezi/ 下内容：lezi.exe、_internal
dist/lezi/lezi.exe --version  → 退出码 0
```

**判定：** 部分 PASS，需人工确认

- 已验证：冻结路径解析逻辑（4 条测试）、构建成功、资源已打入预期位置、exe 可启动且不闪退；后续补测确认打包版在 1 分钟间隔配置下 60 秒内确实弹卡（见文末「补记：人工验证发现的缺陷与修复」）。
- 待人工确认：托盘图标与右键菜单的实际观感、卡片在真实桌面下的位置与淡入淡出效果。
- 注意：本次修复（见下节）改动了 `app.py` 与 `platform/win.py`，`dist/lezi` 需**重新执行 `build.bat`** 才会包含修复；用户已持有的那份 exe 仍是修复前的构建。

---

## 补记：人工验证发现的缺陷与修复

用户在真实使用打包后的 exe 时报告两个现象。以下为按系统化调试流程（先根因调查、后修复）得到的记录。

### 缺陷 1：关闭「设置」或「收藏夹」窗口后，托盘图标消失（程序退出）

- **现象**：托盘图标正常显示，右键打开「设置」或「收藏夹」，关闭该窗口后托盘图标消失。
- **根因**：`QApplication.quitOnLastWindowClosed` 默认为 `True`，而 `Application` 从未将其置为 `False`。本程序常驻托盘、没有主窗口，关闭「设置/收藏夹」（或卡片 15 秒倒计时结束后自行关闭）即构成「最后一个窗口关闭」→ Qt 退出事件循环 → 进程结束、托盘图标消失。
- **证据**：

```
quitOnLastWindowClosed -> True
```

- **修复**：`Application.__init__` 创建 `QApplication` 后调用 `setQuitOnLastWindowClosed(False)`；退出仅由托盘菜单「退出」触发。
- **验证**：新增测试 `tests/test_app.py::test_application_keeps_running_after_last_window_closed`（先失败后通过），并离屏复现「打开设置 → 关闭」：

```
设置窗口已打开，可见: True
exec 返回码: 0 | 耗时: 815 ms
判定: 关窗后程序继续运行（修复生效）
```

（若仍会关窗即退出，`exec()` 会在关窗瞬间返回，耗时远小于 800ms。）

### 缺陷 2：全屏探测恒为 False，全屏抑制从未生效（AC-7 假 PASS 的根源）

- **根因**：`is_fullscreen()` 中引用了不存在的 `win32api.MONITOR_DEFAULTTONEAREST`（该常量实际位于 `win32con`），必然抛 `AttributeError`，又被 `except Exception: return False` 吞掉。
- **证据**：

```
win32api 有 MONITOR_DEFAULTTONEAREST 吗: False
win32con 有 MONITOR_DEFAULTTONEAREST 吗: True 2
```

- **修复**：改用 `win32con.MONITOR_DEFAULTTONEAREST`。
- **验证**：新增 `tests/test_win.py::test_is_fullscreen_true_when_window_covers_monitor`（先失败后通过）与 `::test_is_fullscreen_false_when_window_smaller_than_monitor`；实测真实调用链不再抛异常：

```
窗口矩形: (-7, -7, 1543, 919)
显示器矩形: (0, 0, 1536, 960)
结论: 调用链无异常，全屏判定真实可用（返回值 False 是「确实非全屏」）
```

### 已排除的两个猜想（均有实测证据，确认不是缺陷）

- **「最大化窗口被误判为全屏」**：实测本机可见的 5 个最大化窗口矩形均为 `(-7, -7, 1543, 919)`，显示器为 `(0, 0, 1536, 960)`，底部 919 < 960（未盖住任务栏），`_rect_covers` 判定为 False。且任务栏未自动隐藏（工作区 `(0, 0, 1536, 912)` ≠ 显示器区域 `(0, 0, 1536, 960)`）。故当前不构成误判。
  残留风险（本次未改动）：若把任务栏设为**自动隐藏**，最大化窗口将覆盖整个显示器区域而被判为全屏，从而持续抑制推送。
- **「打包后完全不弹卡」**：给打包目录写入 1 分钟间隔配置后实测，60 秒内 `state.json` 生成 `seen` 记录，进程 75 秒后仍存活：

```
state.json 已生成:
{ "seen": ["62d0929dce01cecd"], "favorites": [], "snooze_until": null }
75 秒后进程仍存活，已停止
```

  即打包后的程序弹卡链路正常；用户未见弹卡的原因是默认间隔为 40~90 分钟、尚未到时间。

**测试总数变化**：47（验收阶段）→ 51（打包）→ 54（本次缺陷修复）。