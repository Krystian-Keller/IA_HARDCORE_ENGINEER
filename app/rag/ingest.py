"""Run explicitly: python -m app.rag.ingest [--max-pages 6]."""

import argparse
import json
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
import httpx

from app.config import Settings
from app.schemas import AppError, Chunk

SEED_URLS = ["https://www.getnet.net/", "https://www.getnet.net/en"]


def chunk_text(text: str, size: int = 180, overlap: int = 30) -> list[str]:
    """Chunks are measured in words, with a small overlap."""
    if not 0 <= overlap < size:
        raise ValueError("Require 0 <= overlap < size")
    words = text.split()
    chunks = []
    for start in range(0, len(words), size - overlap):
        chunks.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
    return chunks


def is_getnet_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc in {"www.getnet.net", "getnet.net"}


def extract_page(html: str, source: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for anchor in soup.select("a[href]"):
        url = urldefrag(urljoin(source, anchor["href"]))[0]
        if is_getnet_url(url) and not urlparse(url).query:
            links.append(url)
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    content = soup.find("main") or soup.find("article") or soup
    return " ".join(content.stripped_strings), list(dict.fromkeys(links))


def ingest(output: Path, *, max_pages: int = 6, timeout: float = 15) -> dict:
    if not 2 <= max_pages <= 10:
        raise ValueError("max_pages deve estar entre 2 e 10.")
    pending = list(SEED_URLS)
    visited = set()
    chunks = []
    failures = []
    loaded_sources = set()
    pages_loaded = 0
    with httpx.Client(
        timeout=timeout, follow_redirects=True,
        headers={"User-Agent": "AIHardcoreEngineer/1.0 (educational RAG)"},
    ) as client:
        while pending and len(visited) < max_pages:
            url = pending.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                response = client.get(url)
                response.raise_for_status()
                source = str(response.url)
                if not is_getnet_url(source):
                    raise ValueError("Redirecionamento para fora do domínio Getnet.")
                if source in loaded_sources:
                    continue
                if "text/html" not in response.headers.get("content-type", ""):
                    raise ValueError("A página não retornou HTML.")
                text, links = extract_page(response.text, source)
                if len(text.split()) < 20:
                    raise ValueError("Página sem texto suficiente para ingestão.")
                chunks.extend(Chunk(text=part, source=source) for part in chunk_text(text))
                loaded_sources.add(source)
                pages_loaded += 1
                pending.extend(link for link in links if link not in visited and link not in pending)
            except (httpx.HTTPError, ValueError) as exc:
                failures.append({"url": url, "error": str(exc)})
    if not chunks:
        raise AppError(503, f"Nenhuma página Getnet foi carregada; base anterior preservada. {failures}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(
        json.dumps([chunk.model_dump(mode="json") for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(output)
    return {"pages_loaded": pages_loaded, "chunks": len(chunks), "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description="Carrega até 10 páginas públicas Getnet para RAG local.")
    parser.add_argument("--max-pages", type=int, default=6, choices=range(2, 11))
    args = parser.parse_args()
    settings = Settings.from_env()
    try:
        report = ingest(settings.data_dir / "rag" / "chunks.json", max_pages=args.max_pages,
                        timeout=settings.http_timeout_seconds)
    except (AppError, OSError) as exc:
        parser.exit(1, f"Falha na ingestão: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
