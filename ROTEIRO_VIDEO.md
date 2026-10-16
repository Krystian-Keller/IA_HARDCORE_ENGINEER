# Roteiro de vídeo — AI Hardcore Engineer

**Duração planejada: 9min20s. Limite: 10 minutos.** As falas abaixo podem ser lidas ou adaptadas. As instruções de tela não fazem parte da fala.

## Preparação antes de gravar

1. Deixe a API rodando e o RAG carregado. Use o README, se precisar preparar o ambiente.
2. Separe os históricos que você já salvou: `pytest`, `evals.run` e logs. Marque os trechos `124 passed` e `Passed: 15 / Failed: 0 / Accuracy: 100.00%`.
3. Execute o **manual completo antes de gravar**, com o comando do apêndice A. Ele leva alguns minutos e salva as respostas em `/tmp/ai-hardcore-manual.txt`.
4. Abra o manual salvo e deixe marcados quatro casos: `customer_deposit`, `getnet_machines`, `weather_porto_alegre` e `guardrail_other_customer`.
5. Prepare três áreas: editor com os arquivos abaixo, terminal com históricos e terminal para uma chamada ao vivo. Deixe a prévia do README com o Mermaid renderizado.
6. Use `.env.example` para mostrar a configuração; mantenha o valor real da chave fora da gravação.

**Estratégia de tempo:** apresente os resultados salvos como uma execução anterior. Durante o vídeo, rode somente uma chamada manual. Caso a API externa demore, use o manual salvo e informe isso. Não espere o lote completo de 15 casos durante a gravação.

## Cronograma

| Tempo | Assunto | Tela principal |
| --- | --- | --- |
| 00:00–00:30 | Objetivo | README, início |
| 00:30–01:05 | Execução e configuração | README, `.env.example`, Docker |
| 01:05–01:50 | Arquitetura | Mermaid e `app/main.py` |
| 01:50–02:40 | Router e Gemini | `router.py`, `schemas.py`, `gemini.py` |
| 02:40–03:40 | Knowledge: RAG e web | `ingest.py`, `retriever.py`, `knowledge.py` |
| 03:40–04:20 | Atendimento e dados | `customer_support.py`, `customers.json` |
| 04:20–05:00 | Guardrail e escalonamento | `guardrail.py`, `human_escalation.py` |
| 05:00–05:35 | Testes automatizados | Histórico do pytest e pasta `tests/` |
| 05:35–06:15 | Avaliação real | Histórico da avaliação e `evals/` |
| 06:15–07:55 | JSON completo | Chamada manual e manual salvo |
| 07:55–08:35 | Logs e rastreabilidade | Histórico dos logs e `logging_config.py` |
| 08:35–09:10 | Decisões e limitações | README, limitações |
| 09:10–09:20 | Encerramento | README ou resultado da avaliação |

## 00:00–00:30 — Apresentação

**Mostrar:** título e primeiro parágrafo do [README](README.md).

**Fala:**

> Neste vídeo eu vou apresentar o AI Hardcore Engineer, uma API de suporte que usa agentes para separar perguntas sobre Getnet, consultas gerais na web e problemas específicos de clientes. Vou mostrar a arquitetura, as principais decisões e os resultados da execução. A solução usa Python, FastAPI e Gemini, com documentos e dados fictícios armazenados localmente.

## 00:30–01:05 — Como executar

**Mostrar:** seções de configuração e Docker do README; `.env.example`; uma passagem rápida pelo `Dockerfile` e `docker-compose.yml`. Apenas aponte os comandos, sem reconstruir a imagem.

**Comando rápido, se quiser mostrar a API respondendo:**

```bash
curl -fsS --max-time 3 http://localhost:8000/health
```

**Fala:**

> O README concentra os comandos para configurar, subir e testar o projeto. A chave e o modelo vêm de variáveis de ambiente. Com Docker, existe apenas um serviço: a API. A ingestão é executada separadamente para preparar o RAG. Aqui o health retorna status ok, indicando que a aplicação está respondendo; ele não testa a disponibilidade do Gemini.

## 01:05–01:50 — Arquitetura

