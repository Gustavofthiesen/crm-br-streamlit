"""Dashboard page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from crm.database import get_session
from crm.formatters import format_currency
from crm.services import get_dashboard_metrics


def render(current_user: dict) -> None:
    st.title("Dashboard")

    with get_session() as session:
        metrics = get_dashboard_metrics(session)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Leads", metrics["total_leads"])
    col2.metric("Oportunidades abertas", metrics["open_deals"])
    col3.metric("Receita prevista", format_currency(metrics["forecast"]))
    col4.metric("Chamados abertos", metrics["open_tickets"])

    col5, col6, col7 = st.columns(3)
    col5.metric("Vendas ganhas", format_currency(metrics["won"]))
    col6.metric("Vendas perdidas", format_currency(metrics["lost"]))
    col7.metric("Tarefas atrasadas", metrics["overdue_tasks"])

    stage_df = pd.DataFrame(metrics["conversion_by_stage"])
    source_df = pd.DataFrame(metrics["leads_by_source"])

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("Conversão por etapa")
        if stage_df.empty:
            st.info("Sem oportunidades cadastradas.")
        else:
            fig = px.funnel(stage_df, x="Quantidade", y="Etapa")
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=360)
            st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader("Leads por origem")
        if source_df.empty:
            st.info("Sem leads cadastrados.")
        else:
            fig = px.bar(source_df, x="Origem", y="Quantidade", text_auto=True)
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=360)
            st.plotly_chart(fig, use_container_width=True)
