from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="CRM BR Streamlit",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

from crm.config import get_admin_email, get_admin_setup_token
from crm.database import get_session, init_db
from crm.pages import audit, dashboard, integrations_page
from crm.pages.crud_pages import render_entity_page
from crm.services import (
    ROLE_LABELS,
    authenticate_user,
    can_access_page,
    ensure_initial_data,
    get_user_count,
    set_admin_password,
)


PAGE_DEFS = [
    ("dashboard", "Dashboard", dashboard.render),
    ("companies", "Clientes / Empresas", lambda user: render_entity_page("companies", user)),
    ("contacts", "Contatos", lambda user: render_entity_page("contacts", user)),
    ("leads", "Leads", lambda user: render_entity_page("leads", user)),
    ("deals", "Oportunidades", lambda user: render_entity_page("deals", user)),
    ("activities", "Atividades", lambda user: render_entity_page("activities", user)),
    ("tasks", "Tarefas", lambda user: render_entity_page("tasks", user)),
    ("products", "Produtos / Serviços", lambda user: render_entity_page("products", user)),
    ("proposals", "Propostas", lambda user: render_entity_page("proposals", user)),
    ("tickets", "Chamados", lambda user: render_entity_page("tickets", user)),
    ("lgpd", "LGPD", lambda user: render_entity_page("lgpd", user)),
    ("audit", "Auditoria", audit.render),
    ("integrations", "Integrações", integrations_page.render),
]


def bootstrap() -> None:
    init_db()
    with get_session() as session:
        result = ensure_initial_data(session, create_random_admin=False)
    if result.get("admin_created"):
        email = result.get("admin_email")
        generated = result.get("generated_password")
        if generated:
            print(f"Admin inicial criado: {email} / senha temporária: {generated}")
            st.session_state["bootstrap_notice"] = (
                "Admin inicial criado. A senha temporária foi exibida no terminal/log "
                "do processo."
            )
        else:
            st.session_state["bootstrap_notice"] = "Admin inicial criado com a senha configurada nos secrets/env."
    elif result.get("admin_updated"):
        st.session_state["bootstrap_notice"] = "Senha do admin sincronizada com os secrets/env configurados."
    elif result.get("setup_required"):
        st.session_state["bootstrap_notice"] = "Crie a senha inicial do admin no painel abaixo."


def apply_style() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
        [data-testid="stMetric"] {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.9rem 1rem;
            background: #ffffff;
        }
        section[data-testid="stSidebar"] {
            border-right: 1px solid #e5e7eb;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def login_view() -> None:
    st.title("CRM BR Streamlit")
    if notice := st.session_state.get("bootstrap_notice"):
        st.info(notice)

    login_tab, setup_tab = st.tabs(["Entrar", "Criar senha admin"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("E-mail", placeholder="admin@crm.local")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", type="primary")

        if submitted:
            with get_session() as session:
                user = authenticate_user(session, email, password)
                if not user:
                    st.error("Credenciais inválidas.")
                    return
                st.session_state["current_user"] = {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                }
            st.rerun()

    with setup_tab:
        render_admin_password_setup()


def render_admin_password_setup() -> None:
    with get_session() as session:
        user_count = get_user_count(session)

    setup_token = get_admin_setup_token()
    initial_setup = user_count == 0

    if initial_setup:
        st.info("Nenhum usuário existe ainda. Defina a senha inicial do admin.")
    elif not setup_token:
        st.warning(
            "Para alterar a senha pelo painel quando já existe usuário, configure "
            "`[admin].setup_token` nos Secrets do Streamlit e reinicie o app."
        )

    with st.form("admin_password_setup_form"):
        admin_email = st.text_input("E-mail do admin", value=get_admin_email())
        if not initial_setup:
            provided_token = st.text_input("Código de configuração", type="password")
        else:
            provided_token = ""
        new_password = st.text_input("Nova senha", type="password")
        confirm_password = st.text_input("Confirmar senha", type="password")
        submitted = st.form_submit_button("Salvar senha", type="primary")

    if not submitted:
        return

    if not initial_setup:
        if not setup_token:
            st.error("Configure um setup_token nos Secrets antes de alterar a senha.")
            return
        if provided_token != setup_token:
            st.error("Código de configuração inválido.")
            return

    if new_password != confirm_password:
        st.error("As senhas não conferem.")
        return

    try:
        with get_session() as session:
            result = set_admin_password(session, admin_email, new_password)
        action = "criada" if result["created"] else "atualizada"
        st.success(f"Senha do admin {action}. Agora faça login com {result['admin_email']}.")
        st.session_state["bootstrap_notice"] = "Senha do admin configurada com sucesso."
    except Exception as exc:
        st.error(str(exc))


def sidebar(current_user: dict) -> tuple[str, str]:
    st.sidebar.title("CRM BR")
    st.sidebar.caption(f"{current_user['name']} · {ROLE_LABELS.get(current_user['role'], current_user['role'])}")

    available_pages = [
        (key, label, renderer)
        for key, label, renderer in PAGE_DEFS
        if can_access_page(current_user["role"], key)
    ]
    labels = [label for _, label, _ in available_pages]
    selected_label = st.sidebar.radio("Navegação", labels, label_visibility="collapsed")

    if st.sidebar.button("Sair"):
        st.session_state.pop("current_user", None)
        st.rerun()

    selected = next(item for item in available_pages if item[1] == selected_label)
    return selected[0], selected[1]


def main() -> None:
    apply_style()
    if not st.session_state.get("_bootstrapped"):
        bootstrap()
        st.session_state["_bootstrapped"] = True

    current_user = st.session_state.get("current_user")
    if not current_user:
        login_view()
        return

    selected_key, _selected_label = sidebar(current_user)
    renderer = next(renderer for key, _label, renderer in PAGE_DEFS if key == selected_key)
    renderer(current_user)


if __name__ == "__main__":
    main()
