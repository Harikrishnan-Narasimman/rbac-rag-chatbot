from pathlib import Path
from typing import List
import logging
from langchain_community.document_loaders import TextLoader, CSVLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


CURRENT_DIR = Path(__file__).resolve().parent
DATA_DIR = CURRENT_DIR.parent/"resources"/"data/"
QDRANT_PATH = str(CURRENT_DIR.parent/"resources"/"qdrant_db")
COLLECTION_NAME = "company_docs"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
log.info(f"Current directory: {DATA_DIR}")


HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3"), ("####", "h4"), ("#####", "h5"), ("######", "h6")]
header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS, strip_headers=False)
char_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)


def load_markdown_chunks(file_path: Path, department: str) -> List[Document]:
    text = TextLoader(str(file_path), encoding="utf-8").load()[0].page_content
    header_splits = header_splitter.split_text(text)
    chunks = char_splitter.split_documents(header_splits)

    for chunk in chunks:
        chunk.metadata.update({"department": department, "source": file_path.name, "doc_type": "markdown"})
    return chunks


def load_csv_chunks(file_path: Path, department: str) -> List[Document]:
    rows = CSVLoader(str(file_path)).load()
    for row in rows:
        row.metadata.update({"department": department, "source": file_path.name, "doc_type": "csv"})
    return rows


def load_documents(data_dir: Path = DATA_DIR) -> List[Document]:
    documents: List[Document] = []

    for directory in sorted(data_dir.iterdir()):
        if not directory.is_dir():
            continue
        department = directory.name

        for file in sorted(directory.iterdir()):
            if file.suffix == ".md":
                documents.extend(load_markdown_chunks(file, department))
            elif file.suffix == ".csv":
                documents.extend(load_csv_chunks(file, department))
            else:
                log.warning(f"Unsupported file type: {file.suffix} in {file}. Skipping.")

    return documents

def ingest() -> None:
    documents = load_documents()
    log.info(f"Loaded {len(documents)} documents")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    QdrantVectorStore.from_documents(
        documents,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        path=QDRANT_PATH,
    )
    log.info(f"Successfully ingested {len(documents)} documents into Qdrant collection '{COLLECTION_NAME}' at '{QDRANT_PATH}'.")


if __name__ == "__main__":
    ingest()