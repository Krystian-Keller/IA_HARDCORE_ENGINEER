import json

import pytest

from app.schemas import AppError, SearchResult
from tests.conftest import ACCEPTANCE_CASES


@pytest.mark.parametrize("message,route", ACCEPTANCE_CASES)
def test_acceptance_cases_through_real_agents(client, settings, gemini, monkeypatch, message, route):
    corpus = settings.data_dir / "rag/chunks.json"
    corpus.parent.mkdir()
    corpus.write_text(json.dumps([{
        "text": "Get Clássica Get Smart Pix bank account Getnet receivables advance antecipação "
                "crediário installments WhatsApp Payment Link. This is only a test document.",
        "source": "https://www.getnet.net/en",
    }]))
    monkeypatch.setattr("app.agents.knowledge.web_search", lambda *args, **kwargs: [
        SearchResult(title="Test result", snippet="Test context", url="https://example.com/test")
    ])
    responses = [json.dumps({"route": route})]
    if route == "customer_support":
        responses.append('{"tools":["get_customer_activity"]}')
    responses.append("Resposta de teste baseada no contexto.")
    gemini.generate.side_effect = responses
    response = client.post("/chat", json={"message": message, "user_id": "cliente1988"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Resposta de teste baseada no contexto."
    expected_agent = "customer_support" if route == "customer_support" else "knowledge"
    assert body["agents_used"] == ["router", expected_agent]
    tool = {"knowledge_getnet": "getnet_rag", "knowledge_web": "web_search",
            "customer_support": "get_customer_activity"}[route]
    assert body["tools_used"] == [tool]
    assert body["sources"] == ({"knowledge_getnet": ["https://www.getnet.net/en"],
                                "knowledge_web": ["https://example.com/test"],
                                "customer_support": []}[route])
    generation_prompt = gemini.generate.call_args.args[0]
    if route == "customer_support":
        assert "DEMO_DECLINED" in generation_prompt
        assert "2026-10-15" in generation_prompt
    else:
        assert body["sources"][0] in generation_prompt


def test_profile_tool_is_selected(client, gemini):
    gemini.generate.side_effect = ['{"route":"customer_support"}',
                                   '{"tools":["get_customer_profile"]}', "Dados fictícios do perfil."]
    response = client.post("/chat", json={"message": "Qual minha configuração de recebimento?",
                                         "user_id": "cliente1988"})
    assert response.status_code == 200
    assert response.json()["tools_used"] == ["get_customer_profile"]
    assert "receiving_configuration" in gemini.generate.call_args.args[0]


def test_unknown_customer_is_explicit(client, gemini):
    gemini.generate.side_effect = ['{"route":"customer_support"}',
                                   '{"tools":["get_customer_activity"]}']
    response = client.post("/chat", json={"message": "Minhas vendas", "user_id": "unknown"})
    assert response.status_code == 404
    assert "Não há dados" in response.json()["detail"]
    assert gemini.generate.call_count == 2


def test_missing_rag_does_not_break_health_or_web(client, gemini, monkeypatch):
    gemini.generate.return_value = '{"route":"knowledge_getnet"}'
    response = client.post("/chat", json={"message": "Getnet?", "user_id": "cliente1988"})
    assert response.status_code == 503
    assert "ingest" in response.json()["detail"]
    assert client.get("/health").json() == {"status": "ok"}
    monkeypatch.setattr("app.agents.knowledge.web_search", lambda *args, **kwargs: [])
    gemini.generate.side_effect = ['{"route":"knowledge_web"}', "Não há informações suficientes."]
    response = client.post("/chat", json={"message": "Clima?", "user_id": "cliente1988"})
    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "CONTEXT: []" in gemini.generate.call_args.args[0]


@pytest.mark.parametrize("decision", ['{"route":"invalid"}', 'not json'])
def test_invalid_router_returns_502(client, gemini, decision):
    gemini.generate.return_value = decision
    assert client.post("/chat", json={"message": "Hello", "user_id": "x"}).status_code == 502


@pytest.mark.parametrize("selection", ['{"tools":[]}', '{"tools":["arbitrary_tool"]}', "not json"])
def test_invalid_tool_selection_is_controlled(client, gemini, selection):
    gemini.generate.side_effect = ['{"route":"customer_support"}', selection]
    assert client.post("/chat", json={"message": "My sales", "user_id": "x"}).status_code == 502


@pytest.mark.parametrize("payload", [
    {}, {"message": "", "user_id": "x"}, {"message": "   ", "user_id": "x"},
    {"message": "Hello", "user_id": ""}, {"message": "a" * 5001, "user_id": "x"},
])
def test_request_validation(client, gemini, payload):
    assert client.post("/chat", json=payload).status_code == 422
    gemini.generate.assert_not_called()


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_dependency_errors_have_consistent_json(client, gemini, status):
    gemini.generate.side_effect = AppError(status, "Serviço indisponível")
    response = client.post("/chat", json={"message": "Hello", "user_id": "x"})
    assert response.status_code == status
    assert response.json() == {"detail": "Serviço indisponível"}