**Mostrar:** diagrama Mermaid na seção “Arquitetura”. Depois, em [app/main.py](app/main.py), localize `chat` e a composição em `get_router`.

**Fala:**

> A entrada é o POST chat. Primeiro passa pelo guardrail. Se a solicitação for suportada, o Router escolhe Knowledge ou Customer Support. O Knowledge possui os modos RAG e busca web. O quarto agente é o Human Escalation, que trata bloqueios e situações que o sistema não consegue resolver. A comunicação acontece por funções Python no mesmo processo. Essa escolha mantém o projeto pequeno, síncrono e fácil de acompanhar, sem filas, microserviços ou framework de agentes.

## 01:50–02:40 — Router, contratos e Gemini

**Mostrar:**

- Em [app/agents/router.py](app/agents/router.py): `classify` e os encaminhamentos em `chat`.
- Em [app/schemas.py](app/schemas.py): `RouteDecision` e `ChatResponse`, sem percorrer o arquivo inteiro.
- Em [app/services/gemini.py](app/services/gemini.py): `generate`, `response_json_schema` e timeout.

**Fala:**

> O Router usa Gemini para escolher entre três rotas: conhecimento Getnet, conhecimento web ou atendimento do cliente. A decisão vem em JSON estruturado e é validada com Pydantic antes de ser usada. Uma rota inválida gera escalonamento. Todas as chamadas ao Gemini estão centralizadas neste módulo, que configura modelo, timeout e tratamento de erros. Assim, os agentes não precisam conhecer os detalhes do SDK, e os contratos permanecem explícitos.

## 02:40–03:40 — Knowledge: RAG e busca web

**Mostrar:**

1. Em [app/rag/ingest.py](app/rag/ingest.py): `SEED_URLS` e `chunk_text`.
2. Em [app/rag/retriever.py](app/rag/retriever.py): `TfidfVectorizer` e `retrieve`.
3. Em [app/agents/knowledge.py](app/agents/knowledge.py): os dois caminhos de `answer` e a condição `if not context`.

**Fala:**

> No RAG, o projeto baixa um conjunto limitado de páginas Getnet, extrai o texto com BeautifulSoup e cria chunks com suas URLs. Os documentos ficam em JSON. Na consulta, o TF-IDF representa os termos e a similaridade de cosseno seleciona até quatro trechos para o Gemini. Escolhi esse caminho porque é local, simples e não exige embeddings pagos nem banco vetorial. O retrieval não depende de baixar as páginas novamente, mas a geração ainda acessa Gemini. Para perguntas externas, o outro caminho usa snippets do DuckDuckGo. Sem resultados, o agente escalona; com contexto, o prompt orienta a responder apenas com o que está fundamentado.

**Ao navegar:** a busca está implementada em [app/tools/web_search.py](app/tools/web_search.py). Basta apontar o arquivo na árvore; não é necessário abri-lo neste minuto.

## 03:40–04:20 — Customer Support

**Mostrar:** o mapa de funções `available` em [app/agents/customer_support.py](app/agents/customer_support.py), depois o cliente `cliente1988` em [data/customers.json](data/customers.json). Aponte perfil, vendas, depósitos e máquina.

**Fala:**

> O atendimento consulta duas tools: uma retorna perfil e configuração de recebimento; a outra retorna atividade, como vendas, depósitos previstos e estado da máquina. O Gemini seleciona as funções necessárias, e a execução usa uma lista explícita de tools permitidas. Os registros de cliente1988 são fictícios e têm um snapshot fixo. As datas de depósito são previsões desses registros, não uma consulta bancária real. Cliente inexistente recebe uma resposta clara de ausência de dados.

**Referência, se precisar localizar as funções:** [app/tools/customer_data.py](app/tools/customer_data.py).

## 04:20–05:00 — Guardrail e escalonamento

**Mostrar:** `check_guardrail` em [app/guardrails/guardrail.py](app/guardrails/guardrail.py) e `handle` em [app/agents/human_escalation.py](app/agents/human_escalation.py).

**Fala:**

