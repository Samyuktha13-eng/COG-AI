from memory.retriever import MemoryRetriever
from memory.store import MemoryStore


def test_retrieve_person_relationship_place_and_no_hallucination():
    store = MemoryStore()
    saved = store.save_memory({"patient_id":"P001","title":"Village temple visit","people":["Anjali"],"relationships":["sister"],"place":"family village","activity":"visiting temple","objects":["flowers","temple"],"story":"Anjali remembers visiting the village temple with her sister.","source":"caregiver","confidence":0.95,"sensitive":False,"language":"en"})
    retriever = MemoryRetriever(store)
    assert retriever.search_memories("P001", "Anjali")[0]["memory_id"] == saved["memory_id"]
    assert retriever.search_memories("P001", "sister")[0]["title"] == "Village temple visit"
    assert retriever.search_memories("P001", "village temple")[0]["title"] == "Village temple visit"
    assert retriever.search_memories("P001", "Delhi") == []


def test_multilingual_metadata_shares_one_store():
    store = MemoryStore()
    store.save_memory({"patient_id":"P001","title":"Telugu memory","story":"నీళ్లు", "source":"caregiver","confidence":1,"sensitive":False,"language":"te"})
    assert len(store.list_memories("P001")) == 1
    assert store.list_memories("P001")[0]["language"] == "te"
