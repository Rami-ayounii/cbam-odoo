from types import SimpleNamespace

from fastapi.testclient import TestClient

import main

TEST_API_KEY = "test-orchestrator-api-key"
AUTH_HEADERS = {"X-Api-Key": TEST_API_KEY}


def test_system_prompt_states_the_job_is_not_done_without_a_write():
    assert "write_declaration_line" in main.SYSTEM_PROMPT
    assert "not finished" in main.SYSTEM_PROMPT


def test_load_tool_schemas_returns_all_seven_wrapped_for_openai():
    schemas = main._load_tool_schemas()

    assert len(schemas) == 7
    for schema in schemas:
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert "parameters" in schema["function"]


def test_create_job_returns_job_id_and_invokes_run_job_in_background(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", TEST_API_KEY)
    calls = []

    def fake_run_job(job_id, request):
        calls.append((job_id, request))
        main._JOBS[job_id] = {"status": "completed", "final_message": "ok", "iterations": 1}

    monkeypatch.setattr(main, "_run_job", fake_run_job)

    with TestClient(main.app) as client:
        response = client.post(
            "/jobs",
            json={"declaration_id": 1, "declaration_line_id": 2, "reporting_year": 2026},
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert len(calls) == 1
    assert calls[0][0] == job_id


def test_create_job_rejects_missing_api_key(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", TEST_API_KEY)

    with TestClient(main.app) as client:
        response = client.post(
            "/jobs",
            json={"declaration_id": 1, "declaration_line_id": 2, "reporting_year": 2026},
        )

    assert response.status_code == 401


def test_create_job_rejects_wrong_api_key(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", TEST_API_KEY)

    with TestClient(main.app) as client:
        response = client.post(
            "/jobs",
            json={"declaration_id": 1, "declaration_line_id": 2, "reporting_year": 2026},
            headers={"X-Api-Key": "wrong-key"},
        )

    assert response.status_code == 401


def test_create_job_rejects_everything_when_api_key_unconfigured(monkeypatch):
    # Fail closed: an unset ORCHESTRATOR_API_KEY must never be treated as
    # "auth disabled" - see _require_api_key's docstring comment.
    monkeypatch.delenv("ORCHESTRATOR_API_KEY", raising=False)

    with TestClient(main.app) as client:
        response = client.post(
            "/jobs",
            json={"declaration_id": 1, "declaration_line_id": 2, "reporting_year": 2026},
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 401


def test_get_job_status_returns_stored_status(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", TEST_API_KEY)
    monkeypatch.setattr(main, "_run_job", lambda job_id, request: None)

    with TestClient(main.app) as client:
        create_response = client.post(
            "/jobs",
            json={"declaration_id": 1, "declaration_line_id": 2, "reporting_year": 2026},
            headers=AUTH_HEADERS,
        )
        job_id = create_response.json()["job_id"]

        status_response = client.get(f"/jobs/{job_id}/status", headers=AUTH_HEADERS)

    assert status_response.status_code == 200
    assert status_response.json()["status"] in ("pending", "running", "completed")


def test_get_job_status_rejects_missing_api_key(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", TEST_API_KEY)

    with TestClient(main.app) as client:
        response = client.get("/jobs/does-not-exist/status")

    assert response.status_code == 401


def test_get_job_status_404_for_unknown_job(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", TEST_API_KEY)

    with TestClient(main.app) as client:
        response = client.get("/jobs/does-not-exist/status", headers=AUTH_HEADERS)

    assert response.status_code == 404


def test_run_job_marks_job_failed_on_exception(monkeypatch):
    monkeypatch.delenv("ODOO_URL", raising=False)
    job_id = "job-under-test"
    main._JOBS[job_id] = {"status": "pending"}

    request = main.JobRequest(declaration_id=1, declaration_line_id=2, reporting_year=2026)
    main._run_job(job_id, request)

    assert main._JOBS[job_id]["status"] == "failed"
    assert "error" in main._JOBS[job_id]


class _FakeLLMResponse:
    content = "nothing to extract"
    tool_calls = []


class _FakeLLMClientNoToolCalls:
    def __init__(self, **kwargs):
        pass

    def chat(self, messages, tools):
        return _FakeLLMResponse()


def _set_run_job_env(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://localhost:8069")
    monkeypatch.setenv("ODOO_DB", "test")
    monkeypatch.setenv("ODOO_USER", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "unused-in-this-test")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_API_KEY", "unused-in-this-test")


def test_run_job_reports_no_write_when_the_model_stops_without_writing(monkeypatch):
    _set_run_job_env(monkeypatch)
    captured = {}

    class FakeOdooClient:
        def __init__(self, **kwargs):
            pass

        def get_declaration_line_context(self, declaration_line_id):
            return {}

        def write_llm_trace(self, declaration_line_id, messages, extraction_status):
            captured["declaration_line_id"] = declaration_line_id
            captured["messages"] = messages
            captured["extraction_status"] = extraction_status

    monkeypatch.setattr(main, "OdooClient", FakeOdooClient)
    monkeypatch.setattr(main, "LLMClient", _FakeLLMClientNoToolCalls)

    job_id = "job-no-write-test"
    main._JOBS[job_id] = {"status": "pending"}
    request = main.JobRequest(declaration_id=1, declaration_line_id=2, reporting_year=2026)

    main._run_job(job_id, request)

    assert main._JOBS[job_id]["status"] == "no_write"
    assert captured["extraction_status"] == "needs_review"
    assert captured["declaration_line_id"] == 2
    assert captured["messages"]  # the actual tool-call trace, not empty
    final_message = main._JOBS[job_id]["final_message"]
    assert final_message  # never blank - always explains why nothing was written
    # The model stopped WITH non-empty content ("nothing to extract",
    # per _FakeLLMResponse) instead of an empty string - a consumer reading
    # only final_message must not be able to mistake that for a success
    # claim. Both the model's own message and an explicit "nothing was
    # recorded" statement must be present, not one replacing the other.
    assert "nothing to extract" in final_message
    assert "no result was recorded" in final_message.lower()


def test_run_job_reports_completed_when_the_model_actually_writes_a_result(monkeypatch):
    _set_run_job_env(monkeypatch)
    captured = {}

    class FakeOdooClient:
        def __init__(self, **kwargs):
            pass

        def get_declaration_line_context(self, declaration_line_id):
            return {}

        def write_declaration_line(self, declaration_line_id, **data):
            return declaration_line_id

        def write_llm_trace(self, declaration_line_id, messages, extraction_status):
            captured["declaration_line_id"] = declaration_line_id
            captured["extraction_status"] = extraction_status

    class _WriteThenStopLLMClient:
        _calls = 0

        def __init__(self, **kwargs):
            pass

        def chat(self, messages, tools):
            _WriteThenStopLLMClient._calls += 1
            if _WriteThenStopLLMClient._calls == 1:
                return SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id="call-1",
                            name="write_declaration_line",
                            args={
                                "declaration_id": 1,
                                "good_id": 5,
                                "installation_id": 7,
                                "quantity_tonnes": 10.0,
                                "data_source": "actual",
                            },
                        )
                    ],
                )
            return SimpleNamespace(content="done", tool_calls=[])

    monkeypatch.setattr(main, "OdooClient", FakeOdooClient)
    monkeypatch.setattr(main, "LLMClient", _WriteThenStopLLMClient)

    job_id = "job-real-completion-test"
    main._JOBS[job_id] = {"status": "pending"}
    request = main.JobRequest(declaration_id=1, declaration_line_id=2, reporting_year=2026)

    main._run_job(job_id, request)

    assert main._JOBS[job_id]["status"] == "completed"
    assert captured["extraction_status"] == "extracted"


def test_run_job_redacts_configured_secrets_from_error_message(monkeypatch):
    monkeypatch.setenv("ODOO_URL", "http://localhost:8069")
    monkeypatch.setenv("ODOO_DB", "test")
    monkeypatch.setenv("ODOO_USER", "admin")
    monkeypatch.setenv("ODOO_PASSWORD", "super-secret-pw")

    class ExplodingOdooClient:
        def __init__(self, **kwargs):
            raise RuntimeError("login failed for password=super-secret-pw")

    monkeypatch.setattr(main, "OdooClient", ExplodingOdooClient)

    job_id = "job-redact-test"
    main._JOBS[job_id] = {"status": "pending"}
    request = main.JobRequest(declaration_id=1, declaration_line_id=2, reporting_year=2026)

    main._run_job(job_id, request)

    assert main._JOBS[job_id]["status"] == "failed"
    assert "super-secret-pw" not in main._JOBS[job_id]["error"]
    assert "[REDACTED]" in main._JOBS[job_id]["error"]


def test_redact_secrets_replaces_all_configured_secret_values(monkeypatch):
    monkeypatch.setenv("ODOO_PASSWORD", "pw-value")
    monkeypatch.setenv("OLLAMA_API_KEY", "ollama-key-value")
    monkeypatch.setenv("ORCHESTRATOR_API_KEY", "orch-key-value")

    result = main._redact_secrets(
        "error: pw-value, ollama-key-value, orch-key-value all appeared"
    )

    assert "pw-value" not in result
    assert "ollama-key-value" not in result
    assert "orch-key-value" not in result


def test_run_job_includes_declaration_line_context_in_initial_user_message(monkeypatch):
    _set_run_job_env(monkeypatch)

    class FakeOdooClient:
        def __init__(self, **kwargs):
            pass

        def get_declaration_line_context(self, declaration_line_id):
            return {"good_id": 5, "installation_id": 7, "quantity_tonnes": 41.88}

        def write_llm_trace(self, **kwargs):
            pass

    captured = {}

    class CapturingLLMClient:
        def __init__(self, **kwargs):
            pass

        def chat(self, messages, tools):
            captured["messages"] = messages
            return _FakeLLMResponse()

    monkeypatch.setattr(main, "OdooClient", FakeOdooClient)
    monkeypatch.setattr(main, "LLMClient", CapturingLLMClient)

    job_id = "job-context-test"
    main._JOBS[job_id] = {"status": "pending"}
    request = main.JobRequest(declaration_id=1, declaration_line_id=2, reporting_year=2026)

    main._run_job(job_id, request)

    user_message = captured["messages"][1]["content"]
    assert '"good_id": 5' in user_message
    assert '"installation_id": 7' in user_message
    assert '"quantity_tonnes": 41.88' in user_message