> O guardrail classifica a entrada como supported, irrelevant, sensitive ou unsafe. Somente supported segue para o Router. Solicitações de dados de outro cliente, por exemplo, são bloqueadas. Uma decisão inválida também recebe tratamento conservador. O Human Escalation devolve uma resposta determinística, com status escalated e um motivo padronizado. Esse encaminhamento é simulado: nenhum operador é contatado. E o guardrail não substitui autenticação; este projeto trabalha com dados de demonstração.

## 05:00–05:35 — Histórico dos testes

**Mostrar:** o histórico já salvo do comando abaixo, terminando em `124 passed`. Aponte rapidamente `test_api.py`, `test_guardrail.py`, `test_rag.py` e `test_logging.py` na pasta `tests/`.

```bash
docker compose exec api python -m pytest -q
```

**Fala:**

> Esta é uma execução anterior dos testes automatizados: 124 passaram. Eles cobrem os contratos da API, roteamento, guardrails, escalonamento, recuperação de documentos e rastreabilidade. Gemini, busca web e downloads são simulados, então esses testes não consomem a API nem dependem da internet. Também há um teste da serialização do SDK com transporte HTTP simulado, para verificar o schema enviado ao Google.

**Se o aviso de depreciação estiver visível:** “O aviso é de uma dependência de testes; nessa execução não houve falha.”

## 05:35–06:15 — Histórico da avaliação real

**Mostrar:** [evals/cases.json](evals/cases.json), incluindo um caso normal e um caso de guardrail. Depois, o histórico de `evals.run` com `15 passed`, `0 failed` e `100.00%`. Se houver tempo, aponte a comparação `actual == expected` em [evals/run.py](evals/run.py).

```bash
docker compose exec api python -m evals.run
```

**Fala:**

> Esta avaliação faz chamadas reais à aplicação. São quinze casos, cobrindo os dez cenários originais, o perfil do cliente e quatro bloqueios de guardrail. Nesta execução, todos passaram. A comparação é determinística: verifica rota, categoria, tools, escalonamento e request ID. Não há outro LLM julgando a redação. Portanto, cem por cento significa aprovação dos critérios de fluxo nessa rodada, e não garantia de precisão factual de todas as respostas.

## 06:15–07:55 — Manual com JSON completo

### Primeiro: uma chamada ao vivo, com timeout de leitura de 25 segundos

**Mostrar:** seção “Teste manual” do README. Cole o comando do apêndice B no terminal. Enquanto aguarda, explique o contrato da resposta.

**Fala enquanto a chamada executa:**

> Agora vou mostrar uma chamada manual com a resposta completa. Diferentemente da avaliação, aqui consigo ler o texto que foi gerado. A resposta também informa a rota, os agentes, as tools, as fontes e o identificador da requisição. Vou perguntar sobre o depósito das vendas do cliente de demonstração.

**Se retornar normalmente, destacar:** `route: customer_support`, `get_customer_activity`, `answer`, `request_id` e `status`.

**Fala após o retorno:**

> Aqui eu confiro tanto o caminho percorrido quanto o conteúdo. As previsões apresentadas devem corresponder aos registros locais que mostrei. O texto é uma interpretação desses dados fictícios, não uma confirmação de que houve transferência.

**Se houver timeout ou escalonamento por indisponibilidade:**

> Nesta tentativa a dependência externa não concluiu normalmente. Vou usar o registro da execução manual preparada antes da gravação para mostrar o formato das respostas. O tratamento da falha e o identificador permitem investigar o que aconteceu.

### Depois: três exemplos no manual salvo

**Mostrar:** `/tmp/ai-hardcore-manual.txt`, sem esperar outro lote. Procure pelos nomes dos casos no editor ou no terminal.

1. **`getnet_machines`:** destacar `knowledge_getnet`, `getnet_rag`, `sources` e ler somente a ideia central de `answer`.
2. **`weather_porto_alegre`:** destacar `knowledge_web`, `web_search` e as URLs.
3. **`guardrail_other_customer`:** destacar `guardrail_category: sensitive`, `status: escalated`, `escalation_reason: sensitive_request` e `tools_used: []`.

**Fala:**

