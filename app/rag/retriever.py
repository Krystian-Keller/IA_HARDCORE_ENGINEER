import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas import AppError, Chunk


class Retriever:
    def __init__(self, chunks: list[Chunk]):
        if not chunks:
            raise AppError(503, "A base RAG está vazia. Execute python -m app.rag.ingest.")
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(strip_accents="unicode", ngram_range=(1, 2))
        try:
            self.matrix = self.vectorizer.fit_transform(chunk.text for chunk in chunks)
        except ValueError as exc:
            raise AppError(503, "A base RAG não possui vocabulário utilizável.") from exc

    @classmethod
    def from_file(cls, path: Path) -> "Retriever":
        try:
            chunks = TypeAdapter(list[Chunk]).validate_python(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (OSError, ValueError, ValidationError) as exc:
            raise AppError(
                503, "Base RAG indisponível. Execute python -m app.rag.ingest."
            ) from exc
        return cls(chunks)

    def retrieve(self, query: str, top_k: int = 4) -> list[Chunk]:
        if top_k < 1:
            return []
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        indexes = scores.argsort()[::-1]
        return [self.chunks[i] for i in indexes if scores[i] > 0][:top_k]
