# 🚀 Projeto de Engenharia de Dados: dbt + Supabase

Plataforma de inteligência comercial para e-commerce, construída com **dbt Core** + **Supabase (PostgreSQL)** + **Streamlit**, seguindo a arquitetura **Medalhão (Bronze → Silver → Gold)**.

---

## 🛠️ Stack Tecnológico

| Tecnologia | Uso |
|---|---|
| **Supabase (PostgreSQL)** | Banco de dados cloud |
| **dbt Core** | Transformação e modelagem dos dados |
| **Streamlit** | Dashboard analítico interativo |
| **Plotly** | Visualizações e gráficos |
| **SQLAlchemy + psycopg2** | Conexão Python → PostgreSQL |
| **Python** | Orquestração e lógica do dashboard |

---

## 📂 Estrutura do Projeto

```text
projeto_dbt_supabase/
├── ecommerce/                   # Projeto dbt
│   ├── models/
│   │   ├── bronze/              # Views — espelho das tabelas raw
│   │   ├── silver/              # Tables — dados limpos e enriquecidos
│   │   └── gold/                # Tables — Data Marts analíticos
│   │       ├── sales/
│   │       ├── customer_success/
│   │       └── pricing/
│   └── dbt_project.yml
├── .llm/
│   ├── app.py                   # Dashboard Streamlit (3 páginas)
│   ├── .env                     # Credenciais (não versionado)
│   └── .env.example             # Template de credenciais
├── requirements.txt             # Dependências Python
└── CLAUDE.md                    # Guia para o Claude Code
```

---

## 📊 Arquitetura Medalhão

### 🥉 Bronze
Views sobre as tabelas raw do Supabase. Sem transformações — apenas tipagem básica e limpeza mínima.

### 🥈 Silver
Tabelas materializadas com lógica de negócio: cálculo de receita por item, extração de componentes de data, categorização de faixas de preço.

### 🥇 Gold — Data Marts

| Modelo | Schema | Descrição |
|--------|--------|-----------|
| `vendas_temporais` | `public_gold_sales` | KPIs de vendas por período, categoria e estado |
| `vendas_acumuladas_mes` | `public_gold_sales` | Receita acumulada mensal |
| `clientes_segmentacao` | `public_gold` | Segmentação RFM: VIP, Regular, Ocasional |
| `precos_competitividade` | `public_gold` | Comparativo de preços vs concorrentes |

---

## ⚙️ Como Executar

### 1. Configurar o dbt

```bash
# Instalar dbt
pip install dbt-postgres

# Configurar ~/.dbt/profiles.yml com as credenciais do Supabase
dbt debug         # Testa a conexão
dbt run           # Executa todas as transformações
```

### 2. Executar o Dashboard

```bash
# Ativar o ambiente virtual
.venv\Scripts\activate

# Instalar dependências (primeira vez)
pip install -r requirements.txt

# Configurar credenciais
cp .llm\.env.example .llm\.env
# Editar .llm\.env com a POSTGRES_URL do Supabase

# Iniciar o dashboard
python -m streamlit run .llm\app.py
```

Dashboard disponível em `http://localhost:8501`.

---

## 📈 Dashboard — Páginas

| Página | Perfil | Conteúdo |
|--------|--------|----------|
| 🛒 **Vendas** | Diretor Comercial | Receita, volume, sazonalidade, top produtos e estados |
| 👥 **Clientes** | Customer Success | Segmentação, ticket médio, ranking e comportamento de compra |
| 💰 **Pricing** | Diretor de Pricing | Competitividade vs concorrentes, alertas de preço e posicionamento |

---

**Desenvolvido por [Vanessa Prado](https://github.com/euvanessa-prado)** 👋
