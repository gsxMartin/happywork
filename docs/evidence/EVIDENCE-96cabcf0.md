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
| 自动化判定为 PASS 的 AC 数 | 5（AC-6、AC-7、AC-8、AC-9、AC-11） |
| 需人工确认的 AC 数 | 6（AC-1、AC-2、AC-3、AC-4、AC-5、AC-10） |
| 测试用例总数 | 47（`python -m pytest -v` 全部通过） |

关键命令执行情况：

- `python -m pytest -v`：成功，`47 passed in 0.30s`（原始输出见文末附录；中文化修正后复跑仍为 47 passed）。
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

**判定：** PASS

说明：全屏判定逻辑 `_rect_covers` 由 4 条单元测试覆盖，`should_pop` 在全屏回调返回 True 时返回 False（`test_should_pop_false_when_fullscreen` 与离屏断言 `pop_fullscreen: False`），即检测到全屏时不弹出。附注：基于 Win32（`GetForegroundWindow`/`MonitorFromWindow`）的 OS 级全屏探测未在真实全屏应用下实测。

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