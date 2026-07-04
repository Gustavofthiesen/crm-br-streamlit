"""Configuration helpers with env-first settings.

Values may also come from Streamlit secrets when the app is running in
Streamlit Community Cloud. Keep real secrets out of committed files.
"""

from __future__ import annotations

import os
from typing import Any


def _read_streamlit_secret(*path: str) -> Any | None:
    try:
        import streamlit as st

        value: Any = st.secrets
        for key in path:
            value = value[key]
        return value
    except Exception:
        return None


def get_database_url() -> str:
    value = (
        os.getenv("CRM_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or _read_streamlit_secret("database", "url")
        or "sqlite:///crm_br_streamlit.db"
    )

    # Some platforms still expose postgres:// URLs. SQLAlchemy expects the
    # postgresql:// scheme.
    if value.startswith("postgres://"):
        value = value.replace("postgres://", "postgresql://", 1)
    return value


def get_admin_email() -> str:
    return (
        os.getenv("CRM_ADMIN_EMAIL")
        or _read_streamlit_secret("admin", "email")
        or "admin@crm.local"
    )


def get_admin_password() -> str | None:
    return os.getenv("CRM_ADMIN_PASSWORD") or _read_streamlit_secret(
        "admin", "password"
    )


def get_timezone_name() -> str:
    return "America/Sao_Paulo"
