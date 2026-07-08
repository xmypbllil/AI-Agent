from memory import CacheEntry, MemoryEvent, SQLiteMemory


def test_sqlite_memory_records_events_and_cache(tmp_path) -> None:
    memory = SQLiteMemory(tmp_path / "memory.sqlite")
    memory.initialize()

    memory.append_event(MemoryEvent(kind="action", payload="opened app"))
    memory.put_cache(CacheEntry(key="project", value="s7-1200"))

    assert memory.recent_events(1)[0].payload == "opened app"
    assert memory.get_cache("project") == "s7-1200"
