from dataclasses import dataclass, field, replace
from typing import List, Optional


@dataclass(frozen=True)
class ReflectionState:
    entries: List[str] = field(default_factory=list)
    last_reflection: Optional[str] = None

    def add_entry(self, entry: str) -> "ReflectionState":
        new_entries = list(self.entries)
        new_entries.append(entry)
        return replace(self, entries=new_entries, last_reflection=entry)

    def summarize_reflections(self):
        # Placeholder for future summarization that would return a new ReflectionState
        return self
    
    def to_list(self) -> list:
        return list(self.entries)

    def to_context(self) -> str:
        return self.last_reflection or ""

    @staticmethod
    def load(entries_list: List[str]) -> "ReflectionState":
        last = entries_list[-1] if entries_list else None
        return ReflectionState(entries=entries_list, last_reflection=last)