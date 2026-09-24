from memory.store import MemoryStore
from memory.story_ingestion import ingest_story


STORY = "\n\n".join(f"# {index}. Section {index}\n\nLakshmi remembers detail {index}." for index in range(1, 17))


def test_ingests_sixteen_ordered_sections_and_chunks():
    store = MemoryStore()
    report = ingest_story("P001", STORY, store=store)
    memories = store.list_memories("P001")
    chunks = store.list_chunks("P001")
    assert report["sections_detected"] == 16
    assert report["memories_stored"] == 16
    assert len(memories) == 16
    assert [item["sequence"] for item in memories] == list(range(1, 17))
    assert all(item["patient_id"] == "P001" and item["source"] == "caregiver" for item in memories)
    assert len(chunks) == 16
    assert all(item["text"].startswith("Lakshmi remembers") for item in chunks)


def test_ingestion_sensitive_metadata_is_source_derived():
    store = MemoryStore()
    story = "# The Last Letter\n\nHer husband became sick. Before he died, he gave her a folded letter."
    ingest_story("P001", story, store=store)
    assert store.list_memories("P001")[0]["sensitive"] is True
