"""
retrieval.py — Document loader, section-level chunker, and TF-IDF search index
for ProcureOps's four RAG corpora.

Adapted directly from sop-deviation-review/backend/retrieval.py: same ##-header
chunking, same TfidfVectorizer + cosine similarity approach, no vector database.
Extended to cover four corpora instead of one:

    procurement_policy_manual   data/policy/procurement_policy_manual.md
    doa_matrix                  data/policy/doa_matrix.md
    contract_terms              data/policy/contract_terms.md
    vendor_master                data/vendor_master/*.md  (one file per vendor)

All four corpora are indexed together (so a query like "what's the freight
term for a raw materials PO over $100k" can surface both a DOA row and a
contract-terms clause), but every chunk carries a `corpus` field so callers
can filter to just one when the calling agent only needs one kind of grounding
(e.g. Invoice Verification only needs policy_manual + vendor_master, not
contract_terms).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_THIS_FILE = Path(__file__).resolve()
_BACKEND_DIR = _THIS_FILE.parent
_POLICY_DIR = _BACKEND_DIR / "data" / "policy"
_VENDOR_DIR = _BACKEND_DIR / "data" / "vendor_master"

_CORPUS_BY_FILENAME = {
    "procurement_policy_manual.md": "procurement_policy_manual",
    "doa_matrix.md":                "doa_matrix",
    "contract_terms.md":            "contract_terms",
}


@dataclass
class DocChunk:
    """A single section from a policy or vendor-master document."""
    chunk_id:       str          # e.g. "procurement_policy_manual__5"
    doc_id:         str          # filename stem
    corpus:         str          # "procurement_policy_manual" | "doa_matrix" | "contract_terms" | "vendor_master"
    source_file:    str
    section_number: str
    section_title:  str
    text:           str
    word_count:     int = field(init=False)

    def __post_init__(self) -> None:
        self.word_count = len(self.text.split())

    def as_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id, "doc_id": self.doc_id, "corpus": self.corpus,
            "source_file": self.source_file, "section_number": self.section_number,
            "section_title": self.section_title, "text": self.text, "word_count": self.word_count,
        }


@dataclass
class SearchResult:
    chunk: DocChunk
    score: float

    def as_dict(self) -> dict:
        return {**self.chunk.as_dict(), "score": round(float(self.score), 4)}


_SECTION_HEADER_RE = re.compile(r"^(## .+)$", re.MULTILINE)


def _split_by_sections(content: str, doc_id: str, corpus: str, source_file: str) -> List[DocChunk]:
    """Split a markdown document into chunks at every ## header (identical logic
    to sop-deviation-review's _split_by_sections, generalised with a corpus tag)."""
    chunks: List[DocChunk] = []
    header_matches = list(_SECTION_HEADER_RE.finditer(content))

    preamble_end = header_matches[0].start() if header_matches else len(content)
    preamble_text = content[:preamble_end].strip()
    if preamble_text:
        chunks.append(DocChunk(
            chunk_id=f"{doc_id}__0", doc_id=doc_id, corpus=corpus, source_file=source_file,
            section_number="", section_title="Preamble", text=preamble_text,
        ))

    for idx, match in enumerate(header_matches):
        header_line = match.group(1).strip()
        section_start = match.start()
        section_end = header_matches[idx + 1].start() if idx + 1 < len(header_matches) else len(content)
        chunk_text = content[section_start:section_end].strip()

        num_match = re.match(r"^## (\d+(?:\.\d+)?)", header_line)
        section_number = num_match.group(1) if num_match else str(idx + 1)

        chunks.append(DocChunk(
            chunk_id=f"{doc_id}__{section_number.replace('.', '_')}",
            doc_id=doc_id, corpus=corpus, source_file=source_file,
            section_number=section_number, section_title=header_line, text=chunk_text,
        ))

    return chunks