> Neste registro do manual completo, o caso Getnet mostra o caminho do RAG e as fontes recuperadas. Quando a resposta admite que faltam informações, isso revela uma limitação da documentação disponível para aquela pergunta. No caso de clima, vemos a rota de busca web e suas fontes; ainda é necessário verificar a atualidade do conteúdo. Já a solicitação de dados de outro cliente foi bloqueada antes das tools, com motivo explícito de escalonamento. Um HTTP 200 indica que a solicitação foi processada; o campo status distingue resposta gerada de escalonamento.

**Controle de tempo:** mostre apenas esses trechos. Não leia quinze respostas nem listas completas de URLs.

## 07:55–08:35 — Logs e request ID

**Mostrar:** o histórico salvo de `docker compose logs -f api`. Selecione uma sequência de eventos que compartilham o mesmo `request_id`, em vez de rolar todo o histórico. Depois, abra [app/logging_config.py](app/logging_config.py), em `JsonFormatter` e `log_event`.

**Fala:**

> Os logs estruturados mostram recebimento, guardrail, rota, tools e conclusão. Estas linhas têm o mesmo request ID e representam etapas de uma única requisição. O volume vem desses eventos e do log de acesso do Uvicorn. A implementação usa apenas logging da biblioteca padrão e registra metadados operacionais, sem incluir mensagem, chave ou dados privados do cliente. O comando com menos f acompanha novas linhas; para a apresentação estou usando um histórico já salvo.

**Se quiser correlacionar o JSON ao vivo com os logs atuais:** copie seu `request_id`, execute o comando abaixo e localize esse identificador. Essa consulta é opcional e termina sozinha.

```bash
docker compose logs --tail 30 api
```

## 08:35–09:10 — Decisões e limitações

**Mostrar:** seção “Limitações” do README.

**Fala:**

> As decisões priorizaram simplicidade: chamadas diretas, JSON local, um container e TF-IDF. As limitações são explícitas: o RAG depende da cobertura e da coincidência de termos; snippets podem estar desatualizados; a redação e o idioma dependem do modelo; e existem cotas e indisponibilidade externas. O projeto demonstra os fluxos e seu tratamento de falhas, sem integração bancária real, autenticação ou atendimento humano real. Os resultados da avaliação precisam ser interpretados dentro desse escopo.

## 09:10–09:20 — Encerramento

**Mostrar:** resumo da avaliação ou início do README.

**Fala:**

> Com isso, a aplicação pode ser executada e verificada pelos comandos do README, tanto por aprovação e falha quanto pela inspeção das respostas completas. Obrigado.

---

## Apêndice A — Preparar e salvar o manual completo

**Execute antes de gravar, com a API funcionando.** Usa Gemini real. O comando lê os mesmos quinze casos da avaliação, imprime o JSON completo e salva o output no computador, fora do repositório.

```bash
docker compose exec -T api python - <<'PY' | tee /tmp/ai-hardcore-manual.txt
import json
import time
from pathlib import Path

import httpx

casos = json.loads(Path("evals/cases.json").read_text(encoding="utf-8"))

with httpx.Client(timeout=150) as client:
    for numero, caso in enumerate(casos, start=1):
        if numero > 1:
            time.sleep(15)
        print(f"\n{'=' * 60}", flush=True)
        print(f"Caso {numero}: {caso['name']}", flush=True)
        print(f"Rota esperada: {caso['expected_route']}", flush=True)
        print(caso["message"], flush=True)
        try:
            resposta = client.post(
                "http://localhost:8000/chat",
                json={"message": caso["message"], "user_id": caso["user_id"]},
            )
            print(f"HTTP {resposta.status_code}", flush=True)
            print(json.dumps(resposta.json(), ensure_ascii=False, indent=2), flush=True)
        except (httpx.HTTPError, ValueError) as erro:
            print(f"Falha: {erro}", flush=True)
PY
```

Abra o resultado no editor ou use:

```bash
less /tmp/ai-hardcore-manual.txt
```

No `less`, procure com `/nome_do_caso`, avance com `n` e saia com `q`. Inspecione as respostas antes da gravação. Se houver 429, aguarde conforme os limites do projeto e aumente a pausa entre casos quando for um limite de frequência.

## Apêndice B — Uma chamada ao vivo com JSON completo

**Use durante o trecho de demonstração.** Faz somente uma requisição ao `/chat`; o fluxo de atendimento pode usar até quatro chamadas Gemini internamente. Não executa novamente os quinze casos.

