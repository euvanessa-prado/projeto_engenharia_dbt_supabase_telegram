import os
import yaml
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# ── Engine SQLAlchemy via profiles.yml do dbt ────────────────────────────────

def _get_engine():
    profiles_path = os.path.join(os.path.expanduser("~"), ".dbt", "profiles.yml")
    with open(profiles_path, "r") as f:
        profiles = yaml.safe_load(f)
    dev = profiles["ecommerce"]["outputs"]["dev"]
    url = (
        f"postgresql+psycopg2://{dev['user']}:{dev['pass']}"
        f"@{dev['host']}:{dev['port']}/{dev['dbname']}"
    )
    return create_engine(url)

def get_data(query: str) -> pd.DataFrame:
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        st.stop()

# ── Config ────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="E-commerce Analytics", layout="wide", page_icon="📊")

# ── Paleta Supabase (preto + verde) ──────────────────────────────────────────

VERDE       = "#3ECF8E"   # verde Supabase principal
VERDE_DARK  = "#1A9E6A"   # verde escuro
VERDE_LIGHT = "#6EDBB0"   # verde claro
PRETO       = "#0F0F0F"   # fundo principal
CINZA_DARK  = "#1C1C1C"   # card background
CINZA_MED   = "#2A2A2A"   # bordas / hover
BRANCO      = "#F0F0F0"   # texto principal
ROXO_SIDEBAR= "#171717"   # sidebar Supabase

CORES = [VERDE, VERDE_LIGHT, VERDE_DARK, "#00E5A0", "#00BF72", "#007A47", "#00FF9F"]

CORES_SEGMENTO = {
    "VIP":      VERDE,
    "TOP_TIER": VERDE_DARK,
    "REGULAR":  CINZA_MED,
}

CORES_CLASSIFICACAO = {
    "MAIS_CARO_QUE_TODOS":   "#FF4D4D",
    "ACIMA_DA_MEDIA":        "#FFA500",
    "NA_MEDIA":              VERDE_DARK,
    "ABAIXO_DA_MEDIA":       VERDE,
    "MAIS_BARATO_QUE_TODOS": VERDE_LIGHT,
}

ORDEM_SEMANA = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]

LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=CINZA_DARK,
    plot_bgcolor=CINZA_DARK,
    font=dict(color=BRANCO, size=12),
    title_font=dict(color=VERDE, size=15, family="monospace"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=BRANCO)),
    margin=dict(t=50, b=30, l=20, r=20),
)

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

    .stApp {{ background-color: {PRETO}; color: {BRANCO}; }}

    section[data-testid="stSidebar"] {{
        background-color: {ROXO_SIDEBAR};
        border-right: 1px solid {VERDE_DARK};
    }}
    section[data-testid="stSidebar"] * {{ color: {BRANCO} !important; }}
    section[data-testid="stSidebar"] .stRadio label {{ color: {BRANCO} !important; }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p {{ color: {VERDE} !important; }}

    [data-testid="metric-container"] {{
        background-color: {CINZA_DARK};
        border: 1px solid {VERDE_DARK};
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 0 12px rgba(62,207,142,0.08);
    }}
    [data-testid="metric-container"] label {{
        color: #A0A0A0 !important;
        font-size: 12px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {VERDE} !important;
        font-size: 24px !important;
        font-weight: 700 !important;
    }}
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {{
        font-size: 12px !important;
    }}

    h1 {{ color: {VERDE} !important; font-weight: 700; border-bottom: 1px solid {VERDE_DARK}; padding-bottom: 8px; }}
    h2, h3 {{ color: {VERDE_LIGHT} !important; }}

    .stSelectbox > div, .stMultiSelect > div {{
        background-color: {CINZA_DARK} !important;
        border: 1px solid {VERDE_DARK} !important;
        border-radius: 6px;
    }}

    .stDataFrame {{ border: 1px solid {VERDE_DARK}; border-radius: 8px; }}

    hr {{ border-color: {CINZA_MED} !important; }}

    .stSidebar .stMarkdown p {{ color: {VERDE} !important; }}
</style>
""", unsafe_allow_html=True)

# ── Formatação ────────────────────────────────────────────────────────────────

def fmt_brl(valor: float) -> str:
    return f"R$ {valor:_.2f}".replace("_", ".").replace(".", ",", 1).replace(",", ".", 1)

def fmt_num(valor: float) -> str:
    return f"{int(valor):,}".replace(",", ".")

def fmt_pct(valor: float) -> str:
    sinal = "+" if valor >= 0 else ""
    return f"{sinal}{valor:.1f}%"

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.markdown("## 📊 E-commerce Analytics")
st.sidebar.markdown("---")
pagina = st.sidebar.radio("Navegação", ["🛒 Vendas", "👥 Clientes", "💰 Pricing"])
st.sidebar.markdown("---")
st.sidebar.markdown(f"<small style='color:#888'>Powered by dbt + Supabase</small>", unsafe_allow_html=True)


# ── Página: Vendas ─────────────────────────────────────────────────────────────

def pagina_vendas():
    st.title("🛒 Vendas — Diretor Comercial")

    df = get_data("SELECT * FROM public_gold_sales.vendas_temporais")
    df["data_venda"] = pd.to_datetime(df["data_venda"])

    # ── Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        anos   = sorted(df["ano_venda"].dropna().unique().astype(int))
        meses  = sorted(df["mes_venda"].dropna().unique().astype(int))
        dias   = ORDEM_SEMANA

        ano_sel  = col_f1.selectbox("Ano", ["Todos"] + anos)
        mes_sel  = col_f2.selectbox("Mês", ["Todos"] + meses)
        dia_sel  = col_f3.multiselect("Dia da Semana", dias)

    if ano_sel != "Todos":
        df = df[df["ano_venda"] == ano_sel]
    if mes_sel != "Todos":
        df = df[df["mes_venda"] == mes_sel]
    if dia_sel:
        df = df[df["dia_semana_nome"].isin(dia_sel)]

    # ── KPIs
    receita_total   = df["receita_total"].sum()
    total_vendas    = df["total_vendas"].sum()
    ticket_medio    = receita_total / total_vendas if total_vendas > 0 else 0
    clientes_unicos = df.groupby("data_venda")["total_clientes_unicos"].max().sum()
    qtd_total       = df["quantidade_total"].sum()
    receita_hora_pico = df.groupby("hora_venda")["receita_total"].sum().max()
    hora_pico       = int(df.groupby("hora_venda")["receita_total"].sum().idxmax())
    dias_ativos     = df["data_venda"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Receita Total",      fmt_brl(receita_total))
    c2.metric("🛒 Total de Vendas",    fmt_num(total_vendas))
    c3.metric("🎯 Ticket Médio",       fmt_brl(ticket_medio))
    c4.metric("👤 Clientes Únicos",    fmt_num(clientes_unicos))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("📦 Itens Vendidos",     fmt_num(qtd_total))
    c6.metric("⚡ Receita Hora Pico",  fmt_brl(receita_hora_pico))
    c7.metric("🕐 Hora de Pico",       f"{hora_pico}h")
    c8.metric("📅 Dias com Vendas",    fmt_num(dias_ativos))

    st.divider()

    # Gráfico 1 — Receita Diária
    df_dia = df.groupby("data_venda")["receita_total"].sum().reset_index()
    fig1 = px.area(df_dia, x="data_venda", y="receita_total", title="Receita Diária",
                   labels={"data_venda": "Data", "receita_total": "Receita (R$)"})
    fig1.update_traces(line=dict(color=VERDE, width=2), fillcolor="rgba(62,207,142,0.15)")
    fig1.update_layout(**LAYOUT)
    st.plotly_chart(fig1, use_container_width=True)

    col1, col2 = st.columns(2)

    # Gráfico 2 — Receita por Dia da Semana
    df_semana = df.groupby("dia_semana_nome")["receita_total"].sum().reset_index()
    df_semana["dia_semana_nome"] = pd.Categorical(df_semana["dia_semana_nome"], categories=ORDEM_SEMANA, ordered=True)
    df_semana = df_semana.sort_values("dia_semana_nome")
    fig2 = px.bar(df_semana, x="dia_semana_nome", y="receita_total", title="Receita por Dia da Semana",
                  labels={"dia_semana_nome": "Dia", "receita_total": "Receita (R$)"},
                  color="receita_total", color_continuous_scale=[[0, VERDE_DARK], [1, VERDE_LIGHT]])
    fig2.update_layout(**LAYOUT, coloraxis_showscale=False)
    col1.plotly_chart(fig2, use_container_width=True)

    # Gráfico 3 — Volume por Hora
    df_hora = df.groupby("hora_venda")["total_vendas"].sum().reset_index()
    fig3 = px.bar(df_hora, x="hora_venda", y="total_vendas", title="Volume de Vendas por Hora",
                  labels={"hora_venda": "Hora", "total_vendas": "Vendas"},
                  color="total_vendas", color_continuous_scale=[[0, CINZA_MED], [1, VERDE]])
    fig3.update_layout(**LAYOUT, coloraxis_showscale=False)
    col2.plotly_chart(fig3, use_container_width=True)

    # Gráfico 4 — Receita Mensal
    df_mes = df.groupby(["ano_venda", "mes_venda"])["receita_total"].sum().reset_index()
    df_mes["periodo"] = df_mes["ano_venda"].astype(int).astype(str) + "-" + df_mes["mes_venda"].astype(int).astype(str).str.zfill(2)
    df_mes = df_mes.sort_values(["ano_venda", "mes_venda"])
    fig4 = px.bar(df_mes, x="periodo", y="receita_total", title="Receita por Mês",
                  labels={"periodo": "Mês", "receita_total": "Receita (R$)"},
                  color_discrete_sequence=[VERDE])
    fig4.update_layout(**LAYOUT)
    st.plotly_chart(fig4, use_container_width=True)


# ── Página: Clientes ───────────────────────────────────────────────────────────

def pagina_clientes():
    st.title("👥 Clientes — Diretora de Customer Success")

    df = get_data("SELECT * FROM public_gold.clientes_segmentacao")

    # ── Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        estados   = sorted(df["estado"].dropna().unique())
        segmentos = ["VIP", "TOP_TIER", "REGULAR"]

        seg_sel    = col_f1.multiselect("Segmento", segmentos)
        estado_sel = col_f2.multiselect("Estado", estados)
        top_n      = col_f3.selectbox("Top N Clientes", [10, 20, 50])

    if seg_sel:
        df = df[df["segmento_cliente"].isin(seg_sel)]
    if estado_sel:
        df = df[df["estado"].isin(estado_sel)]

    # ── KPIs
    total_clientes  = len(df)
    clientes_vip    = len(df[df["segmento_cliente"] == "VIP"])
    clientes_top    = len(df[df["segmento_cliente"] == "TOP_TIER"])
    receita_vip     = df[df["segmento_cliente"] == "VIP"]["receita_total"].sum()
    receita_total   = df["receita_total"].sum()
    pct_vip_receita = (receita_vip / receita_total * 100) if receita_total > 0 else 0
    ticket_medio    = df["ticket_medio"].mean()
    media_compras   = df["total_compras"].mean()
    estados_ativos  = df["estado"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Total Clientes",    fmt_num(total_clientes))
    c2.metric("⭐ Clientes VIP",      fmt_num(clientes_vip))
    c3.metric("🥈 Top Tier",          fmt_num(clientes_top))
    c4.metric("💵 Receita Total",     fmt_brl(receita_total))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("💰 Receita VIP",       fmt_brl(receita_vip))
    c6.metric("📊 % Receita VIP",     fmt_pct(pct_vip_receita))
    c7.metric("🎯 Ticket Médio",      fmt_brl(ticket_medio))
    c8.metric("🗺️ Estados Ativos",    fmt_num(estados_ativos))

    st.divider()

    col1, col2 = st.columns(2)

    # Gráfico 1 — Pizza Segmento
    df_seg = df.groupby("segmento_cliente").size().reset_index(name="total")
    fig1 = px.pie(df_seg, names="segmento_cliente", values="total",
                  title="Distribuição por Segmento", hole=0.45,
                  color="segmento_cliente", color_discrete_map=CORES_SEGMENTO,
                  category_orders={"segmento_cliente": ["VIP", "TOP_TIER", "REGULAR"]})
    fig1.update_traces(textinfo="percent+label", textfont_color=BRANCO)
    fig1.update_layout(**LAYOUT)
    col1.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2 — Receita por Segmento
    df_rec = df.groupby("segmento_cliente")["receita_total"].sum().reset_index()
    fig2 = px.bar(df_rec, x="segmento_cliente", y="receita_total", title="Receita por Segmento",
                  labels={"segmento_cliente": "Segmento", "receita_total": "Receita (R$)"},
                  color="segmento_cliente", color_discrete_map=CORES_SEGMENTO,
                  category_orders={"segmento_cliente": ["VIP", "TOP_TIER", "REGULAR"]})
    fig2.update_layout(**LAYOUT)
    col2.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    # Gráfico 3 — Top N Clientes
    df_top = df.nsmallest(top_n, "ranking_receita").sort_values("receita_total")
    fig3 = px.bar(df_top, x="receita_total", y="nome_cliente", orientation="h",
                  title=f"Top {top_n} Clientes por Receita",
                  labels={"receita_total": "Receita (R$)", "nome_cliente": ""},
                  color="segmento_cliente", color_discrete_map=CORES_SEGMENTO)
    fig3.update_layout(**LAYOUT)
    col3.plotly_chart(fig3, use_container_width=True)

    # Gráfico 4 — Clientes por Estado
    df_estado = df.groupby("estado").agg(total=("cliente_id","count"), receita=("receita_total","sum")).reset_index()
    df_estado = df_estado.sort_values("receita", ascending=False).head(15)
    fig4 = px.bar(df_estado, x="estado", y="receita", title="Receita por Estado (Top 15)",
                  labels={"estado": "Estado", "receita": "Receita (R$)"},
                  color="receita", color_continuous_scale=[[0, VERDE_DARK], [1, VERDE_LIGHT]])
    fig4.update_layout(**LAYOUT, coloraxis_showscale=False)
    col4.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # Gráfico 5 — Scatter Ticket Médio x Total Compras
    fig5 = px.scatter(df, x="total_compras", y="ticket_medio",
                      color="segmento_cliente", size="receita_total",
                      hover_data=["nome_cliente", "estado"],
                      color_discrete_map=CORES_SEGMENTO,
                      title="Frequência de Compras vs Ticket Médio",
                      labels={"total_compras": "Nº de Compras", "ticket_medio": "Ticket Médio (R$)",
                              "segmento_cliente": "Segmento"})
    fig5.update_layout(**LAYOUT)
    st.plotly_chart(fig5, use_container_width=True)

    st.divider()

    # Tabela Detalhada
    st.subheader("📋 Tabela de Clientes")
    st.dataframe(df.sort_values("ranking_receita"), use_container_width=True, hide_index=True)


# ── Página: Pricing ────────────────────────────────────────────────────────────

def pagina_pricing():
    st.title("💰 Pricing — Diretor de Pricing")

    df = get_data("SELECT * FROM public_gold.precos_competitividade")

    # ── Filtros
    with st.expander("🔍 Filtros", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        categorias  = sorted(df["categoria"].unique())
        marcas      = sorted(df["marca"].unique())
        classifs    = sorted(df["classificacao_preco"].unique())

        cat_sel     = col_f1.multiselect("Categoria", categorias)
        marca_sel   = col_f2.multiselect("Marca", marcas)
        class_sel   = col_f3.multiselect("Classificação", classifs)

    if cat_sel:
        df = df[df["categoria"].isin(cat_sel)]
    if marca_sel:
        df = df[df["marca"].isin(marca_sel)]
    if class_sel:
        df = df[df["classificacao_preco"].isin(class_sel)]

    # ── KPIs
    total_produtos  = len(df)
    mais_caros      = len(df[df["classificacao_preco"] == "MAIS_CARO_QUE_TODOS"])
    mais_baratos    = len(df[df["classificacao_preco"] == "MAIS_BARATO_QUE_TODOS"])
    acima_media     = len(df[df["classificacao_preco"] == "ACIMA_DA_MEDIA"])
    dif_media       = df["diferenca_percentual_vs_media"].mean()
    receita_risco   = df[df["classificacao_preco"].isin(["MAIS_CARO_QUE_TODOS","ACIMA_DA_MEDIA"])]["receita_total"].sum()
    receita_total   = df["receita_total"].sum()
    pct_risco       = (receita_risco / receita_total * 100) if receita_total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Produtos Monitorados", fmt_num(total_produtos))
    c2.metric("🔴 Mais Caros que Todos", fmt_num(mais_caros))
    c3.metric("🟢 Mais Baratos que Todos", fmt_num(mais_baratos))
    c4.metric("📈 Acima da Média",       fmt_num(acima_media))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("📊 Dif. Média vs Mercado", fmt_pct(dif_media))
    c6.metric("💵 Receita Total",         fmt_brl(receita_total))
    c7.metric("⚠️ Receita em Risco",      fmt_brl(receita_risco))
    c8.metric("🎯 % Receita em Risco",    fmt_pct(pct_risco))

    st.divider()

    col1, col2 = st.columns(2)

    # Gráfico 1 — Pizza classificação
    df_class = df.groupby("classificacao_preco").size().reset_index(name="total")
    fig1 = px.pie(df_class, names="classificacao_preco", values="total", hole=0.4,
                  title="Posicionamento vs Concorrência",
                  color="classificacao_preco", color_discrete_map=CORES_CLASSIFICACAO)
    fig1.update_traces(textinfo="percent+label", textfont_color=BRANCO)
    fig1.update_layout(**LAYOUT)
    col1.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2 — Competitividade por Categoria
    df_cat = df.groupby("categoria")["diferenca_percentual_vs_media"].mean().reset_index()
    df_cat = df_cat.sort_values("diferenca_percentual_vs_media", ascending=False)
    df_cat["cor"] = df_cat["diferenca_percentual_vs_media"].apply(lambda x: "Acima" if x > 0 else "Abaixo")
    fig2 = px.bar(df_cat, x="categoria", y="diferenca_percentual_vs_media",
                  color="cor",
                  color_discrete_map={"Acima": "#FF4D4D", "Abaixo": VERDE},
                  title="Competitividade Média por Categoria (%)",
                  labels={"categoria": "Categoria", "diferenca_percentual_vs_media": "Dif. % vs Média"})
    fig2.update_layout(**LAYOUT)
    col2.plotly_chart(fig2, use_container_width=True)

    # Gráfico 3 — Scatter
    fig3 = px.scatter(df, x="diferenca_percentual_vs_media", y="quantidade_total",
                      color="classificacao_preco", size="receita_total",
                      hover_data=["nome_produto", "categoria", "marca"],
                      color_discrete_map=CORES_CLASSIFICACAO,
                      title="Competitividade x Volume de Vendas",
                      labels={"diferenca_percentual_vs_media": "Dif. % vs Média",
                              "quantidade_total": "Qtd Vendida",
                              "classificacao_preco": "Classificação"})
    fig3.update_layout(**LAYOUT)
    st.plotly_chart(fig3, use_container_width=True)

    # Gráfico 4 — Receita por Classificação
    df_rec_class = df.groupby("classificacao_preco")["receita_total"].sum().reset_index().sort_values("receita_total", ascending=True)
    fig4 = px.bar(df_rec_class, x="receita_total", y="classificacao_preco", orientation="h",
                  title="Receita por Classificação de Preço",
                  labels={"receita_total": "Receita (R$)", "classificacao_preco": ""},
                  color="classificacao_preco", color_discrete_map=CORES_CLASSIFICACAO)
    fig4.update_layout(**LAYOUT)
    st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # Tabela de Alertas
    st.subheader("🚨 Produtos em Alerta — Mais Caros que Todos os Concorrentes")
    df_alerta = df[df["classificacao_preco"] == "MAIS_CARO_QUE_TODOS"][
        ["produto_id", "nome_produto", "categoria", "marca", "nosso_preco",
         "preco_maximo_concorrentes", "diferenca_percentual_vs_media", "receita_total"]
    ].sort_values("diferenca_percentual_vs_media", ascending=False)
    st.dataframe(df_alerta, use_container_width=True, hide_index=True)


# ── Roteamento ────────────────────────────────────────────────────────────────

if pagina == "🛒 Vendas":
    pagina_vendas()
elif pagina == "👥 Clientes":
    pagina_clientes()
elif pagina == "💰 Pricing":
    pagina_pricing()
