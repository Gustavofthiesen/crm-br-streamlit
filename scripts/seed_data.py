from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crm.database import get_session, init_db
from crm.models import (
    Activity,
    Company,
    Contact,
    Deal,
    LGPDConsent,
    Lead,
    PipelineStage,
    Product,
    Proposal,
    Task,
    Ticket,
    User,
)
from crm.repositories import CRUDRepository
from crm.services import ensure_initial_data
from crm.services_time import br_now


def main() -> None:
    init_db()
    with get_session() as session:
        initial = ensure_initial_data(session)
        if initial.get("admin_created") and initial.get("generated_password"):
            print(
                "Admin inicial criado: "
                f"{initial['admin_email']} / senha temporária: {initial['generated_password']}"
            )

        admin = session.scalar(select(User).where(User.role == "admin").limit(1))
        if not admin:
            raise RuntimeError("Admin inicial não foi criado.")

        existing_companies = session.scalar(select(func.count(Company.id))) or 0
        if existing_companies:
            print("Dados seed já existem. Nada a fazer.")
            return

        stages = {
            stage.name: stage
            for stage in session.scalars(
                select(PipelineStage).order_by(PipelineStage.order_index)
            ).all()
        }

        company_repo = CRUDRepository(session, Company, user_id=admin.id)
        contact_repo = CRUDRepository(session, Contact, user_id=admin.id)
        lead_repo = CRUDRepository(session, Lead, user_id=admin.id)
        deal_repo = CRUDRepository(session, Deal, user_id=admin.id)
        task_repo = CRUDRepository(session, Task, user_id=admin.id)
        product_repo = CRUDRepository(session, Product, user_id=admin.id)
        proposal_repo = CRUDRepository(session, Proposal, user_id=admin.id)
        ticket_repo = CRUDRepository(session, Ticket, user_id=admin.id)
        activity_repo = CRUDRepository(session, Activity, user_id=admin.id)
        lgpd_repo = CRUDRepository(session, LGPDConsent, user_id=admin.id)

        aurora = company_repo.create(
            {
                "name": "Café Aurora LTDA",
                "trade_name": "Café Aurora",
                "document_type": "CNPJ",
                "document_number": "11222333000181",
                "industry": "Alimentos",
                "status": "ativo",
                "email": "contato@cafeaurora.example",
                "phone": "11988887777",
                "cep": "01311000",
                "address": "Avenida Paulista",
                "number": "1000",
                "neighborhood": "Bela Vista",
                "city": "São Paulo",
                "state": "SP",
                "owner_id": admin.id,
                "notes": "Cliente estratégico para expansão B2B.",
            }
        )
        clinic = company_repo.create(
            {
                "name": "Clínica Boa Vista",
                "document_type": "CNPJ",
                "document_number": "04252011000110",
                "industry": "Saúde",
                "status": "prospect",
                "email": "adm@boavista.example",
                "phone": "2133334444",
                "cep": "20040002",
                "city": "Rio de Janeiro",
                "state": "RJ",
                "owner_id": admin.id,
            }
        )

        ana = contact_repo.create(
            {
                "company_id": aurora.id,
                "first_name": "Ana",
                "last_name": "Silva",
                "cpf": "52998224725",
                "email": "ana.silva@cafeaurora.example",
                "phone": "11977776666",
                "role_title": "Diretora comercial",
                "department": "Comercial",
                "marketing_opt_in": True,
                "owner_id": admin.id,
            }
        )
        bruno = contact_repo.create(
            {
                "company_id": clinic.id,
                "first_name": "Bruno",
                "last_name": "Costa",
                "email": "bruno@boavista.example",
                "phone": "21988885555",
                "role_title": "Gerente administrativo",
                "marketing_opt_in": False,
                "owner_id": admin.id,
            }
        )

        lead = lead_repo.create(
            {
                "name": "Expansão de vendas regionais",
                "company_id": aurora.id,
                "contact_id": ana.id,
                "source": "Indicação",
                "status": "qualificado",
                "pipeline_stage_id": stages["Diagnóstico"].id,
                "estimated_value": Decimal("45000.00"),
                "expected_close_date": date.today() + timedelta(days=25),
                "assigned_to": admin.id,
            }
        )
        lead_repo.create(
            {
                "name": "Automação de relacionamento",
                "company_id": clinic.id,
                "contact_id": bruno.id,
                "source": "Site",
                "status": "novo",
                "pipeline_stage_id": stages["Novo lead"].id,
                "estimated_value": Decimal("18000.00"),
                "expected_close_date": date.today() + timedelta(days=40),
                "assigned_to": admin.id,
            }
        )

        deal = deal_repo.create(
            {
                "title": "Contrato anual Café Aurora",
                "company_id": aurora.id,
                "contact_id": ana.id,
                "lead_id": lead.id,
                "pipeline_stage_id": stages["Proposta enviada"].id,
                "value": Decimal("52000.00"),
                "probability": 60,
                "status": "open",
                "expected_close_date": date.today() + timedelta(days=18),
                "assigned_to": admin.id,
            }
        )
        deal_repo.create(
            {
                "title": "Projeto piloto Boa Vista",
                "company_id": clinic.id,
                "contact_id": bruno.id,
                "pipeline_stage_id": stages["Fechado ganho"].id,
                "value": Decimal("12000.00"),
                "probability": 100,
                "status": "won",
                "closed_at": br_now(),
                "assigned_to": admin.id,
            }
        )

        product = product_repo.create(
            {
                "name": "Implantação CRM",
                "sku": "SERV-CRM-IMPL",
                "description": "Projeto de implantação e treinamento.",
                "unit": "projeto",
                "price": Decimal("15000.00"),
                "active": True,
                "tax_notes": "Serviço sujeito a NFS-e conforme município.",
            }
        )
        product_repo.create(
            {
                "name": "Suporte mensal",
                "sku": "SERV-SUP-MENSAL",
                "unit": "mês",
                "price": Decimal("2500.00"),
                "active": True,
            }
        )

        proposal_repo.create(
            {
                "number": "PROP-2026-001",
                "title": "Proposta Café Aurora",
                "company_id": aurora.id,
                "contact_id": ana.id,
                "deal_id": deal.id,
                "status": "enviada",
                "subtotal": Decimal("52000.00"),
                "discount": Decimal("2000.00"),
                "total": Decimal("50000.00"),
                "valid_until": date.today() + timedelta(days=15),
                "sent_at": date.today(),
                "terms": "Pagamento em 3 parcelas via boleto ou Pix.",
            }
        )

        task_repo.create(
            {
                "title": "Retornar proposta Café Aurora",
                "description": "Confirmar dúvidas técnicas e próximos passos.",
                "status": "aberta",
                "priority": "alta",
                "due_date": date.today() - timedelta(days=1),
                "assigned_to": admin.id,
                "related_entity_type": "deals",
                "related_entity_id": deal.id,
            }
        )
        task_repo.create(
            {
                "title": "Agendar diagnóstico Boa Vista",
                "status": "aberta",
                "priority": "media",
                "due_date": date.today() + timedelta(days=3),
                "assigned_to": admin.id,
                "related_entity_type": "companies",
                "related_entity_id": clinic.id,
            }
        )

        activity_repo.create(
            {
                "type": "reunião",
                "subject": "Diagnóstico inicial",
                "description": f"Apresentado escopo de {product.name}.",
                "occurred_at": br_now(),
                "company_id": aurora.id,
                "contact_id": ana.id,
                "deal_id": deal.id,
                "created_by": admin.id,
            }
        )

        ticket_repo.create(
            {
                "company_id": aurora.id,
                "contact_id": ana.id,
                "title": "Dúvida sobre integração fiscal",
                "description": "Cliente pediu detalhes sobre roadmap de NF-e/NFS-e.",
                "status": "aberto",
                "priority": "media",
                "channel": "e-mail",
                "assigned_to": admin.id,
            }
        )

        lgpd_repo.create(
            {
                "company_id": aurora.id,
                "contact_id": ana.id,
                "legal_basis": "consentimento",
                "marketing_consent": True,
                "consent_date": date.today(),
                "purpose": "Relacionamento comercial, envio de propostas e comunicações de marketing B2B.",
                "source": "Formulário comercial",
            }
        )

        print("Seed concluído com dados de demonstração.")


if __name__ == "__main__":
    main()
