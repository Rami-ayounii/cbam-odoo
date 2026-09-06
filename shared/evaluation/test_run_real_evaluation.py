from run_real_evaluation import build_llm_client_factory


def test_llm_client_factory_returns_one_client_per_record_with_shared_config():
    factory = build_llm_client_factory(
        model="test-model", base_url="http://localhost:11434/v1", api_key="ollama"
    )

    client_a = factory({"record_id": "A"})
    client_b = factory({"record_id": "B"})

    assert client_a is not client_b  # a fresh client per record - no shared mutable state
    assert client_a._model == "test-model"
