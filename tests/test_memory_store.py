from memory.store import MemoryStore


def record(patient_id="P001", title="Village temple visit", story="Anjali visited the village temple with her sister.", **extra):
    return {"patient_id": patient_id, "title": title, "story": story, "source": "caregiver", "confidence": 0.95, "sensitive": False, "language": "en", **extra}


def test_save_get_list_update_delete():
    store = MemoryStore()
    saved = store.save_memory(record())
    assert saved["memory_id"].startswith("mem_")
    assert store.get_memory(saved["memory_id"])["title"] == saved["title"]
    assert store.update_memory(saved["memory_id"], "P001", {"emotion": "happy"})["emotion"] == "happy"
    assert store.delete_memory(saved["memory_id"], "P001") is True
    assert store.get_memory(saved["memory_id"]) is None


def test_patient_isolation():
    store = MemoryStore()
    p1 = store.save_memory(record("P001"))
    p2 = store.save_memory(record("P002", title="Private memory", story="Private place."))
    assert len(store.list_memories("P001")) == 1
    assert store.get_memory(p2["memory_id"], "P001") is None
