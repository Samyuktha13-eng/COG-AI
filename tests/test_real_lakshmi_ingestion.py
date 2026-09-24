from pathlib import Path

from memory.retriever import MemoryRetriever
from memory.store import MemoryStore
from memory.story_ingestion import ingest_story


EXPECTED = [
    "The Jasmine Morning", "The Mango Tree", "The Rainy-Day Kitchen", "The School Morning",
    "The Railway Station", "Her Wedding Morning", "The First Home With Her Husband",
    "The Day Her Daughter Was Born", "The First Day of School", "The First Festival With Her Children",
    "Her Husband's Evening Ritual", "The Last Letter", "The Grandchildren",
    "The House After Everyone Left", "The Memory of Making Pickles", "The Last Walk Through the Garden",
]


def test_real_lakshmi_story_ingestion_and_retrieval():
    text = Path("data/lakshmi_story.txt").read_text(encoding="utf-8")
    store = MemoryStore()
    first = ingest_story("P001", text, source="caregiver", store=store)
    second = ingest_story("P001", text, source="caregiver", store=store)
    memories = store.list_memories("P001")
    assert first["sections_detected"] == 16
    assert first["memories_created"] == 16
    assert second["memories_created"] == 0
    assert second["chunks_stored"] == 0
    assert [memory["title"] for memory in memories] == EXPECTED
    assert len(store.list_chunks("P001")) == first["chunks_stored"]
    retriever = MemoryRetriever(store)
    expected = {
        "Tell me about Lakshmi's jasmine flowers.": "The Jasmine Morning",
        "What did Lakshmi make every summer?": "The Memory of Making Pickles",
        "Tell me about her grandchildren.": "The Grandchildren",
        "What happened at the railway station?": "The Railway Station",
        "Tell me about her husband.": "The First Home With Her Husband",
        "What did Lakshmi do before festivals?": "The First Festival With Her Children",
        "What did Lakshmi's father do with the mango?": "The Mango Tree",
        "Tell me about Lakshmi's daughter's first day of school.": "The First Day of School",
    }
    for query, title in expected.items():
        results = retriever.search_memories("P001", query)
        assert results and results[0]["title"] == title
        assert results[0]["memory"]["story"] in text
    private = store.save_memory({"patient_id":"P002","title":"Private test","story":"P002 only.","source":"test","confidence":1,"sensitive":False,"language":"en"})
    assert all(item["memory_id"] != private["memory_id"] for item in retriever.search_memories("P001", "P002 only"))
    assert store.delete_memory(private["memory_id"], "P002")
    store.close()
