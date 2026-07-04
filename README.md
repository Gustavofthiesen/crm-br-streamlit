# CRM BR Streamlit

MVP de CRM brasileiro em Python com Streamlit, SQLite e uma arquitetura simples para evoluir para PostgreSQL. O projeto cobre cadastro comercial, funil de vendas, propostas, tarefas, chamados, LGPD, auditoria e placeholders de integrações comuns no contexto brasileiro.

## Funcionalidades

- App Streamlit multipágina com autenticação local.
- Perfis: `admin`, `gerente`, `vendedor` e `atendimento`.
- CRUD completo para clientes/empresas, contatos, leads, oportunidades, atividades, tarefas, produtos/serviços, propostas e chamados.
- Tabelas adicionais para usuários, etapas do funil, anexos, auditoria e consentimentos LGPD.
- Dashboard com leads, oportunidades abertas, receita prevista, vendas ganhas/perdidas, conversão por etapa, leads por origem, tarefas atrasadas e chamados abertos.
- Funil padrão: Novo lead, Contato feito, Diagnóstico, Proposta enviada, Negociação, Fechado ganho e Fechado perdido.
- Campos brasileiros: CPF, CNPJ, telefone com DDD, CEP, moeda em Real, datas DD/MM/AAAA e fuso America/Sao_Paulo.
- Validação de CPF/CNPJ com `validate-docbr`.
- Busca de endereço por CEP via ViaCEP.
- Exportação CSV com `pandas` e gráficos com `plotly`.
- Logs de auditoria em criação, edição e exclusão de registros importantes.

## Estrutura

```text
app.py
crm/
  config.py
  database.py
  formatters.py
  models.py
  repositories.py
  services.py
  services_time.py
  validators_br.py
  integrations/
  pages/
scripts/
  seed_data.py
  pull_reference_crms.sh
.streamlit/
  secrets.toml.example
requirements.txt
```

## Como rodar localmente

No Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:CRM_ADMIN_PASSWORD="defina-uma-senha-forte"
python scripts/seed_data.py
streamlit run app.py
```

No macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CRM_ADMIN_PASSWORD="defina-uma-senha-forte"
python scripts/seed_data.py
streamlit run app.py
```

Se `CRM_ADMIN_PASSWORD` ou `[admin].password` não estiver configurado antes do primeiro seed, o sistema gera uma senha temporária e a imprime uma vez no terminal/log.

## Secrets

Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` apenas no ambiente local ou configure os mesmos blocos no Streamlit Community Cloud. Não versione `.streamlit/secrets.toml`.

Exemplo mínimo:

```toml
[admin]
email = "admin@crm.local"
password = "uma-senha-forte"

[database]
url = "sqlite:///crm_br_streamlit.db"
```

Para PostgreSQL no futuro, use uma URL SQLAlchemy em `CRM_DATABASE_URL`, `DATABASE_URL` ou `[database].url`, por exemplo `postgresql://usuario:senha@host:5432/banco`.

## Deploy no Streamlit Community Cloud

1. Envie este repositório para o GitHub.
2. Acesse o Streamlit Community Cloud e crie um app apontando para o arquivo `app.py`.
3. Configure os secrets usando `.streamlit/secrets.toml.example` como referência.
4. Faça o primeiro deploy. O Streamlit instalará `requirements.txt` automaticamente.

SQLite funciona para demonstração e MVP pequeno. Para uso multiusuário com persistência robusta, configure PostgreSQL.

## Repositórios de referência

O script `scripts/pull_reference_crms.sh` clona cópias rasas em `reference_repos/` somente para estudo funcional e arquitetural:

- SuiteCRM
- EspoCRM
- Twenty CRM
- Odoo
- Monica

Esses repositórios não fazem parte do app Streamlit, não são dependências do MVP e não devem ser commitados.

```bash
bash scripts/pull_reference_crms.sh
```

## Roadmap de integrações

- WhatsApp Business Platform: templates, mensagens transacionais e timeline.
- SMTP/e-mail: envio de propostas e notificações.
- Google Calendar: reuniões, lembretes e convites.
- ERP/financeiro: pedidos, contas a receber e cadastro financeiro.
- Pix: cobranças, QR Code dinâmico e baixa automática.
- NF-e/NFS-e: emissão fiscal, XML/PDF e consulta de status.
- BI/exportação: conectores analíticos e modelos para dashboards externos.

## GitHub

Com GitHub CLI autenticado:

```bash
gh repo create crm-br-streamlit --public --source=. --remote=origin --push
```

Sem GitHub CLI autenticado:

```bash
git remote add origin <URL_DO_REPOSITORIO>
git branch -M main
git push -u origin main
```
