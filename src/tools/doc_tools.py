# TODO: Import docling modules once installed
# from docling.document import DoclingDocument
# from docling.chunking import HybridChunker

def ingest_pdf(file_path: str) -> list[str]:
    """Stub: Ingest and chunk a PDF using Docling."""
    # TODO: Implement docling parsing
    # doc = DoclingDocument.load(file_path)
    # chunker = HybridChunker()
    # chunks = chunker.chunk(doc)
    print(f"Stub: Ingesting PDF {file_path}")
    return ["Chunk 1: Project overview", "Chunk 2: Dependency requirements"]

def query_pdf(query: str, chunks: list[str]) -> str:
    """Stub: Simple search or RAG over standard PDF chunks."""
    # TODO: Vectorize chunks and perform similarity search
    print(f"Stub: Querying chunks for '{query}'")
    matches = [c for c in chunks if query.lower() in c.lower()]
    return "\\n".join(matches) if matches else "No relevant information found."
