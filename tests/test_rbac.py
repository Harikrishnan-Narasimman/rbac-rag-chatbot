import pytest

from app.core.rbac import ROLE_DEPARTMENT_MAPPING, get_allowed_departments
from app.services.retrieval import retrieve

QUERIES = [
    "quarterly revenue and expenses",
    "employee salary and payroll",
    "marketing campaign spend",
    "engineering architecture and tech stack",
    "annual leave policy",
    "Aadhya Saxena salary",
]

RESTRICTED_ROLES = [r for r, d in ROLE_DEPARTMENT_MAPPING.items() if d is not None]


def test_unknown_role_raises():
    with pytest.raises(ValueError):
        get_allowed_departments("intern")


def test_allowed_list_is_a_copy():
    departments = get_allowed_departments("hr")
    departments.append("finance")
    assert "finance" not in get_allowed_departments("hr")


def test_c_level_is_unrestricted():
    assert get_allowed_departments("c-level") is None


@pytest.mark.parametrize("role", RESTRICTED_ROLES)
@pytest.mark.parametrize("query", QUERIES)
def test_retrieval_never_leaves_allowed_departments(role, query):
    allowed = set(get_allowed_departments(role))
    found = {d.metadata["department"] for d in retrieve(query, role, k=10)}
    assert found <= allowed


def test_hr_reaches_hr_data_but_marketing_does_not():
    hr = {d.metadata["department"] for d in retrieve("Aadhya Saxena salary", "hr")}
    marketing = {d.metadata["department"] for d in retrieve("Aadhya Saxena salary", "marketing")}
    assert "hr" in hr
    assert "hr" not in marketing
