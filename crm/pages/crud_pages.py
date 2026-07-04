"""Metadata-driven CRUD pages."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import select

from crm.database import get_session
from crm.formatters import (
    format_bool,
    format_currency,
    format_date_br,
    format_datetime_br,
    mask_cep,
    mask_cpf,
    mask_document,
    mask_phone,
    only_digits,
    parse_date_br,
    parse_datetime_br,
)
from crm.integrations.viacep import lookup_cep
from crm.models import (
    Activity,
    Company,
    Contact,
    Deal,
    Lead,
    LGPDConsent,
    PipelineStage,
    Product,
    Proposal,
    Task,
    Ticket,
    User,
)
from crm.repositories import CRUDRepository, model_to_dict
from crm.services import can_access_page, can_mutate
from crm.services_time import br_now
from crm.validators_br import validate_cpf, validate_document


def _status_options(*pairs: tuple[str, str]) -> list[tuple[str, str]]:
    return list(pairs)


ENTITY_CONFIGS: dict[str, dict[str, Any]] = {
    "companies": {
        "title": "Clientes / Empresas",
        "model": Company,
        "list_columns": [
            "id",
            "name",
            "document_number",
            "email",
            "phone",
            "city",
            "state",
            "status",
        ],
        "fields": [
            {"name": "name", "label": "Razão social / nome", "type": "text", "required": True},
            {"name": "trade_name", "label": "Nome fantasia", "type": "text"},
            {"name": "document_type", "label": "Tipo de documento", "type": "select", "options": ["CNPJ", "CPF"], "default": "CNPJ"},
            {"name": "document_number", "label": "CPF/CNPJ", "type": "text", "placeholder": "00.000.000/0000-00"},
            {"name": "industry", "label": "Segmento", "type": "text"},
            {"name": "status", "label": "Status", "type": "select", "options": ["prospect", "ativo", "inativo"], "default": "prospect"},
            {"name": "email", "label": "E-mail", "type": "text"},
            {"name": "phone", "label": "Telefone com DDD", "type": "text", "placeholder": "(11) 99999-9999"},
            {"name": "website", "label": "Site", "type": "text"},
            {"name": "cep", "label": "CEP", "type": "text", "placeholder": "00000-000"},
            {"name": "address", "label": "Endereço", "type": "text"},
            {"name": "number", "label": "Número", "type": "text"},
            {"name": "complement", "label": "Complemento", "type": "text"},
            {"name": "neighborhood", "label": "Bairro", "type": "text"},
            {"name": "city", "label": "Cidade", "type": "text"},
            {"name": "state", "label": "UF", "type": "text", "placeholder": "SP"},
            {"name": "owner_id", "label": "Responsável", "type": "fk", "model": User},
            {"name": "notes", "label": "Observações", "type": "textarea"},
        ],
    },
    "contacts": {
        "title": "Contatos",
        "model": Contact,
        "list_columns": ["id", "first_name", "last_name", "cpf", "email", "phone", "company_id", "marketing_opt_in"],
        "fields": [
            {"name": "company_id", "label": "Empresa", "type": "fk", "model": Company},
            {"name": "first_name", "label": "Nome", "type": "text", "required": True},
            {"name": "last_name", "label": "Sobrenome", "type": "text"},
            {"name": "cpf", "label": "CPF", "type": "text", "placeholder": "000.000.000-00"},
            {"name": "email", "label": "E-mail", "type": "text"},
            {"name": "phone", "label": "Telefone com DDD", "type": "text", "placeholder": "(11) 99999-9999"},
            {"name": "role_title", "label": "Cargo", "type": "text"},
            {"name": "department", "label": "Departamento", "type": "text"},
            {"name": "birth_date", "label": "Data de nascimento", "type": "date"},
            {"name": "marketing_opt_in", "label": "Consentimento de marketing", "type": "bool"},
            {"name": "owner_id", "label": "Responsável", "type": "fk", "model": User},
            {"name": "notes", "label": "Observações", "type": "textarea"},
        ],
    },
    "leads": {
        "title": "Leads",
        "model": Lead,
        "list_columns": ["id", "name", "source", "status", "pipeline_stage_id", "estimated_value", "expected_close_date"],
        "fields": [
            {"name": "name", "label": "Lead", "type": "text", "required": True},
            {"name": "company_id", "label": "Empresa", "type": "fk", "model": Company},
            {"name": "contact_id", "label": "Contato", "type": "fk", "model": Contact},
            {"name": "source", "label": "Origem", "type": "select", "options": ["Indicação", "Site", "WhatsApp", "Evento", "Outbound", "Mídia paga", "Outro"]},
            {"name": "status", "label": "Status", "type": "select", "options": ["novo", "qualificado", "desqualificado", "convertido"], "default": "novo"},
            {"name": "pipeline_stage_id", "label": "Etapa do funil", "type": "fk", "model": PipelineStage},
            {"name": "estimated_value", "label": "Valor estimado (R$)", "type": "currency"},
            {"name": "expected_close_date", "label": "Previsão de fechamento", "type": "date"},
            {"name": "assigned_to", "label": "Responsável", "type": "fk", "model": User},
            {"name": "notes", "label": "Observações", "type": "textarea"},
        ],
    },
    "deals": {
        "title": "Oportunidades",
        "model": Deal,
        "list_columns": ["id", "title", "company_id", "pipeline_stage_id", "value", "probability", "status", "expected_close_date"],
        "fields": [
            {"name": "title", "label": "Oportunidade", "type": "text", "required": True},
            {"name": "company_id", "label": "Empresa", "type": "fk", "model": Company},
            {"name": "contact_id", "label": "Contato", "type": "fk", "model": Contact},
            {"name": "lead_id", "label": "Lead relacionado", "type": "fk", "model": Lead},
            {"name": "pipeline_stage_id", "label": "Etapa do funil", "type": "fk", "model": PipelineStage},
            {"name": "value", "label": "Valor (R$)", "type": "currency"},
            {"name": "probability", "label": "Probabilidade (%)", "type": "int", "min": 0, "max": 100},
            {"name": "status", "label": "Status", "type": "select", "options": _status_options(("open", "Aberta"), ("won", "Ganha"), ("lost", "Perdida")), "default": "open"},
            {"name": "expected_close_date", "label": "Previsão de fechamento", "type": "date"},
            {"name": "closed_at", "label": "Data de fechamento", "type": "datetime"},
            {"name": "assigned_to", "label": "Responsável", "type": "fk", "model": User},
            {"name": "notes", "label": "Observações", "type": "textarea"},
        ],
    },
    "activities": {
        "title": "Atividades",
        "model": Activity,
        "list_columns": ["id", "type", "subject", "company_id", "contact_id", "deal_id", "occurred_at"],
        "fields": [
            {"name": "type", "label": "Tipo", "type": "select", "options": ["nota", "ligação", "e-mail", "reunião", "whatsapp"], "default": "nota"},
            {"name": "subject", "label": "Assunto", "type": "text", "required": True},
            {"name": "description", "label": "Descrição", "type": "textarea"},
            {"name": "occurred_at", "label": "Data da atividade", "type": "datetime"},
            {"name": "company_id", "label": "Empresa", "type": "fk", "model": Company},
            {"name": "contact_id", "label": "Contato", "type": "fk", "model": Contact},
            {"name": "lead_id", "label": "Lead", "type": "fk", "model": Lead},
            {"name": "deal_id", "label": "Oportunidade", "type": "fk", "model": Deal},
            {"name": "entity_type", "label": "Objeto relacionado", "type": "select", "options": ["", "companies", "contacts", "leads", "deals", "tickets"]},
            {"name": "entity_id", "label": "ID relacionado", "type": "int", "min": 0},
            {"name": "created_by", "label": "Criado por", "type": "fk", "model": User},
        ],
    },
    "tasks": {
        "title": "Tarefas",
        "model": Task,
        "list_columns": ["id", "title", "status", "priority", "due_date", "assigned_to", "related_entity_type", "related_entity_id"],
        "fields": [
            {"name": "title", "label": "Tarefa", "type": "text", "required": True},
            {"name": "description", "label": "Descrição", "type": "textarea"},
            {"name": "status", "label": "Status", "type": "select", "options": ["aberta", "em_andamento", "concluida", "cancelada"], "default": "aberta"},
            {"name": "priority", "label": "Prioridade", "type": "select", "options": ["baixa", "media", "alta", "urgente"], "default": "media"},
            {"name": "due_date", "label": "Vencimento", "type": "date"},
            {"name": "assigned_to", "label": "Responsável", "type": "fk", "model": User},
            {"name": "related_entity_type", "label": "Objeto relacionado", "type": "select", "options": ["", "companies", "contacts", "leads", "deals", "tickets"]},
            {"name": "related_entity_id", "label": "ID relacionado", "type": "int", "min": 0},
        ],
    },
    "products": {
        "title": "Produtos / Serviços",
        "model": Product,
        "list_columns": ["id", "name", "sku", "unit", "price", "active"],
        "fields": [
            {"name": "name", "label": "Produto/serviço", "type": "text", "required": True},
            {"name": "sku", "label": "SKU", "type": "text"},
            {"name": "description", "label": "Descrição", "type": "textarea"},
            {"name": "unit", "label": "Unidade", "type": "select", "options": ["un", "hora", "mês", "projeto", "licença"], "default": "un"},
            {"name": "price", "label": "Preço (R$)", "type": "currency"},
            {"name": "active", "label": "Ativo", "type": "bool", "default": True},
            {"name": "tax_notes", "label": "Observações fiscais", "type": "textarea"},
        ],
    },
    "proposals": {
        "title": "Propostas",
        "model": Proposal,
        "list_columns": ["id", "number", "title", "company_id", "deal_id", "status", "total", "valid_until"],
        "fields": [
            {"name": "number", "label": "Número", "type": "text"},
            {"name": "title", "label": "Proposta", "type": "text", "required": True},
            {"name": "company_id", "label": "Empresa", "type": "fk", "model": Company},
            {"name": "contact_id", "label": "Contato", "type": "fk", "model": Contact},
            {"name": "deal_id", "label": "Oportunidade", "type": "fk", "model": Deal},
            {"name": "status", "label": "Status", "type": "select", "options": ["rascunho", "enviada", "aceita", "rejeitada", "expirada"], "default": "rascunho"},
            {"name": "subtotal", "label": "Subtotal (R$)", "type": "currency"},
            {"name": "discount", "label": "Desconto (R$)", "type": "currency"},
            {"name": "total", "label": "Total (R$)", "type": "currency"},
            {"name": "valid_until", "label": "Validade", "type": "date"},
            {"name": "sent_at", "label": "Envio", "type": "date"},
            {"name": "accepted_at", "label": "Aceite", "type": "date"},
            {"name": "terms", "label": "Condições comerciais", "type": "textarea"},
            {"name": "notes", "label": "Observações", "type": "textarea"},
        ],
    },
    "tickets": {
        "title": "Chamados",
        "model": Ticket,
        "list_columns": ["id", "title", "company_id", "contact_id", "status", "priority", "channel", "opened_at"],
        "fields": [
            {"name": "company_id", "label": "Empresa", "type": "fk", "model": Company},
            {"name": "contact_id", "label": "Contato", "type": "fk", "model": Contact},
            {"name": "title", "label": "Chamado", "type": "text", "required": True},
            {"name": "description", "label": "Descrição", "type": "textarea"},
            {"name": "status", "label": "Status", "type": "select", "options": ["aberto", "em_atendimento", "resolvido", "fechado"], "default": "aberto"},
            {"name": "priority", "label": "Prioridade", "type": "select", "options": ["baixa", "media", "alta", "urgente"], "default": "media"},
            {"name": "channel", "label": "Canal", "type": "select", "options": ["", "e-mail", "telefone", "whatsapp", "portal", "outro"]},
            {"name": "assigned_to", "label": "Responsável", "type": "fk", "model": User},
            {"name": "opened_at", "label": "Abertura", "type": "datetime"},
            {"name": "closed_at", "label": "Fechamento", "type": "datetime"},
        ],
    },
    "lgpd": {
        "title": "LGPD",
        "model": LGPDConsent,
        "list_columns": ["id", "company_id", "contact_id", "legal_basis", "marketing_consent", "consent_date", "revoked_at"],
        "fields": [
            {"name": "company_id", "label": "Empresa", "type": "fk", "model": Company},
            {"name": "contact_id", "label": "Contato", "type": "fk", "model": Contact},
            {"name": "legal_basis", "label": "Base legal", "type": "select", "options": ["consentimento", "execução de contrato", "legítimo interesse", "obrigação legal", "proteção ao crédito"], "required": True},
            {"name": "marketing_consent", "label": "Consentimento de marketing", "type": "bool"},
            {"name": "consent_date", "label": "Data de consentimento", "type": "date"},
            {"name": "purpose", "label": "Finalidade do tratamento", "type": "textarea", "required": True},
            {"name": "source", "label": "Origem do consentimento", "type": "text"},
            {"name": "revoked_at", "label": "Revogação", "type": "date"},
            {"name": "notes", "label": "Observações", "type": "textarea"},
        ],
    },
}


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def _cached_lookup_cep(cep: str) -> dict[str, Any] | None:
    return lookup_cep(cep)


def render_entity_page(entity_key: str, current_user: dict) -> None:
    config = ENTITY_CONFIGS[entity_key]
    if not can_access_page(current_user["role"], entity_key):
        st.warning("Acesso não permitido para este perfil.")
        return

    st.title(config["title"])

    with get_session() as session:
        repo = CRUDRepository(session, config["model"], user_id=current_user["id"])
        tabs = ["Registros"]
        if can_mutate(current_user["role"], entity_key):
            tabs.extend(["Novo", "Editar", "Excluir"])
        tab_objects = st.tabs(tabs)

        with tab_objects[0]:
            _render_records_table(session, config)

        if len(tab_objects) > 1:
            with tab_objects[1]:
                _render_create(session, repo, config, entity_key, current_user)
            with tab_objects[2]:
                _render_update(session, repo, config, entity_key)
            with tab_objects[3]:
                _render_delete(session, repo, config)


def _render_records_table(session, config: dict[str, Any]) -> None:
    records = CRUDRepository(session, config["model"]).list(limit=1000)
    if not records:
        st.info("Nenhum registro encontrado.")
        return

    rows = [_format_record_row(session, config, record) for record in records]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Exportar CSV",
        data=csv,
        file_name=f"{config['model'].__tablename__}.csv",
        mime="text/csv",
    )


def _render_create(session, repo: CRUDRepository, config: dict[str, Any], entity_key: str, current_user: dict) -> None:
    values = _render_fields(session, config, entity_key, prefix=f"{entity_key}_create")
    if st.button("Criar", type="primary", key=f"{entity_key}_create_button"):
        _save_create(repo, config, entity_key, values, current_user)


def _render_update(session, repo: CRUDRepository, config: dict[str, Any], entity_key: str) -> None:
    records = repo.list(limit=1000)
    if not records:
        st.info("Nenhum registro para editar.")
        return
    selected_id = st.selectbox(
        "Registro",
        options=[record.id for record in records],
        format_func=lambda record_id: _select_label(session.get(config["model"], record_id)),
        key=f"{entity_key}_edit_select",
    )
    record = repo.get(int(selected_id))
    values = _render_fields(
        session,
        config,
        entity_key,
        current=model_to_dict(record, include_private=False),
        prefix=f"{entity_key}_edit_{selected_id}",
    )
    if st.button("Salvar alterações", type="primary", key=f"{entity_key}_edit_button"):
        _save_update(repo, config, entity_key, int(selected_id), values)


def _render_delete(session, repo: CRUDRepository, config: dict[str, Any]) -> None:
    records = repo.list(limit=1000)
    if not records:
        st.info("Nenhum registro para excluir.")
        return
    selected_id = st.selectbox(
        "Registro",
        options=[record.id for record in records],
        format_func=lambda record_id: _select_label(session.get(config["model"], record_id)),
        key=f"{config['model'].__tablename__}_delete_select",
    )
    confirm = st.checkbox("Confirmar exclusão", key=f"{config['model'].__tablename__}_delete_confirm")
    if st.button("Excluir", disabled=not confirm, key=f"{config['model'].__tablename__}_delete_button"):
        repo.delete(int(selected_id))
        st.success("Registro excluído.")
        st.rerun()


def _render_fields(
    session,
    config: dict[str, Any],
    entity_key: str,
    current: dict[str, Any] | None = None,
    prefix: str = "form",
) -> dict[str, Any]:
    current = current or {}
    values: dict[str, Any] = {}
    cep_autofill: dict[str, Any] = {}
    cols = st.columns(2)

    for index, field in enumerate(config["fields"]):
        name = field["name"]
        key = f"{prefix}_{name}"
        if entity_key == "companies" and name in {"address", "neighborhood", "city", "state"}:
            mapped = cep_autofill.get(name)
            if mapped and not current.get(name) and not st.session_state.get(key):
                st.session_state[key] = mapped

        target = cols[index % 2]
        if field["type"] == "textarea":
            target = st.container()
        with target:
            values[name] = _render_field(session, field, key, current.get(name))

        if entity_key == "companies" and name == "cep":
            digits = only_digits(values[name])
            if len(digits) == 8:
                try:
                    cep_autofill = _cached_lookup_cep(digits) or {}
                except Exception as exc:
                    st.warning(f"ViaCEP indisponível: {exc}")

    return values


def _render_field(session, field: dict[str, Any], key: str, current_value: Any) -> Any:
    label = field["label"]
    field_type = field["type"]

    if field_type == "textarea":
        return st.text_area(
            label,
            value=str(current_value or ""),
            key=key,
            height=120,
            placeholder=field.get("placeholder", ""),
        )
    if field_type == "text":
        value = current_value or ""
        if field["name"] == "cpf":
            value = mask_cpf(value)
        elif field["name"] == "document_number":
            value = str(value or "")
        elif field["name"] == "phone":
            value = mask_phone(value)
        elif field["name"] == "cep":
            value = mask_cep(value)
        return st.text_input(
            label,
            value=str(value),
            key=key,
            placeholder=field.get("placeholder", ""),
        )
    if field_type == "select":
        return _render_select(field, key, current_value)
    if field_type == "bool":
        default = field.get("default", False) if current_value is None else bool(current_value)
        return st.checkbox(label, value=default, key=key)
    if field_type == "currency":
        current = float(current_value or 0)
        return Decimal(str(st.number_input(label, min_value=0.0, value=current, step=100.0, key=key)))
    if field_type == "int":
        minimum = int(field.get("min", 0))
        maximum = int(field.get("max", 999999999))
        current = int(current_value or minimum)
        return int(st.number_input(label, min_value=minimum, max_value=maximum, value=current, step=1, key=key))
    if field_type == "date":
        return st.text_input(
            label,
            value=format_date_br(current_value),
            key=key,
            placeholder="DD/MM/AAAA",
        )
    if field_type == "datetime":
        return st.text_input(
            label,
            value=format_datetime_br(current_value)[:10],
            key=key,
            placeholder="DD/MM/AAAA",
        )
    if field_type == "fk":
        return _render_fk_select(session, field, key, current_value)
    return st.text_input(label, value=str(current_value or ""), key=key)


def _render_select(field: dict[str, Any], key: str, current_value: Any) -> Any:
    options = field.get("options", [])
    values = [_option_value(option) for option in options]
    labels = [_option_label(option) for option in options]
    default = field.get("default")
    selected_value = current_value if current_value not in (None, "") else default
    if selected_value not in values and values:
        selected_value = values[0]
    index = values.index(selected_value) if selected_value in values else 0
    selected_label = st.selectbox(field["label"], labels, index=index, key=key)
    return values[labels.index(selected_label)]


def _render_fk_select(session, field: dict[str, Any], key: str, current_value: Any) -> int | None:
    model = field["model"]
    statement = select(model)
    if model is PipelineStage:
        statement = statement.order_by(PipelineStage.order_index)
    elif hasattr(model, "id"):
        statement = statement.order_by(model.id.desc())
    records = list(session.scalars(statement).all())
    options = [None] + [record.id for record in records]
    if current_value not in options:
        current_value = None
    index = options.index(current_value)
    return st.selectbox(
        field["label"],
        options=options,
        format_func=lambda value: "Nenhum" if value is None else _select_label(session.get(model, value)),
        index=index,
        key=key,
    )


def _save_create(repo: CRUDRepository, config: dict[str, Any], entity_key: str, values: dict[str, Any], current_user: dict) -> None:
    try:
        payload = _prepare_payload(config, entity_key, values)
        if entity_key == "activities" and not payload.get("created_by"):
            payload["created_by"] = current_user["id"]
        repo.create(payload)
        st.success("Registro criado.")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))


def _save_update(repo: CRUDRepository, config: dict[str, Any], entity_key: str, record_id: int, values: dict[str, Any]) -> None:
    try:
        payload = _prepare_payload(config, entity_key, values)
        repo.update(record_id, payload)
        st.success("Registro atualizado.")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))


def _prepare_payload(config: dict[str, Any], entity_key: str, values: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    errors: list[str] = []

    for field in config["fields"]:
        name = field["name"]
        value = values.get(name)
        field_type = field["type"]

        if field_type in {"text", "textarea", "select"}:
            value = str(value or "").strip() or None
        elif field_type == "date":
            value = parse_date_br(value)
        elif field_type == "datetime":
            value = parse_datetime_br(value)
        elif field_type == "currency":
            value = Decimal(str(value or 0))
        elif field_type == "int":
            value = int(value or 0)
            if value == 0 and not field.get("keep_zero", True):
                value = None
        elif field_type == "bool":
            value = bool(value)

        if field.get("required") and value in (None, ""):
            errors.append(f"{field['label']} é obrigatório.")
        payload[name] = value

    if entity_key == "companies":
        payload["document_number"] = only_digits(payload.get("document_number"))
        payload["phone"] = only_digits(payload.get("phone"))
        payload["cep"] = only_digits(payload.get("cep"))
        if payload.get("state"):
            payload["state"] = str(payload["state"]).upper()[:2]
        if payload.get("document_number") and not validate_document(payload.get("document_type"), payload.get("document_number")):
            errors.append("CPF/CNPJ inválido.")
        _apply_viacep_payload(payload)
    elif entity_key == "contacts":
        payload["cpf"] = only_digits(payload.get("cpf"))
        payload["phone"] = only_digits(payload.get("phone"))
        if payload.get("cpf") and not validate_cpf(payload.get("cpf")):
            errors.append("CPF inválido.")
    elif entity_key == "activities" and not payload.get("occurred_at"):
        payload["occurred_at"] = br_now()
    elif entity_key == "tickets" and not payload.get("opened_at"):
        payload["opened_at"] = br_now()
    elif entity_key == "proposals":
        if not payload.get("total"):
            payload["total"] = Decimal(payload.get("subtotal") or 0) - Decimal(payload.get("discount") or 0)

    if errors:
        raise ValueError(" ".join(errors))
    return payload


def _apply_viacep_payload(payload: dict[str, Any]) -> None:
    cep = only_digits(payload.get("cep"))
    if len(cep) != 8:
        return
    try:
        address_data = _cached_lookup_cep(cep)
    except Exception:
        return
    if not address_data:
        return
    for key in ("address", "neighborhood", "city", "state"):
        if not payload.get(key) and address_data.get(key):
            payload[key] = address_data[key]


def _format_record_row(session, config: dict[str, Any], record: Any) -> dict[str, Any]:
    data = model_to_dict(record)
    field_map = {field["name"]: field for field in config["fields"]}
    row: dict[str, Any] = {}
    for column in config["list_columns"]:
        field = field_map.get(column, {})
        label = field.get("label", column)
        value = data.get(column)
        row[label] = _format_value(session, record, column, value, field)
    return row


def _format_value(session, record: Any, column: str, value: Any, field: dict[str, Any]) -> Any:
    if value is None:
        return ""
    if field.get("type") == "fk":
        model = field["model"]
        related = session.get(model, value)
        return _select_label(related) if related else ""
    if field.get("type") == "currency":
        return format_currency(value)
    if field.get("type") == "bool":
        return format_bool(value)
    if field.get("type") == "date":
        return format_date_br(value)
    if field.get("type") == "datetime":
        return format_datetime_br(value)
    if column == "document_number":
        return mask_document(getattr(record, "document_type", None), value)
    if column == "cpf":
        return mask_cpf(value)
    if column == "phone":
        return mask_phone(value)
    if column == "cep":
        return mask_cep(value)
    return value


def _select_label(record: Any) -> str:
    if record is None:
        return "Nenhum"
    if isinstance(record, Company):
        return f"#{record.id} - {record.name}"
    if isinstance(record, Contact):
        full_name = f"{record.first_name or ''} {record.last_name or ''}".strip()
        return f"#{record.id} - {full_name}"
    if isinstance(record, Lead):
        return f"#{record.id} - {record.name}"
    if isinstance(record, Deal):
        return f"#{record.id} - {record.title}"
    if isinstance(record, User):
        return f"#{record.id} - {record.name}"
    if isinstance(record, PipelineStage):
        return record.name
    if isinstance(record, Product):
        return f"#{record.id} - {record.name}"
    if isinstance(record, Proposal):
        return f"#{record.id} - {record.title}"
    if isinstance(record, Ticket):
        return f"#{record.id} - {record.title}"
    if isinstance(record, LGPDConsent):
        return f"#{record.id} - {record.legal_basis}"
    return f"#{getattr(record, 'id', '')}"


def _option_value(option: Any) -> Any:
    return option[0] if isinstance(option, tuple) else option


def _option_label(option: Any) -> str:
    return option[1] if isinstance(option, tuple) else str(option)
