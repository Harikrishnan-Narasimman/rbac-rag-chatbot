from typing import Optional

ROLE_DEPARTMENT_MAPPING: dict[str, Optional[list[str]]] = {
    "engineering": ["engineering", "general"],
    "finance": ["finance", "general"],
    "hr": ["hr", "general"],
    "marketing": ["marketing", "general"],
    "general": ["general"],
    "c-level": None
}

def get_allowed_departments(role: str) -> Optional[list[str]]:
    if role not in ROLE_DEPARTMENT_MAPPING:
        raise ValueError(f"Role '{role}' is not defined.")
    department = ROLE_DEPARTMENT_MAPPING[role]
    return None if department is None else list(department)