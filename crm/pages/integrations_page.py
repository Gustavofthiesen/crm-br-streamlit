"""Integration roadmap page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from crm.integrations import bi_export, email, erp_financeiro, fiscal, google_calendar, pix, whatsapp
from crm.services import can_access_page


INTEGRATIONS = [
    ("WhatsApp Business Platform", whatsapp.planned_capabilities()),
    ("SMTP / e-mail", email.planned_capabilities()),
    ("Google Calendar", google_calendar.planned_capabilities()),
    ("ERP / financeiro", erp_financeiro.planned_capabilities()),
    ("Pix", pix.planned_capabilities()),
    ("NF-e / NFS-e", fiscal.planned_capabilities()),
    ("BI / exportação", bi_export.planned_capabilities()),
]


def render(current_user: dict) -> None:
    if not can_access_page(current_user["role"], "integrations"):
        st.warning("Acesso não permitido para este perfil.")
        return

    st.title("Integrações")
    rows = [
        {
            "Integração": name,
            "Status": "Planejada",
            "Escopo inicial": ", ".join(capabilities),
        }
        for name, capabilities in INTEGRATIONS
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