def load_all_documents(policy_dir: Path | None = None, vendor_dir: Path | None = None) -> List[DocChunk]:
    """Load every .md file across the policy directory and the vendor_master
    directory, tagging each chunk with its corpus."""
    p_dir = policy_dir or _POLICY_DIR
    v_dir = vendor_dir or _VENDOR_DIR

    all_chunks: List[DocChunk] = []

    if not p_dir.exists():
        raise FileNotFoundError(f"Policy directory not found: {p_dir}")
    for md_path in sorted(p_dir.glob("*.md")):
        corpus = _CORPUS_BY_FILENAME.get(md_path.name, md_path.stem)
        content = md_path.read_text(encoding="utf-8")
        all_chunks.extend(_split_by_sections(content, md_path.stem, corpus, md_path.name))

    if not v_dir.exists():
        raise FileNotFoundError(f"Vendor master directory not found: {v_dir}")
    for md_path in sorted(v_dir.glob("*.md")):
        content = md_path.read_text(encoding="utf-8")
        all_chunks.extend(_split_by_sections(content, md_path.stem, "vendor_master", md_path.name))

    if not all_chunks:
        raise FileNotFoundError(f"No .md files found in {p_dir} or {v_dir}")

    return all_chunks


class DocIndex:
    """TF-IDF index over all chunks from all four corpora. Built once, reused."""

    def __init__(self, chunks: List[DocChunk]) -> None:
        if not chunks:
            raise ValueError("Cannot build index from an empty chunk list.")
        self.chunks = chunks
        self._vectorizer = TfidfVectorizer(
            sublinear_tf=True, min_df=1, ngram_range=(1, 2),
            stop_words="english", strip_accents="unicode",
        )
        texts = [c.text for c in self.chunks]
        self._matrix = self._vectorizer.fit_transform(texts)

    def search(self, query: str, top_k: int = 3, corpus: Optional[str] = None) -> List[SearchResult]:
        """Return the top_k chunks most relevant to query, optionally restricted
        to a single corpus (e.g. corpus='vendor_master')."""
        query = query.strip()
        if not query:
            return []

        if corpus is not None:
            indices = [i for i, c in enumerate(self.chunks) if c.corpus == corpus]
        else:
            indices = list(range(len(self.chunks)))
        if not indices:
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()

        scored = sorted(((scores[i], i) for i in indices), key=lambda t: t[0], reverse=True)
        k = min(top_k, len(scored))

        return [
            SearchResult(chunk=self.chunks[i], score=s)
            for s, i in scored[:k]
            if s > 0.0
        ]


_index: DocIndex | None = None


def _get_index() -> DocIndex:
    global _index
    if _index is None:
        _index = DocIndex(load_all_documents())
    return _index


def reset_index() -> None:
    global _index
    _index = None


def search_docs(query: str, top_k: int = 3, corpus: Optional[str] = None) -> List[dict]:
    """Public entry point. corpus: None (search everything) or one of
    'procurement_policy_manual', 'doa_matrix', 'contract_terms', 'vendor_master'."""
    index = _get_index()
    return [r.as_dict() for r in index.search(query, top_k=top_k, corpus=corpus)]


def get_doc_chunks(doc_id_prefix: str, corpus: Optional[str] = None) -> List[dict]:
    """Return every chunk whose doc_id starts with doc_id_prefix (e.g. a vendor_id
    like "V-001", which is a prefix of every vendor's doc_id "V-001-<slug>").

    Used once a specific document is already identified (by vendor_id, or by
    the top hit of a prior search_docs call) to fetch its full text instead of
    letting individual sections compete for a shared top_k slot against every
    other document in the corpus. A vendor's Certifications section losing out
    to a different vendor's Preamble in a global top-k ranking was a real bug
    found while testing ProcureOps live — this is the fix."""
    index = _get_index()
    matches = [c for c in index.chunks
               if c.doc_id.startswith(doc_id_prefix) and (corpus is None or c.corpus == corpus)]
    return [c.as_dict() for c in matches]


def get_chunk_by_id(chunk_id: str) -> Optional[dict]:
    """Resolve a single chunk_id (as stored in traces.retrieved_chunks) back to
    its full text + metadata, for displaying citations in the UI."""
    index = _get_index()
    for c in index.chunks:
        if c.chunk_id == chunk_id:
            return c.as_dict()
    return None


def get_all_chunks() -> List[dict]:
    return [c.as_dict() for c in _get_index().chunks]
