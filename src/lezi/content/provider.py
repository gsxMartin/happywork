from __future__ import annotations

import random

from ..models import ContentItem
from ..state import StateStore
from .fetcher import QuipFetcher
from .store import ContentStore


class ContentProvider:
    def __init__(
        self,
        store: ContentStore,
        fetcher: QuipFetcher | None,
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
        local = self.store.all()

        # 本地趣味内容与联网乐子并重：未看过的合并成一个池子随机抽取，
        # 避免任何一方（尤其量少的本地库）被永久饿死。
        fresh = [i for i in (*online, *local) if not self.state.is_seen(i.id)]
        if fresh:
            return self.rng.choice(fresh)

        if local:
            return self.rng.choice(local)
        return None