"""Audit log page."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import select

from crm.database import get_session
from crm.formatters import format_datetime_br
from crm.models import AuditLog, User
from crm.services import can_access_page


def render(current_user: dict) -> None:
    if not can_access_page(current_user["role"], "audit"):
        st.warning("Acesso não permitido para este perfil.")
        return

    st.title("Auditoria")
    with get_session() as session:
        logs = list(
            session.scalars(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)
            ).all()
        )
        rows = []
        for log in logs:
            user = session.get(User, log.user_id) if log.user_id else None
            rows.append(
                {
                    "Data": format_datetime_br(log.created_at),
                    "Usuário": user.email if user else "sistema",
                    "Entidade": log.entity_type,
                    "Registro": log.entity_id or "",
                    "Ação": log.action,
                    "Valores anteriores": log.old_values or "",
                    "Novos valores": log.new_values or "",
                }
            )

    if not rows:
        st.info("Nenhum evento de auditoria encontrado.")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
