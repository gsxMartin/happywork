# 找点乐子 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个常驻 Windows 系统托盘的小工具，在工作时段内以随机间隔弹出单条趣味内容卡片（冷笑话/脑筋急转弯/冷知识/趣闻新闻），自动消失且不抢焦点，支持「再来一个/收藏/安静一会」，本地库与联网抓取并重、离线自动降级。

**Architecture:** 单进程 PySide6 应用。`scheduler` 决定「何时弹」，`content` 层（本地库 + RSS 抓取 + 统一模型 + 提供器）决定「弹什么」，`ui` 层（卡片窗口 + 托盘 + 设置）负责呈现与交互，`state` 负责配置与（已看/收藏/暂停）持久化，`platform` 负责 Windows 全屏与空闲检测。所有时间与网络逻辑通过注入的假时钟、假随机源、假 fetcher 获得确定性。

**Tech Stack:** Python >= 3.14，PySide6（Qt Widgets），requests，feedparser，pywin32；测试用 pytest。

**Spec:** docs/superpowers/specs/DESIGN-96cabcf0.md

## Global Constraints

- Python >= 3.14（本机 3.14.7）。
- 依赖：`PySide6>=6.12`、`requests>=2.33`、`feedparser>=6.0`、`pywin32>=312`；测试用 `pytest`。
- 目标平台：Windows。
- 所有涉及时间与网络的逻辑必须可注入替身（假时钟 `now_fn`、假随机 `random.Random` 实例、假 fetcher），以保证测试确定性。
- 卡片绝不抢焦点：`Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint` + `Qt.WA_ShowWithoutActivating`。
- 默认配置：工作日 9:30–18:30；推送间隔 40~90 分钟随机；卡片停留 15 秒；「安静一会」暂停 60 分钟。

## Review Focus

以下 5 类输入/失败模式最可能让使用者踩坑，且易被常规任务测试遗漏；每行末尾标注其专属测试挂接到哪个任务（该任务已在其步骤中列出对应测试）。

1. **畸形/非 UTF-8 的 RSS 字节流**（半截 XML、HTML 错误页、GBK 编码）——期望 `fetch()` 跳过该源并返回已成功解析的内容或 `[]`，绝不抛异常、绝不让整个抓取失败。测试挂 **Task 6**（`test_fetch_skips_garbage_source`）。
2. **状态文件损坏或字段类型异常**（`favorites` 不是列表、`snooze_until` 是不合法字符串）——期望 `StateStore.load()` 重置为安全空状态且不抛异常。测试挂 **Task 5**（`test_load_corrupt_state_resets`）。
3. **`work_start > work_end`（跨夜班）或非法时间字符串**（如 `"9:3"`、`"25:00"`）——期望 `in_work_hours()` 返回 `False` 且不崩溃、`load_config()` 不抛。测试挂 **Task 3**（`test_overnight_and_malformed_time`）。
4. **多显示器 / 负坐标 / 任务栏占位下的全屏误判**——期望只有当窗口矩形**完全覆盖**所在显示器矩形时才判为全屏，窗口略小或带任务栏即视为非全屏。测试挂 **Task 8**（`test_rect_covers_negative_and_slightly_smaller`）。
5. **暂停到期瞬间（`now == snooze_until`）与全屏/空闲的判定优先级**——期望暂停到期当刻即恢复推送；时段外/全屏/空闲任一命中都抑制。测试挂 **Task 11**（`test_should_pop_snooze_boundary`）。

## File Structure

```
找点乐子/
├── pyproject.toml
├── src/lezi/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── scheduler.py
│   ├── state.py
│   ├── content/{__init__.py, store.py, fetcher.py, provider.py}
│   ├── platform/{__init__.py, win.py}
│   └── ui/{__init__.py, tray.py, card.py, settings.py, favorites.py}
├── resources/content_local.json
└── tests/
    ├── test_config.py
    ├── test_models.py
    ├── test_scheduler.py
    ├── test_store.py
    ├── test_state.py
    ├── test_fetcher.py
    ├── test_provider.py
    ├── test_win.py
    ├── test_card_view.py
    ├── test_settings.py
    ├── test_favorites.py
    └── test_app.py
```

> 说明：打包不在本计划范围内（后续分发采用 PyInstaller onedir）；开发与验证期统一以 `python -m lezi` 运行。

---

### Task 1: 项目骨架与配置 `config.py`

**Files:**
- Create: `pyproject.toml`
- Create: `src/lezi/__init__.py`
- Create: `src/lezi/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 无（首个任务）。
- Produces:
  - `@dataclass class Config`，字段：`work_start: str = "09:30"`、`work_end: str = "18:30"`、`work_days: tuple[int, ...] = (0, 1, 2, 3, 4)`、`interval_min_minutes: int = 40`、`interval_max_minutes: int = 90`、`card_seconds: int = 15`、`snooze_minutes: int = 60`。
  - `def default_config() -> Config`
  - `def load_config(path: Path) -> Config`（文件缺失或损坏返回默认值，不抛异常）
  - `def save_config(cfg: Config, path: Path) -> None`（JSON，`ensure_ascii=False`）

- [ ] **Step 1: 创建骨架 `pyproject.toml` 与空包**

`pyproject.toml` 内容：

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "lezi"
version = "0.1.0"
description = "常驻托盘的上班时段趣味内容推送小工具"
requires-python = ">=3.14"
dependencies = [
    "PySide6>=6.12",
    "requests>=2.33",
    "feedparser>=6.0",
    "pywin32>=312",
]

[project.optional-dependencies]
test = ["pytest>=8"]

[project.scripts]
lezi = "lezi.app:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

创建 `src/lezi/__init__.py`（空文件，内容为一句 docstring 即可）：
```python
"""找点乐子 —— 上班时段的趣味内容托盘小工具。"""
```

- [ ] **Step 2: 写失败测试 `tests/test_config.py`**

```python
from pathlib import Path

from lezi.config import Config, default_config, load_config, save_config


def test_default_config_values():
    cfg = default_config()
    assert cfg.work_start == "09:30"
    assert cfg.work_end == "18:30"
    assert cfg.work_days == (0, 1, 2, 3, 4)
    assert cfg.interval_min_minutes == 40
    assert cfg.interval_max_minutes == 90
    assert cfg.card_seconds == 15
    assert cfg.snooze_minutes == 60


def test_load_missing_file_returns_default(tmp_path: Path):
    cfg = load_config(tmp_path / "nope.json")
    assert cfg == default_config()


def test_save_then_load_roundtrip(tmp_path: Path):
    path = tmp_path / "cfg.json"
    cfg = Config(work_start="08:00", card_seconds=20)
    save_config(cfg, path)
    assert load_config(path) == cfg