```bash
docker compose exec -T api python - <<'PY'
import json

import httpx

mensagem = "When will my recent sales be deposited?"
print(f"Pergunta: {mensagem}", flush=True)

try:
    with httpx.Client(timeout=httpx.Timeout(25.0, connect=3.0)) as client:
        resposta = client.post(
            "http://localhost:8000/chat",
            json={"message": mensagem, "user_id": "cliente1988"},
        )
    print(f"HTTP {resposta.status_code}", flush=True)
    print(json.dumps(resposta.json(), ensure_ascii=False, indent=2), flush=True)
except (httpx.HTTPError, ValueError) as erro:
    print(f"A chamada não concluiu normalmente: {type(erro).__name__}.", flush=True)
    print("Use o registro manual salvo para continuar a demonstração.", flush=True)
PY
```

## Guia de navegação dos arquivos

Use a busca do editor pelos símbolos abaixo. Não é necessário ler os arquivos inteiros.

| Arquivo | Trecho a localizar | O que explicar |
| --- | --- | --- |
| `README.md` | Configurar, Docker, testes, avaliação, manual, arquitetura e limitações | Orientação para executar e entender o projeto |
| `.env.example` | `GEMINI_API_KEY`, `GEMINI_MODEL`, timeouts | Configuração sem mostrar a chave real |
| `Dockerfile` / `docker-compose.yml` | Comando do Uvicorn, serviço `api`, volume `data` | Um serviço e persistência local |
| `app/main.py` | `get_router`, `chat`, `request_context` | Composição, endpoint e UUID por requisição |
| `app/schemas.py` | `ChatRequest`, `RouteDecision`, `ChatResponse` | Contratos Pydantic e metadados de resposta |
| `app/agents/router.py` | `classify`, `chat` | JSON validado, guardrail antes da rota e chamadas diretas |
| `app/services/gemini.py` | `generate`, `response_json_schema`, `HttpOptions` | Único acesso ao LLM e erros controlados |
| `app/rag/ingest.py` | `SEED_URLS`, `chunk_text`, `ingest` | Coleta limitada, extração, chunks e arquivo local |
| `app/rag/retriever.py` | `TfidfVectorizer`, `retrieve` | Ranking lexical por similaridade de cosseno |
| `app/agents/knowledge.py` | `answer`, `if not context` | RAG ou web, contexto e escalonamento por ausência de resultados |
| `app/tools/web_search.py` | `web_search` | DuckDuckGo e normalização de snippets e URLs |
| `app/agents/customer_support.py` | `available`, chamada das tools | Seleção validada e funções permitidas |
| `app/tools/customer_data.py` | `get_customer_profile`, `get_customer_activity` | Consulta ao JSON e cliente inexistente |
| `data/customers.json` | `cliente1988`, `snapshot_at`, `activity` | Dados fictícios usados na resposta |
| `app/guardrails/guardrail.py` | `check_guardrail` | Categorias e comportamento conservador |
| `app/agents/human_escalation.py` | `handle` | Resposta fixa, motivo e ausência de integração real |
| `app/logging_config.py` | `JsonFormatter`, `log_event` | Eventos JSON e correlação por UUID |
| `tests/` | Arquivos de API, guardrail, RAG e logging | Verificação automatizada com mocks |
| `evals/cases.json` / `evals/run.py` | Casos e `evaluate_case` | Avaliação real com critérios determinísticos |

## Cortes para manter o vídeo abaixo de 10 minutos

- **Se chegar a 06:15 atrasado:** use diretamente o manual salvo e omita a chamada ao vivo. Mostre o comando que produziu o registro e diga que foi executado antes.
- **Se chegar a 07:55 atrasado:** mostre somente Customer Support e o bloqueio do guardrail no manual; as outras rotas já aparecem na avaliação e na arquitetura.
- **Se chegar a 08:35 atrasado:** resuma os logs em uma sequência de mesmo UUID e finalize com duas limitações: cobertura documental e dependência das APIs.
- Não reconstrua Docker, repita a avaliação completa ou percorra todo o histórico dos logs durante a gravação.
