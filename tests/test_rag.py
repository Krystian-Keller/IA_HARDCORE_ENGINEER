import json

import httpx
import pytest

from app.rag import ingest as ingestion
from app.rag.retriever import Retriever
from app.schemas import AppError, Chunk


def test_retrieves_relevant_local_chunks_without_network(tmp_path):
    path = tmp_path / "chunks.json"
    path.write_text(json.dumps([
        {"text": "Pix is an instant payment service with QR codes.", "source": "https://www.getnet.net/pix"},
        {"text": "Smart card machines print receipts and connect via Wi-Fi.", "source": "https://www.getnet.net/machines"},
        {"text": "Antecipação permite antecipar recebíveis de vendas.", "source": "https://www.getnet.net/advance"},
    ]), encoding="utf-8")
    retriever = Retriever.from_file(path)
    assert str(retriever.retrieve("instant Pix QR", top_k=1)[0].source).endswith("/pix")
    assert str(retriever.retrieve("card machines receipts", top_k=1)[0].source).endswith("/machines")
    assert str(retriever.retrieve("antecipacao recebiveis", top_k=1)[0].source).endswith("/advance")
    assert retriever.retrieve("astronomy") == []
    assert retriever.retrieve("Pix", top_k=0) == []


@pytest.mark.parametrize("content", [None, "not json", "[]", '[{"text":"missing source"}]'])
def test_missing_or_invalid_corpus_is_explicit(tmp_path, content):
    path = tmp_path / "chunks.json"
    if content is not None:
        path.write_text(content)
    with pytest.raises(AppError) as error:
        Retriever.from_file(path)
    assert error.value.status_code == 503


def test_unusable_vocabulary():
    with pytest.raises(AppError):
        Retriever([Chunk(text="a !", source="https://www.getnet.net/")])


def test_chunking_preserves_words_and_overlap():
    assert ingestion.chunk_text("one two three four five six", size=4, overlap=2) == [
        "one two three four", "three four five six"
    ]
    assert ingestion.chunk_text("") == []
    with pytest.raises(ValueError):
        ingestion.chunk_text("hello", size=2, overlap=2)


def test_html_extraction_and_domain_limits():
    html = '<nav>navigation</nav><script>bad()</script><main>Pix payment information</main>' \
           '<a href="/en">English</a><a href="https://evil.example/">external</a>' \
           '<a href="https://www.getnet.net.evil.example/">lookalike</a>' \
           '<a href="/en?search=foo">query</a>'
    text, links = ingestion.extract_page(html, "https://www.getnet.net/")
    assert text == "Pix payment information"
    assert links == ["https://www.getnet.net/en"]


def mock_downloads(monkeypatch, handler):
    original_client = httpx.Client
    monkeypatch.setattr(ingestion.httpx, "Client", lambda **kwargs: original_client(
        **kwargs, transport=httpx.MockTransport(handler)
    ))


def test_ingest_limits_crawl_and_keeps_sources(tmp_path, monkeypatch):
    fetched = []

    def handler(request):
        fetched.append(str(request.url))
        html = '<main>' + 'Getnet Pix payments and card machine services. ' * 30 + '</main>'
        html += ''.join(f'<a href="/page-{n}">page</a>' for n in range(10))
        html += '<a href="https://other.example">external</a>'
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    mock_downloads(monkeypatch, handler)
    output = tmp_path / "rag/chunks.json"
    report = ingestion.ingest(output, max_pages=3)
    assert len(fetched) == 3
    assert fetched[:2] == ingestion.SEED_URLS
    assert report["pages_loaded"] == 3
    assert report["failures"] == []
    assert Retriever.from_file(output).retrieve("Pix")
    assert {chunk["source"] for chunk in json.loads(output.read_text())} == set(fetched)


def test_failed_ingestion_preserves_existing_corpus(tmp_path, monkeypatch):
    output = tmp_path / "chunks.json"
    output.write_text("previous corpus")
    mock_downloads(monkeypatch, lambda request: httpx.Response(503))
    with pytest.raises(AppError, match="preservada"):
        ingestion.ingest(output, max_pages=2)
    assert output.read_text() == "previous corpus"


def test_redirected_seed_pages_do_not_duplicate_chunks(tmp_path, monkeypatch):
    def handler(request):
        if request.url.path != "/en/":
            return httpx.Response(302, headers={"location": "https://www.getnet.net/en/"})
        return httpx.Response(200, text='<main>' + 'Getnet payment products ' * 30 + '</main>',
                              headers={"content-type": "text/html"})

    mock_downloads(monkeypatch, handler)
    output = tmp_path / "chunks.json"
    report = ingestion.ingest(output, max_pages=2)
    assert report["pages_loaded"] == 1
    assert report["chunks"] == 1
    assert json.loads(output.read_text())[0]["source"] == "https://www.getnet.net/en/"


def test_partial_ingestion_reports_failure(tmp_path, monkeypatch):
    def handler(request):
        if request.url.path == "/en":
            return httpx.Response(403)
        return httpx.Response(200, text='<main>' + 'Getnet products ' * 30 + '</main>',
                              headers={"content-type": "text/html"})

    mock_downloads(monkeypatch, handler)
    report = ingestion.ingest(tmp_path / "chunks.json", max_pages=2)
    assert report["pages_loaded"] == 1
    assert report["failures"][0]["url"] == "https://www.getnet.net/en"
