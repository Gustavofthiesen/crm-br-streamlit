"""Application services: auth, defaults, permissions and analytics."""

from __future__ import annotations

import secrets as token_secrets
from datetime import date
from decimal import Decimal
from typing import Any

import bcrypt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_admin_email, get_admin_password
from .models import (
    Deal,
    Lead,
    PipelineStage,
    Task,
    Ticket,
    User,
)


DEFAULT_PIPELINE_STAGES = [
    ("Novo lead", 1, 5, False, False),
    ("Contato feito", 2, 15, False, False),
    ("Diagnóstico", 3, 30, False, False),
    ("Proposta enviada", 4, 55, False, False),
    ("Negociação", 5, 75, False, False),
    ("Fechado ganho", 6, 100, True, False),
    ("Fechado perdido", 7, 0, False, True),
]

ROLE_LABELS = {
    "admin": "Administrador",
    "gerente": "Gerente",
    "vendedor": "Vendedor",
    "atendimento": "Atendimento",
}

PAGE_ACCESS = {
    "admin": {
        "dashboard",
        "companies",
        "contacts",
        "leads",
        "deals",
        "activities",
        "tasks",
        "products",
        "proposals",
        "tickets",
        "lgpd",
        "audit",
        "integrations",
    },
    "gerente": {
        "dashboard",
        "companies",
        "contacts",
        "leads",
        "deals",
        "activities",
        "tasks",
        "products",
        "proposals",
        "tickets",
        "lgpd",
        "audit",
        "integrations",
    },
    "vendedor": {
        "dashboard",
        "companies",
        "contacts",
        "leads",
        "deals",
        "activities",
        "tasks",
        "products",
        "proposals",
        "integrations",
    },
    "atendimento": {
        "dashboard",
        "companies",
        "contacts",
        "activities",
        "tasks",
        "tickets",
        "lgpd",
        "integrations",
    },
}

READ_ONLY_PAGES = {"dashboard", "audit", "integrations"}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    normalized = email.strip().lower()
    user = session.scalar(
        select(User).where(func.lower(User.email) == normalized, User.is_active.is_(True))
    )
    if not user:
        return None
    if verify_password(password, user.password_hash):
        return user
    return None


def can_access_page(role: str, page_key: str) -> bool:
    return page_key in PAGE_ACCESS.get(role, set())


def can_mutate(role: str, page_key: str) -> bool:
    return can_access_page(role, page_key) and page_key not in READ_ONLY_PAGES


def ensure_initial_data(session: Session) -> dict[str, Any]:
    result: dict[str, Any] = {"admin_created": False, "generated_password": None}
    ensure_default_pipeline_stages(session)

    user_count = session.scalar(select(func.count(User.id))) or 0
    if user_count == 0:
        password = get_admin_password()
        generated_password = None
        if not password:
            password = token_secrets.token_urlsafe(14)
            generated_password = password
        admin = User(
            name="Administrador",
            email=get_admin_email(),
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        session.add(admin)
        session.commit()
        result["admin_created"] = True
        result["generated_password"] = generated_password
        result["admin_email"] = admin.email
    return result


def ensure_default_pipeline_stages(session: Session) -> None:
    existing = session.scalar(select(func.count(PipelineStage.id))) or 0
    if existing:
        return
    for name, order, probability, is_won, is_lost in DEFAULT_PIPELINE_STAGES:
        session.add(
            PipelineStage(
                name=name,
                order_index=order,
                win_probability=probability,
                is_won=is_won,
                is_lost=is_lost,
            )
        )
    session.commit()


def get_dashboard_metrics(session: Session) -> dict[str, Any]:
    total_leads = session.scalar(select(func.count(Lead.id))) or 0
    open_deals = session.scalar(
        select(func.count(Deal.id)).where(Deal.status == "open")
    ) or 0
    forecast = session.scalar(
        select(func.coalesce(func.sum(Deal.value), Decimal("0"))).where(
            Deal.status == "open"
        )
    ) or Decimal("0")
    won = session.scalar(
        select(func.coalesce(func.sum(Deal.value), Decimal("0"))).where(
            Deal.status == "won"
        )
    ) or Decimal("0")
    lost = session.scalar(
        select(func.coalesce(func.sum(Deal.value), Decimal("0"))).where(
            Deal.status == "lost"
        )
    ) or Decimal("0")
    overdue_tasks = session.scalar(
        select(func.count(Task.id)).where(
            Task.due_date < date.today(),
            Task.status.notin_(["concluida", "cancelada"]),
        )
    ) or 0
    open_tickets = session.scalar(
        select(func.count(Ticket.id)).where(Ticket.status.notin_(["resolvido", "fechado"]))
    ) or 0

    stage_rows = session.execute(
        select(PipelineStage.name, func.count(Deal.id))
        .outerjoin(Deal, Deal.pipeline_stage_id == PipelineStage.id)
        .group_by(PipelineStage.id)
        .order_by(PipelineStage.order_index)
    ).all()
    source_rows = session.execute(
        select(Lead.source, func.count(Lead.id)).group_by(Lead.source)
    ).all()

    return {
        "total_leads": total_leads,
        "open_deals": open_deals,
        "forecast": forecast,
        "won": won,
        "lost": lost,
        "overdue_tasks": overdue_tasks,
        "open_tickets": open_tickets,
        "conversion_by_stage": [
            {"Etapa": stage or "Sem etapa", "Quantidade": count}
            for stage, count in stage_rows
        ],
        "leads_by_source": [
            {"Origem": source or "Sem origem", "Quantidade": count}
            for source, count in source_rows
        ],
    }
