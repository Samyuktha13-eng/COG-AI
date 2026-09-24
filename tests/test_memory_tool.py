from memory.store import MemoryStore
from tools.memory import MemoryTool
from tools.router import ToolRouter


def test_memory_tool_save_query_get():
    tool = MemoryTool(MemoryStore())
    saved = tool.save({"patient_id":"P001","title":"Jasmine morning","story":"Lakshmi collected jasmine flowers.","source":"caregiver","confidence":1,"sensitive":False,"language":"en"})
    assert saved["success"] is True
    result = tool.query("P001", "jasmine flowers")
    assert result["results"][0]["memory_id"] == saved["memory_id"]
    assert tool.get("P001", saved["memory_id"])["success"] is True


def test_router_memory_execution_and_clarification_safety():
    store = MemoryStore()
    tool = MemoryTool(store)
    router = ToolRouter(memory_tool=tool)
    keys = ("task", "time", "date", "reminder_type", "recurrence", "person", "memory_id", "game")
    semantic = {"intent":"query_memory","language":"en","entities":{key:None for key in keys},"confidence":.9,"needs_clarification":False,"clarification_question":None}
    semantic["entities"]["person"] = "Anjali"
    assert router.execute(semantic, patient_id="P001")["tool_result"]["operation"] == "query"
    semantic["intent"] = "save_memory"
    semantic["needs_clarification"] = True
    semantic["clarification_question"] = "What should I remember?"
    assert router.execute(semantic, patient_id="P001")["route"] == "clarification"
