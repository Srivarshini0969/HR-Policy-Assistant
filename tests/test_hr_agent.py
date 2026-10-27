import json
from pathlib import Path

import app as hr_app


def test_home_page_loads():
    client = hr_app.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"HR Policy Assistant" in response.data


def test_empty_question_rejected():
    client = hr_app.app.test_client()
    response = client.post("/api/chat", json={"question": "   "})
    assert response.status_code == 400


def test_unknown_question_escalates_without_calling_ollama(monkeypatch):
    client = hr_app.app.test_client()
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Ollama should not be called for unsupported questions")
    monkeypatch.setattr(hr_app.requests, "post", fail_if_called)
    response = client.post("/api/chat", json={"question": "What is the Mars relocation allowance?"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["escalated"] is True


def test_sick_documentation_question_escalates(monkeypatch):
    client = hr_app.app.test_client()
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Ollama should not be called for policy not specified")
    monkeypatch.setattr(hr_app.requests, "post", fail_if_called)
    response = client.post("/api/chat", json={"question": "Is medical documentation required for sick leave?"})
    assert response.status_code == 200
    assert response.get_json()["escalated"] is True


def test_reindex_endpoint():
    client = hr_app.app.test_client()
    response = client.post("/api/reindex")
    assert response.status_code == 200
    assert response.get_json()["document_sections"] > 0
