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