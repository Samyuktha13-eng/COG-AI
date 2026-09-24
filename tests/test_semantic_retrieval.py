from memory.minilm_embedder import MiniLMEmbedder, MiniLMUnavailableError
from memory.semantic_retriever import SemanticMemoryRetriever
from reminiscence.memory_selector import MemoryCandidate, MemorySelector
import importlib.util


class FakeEmbedder:
    def embed(self, texts):
        result = []
        for text in texts:
            lowered = text.casefold()
            result.append([1.0, 0.0] if "school" in lowered or "radha" in lowered or "walk" in lowered else [0.0, 1.0])
        return result


class CandidateSource:
    def candidates(self, patient_id):
        return [
            MemoryCandidate("school", "School Morning", "story_scene", topics=["school", "morning"], people=["Radha"], activities=["walking"]),
            MemoryCandidate("mango", "Mango Tree", "story_scene", topics=["mango", "summer"], people=["father"], activities=["eating"]),
        ]


def test_semantic_retrieval_ranks_structured_school_memory():
    retriever = SemanticMemoryRetriever(MemorySelector([CandidateSource()]), FakeEmbedder(), semantic_weight=0.35)
    ranked = retriever.retrieve("P001", "I used to walk with Radha.", {"entities": {"person": "Radha", "concepts": ["school", "walking"]}})
    assert [candidate.memory_id for candidate in ranked] == ["school", "mango"]


def test_retriever_does_not_invent_memories():
    retriever = SemanticMemoryRetriever(MemorySelector([CandidateSource()]), FakeEmbedder())
    assert retriever.retrieve("P001", "A memory not present", limit=0) == []
    assert {candidate.memory_id for candidate in retriever.retrieve("P001", "I used to walk with Radha.")} <= {"school", "mango"}


def test_minilm_adapter_is_import_safe_and_clear_when_unavailable():
    if importlib.util.find_spec("sentence_transformers") is None:
        try:
            MiniLMEmbedder().embed(["hello"])
        except MiniLMUnavailableError as error:
            assert "sentence-transformers" in str(error)
    else:
        class FakeModel:
            def encode(self, texts, convert_to_numpy):
                return [[1.0] for _ in texts]

        assert MiniLMEmbedder(model=FakeModel()).embed(["hello"]) == [[1.0]]
