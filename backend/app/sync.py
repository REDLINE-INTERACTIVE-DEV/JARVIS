"""Provider-neutral incremental sync boundary for JARVIS."""
from dataclasses import dataclass

@dataclass(frozen=True)
class SyncEvent:
    provider: str
    account_id: str
    external_id: str
    version: str
    event_type: str
    title: str
    content: str
    occurred_at: str | None = None

class IncrementalSync:
    def __init__(self, provider: str):
        self.provider = provider

    def to_event(self, device_id: str, item: SyncEvent) -> dict:
        if item.provider != self.provider:
            raise ValueError(f"expected provider {self.provider}")
        return {"source_device": device_id, "provider": item.provider, "account_id": item.account_id,
                "event_type": item.event_type, "title": item.title, "content": item.content,
                "external_id": item.external_id, "version": item.version, "created_at": item.occurred_at}
