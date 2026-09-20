from typing import Optional
from qdrant_client.models import Filter, MatchAny, FieldCondition
from langchain_core.documents import Document

from app.core.rbac import get_allowed_departments
from app.services.vectorstore import get_vectorstore

def build_department_filter(departments: Optional[list[str]]) -> Optional[Filter]:
    if departments is None:
        return None
    return Filter(
        must=[FieldCondition(key="metadata.department", match=MatchAny(any=departments))]
    )

def retrieve(question: str, role: str, k: int = 5) -> list[Document]:
    departments = get_allowed_departments(role)
    department_filter = build_department_filter(departments)
    return get_vectorstore().similarity_search(
        query=question,
        k=k,
        filter=department_filter
    )