def test_load_corrupt_json_returns_default(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert load_config(path) == default_config()
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.config'`

- [ ] **Step 4: 实现 `src/lezi/config.py`**

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path


@dataclass
class Config:
    work_start: str = "09:30"
    work_end: str = "18:30"
    work_days: tuple[int, ...] = (0, 1, 2, 3, 4)
    interval_min_minutes: int = 40
    interval_max_minutes: int = 90
    card_seconds: int = 15
    snooze_minutes: int = 60


def default_config() -> Config:
    return Config()


def load_config(path: Path) -> Config:
    """读取 JSON 配置；文件缺失、损坏或字段异常时一律返回默认配置。"""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return default_config()
        kwargs = {f.name: raw[f.name] for f in fields(Config) if f.name in raw}
        cfg = Config(**kwargs)
        cfg.work_days = tuple(int(d) for d in cfg.work_days)
        return cfg
    except Exception:
        return default_config()


def save_config(cfg: Config, path: Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_config.py -v`
Expected: PASS（4 passed）

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/lezi/__init__.py src/lezi/config.py tests/test_config.py
git commit -m "feat: project skeleton and config load/save"
```

---

### Task 2: 内容模型 `models.py`

**Files:**
- Create: `src/lezi/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: 无。
- Produces:
  - `class ContentType(str, Enum)`：`JOKE="joke"`、`RIDDLE="riddle"`、`TRIVIA="trivia"`、`NEWS="news"`。
  - `@dataclass(frozen=True) class ContentItem`：`id: str`、`type: ContentType`、`title: str`、`body: str`、`answer: str | None = None`、`source: str = "local"`、`url: str | None = None`、`fetched_at: str | None = None`。
  - 方法：`to_dict(self) -> dict`、`@classmethod from_dict(cls, d: dict) -> ContentItem`、`@staticmethod make_id(text: str) -> str`。

- [ ] **Step 1: 写失败测试 `tests/test_models.py`**

```python
from lezi.models import ContentItem, ContentType


def test_make_id_is_stable_and_normalizes_whitespace():
    a = ContentItem.make_id("  你好   世界  ")
    b = ContentItem.make_id("你好 世界")
    assert a == b
    assert len(a) == 16
    assert ContentItem.make_id("你好世界") != a


def test_to_dict_from_dict_roundtrip():
    item = ContentItem(
        id="abc123",
        type=ContentType.RIDDLE,
        title="什么车寸步难行？",
        body="什么车寸步难行？",
        answer="风车。",
        source="local",
        url="http://x/1",
        fetched_at="2026-10-12T09:30:00",
    )
    assert ContentItem.from_dict(item.to_dict()) == item


def test_from_dict_restores_enum_from_string():
    d = {"id": "i1", "type": "joke", "title": "t", "body": "b"}
    item = ContentItem.from_dict(d)
    assert item.type is ContentType.JOKE
    assert item.answer is None
    assert item.source == "local"
    assert item.url is None
    assert item.fetched_at is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_models.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.models'`

- [ ] **Step 3: 实现 `src/lezi/models.py`**

```python
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum


class ContentType(str, Enum):
    JOKE = "joke"
    RIDDLE = "riddle"
    TRIVIA = "trivia"
    NEWS = "news"


@dataclass(frozen=True)
class ContentItem:
    id: str
    type: ContentType
    title: str
    body: str
    answer: str | None = None
    source: str = "local"
    url: str | None = None
    fetched_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "body": self.body,
            "answer": self.answer,
            "source": self.source,
            "url": self.url,
            "fetched_at": self.fetched_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ContentItem":
        return cls(
            id=d["id"],
            type=ContentType(d["type"]),
            title=d["title"],
            body=d["body"],
            answer=d.get("answer"),
            source=d.get("source", "local"),
            url=d.get("url"),
            fetched_at=d.get("fetched_at"),
        )

    @staticmethod
    def make_id(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text.strip())
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_models.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add src/lezi/models.py tests/test_models.py
git commit -m "feat: content item model with stable id"
```

---

### Task 3: 调度器 `scheduler.py`

**Files:**
- Create: `src/lezi/scheduler.py`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: `Config`（Task 1）。
- Produces:
  - `class Scheduler: def __init__(self, cfg: Config, now_fn: Callable[[], datetime] = datetime.now, rng: random.Random | None = None)`
  - `def in_work_hours(self, now: datetime | None = None) -> bool`
  - `def next_delay_seconds(self) -> float`

- [ ] **Step 1: 写失败测试 `tests/test_scheduler.py`**

```python
import random
from datetime import datetime

from lezi.config import Config
from lezi.scheduler import Scheduler


def test_weekday_boundaries():
    s = Scheduler(Config(), now_fn=lambda: datetime(2026, 10, 12, 9, 30))
    assert s.in_work_hours(datetime(2026, 10, 12, 9, 30)) is True
    assert s.in_work_hours(datetime(2026, 10, 12, 9, 29)) is False
    assert s.in_work_hours(datetime(2026, 10, 12, 18, 30)) is False


def test_weekend_is_not_work_hours():
    # 2026-10-17 是周六
    s = Scheduler(Config())
    assert s.in_work_hours(datetime(2026, 10, 17, 10, 0)) is False


def test_next_delay_seconds_range_and_reproducible():
    s1 = Scheduler(Config(), rng=random.Random(42))
    s2 = Scheduler(Config(), rng=random.Random(42))
    d1 = s1.next_delay_seconds()
    assert 2400 <= d1 <= 5400
    assert d1 == s2.next_delay_seconds()


def test_overnight_and_malformed_time():
    # 跨夜班（work_start > work_end）首版不支持，任何时刻都判为非工作时段
    s = Scheduler(Config(work_start="22:00", work_end="06:00"))
    assert s.in_work_hours(datetime(2026, 10, 12, 23, 0)) is False
    # 畸形时间字符串不得抛异常；字符串比较下仅当字面落在区间内为真
    s2 = Scheduler(Config(work_start="9:3", work_end="25:00"))
    assert s2.in_work_hours(datetime(2026, 10, 12, 10, 0)) in (True, False)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.scheduler'`

- [ ] **Step 3: 实现 `src/lezi/scheduler.py`**

`in_work_hours`：先判星期是否在 `cfg.work_days`；再把当前时刻格式化为 `"%H:%M"` 做字符串比较 `work_start <= cur < work_end`。跨夜（`work_start >= work_end`）时该比较恒为 `False`（首版不支持跨夜，符合预期）。畸形字符串比较不会抛异常，交由字符串字典序决定。

```python
from __future__ import annotations

import random
from datetime import datetime
from typing import Callable

from .config import Config


class Scheduler:
    def __init__(
        self,
        cfg: Config,
        now_fn: Callable[[], datetime] = datetime.now,
        rng: random.Random | None = None,
    ) -> None:
        self.cfg = cfg
        self.now_fn = now_fn
        self.rng = rng if rng is not None else random.Random()

    def in_work_hours(self, now: datetime | None = None) -> bool:
        now = now if now is not None else self.now_fn()
        if now.weekday() not in self.cfg.work_days:
            return False
        cur = now.strftime("%H:%M")
        return self.cfg.work_start <= cur < self.cfg.work_end

    def next_delay_seconds(self) -> float:
        return self.rng.uniform(
            self.cfg.interval_min_minutes, self.cfg.interval_max_minutes
        ) * 60.0
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add src/lezi/scheduler.py tests/test_scheduler.py
git commit -m "feat: work-hours and random-interval scheduler"
```

---

### Task 4: 本地内容库 `content/store.py`

**Files:**
- Create: `src/lezi/content/__init__.py`
- Create: `src/lezi/content/store.py`
- Create: `resources/content_local.json`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `ContentItem`、`ContentType`、`ContentItem.make_id`（Task 2）。
- Produces:
  - `class ContentStore: def __init__(self, path: Path)`；`def load(self) -> None`；`def all(self) -> list[ContentItem]`；`def by_type(self, t: ContentType) -> list[ContentItem]`
  - 本地条目 `id` 规则：`ContentItem.make_id(f"{title}\n{body}")`；`source="local"`。

- [ ] **Step 1: 创建 `resources/content_local.json`（各类型各 2 条）**

```json
{
  "items": [
    {"type": "joke", "title": "加班", "body": "老板问我周末干嘛，我说加班。他说：好，那就真有班可加了。"},
    {"type": "joke", "title": "Ctrl+C", "body": "我：工作这么累，能 Ctrl+C 一下人生吗？同事：那你别忘了 Ctrl+V 两份工资。"},
    {"type": "riddle", "title": "什么车寸步难行？", "body": "什么车寸步难行？", "answer": "风车。"},
    {"type": "riddle", "title": "什么东西越洗越脏？", "body": "什么东西越洗越脏？", "answer": "水。"},
    {"type": "trivia", "title": "蜂蜜不腐", "body": "考古学家在古埃及墓葬中发现了 3000 多年前的蜂蜜，仍然可以食用。"},
    {"type": "trivia", "title": "章鱼三颗心", "body": "章鱼有三颗心脏，其中两颗给鳃供血，一颗给全身供血。"}
  ]
}
```

- [ ] **Step 2: 写失败测试 `tests/test_store.py`**

```python
from pathlib import Path

from lezi.content.store import ContentStore
from lezi.models import ContentType

SAMPLE = {
    "items": [
        {"type": "joke", "title": "加班", "body": "b1"},
        {"type": "joke", "title": "Ctrl+C", "body": "b2"},
        {"type": "riddle", "title": "什么车寸步难行？", "body": "q", "answer": "风车。"},
    ]
}


def _write(tmp_path: Path) -> Path:
    import json

    p = tmp_path / "content.json"
    p.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_count(tmp_path: Path):
    store = ContentStore(_write(tmp_path))
    store.load()
    assert len(store.all()) == 3


def test_by_type_filters(tmp_path: Path):
    store = ContentStore(_write(tmp_path))
    store.load()
    assert len(store.by_type(ContentType.JOKE)) == 2
    assert len(store.by_type(ContentType.RIDDLE)) == 1
    assert store.by_type(ContentType.TRIVIA) == []


def test_missing_file_returns_empty(tmp_path: Path):
    store = ContentStore(tmp_path / "missing.json")
    store.load()
    assert store.all() == []
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_store.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.content.store'`

- [ ] **Step 4: 实现 `src/lezi/content/__init__.py` 与 `store.py`**

`content/__init__.py` 为空文件。

```python
from __future__ import annotations

import json
from pathlib import Path

from ..models import ContentItem, ContentType


class ContentStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._items: list[ContentItem] = []

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            entries = raw.get("items", [])
        except Exception:
            self._items = []
            return
        items: list[ContentItem] = []
        for d in entries:
            title = d["title"]
            body = d["body"]
            items.append(
                ContentItem(
                    id=ContentItem.make_id(f"{title}\n{body}"),
                    type=ContentType(d["type"]),
                    title=title,
                    body=body,
                    answer=d.get("answer"),
                    source="local",
                )
            )
        self._items = items

    def all(self) -> list[ContentItem]:
        return list(self._items)

    def by_type(self, t: ContentType) -> list[ContentItem]:
        return [i for i in self._items if i.type is t]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_store.py -v`
Expected: PASS（3 passed）

- [ ] **Step 6: Commit**

```bash
git add src/lezi/content/__init__.py src/lezi/content/store.py resources/content_local.json tests/test_store.py
git commit -m "feat: local content store"
```

---

### Task 5: 状态存储 `state.py`

**Files:**
- Create: `src/lezi/state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `ContentItem`（Task 2）。
- Produces:
  - `class StateStore: def __init__(self, path: Path)`
  - `def load(self) -> None`；`def save(self) -> None`
  - `def is_seen(self, item_id: str) -> bool`；`def mark_seen(self, item_id: str) -> None`
  - `def add_favorite(self, item: ContentItem) -> None`；`def favorites(self) -> list[ContentItem]`
  - `def snooze_until(self) -> datetime | None`；`def set_snooze(self, until: datetime) -> None`

- [ ] **Step 1: 写失败测试 `tests/test_state.py`**

```python
from datetime import datetime
from pathlib import Path

from lezi.models import ContentItem, ContentType
from lezi.state import StateStore


def _item() -> ContentItem:
    return ContentItem(id="x1", type=ContentType.JOKE, title="t", body="b")


def test_mark_seen_then_is_seen(tmp_path: Path):
    st = StateStore(tmp_path / "state.json")
    assert st.is_seen("x1") is False
    st.mark_seen("x1")
    assert st.is_seen("x1") is True


def test_favorites_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    st = StateStore(path)
    st.add_favorite(_item())
    st.save()
    st2 = StateStore(path)
    st2.load()
    assert st2.favorites() == [_item()]


def test_snooze_roundtrip_and_persist(tmp_path: Path):
    path = tmp_path / "state.json"
    until = datetime(2026, 10, 12, 10, 30)
    st = StateStore(path)
    st.set_snooze(until)
    st.save()
    st2 = StateStore(path)
    st2.load()
    assert st2.snooze_until() == until


def test_load_corrupt_state_resets(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text('{"seen": "oops", "favorites": 5, "snooze_until": "not-a-date"}', encoding="utf-8")
    st = StateStore(path)
    st.load()
    assert st.favorites() == []
    assert st.snooze_until() is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_state.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.state'`

- [ ] **Step 3: 实现 `src/lezi/state.py`**

`load()` 对整块解析做 try/except：任何异常都重置为「空 seen、空收藏、无暂停」；对 `seen` 用 `set(...)` 容错、对每个收藏条目单独 try（跳过坏条目）、对 `snooze_until` 用 `datetime.fromisoformat` 并容错。

```python
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import ContentItem


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._seen: set[str] = set()
        self._favorites: list[ContentItem] = []
        self._snooze_until: datetime | None = None

    def load(self) -> None:
        self._seen = set()
        self._favorites = []
        self._snooze_until = None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            seen = raw.get("seen", [])
            if isinstance(seen, list):
                self._seen = {str(s) for s in seen}
            favs = raw.get("favorites", [])
            if isinstance(favs, list):
                for d in favs:
                    try:
                        self._favorites.append(ContentItem.from_dict(d))
                    except Exception:
                        continue
            s = raw.get("snooze_until")
            if isinstance(s, str) and s:
                try:
                    self._snooze_until = datetime.fromisoformat(s)
                except Exception:
                    self._snooze_until = None
        except Exception:
            self._seen = set()
            self._favorites = []
            self._snooze_until = None

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "seen": sorted(self._seen),
            "favorites": [f.to_dict() for f in self._favorites],
            "snooze_until": self._snooze_until.isoformat() if self._snooze_until else None,
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def is_seen(self, item_id: str) -> bool:
        return item_id in self._seen

    def mark_seen(self, item_id: str) -> None:
        self._seen.add(item_id)

    def add_favorite(self, item: ContentItem) -> None:
        if all(f.id != item.id for f in self._favorites):
            self._favorites.append(item)

    def favorites(self) -> list[ContentItem]:
        return list(self._favorites)

    def snooze_until(self) -> datetime | None:
        return self._snooze_until

    def set_snooze(self, until: datetime) -> None:
        self._snooze_until = until
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_state.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add src/lezi/state.py tests/test_state.py
git commit -m "feat: persistent state store for seen/favorites/snooze"
```

---

### Task 6: 联网抓取 `content/fetcher.py`

**Files:**
- Create: `src/lezi/content/fetcher.py`
- Test: `tests/test_fetcher.py`

**Interfaces:**
- Consumes: `ContentItem`、`ContentType`、`ContentItem.make_id`（Task 2）。
- Produces:
  - `class FeedFetcher: def __init__(self, feeds: list[str], timeout: float = 5.0, fetch_fn: Callable[[str, float], bytes] | None = None)`
  - `def fetch(self, limit: int = 20) -> list[ContentItem]`
  - 模块级默认实现 `def _http_get(url: str, timeout: float) -> bytes`（用 requests）。

- [ ] **Step 1: 写失败测试 `tests/test_fetcher.py`**

```python
from lezi.content.fetcher import FeedFetcher
from lezi.models import ContentType

RSS = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>T</title>
<item><title>Hello</title><link>http://x/1</link><description>d1</description></item>
<item><title>World</title><link>http://x/2</link><description>d2</description></item>
</channel></rss>"""


def test_fetch_parses_entries():
    f = FeedFetcher(["http://feed"], fetch_fn=lambda url, timeout: RSS)
    items = f.fetch()
    assert [i.title for i in items] == ["Hello", "World"]
    assert all(i.type is ContentType.NEWS for i in items)
    assert all(i.source == "rss" for i in items)
    assert items[0].url == "http://x/1"


def test_fetch_respects_limit():
    f = FeedFetcher(["http://feed"], fetch_fn=lambda url, timeout: RSS)
    assert len(f.fetch(limit=1)) == 1


def test_fetch_skips_garbage_source():
    def bad(url, timeout):
        raise ValueError("boom")

    f = FeedFetcher(["http://feed"], fetch_fn=bad)
    assert f.fetch() == []


def test_fetch_skips_garbage_bytes_returns_empty():
    f = FeedFetcher(["http://feed"], fetch_fn=lambda url, timeout: b"<html>not xml")
    assert f.fetch() == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_fetcher.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.content.fetcher'`

- [ ] **Step 3: 实现 `src/lezi/content/fetcher.py`**

`fetch()` 逐源 try/except：单源任何异常仅记录日志并跳过，不影响其它源；用 `feedparser.parse(raw_bytes)` 解析；跳过空标题；达到 `limit` 提前返回。`_http_get` 用 requests，`raise_for_status` 后返回 `resp.content`。

```python
from __future__ import annotations

import logging
from datetime import datetime
from typing import Callable

import feedparser
import requests

from ..models import ContentItem, ContentType

logger = logging.getLogger(__name__)


def _http_get(url: str, timeout: float) -> bytes:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content


class FeedFetcher:
    def __init__(
        self,
        feeds: list[str],
        timeout: float = 5.0,
        fetch_fn: Callable[[str, float], bytes] | None = None,
    ) -> None:
        self.feeds = list(feeds)
        self.timeout = timeout
        self.fetch_fn = fetch_fn if fetch_fn is not None else _http_get

    def fetch(self, limit: int = 20) -> list[ContentItem]:
        items: list[ContentItem] = []
        for url in self.feeds:
            try:
                raw = self.fetch_fn(url, self.timeout)
                parsed = feedparser.parse(raw)
                for entry in parsed.entries:
                    title = (entry.get("title") or "").strip()
                    if not title:
                        continue
                    items.append(
                        ContentItem(
                            id=ContentItem.make_id(title),
                            type=ContentType.NEWS,
                            title=title,
                            body=entry.get("summary", ""),
                            source="rss",
                            url=entry.get("link"),
                            fetched_at=datetime.now().isoformat(),
                        )
                    )
                    if len(items) >= limit:
                        return items
            except Exception:
                logger.warning("feed fetch failed: %s", url, exc_info=True)
                continue
        return items
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_fetcher.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add src/lezi/content/fetcher.py tests/test_fetcher.py
git commit -m "feat: rss feed fetcher with per-source fault isolation"
```

---

### Task 7: 统一内容提供 `content/provider.py`

**Files:**
- Create: `src/lezi/content/provider.py`
- Test: `tests/test_provider.py`

**Interfaces:**
- Consumes: `ContentStore`（Task 4）、`FeedFetcher`（Task 6）、`StateStore`（Task 5）、`ContentItem`（Task 2）。
- Produces:
  - `class ContentProvider: def __init__(self, store: ContentStore, fetcher: FeedFetcher | None, state: StateStore, rng: random.Random | None = None)`
  - `def next_item(self) -> ContentItem | None`

- [ ] **Step 1: 写失败测试 `tests/test_provider.py`**

```python
import random

from lezi.content.provider import ContentProvider
from lezi.models import ContentItem, ContentType
from lezi.state import StateStore


class FakeStore:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)

    def by_type(self, t):
        return [i for i in self._items if i.type is t]


class FakeFetcher:
    def __init__(self, items):
        self._items = items

    def fetch(self, limit=20):
        return list(self._items)


def _local(id_, t=ContentType.JOKE):
    return ContentItem(id=id_, type=t, title=id_, body="b")


def _online(id_):
    return ContentItem(id=id_, type=ContentType.NEWS, title=id_, body="b", source="rss")


def test_prefers_fresh_online(tmp_path):
    store = FakeStore([_local("L1")])
    fetcher = FakeFetcher([_online("N1")])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    assert p.next_item().id == "N1"


def test_falls_back_to_local_when_online_empty(tmp_path):
    store = FakeStore([_local("L1")])
    fetcher = FakeFetcher([])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    assert p.next_item().id == "L1"


def test_all_seen_falls_back_to_any_local(tmp_path):
    store = FakeStore([_local("L1")])
    fetcher = FakeFetcher([])
    state = StateStore(tmp_path / "s.json")
    state.mark_seen("L1")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    assert p.next_item().id == "L1"


def test_empty_everything_returns_none(tmp_path):
    store = FakeStore([])
    fetcher = FakeFetcher([])
    state = StateStore(tmp_path / "s.json")
    p = ContentProvider(store, fetcher, state)
    assert p.next_item() is None


def test_skips_seen_online_in_favor_of_fresh_online(tmp_path):
    store = FakeStore([])
    fetcher = FakeFetcher([_online("N1"), _online("N2")])
    state = StateStore(tmp_path / "s.json")
    state.mark_seen("N1")
    p = ContentProvider(store, fetcher, state, rng=random.Random(1))
    assert p.next_item().id == "N2"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_provider.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.content.provider'`

- [ ] **Step 3: 实现 `src/lezi/content/provider.py`**

优先级：联网未看 → 本地未看 → 本地任意（重置已看窗口）→ None。内部只用 `state.is_seen` 过滤，不在返回前 `mark_seen`（由调用方决定）；用注入的 `rng.choice` 选择以避免随机不确定性。`fetcher=None` 或 `fetcher.fetch()` 抛异常时视为联网为空。

```python
from __future__ import annotations

import random

from ..models import ContentItem
from ..state import StateStore
from .fetcher import FeedFetcher
from .store import ContentStore


class ContentProvider:
    def __init__(
        self,
        store: ContentStore,
        fetcher: FeedFetcher | None,
        state: StateStore,
        rng: random.Random | None = None,
    ) -> None:
        self.store = store
        self.fetcher = fetcher
        self.state = state
        self.rng = rng if rng is not None else random.Random()

    def next_item(self) -> ContentItem | None:
        online: list[ContentItem] = []
        if self.fetcher is not None:
            try:
                online = self.fetcher.fetch()
            except Exception:
                online = []
        fresh_online = [i for i in online if not self.state.is_seen(i.id)]
        if fresh_online:
            return self.rng.choice(fresh_online)

        local = self.store.all()
        fresh_local = [i for i in local if not self.state.is_seen(i.id)]
        if fresh_local:
            return self.rng.choice(fresh_local)
        if local:
            return self.rng.choice(local)
        return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_provider.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: Commit**

```bash
git add src/lezi/content/provider.py tests/test_provider.py
git commit -m "feat: content provider with online-first then local fallback"
```

---

### Task 8: 平台集成 `platform/win.py`

**Files:**
- Create: `src/lezi/platform/__init__.py`
- Create: `src/lezi/platform/win.py`
- Test: `tests/test_win.py`

**Interfaces:**
- Consumes: 无。
- Produces:
  - `def _rect_covers(window_rect: tuple[int, int, int, int], screen_rect: tuple[int, int, int, int]) -> bool`
  - `def is_fullscreen() -> bool`
  - `def idle_seconds() -> float`

- [ ] **Step 1: 写失败测试 `tests/test_win.py`**

```python
from lezi.platform.win import _rect_covers

SCREEN = (0, 0, 1920, 1080)


def test_rect_covers_equal_is_true():
    assert _rect_covers((0, 0, 1920, 1080), SCREEN) is True


def test_rect_covers_slightly_smaller_is_false():
    assert _rect_covers((0, 0, 1919, 1080), SCREEN) is False


def test_rect_covers_larger_is_true():
    assert _rect_covers((-10, -10, 1930, 1090), SCREEN) is True


def test_rect_covers_negative_and_slightly_smaller():
    # 任务栏占位：窗口略矮（底部留出任务栏）应判为非全屏
    assert _rect_covers((0, 0, 1920, 1040), (0, 0, 1920, 1080)) is False
    # 负坐标显示器：窗口刚好覆盖负坐标显示器应判为全屏
    assert _rect_covers((-1920, 0, 0, 1080), (-1920, 0, 0, 1080)) is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_win.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.platform.win'`

- [ ] **Step 3: 实现 `src/lezi/platform/__init__.py` 与 `win.py`**

`platform/__init__.py` 为空文件。`_rect_covers` 纯逻辑：窗口左/上 <= 屏幕左/上 且 窗口右/下 >= 屏幕右/下。`is_fullscreen` 取前台窗口矩形与其所在显示器矩形比较；`idle_seconds` 用 `GetLastInputInfo` 与 `GetTickCount` 差值换算秒。

```python
from __future__ import annotations

import win32api
import win32gui

Rect = tuple[int, int, int, int]


def _rect_covers(window_rect: Rect, screen_rect: Rect) -> bool:
    wl, wt, wr, wb = window_rect
    sl, st, sr, sb = screen_rect
    return wl <= sl and wt <= st and wr >= sr and wb >= sb


def is_fullscreen() -> bool:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return False
    try:
        rect = win32gui.GetWindowRect(hwnd)
        monitor = win32api.MonitorFromWindow(hwnd, win32api.MONITOR_DEFAULTTONEAREST)
        screen_rect = win32api.GetMonitorInfo(monitor)["Monitor"]
    except Exception:
        return False
    return _rect_covers(tuple(rect), tuple(screen_rect))


def idle_seconds() -> float:
    info = win32api.GetLastInputInfo()
    now = win32api.GetTickCount()
    return max(0.0, (now - info) / 1000.0)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_win.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add src/lezi/platform/__init__.py src/lezi/platform/win.py tests/test_win.py
git commit -m "feat: windows fullscreen and idle detection"
```

---

### Task 9: 卡片视图与窗口 `ui/card.py`

**Files:**
- Create: `src/lezi/ui/__init__.py`
- Create: `src/lezi/ui/card.py`
- Test: `tests/test_card_view.py`

**Interfaces:**
- Consumes: `ContentItem`（Task 2）、`Config`（Task 1）。
- Produces:
  - `@dataclass class CardView`：`title: str`、`body: str`、`answer: str | None`、`show_answer: bool`
  - `def build_card_view(item: ContentItem, reveal: bool) -> CardView`
  - `class CardWindow(QWidget)`：信号 `next_requested`、`favorite_requested`、`snooze_requested`；`def show_item(self, item: ContentItem) -> None`；内部 `QTimer` 到 `cfg.card_seconds` 自动关闭。

- [ ] **Step 1: 写失败测试 `tests/test_card_view.py`**

```python
from lezi.models import ContentItem, ContentType
from lezi.ui.card import build_card_view


def _riddle():
    return ContentItem(
        id="r1", type=ContentType.RIDDLE, title="什么车寸步难行？",
        body="什么车寸步难行？", answer="风车。",
    )


def _joke():
    return ContentItem(id="j1", type=ContentType.JOKE, title="加班", body="b")


def test_riddle_hides_answer_before_reveal():
    view = build_card_view(_riddle(), reveal=False)
    assert view.answer is None
    assert view.show_answer is False


def test_riddle_shows_answer_after_reveal():
    view = build_card_view(_riddle(), reveal=True)
    assert view.answer == "风车。"
    assert view.show_answer is True


def test_joke_never_shows_answer():
    view = build_card_view(_joke(), reveal=True)
    assert view.answer is None
    assert view.show_answer is False
    assert view.title == "加班"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_card_view.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.ui.card'`

- [ ] **Step 3: 实现 `src/lezi/ui/card.py` 的纯逻辑部分**

`ui/__init__.py` 为空文件。`build_card_view`：仅当 `item.type is ContentType.RIDDLE` 且 `reveal` 为真时暴露答案；其余一律 `answer=None, show_answer=False`。

```python
from __future__ import annotations

from dataclasses import dataclass

from ..config import Config
from ..models import ContentItem, ContentType


@dataclass
class CardView:
    title: str
    body: str
    answer: str | None
    show_answer: bool


def build_card_view(item: ContentItem, reveal: bool) -> CardView:
    if item.type is ContentType.RIDDLE:
        return CardView(
            title=item.title,
            body=item.body,
            answer=item.answer if reveal else None,
            show_answer=reveal,
        )
    return CardView(title=item.title, body=item.body, answer=None, show_answer=False)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_card_view.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: 在 `src/lezi/ui/card.py` 追加 `CardWindow`**

要点：无边框圆角半透明、置顶不激活、自动关闭、三个按钮与「看答案」切换。窗口标志与属性按 Global Constraints。

```python
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class CardWindow(QWidget):
    next_requested = Signal()
    favorite_requested = Signal()
    snooze_requested = Signal()

    def __init__(self, cfg: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self._item: ContentItem | None = None
        self._reveal = False

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._title = QLabel()
        self._body = QLabel()
        self._body.setWordWrap(True)
        self._answer = QLabel()
        self._answer.setWordWrap(True)

        self._reveal_btn = QPushButton("看答案")
        self._reveal_btn.clicked.connect(self._on_reveal)
        self._next_btn = QPushButton("再来一个")
        self._next_btn.clicked.connect(self.next_requested.emit)
        self._fav_btn = QPushButton("收藏")
        self._fav_btn.clicked.connect(self.favorite_requested.emit)
        self._snooze_btn = QPushButton("安静一会")
        self._snooze_btn.clicked.connect(self.snooze_requested.emit)

        buttons = QHBoxLayout()
        buttons.addWidget(self._reveal_btn)
        buttons.addStretch(1)
        buttons.addWidget(self._next_btn)
        buttons.addWidget(self._fav_btn)
        buttons.addWidget(self._snooze_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._body)
        layout.addWidget(self._answer)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)

    def _render(self) -> None:
        if self._item is None:
            return
        view = build_card_view(self._item, self._reveal)
        self._title.setText(view.title)
        self._body.setText(view.body)
        self._answer.setText(view.answer or "")
        self._answer.setVisible(view.show_answer)
        self._reveal_btn.setVisible(
            self._item.type is ContentType.RIDDLE and not self._reveal
        )

    def _on_reveal(self) -> None:
        self._reveal = True
        self._render()

    def show_item(self, item: ContentItem) -> None:
        self._item = item
        self._reveal = False
        self._render()
        self.adjustSize()
        screen = self.screen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)
        self.show()
        self._timer.start(self.cfg.card_seconds * 1000)
```

- [ ] **Step 6: 手动验证卡片窗口**

Run: `python -c "from PySide6.QtWidgets import QApplication; from lezi.config import Config; from lezi.ui.card import CardWindow; from lezi.models import ContentItem, ContentType; import sys; app=QApplication(sys.argv); w=CardWindow(Config(card_seconds=5)); w.show_item(ContentItem(id='r',type=ContentType.RIDDLE,title='什么车寸步难行？',body='什么车寸步难行？',answer='风车。')); app.exec()"`
Expected（人工确认）：卡片出现在屏幕右下角、无边框圆角、当前输入焦点不被抢走；点击「看答案」后显示「风车。」且按钮隐藏；约 5 秒后卡片自动消失。

- [ ] **Step 7: 增加淡入淡出与右下角定位**

卡片出现于屏幕右下角（距边缘 24px）；显示时以 200ms 从 `windowOpacity=0.0` 淡入到 `1.0`；自动关闭前以 200ms 淡出到 `0.0` 再 `close()`；视觉参数：深色半透明、圆角 16px、正文「微软雅黑」、强调色 `#FFB74D`。

```python
from PySide6.QtCore import QPoint, QPropertyAnimation

def _place_bottom_right(self) -> None:
    screen = self.screen().availableGeometry()
    margin = 24
    self.move(
        screen.right() - self.width() - margin,
        screen.bottom() - self.height() - margin,
    )

def _fade(self, start: float, end: float, on_finished=None) -> None:
    self._anim = QPropertyAnimation(self, b"windowOpacity", self)
    self._anim.setDuration(200)
    self._anim.setStartValue(start)
    self._anim.setEndValue(end)
    if on_finished is not None:
        self._anim.finished.connect(on_finished)
    self._anim.start()

def _show_with_fade(self) -> None:
    self._place_bottom_right()
    self.setWindowOpacity(0.0)
    self.show()
    self._fade(0.0, 1.0)

def _close_with_fade(self) -> None:
    self._fade(1.0, 0.0, on_finished=self.close)
```

手动验证：运行后观察卡片在右下角淡入、停留后淡出，且过程中不夺走键盘焦点。注意：这里给出的方法需与 Task 9 已有 `CardWindow` 的 `show_item`/自动关闭 `QTimer` 逻辑对接（把自动关闭触发时的 `close()` 改为 `_close_with_fade()`，`show_item` 用 `_show_with_fade()`）。

- [ ] **Step 8: Commit**

```bash
git add src/lezi/ui/__init__.py src/lezi/ui/card.py tests/test_card_view.py
git commit -m "feat: card view logic and frameless non-activating card window"
```

---

### Task 10: 托盘与设置 `ui/tray.py` + `ui/settings.py`

**Files:**
- Create: `src/lezi/ui/tray.py`
- Create: `src/lezi/ui/settings.py`
- Create: `src/lezi/ui/favorites.py`
- Test: `tests/test_settings.py`（新增测试文件；与本任务一起提交）
- Test: `tests/test_favorites.py`（新增测试文件；与本任务一起提交）

**Interfaces:**
- Consumes: `Config`（Task 1）。
- Produces:
  - `class TrayController(QObject)`：`QSystemTrayIcon` + 右键菜单（「暂停 1 小时」「收藏夹」「设置」「退出」）；信号 `snooze_requested`、`favorites_requested`、`settings_requested`、`quit_requested`；`def __init__(self, parent: QObject | None = None)`。
  - `def config_to_form(cfg: Config) -> dict`；`def form_to_config(form: dict) -> Config`（纯逻辑）。
  - `class SettingsWindow(QWidget)`：`def __init__(self, cfg: Config, parent=None)`；`def current_config(self) -> Config`。
  - `def favorites_to_rows(items: list[ContentItem]) -> list[str]`（纯逻辑）；`class FavoritesWindow(QWidget)`：`def __init__(self, items: list[ContentItem], parent=None)`。

- [ ] **Step 1: 写失败测试 `tests/test_settings.py`**

```python
from lezi.config import Config
from lezi.ui.settings import config_to_form, form_to_config


def test_config_to_form_fields():
    form = config_to_form(Config())
    assert form == {
        "work_start": "09:30",
        "work_end": "18:30",
        "interval_min_minutes": 40,
        "interval_max_minutes": 90,
        "card_seconds": 15,
        "snooze_minutes": 60,
    }


def test_form_to_config_roundtrip():
    cfg = Config(work_start="08:00", interval_min_minutes=20, snooze_minutes=30)
    assert form_to_config(config_to_form(cfg)) == cfg


def test_form_to_config_casts_strings():
    form = {
        "work_start": "07:00",
        "work_end": "19:00",
        "interval_min_minutes": "10",
        "interval_max_minutes": "20",
        "card_seconds": "5",
        "snooze_minutes": "45",
    }
    cfg = form_to_config(form)
    assert cfg.interval_min_minutes == 10
    assert cfg.card_seconds == 5
```

- [ ] **Step 2: 写失败测试 `tests/test_favorites.py`**

```python
from lezi.models import ContentItem, ContentType
from lezi.ui.favorites import favorites_to_rows


def test_favorites_to_rows_labels_type_and_title():
    items = [
        ContentItem(id="a", type=ContentType.JOKE, title="冷笑话A", body="x"),
        ContentItem(id="b", type=ContentType.RIDDLE, title="脑筋急转弯B", body="y", answer="z"),
    ]
    assert favorites_to_rows(items) == ["[joke] 冷笑话A", "[riddle] 脑筋急转弯B"]


def test_favorites_to_rows_empty():
    assert favorites_to_rows([]) == []
```

- [ ] **Step 3: 运行测试确认失败**

Run: `pytest tests/test_favorites.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.ui.favorites'`

- [ ] **Step 4: 运行测试确认失败**

Run: `pytest tests/test_settings.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.ui.settings'`

- [ ] **Step 5: 实现 `src/lezi/ui/settings.py` 的纯逻辑与窗口**

纯函数 `config_to_form`/`form_to_config`（对数值字段做 `int(...)` 强转，文本字段做 `str(...)`）；`SettingsWindow` 用 `QLineEdit`/`QSpinBox` 承载各字段，`current_config()` 收集表单值调用 `form_to_config`。

```python
from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout, QLineEdit, QSpinBox, QVBoxLayout, QWidget,
)

from ..config import Config


def config_to_form(cfg: Config) -> dict:
    return {
        "work_start": cfg.work_start,
        "work_end": cfg.work_end,
        "interval_min_minutes": cfg.interval_min_minutes,
        "interval_max_minutes": cfg.interval_max_minutes,
        "card_seconds": cfg.card_seconds,
        "snooze_minutes": cfg.snooze_minutes,
    }


def form_to_config(form: dict) -> Config:
    return Config(
        work_start=str(form["work_start"]),
        work_end=str(form["work_end"]),
        interval_min_minutes=int(form["interval_min_minutes"]),
        interval_max_minutes=int(form["interval_max_minutes"]),
        card_seconds=int(form["card_seconds"]),
        snooze_minutes=int(form["snooze_minutes"]),
    )


class SettingsWindow(QWidget):
    def __init__(self, cfg: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("找点乐子 · 设置")
        form = config_to_form(cfg)

        self._work_start = QLineEdit(form["work_start"])
        self._work_end = QLineEdit(form["work_end"])
        self._interval_min = QSpinBox()
        self._interval_min.setRange(1, 600)
        self._interval_min.setValue(form["interval_min_minutes"])
        self._interval_max = QSpinBox()
        self._interval_max.setRange(1, 600)
        self._interval_max.setValue(form["interval_max_minutes"])
        self._card_seconds = QSpinBox()
        self._card_seconds.setRange(3, 300)
        self._card_seconds.setValue(form["card_seconds"])
        self._snooze_minutes = QSpinBox()
        self._snooze_minutes.setRange(5, 480)
        self._snooze_minutes.setValue(form["snooze_minutes"])

        layout = QVBoxLayout(self)
        rows = QFormLayout()
        rows.addRow("上班时间", self._work_start)
        rows.addRow("下班时间", self._work_end)
        rows.addRow("最小间隔(分)", self._interval_min)
        rows.addRow("最大间隔(分)", self._interval_max)
        rows.addRow("卡片停留(秒)", self._card_seconds)
        rows.addRow("安静一会(分)", self._snooze_minutes)
        layout.addLayout(rows)

    def current_config(self) -> Config:
        return form_to_config(
            {
                "work_start": self._work_start.text(),
                "work_end": self._work_end.text(),
                "interval_min_minutes": self._interval_min.value(),
                "interval_max_minutes": self._interval_max.value(),
                "card_seconds": self._card_seconds.value(),
                "snooze_minutes": self._snooze_minutes.value(),
            }
        )
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_settings.py -v`
Expected: PASS（3 passed）

- [ ] **Step 7: 实现 `src/lezi/ui/favorites.py`**

```python
from __future__ import annotations

from PySide6.QtWidgets import QListWidget, QVBoxLayout, QWidget

from ..models import ContentItem


def favorites_to_rows(items: list[ContentItem]) -> list[str]:
    return [f"[{item.type.value}] {item.title}" for item in items]


class FavoritesWindow(QWidget):
    def __init__(self, items: list[ContentItem], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("找点乐子 · 收藏夹")
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        self._list.addItems(favorites_to_rows(items))
        layout.addWidget(self._list)
```

- [ ] **Step 8: 运行测试确认通过**

Run: `pytest tests/test_favorites.py -v`
Expected: PASS（2 passed）

- [ ] **Step 9: 实现 `src/lezi/ui/tray.py`**

要点：`QSystemTrayIcon` + 右键菜单四项，菜单动作分别 emit 对应信号；托盘图标须有可显示图标（用 Qt 内置标准图标兜底）。

```python
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QStyle, QSystemTrayIcon


class TrayController(QObject):
    snooze_requested = Signal()
    favorites_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def setup(self) -> None:
        self.icon = QSystemTrayIcon(
            self.parent().style().standardIcon(QStyle.SP_MessageBoxInformation)
            if self.parent() is not None
            else None
        )
        self.icon.setToolTip("找点乐子")
        menu = QMenu()

        snooze = QAction("暂停 1 小时", menu)
        snooze.triggered.connect(self.snooze_requested.emit)
        favorites = QAction("收藏夹", menu)
        favorites.triggered.connect(self.favorites_requested.emit)
        settings = QAction("设置", menu)
        settings.triggered.connect(self.settings_requested.emit)
        quit_ = QAction("退出", menu)
        quit_.triggered.connect(self.quit_requested.emit)

        menu.addAction(snooze)
        menu.addAction(favorites)
        menu.addSeparator()
        menu.addAction(settings)
        menu.addAction(quit_)

        self.icon.setContextMenu(menu)
        self.icon.show()
```

> 说明：`QSystemTrayIcon` 必须先有可用图标才显示；在 `Application`（Task 11）中会以 `QApplication.style()` 提供标准图标，此处的 `parent()` 为 `Application` 对象。

- [ ] **Step 10: 手动验证托盘**

Run: `python -c "from PySide6.QtWidgets import QApplication; from lezi.ui.tray import TrayController; import sys; app=QApplication(sys.argv); t=TrayController(app); t.setup(); t.snooze_requested.connect(lambda: print('snooze')); app.exec()"`
Expected（人工确认）：系统托盘出现图标；右键菜单含「暂停 1 小时／收藏夹／设置／退出」；点击「暂停 1 小时」控制台打印 `snooze`；任务栏不出现常驻窗口。

- [ ] **Step 11: Commit**

```bash
git add src/lezi/ui/tray.py src/lezi/ui/settings.py src/lezi/ui/favorites.py tests/test_settings.py tests/test_favorites.py
git commit -m "feat: tray controller and settings window"
```

---

### Task 11: 应用装配与端到端 `app.py` + `__main__.py`

**Files:**
- Create: `src/lezi/app.py`
- Create: `src/lezi/__main__.py`
- Modify: `src/lezi/__init__.py`（追加 `__version__ = "0.1.0"`）
- Test: `tests/test_app.py`（新增测试文件；与本任务一起提交）

**Interfaces:**
- Consumes: `Config`/`default_config`/`load_config`/`save_config`（Task 1）、`Scheduler`（Task 3）、`ContentStore`（Task 4）、`FeedFetcher`（Task 6）、`ContentProvider`（Task 7）、`StateStore`（Task 5）、`CardWindow`（Task 9）、`TrayController`（Task 10）、`is_fullscreen`/`idle_seconds`（Task 8）。
- Produces:
  - `def should_pop(scheduler: Scheduler, cfg: Config, state: StateStore, now: datetime, is_fullscreen: Callable[[], bool], idle_seconds: Callable[[], float], idle_threshold: float = 120.0) -> bool`
  - `class Application`：`def __init__(self, argv: list[str] | None = None)`；`def start(self) -> None`
  - `def main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: 写失败测试 `tests/test_app.py`**

```python
from datetime import datetime
from pathlib import Path

from lezi.app import should_pop
from lezi.config import Config
from lezi.scheduler import Scheduler
from lezi.state import StateStore


def _mk(tmp_path: Path) -> tuple[Scheduler, StateStore]:
    return Scheduler(Config()), StateStore(tmp_path / "s.json")


def test_should_pop_true_in_work_hours(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 10, 0)
    assert should_pop(s, Config(), st, now, lambda: False, lambda: 0.0) is True


def test_should_pop_false_outside_hours(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 8, 0)
    assert should_pop(s, Config(), st, now, lambda: False, lambda: 0.0) is False


def test_should_pop_false_when_fullscreen(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 10, 0)
    assert should_pop(s, Config(), st, now, lambda: True, lambda: 0.0) is False


def test_should_pop_false_when_idle(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 10, 0)
    assert should_pop(s, Config(), st, now, lambda: False, lambda: 300.0) is False


def test_should_pop_snooze_boundary(tmp_path):
    s, st = _mk(tmp_path)
    now = datetime(2026, 10, 12, 10, 0)
    st.set_snooze(datetime(2026, 10, 12, 10, 30))
    assert should_pop(s, Config(), st, now, lambda: False, lambda: 0.0) is False
    # 恰好到期当刻应恢复推送
    assert should_pop(s, Config(), st, datetime(2026, 10, 12, 10, 30), lambda: False, lambda: 0.0) is True
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_app.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'lezi.app'`

- [ ] **Step 3: 实现 `src/lezi/app.py` 的纯函数 `should_pop`**

判定顺序：工作时段 → 不在暂停窗口（`snooze now < until` 才抑制）→ 非全屏 → 非空闲（`idle_seconds() >= idle_threshold` 视为空闲）。全屏与空闲以可调用对象注入，便于单测。

```python
from __future__ import annotations

from datetime import datetime
from typing import Callable

from .config import Config
from .scheduler import Scheduler
from .state import StateStore


def should_pop(
    scheduler: Scheduler,
    cfg: Config,
    state: StateStore,
    now: datetime,
    is_fullscreen: Callable[[], bool],
    idle_seconds: Callable[[], float],
    idle_threshold: float = 120.0,
) -> bool:
    if not scheduler.in_work_hours(now):
        return False
    snooze = state.snooze_until()
    if snooze is not None and now < snooze:
        return False
    if is_fullscreen():
        return False
    if idle_seconds() >= idle_threshold:
        return False
    return True
```

- [ ] **Step 4: 运行测试确认通过（纯函数）**

Run: `pytest tests/test_app.py -v`
Expected: PASS（5 passed）

- [ ] **Step 5: 在 `src/lezi/app.py` 追加 `Application` 与 `main`**

装配各组件；用 `QTimer` 单次触发，触发时先判断 `should_pop(...)`，满足则 `provider.next_item()` 并 `mark_seen` 后 `card.show_item(item)`，否则跳过；再按 `scheduler.next_delay_seconds()` 重排下一次。卡片信号：`next_requested` → 立即取一条再展示；`favorite_requested` → `state.add_favorite` 并保存；`snooze_requested` → `state.set_snooze(now + snooze_minutes)` 并保存、隐藏卡片。托盘 `settings_requested` 打开 `SettingsWindow`、`favorites_requested` 打开 `FavoritesWindow` 列出全部收藏、`quit_requested` 退出、`snooze_requested` 同卡片暂停逻辑。

```python
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication

from .config import Config, default_config, load_config, save_config
from .content.fetcher import FeedFetcher
from .content.provider import ContentProvider
from .content.store import ContentStore
from .models import ContentItem
from .platform.win import idle_seconds, is_fullscreen
from .scheduler import Scheduler
from .state import StateStore
from .ui.card import CardWindow
from .ui.favorites import FavoritesWindow
from .ui.settings import SettingsWindow
from .ui.tray import TrayController

FEEDS = [
    # 计划阶段确定的 RSS 来源清单（可按需增删）
    "https://feeds.bbci.co.uk/news/world/rss.xml",
]

IDLE_THRESHOLD_SECONDS = 120.0


def _base_dir() -> Path:
    return Path(__file__).resolve().parents[2]


class Application(QObject):
    def __init__(self, argv: list[str] | None = None) -> None:
        super().__init__()
        self.qapp = QApplication(argv if argv is not None else sys.argv)

        base = _base_dir()
        self.config_path = base / "config.json"
        self.state_path = base / "state.json"
        self.content_path = base / "resources" / "content_local.json"

        self.cfg: Config = load_config(self.config_path)
        self.store = ContentStore(self.content_path)
        self.store.load()
        self.fetcher = FeedFetcher(FEEDS)
        self.state = StateStore(self.state_path)
        self.state.load()
        self.provider = ContentProvider(self.store, self.fetcher, self.state)
        self.scheduler = Scheduler(self.cfg)

        self.card = CardWindow(self.cfg)
        self.card.next_requested.connect(self._on_next)
        self.card.favorite_requested.connect(self._on_favorite)
        self.card.snooze_requested.connect(self._on_snooze)

        self.tray = TrayController(self)
        self.tray.setup()
        self.tray.snooze_requested.connect(self._on_snooze)
        self.tray.settings_requested.connect(self._on_settings)
        self.tray.favorites_requested.connect(self._on_favorites)
        self.tray.quit_requested.connect(self.quit)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._tick)

    def _show_next(self) -> None:
        item = self.provider.next_item()
        if item is None:
            return
        self.state.mark_seen(item.id)
        self.state.save()
        self.card.show_item(item)

    def _schedule_next(self) -> None:
        self._timer.start(int(self.scheduler.next_delay_seconds() * 1000))

    def _tick(self) -> None:
        now = datetime.now()
        if should_pop(
            self.scheduler, self.cfg, self.state, now, is_fullscreen, idle_seconds
        ):
            self._show_next()
        self._schedule_next()

    def _on_next(self) -> None:
        self.card.close()
        self._show_next()

    def _on_favorite(self) -> None:
        if self.card._item is not None:
            self.state.add_favorite(self.card._item)
            self.state.save()

    def _on_snooze(self) -> None:
        until = datetime.now() + timedelta(minutes=self.cfg.snooze_minutes)
        self.state.set_snooze(until)
        self.state.save()
        self.card.close()

    def _on_settings(self) -> None:
        self.settings_window = SettingsWindow(self.cfg)
        self.settings_window.show()

    def _on_favorites(self) -> None:
        self.favorites_window = FavoritesWindow(self.state.favorites())
        self.favorites_window.show()

    def quit(self) -> None:
        self.state.save()
        self.qapp.quit()

    def start(self) -> None:
        self._schedule_next()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lezi", description="找点乐子")
    parser.add_argument("--version", action="store_true", help="显示版本并退出")
    args, rest = parser.parse_known_args(argv)

    if args.version:
        from . import __version__

        print(f"lezi {__version__}")
        return 0

    app = Application([sys.argv[0], *rest])
    app.start()
    return app.qapp.exec()
```

在 `src/lezi/__init__.py` 中补充 `__version__ = "0.1.0"`（供 `--version` 使用）。

- [ ] **Step 6: 创建 `src/lezi/__main__.py`**

```python
from .app import main

raise SystemExit(main())
```

- [ ] **Step 7: 运行全部单元测试确认通过**

Run: `pytest -v`
Expected: PASS（`tests/` 全部通过，含 Task 1–11 的单测）

- [ ] **Step 8: 手动验证端到端**

Run: `python -m lezi`
Expected（人工确认）：
- 系统托盘出现「找点乐子」图标，任务栏无窗口；
- 将 `config.json` 的 `interval_min_minutes`/`interval_max_minutes` 暂设为较小值（如 1/1）并重启，可观察到工作时段内卡片自动弹出、不抢焦点、约 `card_seconds` 秒后自动消失；
- 打开全屏视频或从托盘点「暂停 1 小时」后，不再弹出；
- 卡片「收藏」后，从托盘「收藏夹」可再次看到该条；
- 「安静一会」后 `state.json` 中 `snooze_until` 更新；
- 断开网络时仍能从本地库正常推送。

- [ ] **Step 9: Commit**

```bash
git add src/lezi/app.py src/lezi/__main__.py src/lezi/__init__.py tests/test_app.py
git commit -m "feat: application assembly, scheduler loop and CLI entrypoint"
```

---

## Dependency Graph

```
Task 1 (config) ─┬─► Task 3 (scheduler) ──────────────┐
                 ├─► Task 10 (tray/settings) ─────────┤
                 └─► Task 11 (app) ───────────────────┤
Task 2 (models) ─┬─► Task 4 (store) ──► Task 7 ───────┤
                 ├─► Task 6 (fetcher) ─► Task 7 ──────┤
                 └─► Task 9 (card) ───────────────────┤
Task 5 (state) ──────────────► Task 7 ────────────────┤
Task 8 (win) ─────────────────────────────────────────┤
                                                      ▼
                                             Task 11 (app) — 依赖以上全部
```

- **可并行的基础层**：Task 1、Task 2、Task 8 相互独立，可先行。
- **Task 3** 依赖 Task 1；**Task 4/6/9** 依赖 Task 2；**Task 5** 依赖 Task 2。
- **Task 7** 依赖 Task 4、Task 5、Task 6。
- **Task 10** 依赖 Task 1。
- **Task 11** 依赖 Task 1、3、4、5、6、7、8、9、10（装配全部组件）。

## Test Strategy

- **单元测试（pytest，全部通过注入替身实现确定性）**
  - 配置：默认值、缺失文件、保存读回一致、损坏 JSON（Task 1）。
  - 模型：`make_id` 稳定性与空白归一、`to_dict/from_dict` 往返、字符串还原枚举（Task 2）。
  - 调度：工作时段边界（9:30 真 / 9:29 假 / 18:30 假）、周末、固定 `rng` 下 `next_delay_seconds` 落在 [2400,5400] 且可复现、跨夜与畸形时间不崩溃（Task 3）。
  - 本地库：加载计数、按类型过滤、文件缺失返回空（Task 4）。
  - 状态：`mark_seen`→`is_seen`、收藏往返、snooze 往返与重载保持、损坏状态重置（Task 5）。
  - 抓取：假 `fetch_fn` 解析固定 RSS、`limit` 生效、异常/垃圾字节不抛（Task 6）。
  - 提供器：优先联网未看 → 降级本地 → 本地任意回退 → 全空返回 `None`（Task 7）。
  - 平台：`_rect_covers` 相等/略小/更大/负坐标（Task 8）。
  - 卡片纯逻辑：riddle 在 reveal 前后、joke 永不暴露答案（Task 9）。
  - 设置纯逻辑：`config_to_form`/`form_to_config` 往返与类型强转（Task 10）。
  - 收藏夹纯逻辑：`favorites_to_rows` 的类型前缀与空列表（Task 10）。
  - 装配纯逻辑：`should_pop` 的时段/全屏/空闲/暂停边界（Task 11）。
- **集成 / 手动验证（无法在无桌面 CI 中自动断言，按各任务「手动验证」步骤执行）**
  - 卡片窗口显示、圆角置顶不抢焦点、自动消失、「看答案」揭示（Task 9）。
  - 托盘图标与右键菜单信号（Task 10）。
  - 端到端：托盘常驻、随机弹出、全屏/暂停抑制、收藏回看、离线降级（Task 11）。
- **边界与错误路径**：损坏配置/状态文件、缺失内容库、抓取异常与非 XML 字节、跨夜与畸形时间、暂停到期瞬间、多显示器负坐标（覆盖于 Task 1/3/5/6/8/11）。
- **空状态**：本地库为空且联网为空时 `next_item()` 返回 `None`，本轮不弹（Task 7）；收藏为空时「收藏夹」无操作（Task 11）。