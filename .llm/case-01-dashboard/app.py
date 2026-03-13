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

@st.cache_resource
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

@st.cache_data(ttl=300)
def _fetch(query: str) -> pd.DataFrame:
    engine = _get_engine()
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def get_data(query: str) -> pd.DataFrame:
    try:
        return _fetch(query)
    except Exception as e:
        st.error(f"Erro ao conectar com o banco de dados: {e}")
        st.stop()

# ── Config ────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="E-commerce Analytics", layout="wide", page_icon="📊")

# ── Paleta tema roxo ──────────────────────────────────────────────────────────

VERDE       = "#7C3AED"   # roxo principal
VERDE_DARK  = "#5B21B6"   # roxo escuro
VERDE_LIGHT = "#C4B5FD"   # roxo claro
PRETO       = "#0F172A"   # texto principal
CINZA_DARK  = "#FFFFFF"   # fundo cards
CINZA_MED   = "#E2E8F0"   # bordas
BRANCO      = "#F8FAFC"   # fundo app
CINZA       = "#64748B"   # texto secundário
ROXO_SIDEBAR= "#171717"   # unused

CORES = [
    "#7C3AED", "#60A5FA", "#FB923C", "#F87171", "#A78BFA",
    "#FBBF24", "#34D399", "#F472B6", "#38BDF8", "#4ADE80",
    "#818CF8", "#FCD34D", "#2DD4BF", "#F9A8D4", "#DDD6FE",
]

CORES_SEGMENTO = {
    "VIP":      "#8454E9",
    "Top Tier": "#FF4D4D",
    "Regular":  "#94A3B8",
}

CORES_CLASSIFICACAO = {
    "Mais Caro que Todos":   "#FF4D4D",
    "Acima da Média":        "#FFA500",
    "Na Média":              VERDE_DARK,
    "Abaixo da Média":       VERDE,
    "Mais Barato que Todos": VERDE_LIGHT,
}

ORDEM_SEMANA = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]

# ── Labels legíveis (sem underscores) ────────────────────────────────────────

LABEL_SEGMENTO = {
    "VIP":      "VIP",
    "TOP_TIER": "Top Tier",
    "REGULAR":  "Regular",
}

LABEL_CLASSIFICACAO = {
    "MAIS_CARO_QUE_TODOS":   "Mais Caro que Todos",
    "ACIMA_DA_MEDIA":        "Acima da Média",
    "NA_MEDIA":              "Na Média",
    "ABAIXO_DA_MEDIA":       "Abaixo da Média",
    "MAIS_BARATO_QUE_TODOS": "Mais Barato que Todos",
}

LABEL_COLUNAS = {
    # clientes
    "cliente_id":                    "ID Cliente",
    "nome_cliente":                  "Nome",
    "estado":                        "Estado",
    "receita_total":                 "Receita Total (R$)",
    "total_compras":                 "Nº Compras",
    "ticket_medio":                  "Ticket Médio (R$)",
    "primeira_compra":               "Primeira Compra",
    "ultima_compra":                 "Última Compra",
    "segmento_cliente":              "Segmento",
    "ranking_receita":               "Ranking",
    # pricing
    "produto_id":                    "ID Produto",
    "nome_produto":                  "Produto",
    "categoria":                     "Categoria",
    "marca":                         "Marca",
    "nosso_preco":                   "Nosso Preço (R$)",
    "preco_medio_concorrentes":      "Preço Médio Conc. (R$)",
    "preco_minimo_concorrentes":     "Preço Mín. Conc. (R$)",
    "preco_maximo_concorrentes":     "Preço Máx. Conc. (R$)",
    "total_concorrentes":            "Nº Concorrentes",
    "diferenca_percentual_vs_media": "Dif. % vs Média",
    "diferenca_percentual_vs_minimo":"Dif. % vs Mínimo",
    "classificacao_preco":           "Classificação",
    "quantidade_total":              "Qtd Vendida",
    # vendas
    "data_venda":                    "Data",
    "ano_venda":                     "Ano",
    "mes_venda":                     "Mês",
    "dia_venda":                     "Dia",
    "dia_semana_nome":               "Dia da Semana",
    "hora_venda":                    "Hora",
    "total_vendas":                  "Nº Vendas",
    "total_clientes_unicos":         "Clientes Únicos",
}

def aplicar_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "segmento_cliente" in df.columns:
        df["segmento_cliente"] = df["segmento_cliente"].map(LABEL_SEGMENTO).fillna(df["segmento_cliente"])
    if "classificacao_preco" in df.columns:
        df["classificacao_preco"] = df["classificacao_preco"].map(LABEL_CLASSIFICACAO).fillna(df["classificacao_preco"])
    return df

def renomear_colunas(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={c: LABEL_COLUNAS.get(c, c) for c in df.columns})

def kpi(col, label: str, value: str, delta: float = None, delta_label: str = "vs ano anterior"):
    if delta is not None:
        cor_delta  = "#16A34A" if delta >= 0 else "#DC2626"
        bg_delta   = "#F0FDF4" if delta >= 0 else "#FEF2F2"
        arrow      = "▲" if delta >= 0 else "▼"
        sign       = "+" if delta >= 0 else ""
        delta_html = (
            f'<span style="display:inline-flex;align-items:center;gap:4px;margin-top:8px;'
            f'background:{bg_delta};border-radius:4px;padding:2px 7px;">'
            f'<span style="color:{cor_delta};font-size:0.78rem;font-weight:600">'
            f'{arrow} {sign}{delta:.1f}%</span>'
            f'<span style="color:#9CA3AF;font-size:0.72rem">{delta_label}</span>'
            f'</span>'
        )
    else:
        delta_html = ""
    col.markdown(f"""
<div style="background:#F4F6F8;border:1.5px solid #D0D5DD;border-radius:8px;
padding:16px 18px 18px 18px;box-shadow:none">
  <span style="color:#667085;font-size:0.78rem;font-weight:400;font-family:Inter,sans-serif;
  display:block;margin-bottom:10px;line-height:1.2">{label}</span>
  <span style="color:#101828;font-size:2.25rem;font-weight:400;font-family:Inter,sans-serif;
  display:block;letter-spacing:-0.02em;line-height:1">{value}</span>
  {delta_html}
</div>""", unsafe_allow_html=True)

def render_tabela(df: pd.DataFrame, badges: dict, progress: dict) -> str:
    """Renderiza tabela HTML com pílulas coloridas e barras de progresso coloridas.
    badges:  {col: {val: (bg_hex, fg_hex)}}
    progress: {col: (max_val, format_str)}  ou  {col: (max_val, format_str, cor_ou_fn)}
              cor_ou_fn pode ser: str hex como "#7C3AED", ou callable(valor) -> str hex
    """
    ths = "".join(
        f'<th style="padding:10px 14px;text-align:left;font-size:0.82rem;font-weight:600;'
        f'color:#9CA3AF;background:#F8F9FB;border-bottom:1px solid #E5E7EB;'
        f'white-space:nowrap">{c}</th>'
        for c in df.columns
    )
    body = ""
    for _, row in df.iterrows():
        cells = ""
        for col in df.columns:
            v = row[col]
            s = "" if (isinstance(v, float) and pd.isna(v)) else v
            td = 'style="padding:8px 14px;border-bottom:1px solid #F3F4F6;vertical-align:middle"'
            if col in badges and str(s) in badges[col]:
                bg, fg = badges[col][str(s)]
                cells += (
                    f'<td {td}><span style="background:{bg};color:{fg};'
                    f'padding:3px 12px;border-radius:999px;font-size:0.81em;'
                    f'font-weight:600;white-space:nowrap;display:inline-block">{s}</span></td>'
                )
            elif col in progress:
                cfg = progress[col]
                mx, fmt = cfg[0], cfg[1]
                cor_cfg = cfg[2] if len(cfg) > 2 else "#7C3AED"
                pct = min((float(v) / mx * 100) if mx else 0, 100) if pd.notna(v) else 0
                fv = fmt.format(float(v)) if pd.notna(v) else "—"
                bar_color = cor_cfg(float(v)) if callable(cor_cfg) else cor_cfg
                cells += (
                    f'<td {td}><div style="display:flex;align-items:center;gap:8px">'
                    f'<div style="flex:1;min-width:60px;background:#E5E7EB;border-radius:4px;height:7px">'
                    f'<div style="width:{pct:.1f}%;background:{bar_color};border-radius:4px;height:7px"></div>'
                    f'</div><span style="white-space:nowrap;font-size:0.85em;color:#374151">{fv}</span>'
                    f'</div></td>'
                )
            else:
                ds = str(s) if s != "" else '<span style="color:#CBD5E1">—</span>'
                cells += f'<td {td}><span style="color:#374151;font-size:0.88em">{ds}</span></td>'
        body += (
            f'<tr style="cursor:default" '
            f'onmouseover="this.style.background=\'#EFF6FF\';this.style.borderLeft=\'3px solid #7C3AED\'" '
            f'onmouseout="this.style.background=\'\';this.style.borderLeft=\'3px solid transparent\'">'
            f'{cells}</tr>'
        )
    return (
        '<div style="overflow-x:auto;border:1px solid #E5E7EB;border-radius:10px;'
        'max-height:520px;overflow-y:auto">'
        '<table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif">'
        f'<thead><tr>{ths}</tr></thead><tbody>{body}</tbody></table></div>'
    )

LAYOUT = dict(
    template="simple_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=PRETO, size=13, family="Inter, sans-serif"),
    title_font=dict(color="#1E293B", size=15, family="Merriweather, Georgia, serif"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#374151", size=12)),
    margin=dict(t=52, b=40, l=54, r=20),
    height=460,
    xaxis=dict(linecolor="#CBD5E1", tickcolor="#CBD5E1", gridcolor="#E2E8F0", tickfont=dict(color=CINZA), showgrid=True, zeroline=False),
    yaxis=dict(linecolor="#CBD5E1", tickcolor="#CBD5E1", gridcolor="#E2E8F0", tickfont=dict(color=CINZA), showgrid=True, zeroline=False),
)

def apply_layout(fig, **kwargs):
    fig.update_layout(**LAYOUT, **kwargs)
    fig.update_traces(marker_cornerradius=6, selector=dict(type="bar"))
    return fig

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700;900&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; background-color: #F4F6F8; }}

    .stApp {{ background-color: #F4F6F8; color: {PRETO}; }}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{ background-color: #FFFFFF !important; }}
    section[data-testid="stSidebar"] > div {{ padding-top: 2rem !important; }}

    /* ── Centralização ── */
    .block-container {{
        max-width: 92% !important;
        padding: 2.5rem 2rem 4rem 2rem !important;
        margin: 0 auto !important;
    }}

    /* ── Tipografia ── */
    h1 {{
        font-family: 'Merriweather', Georgia, serif !important;
        font-size: 2.1rem !important;
        font-weight: 900 !important;
        color: {PRETO} !important;
        line-height: 1.25 !important;
        letter-spacing: -0.02em !important;
        border-bottom: 2px solid {VERDE} !important;
        padding-bottom: 10px !important;
        margin-bottom: 1.2rem !important;
    }}
    h2 {{
        font-family: 'Merriweather', Georgia, serif !important;
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        color: {PRETO} !important;
        line-height: 1.35 !important;
        margin-top: 2rem !important;
    }}
    h3 {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.70rem !important;
        font-weight: 700 !important;
        color: {VERDE_DARK} !important;
        text-transform: uppercase !important;
        letter-spacing: 0.12em !important;
    }}
    h5 {{
        font-family: 'Merriweather', Georgia, serif !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        color: #1E293B !important;
        margin-bottom: 0.75rem !important;
        margin-top: 1.5rem !important;
    }}
    p, li {{
        font-family: 'Inter', sans-serif !important;
        color: #374151 !important;
        line-height: 1.75 !important;
    }}

    /* ── Métricas — KPIs agora são HTML puro via kpi() ── */
    [data-testid="metric-container"] {{ display: none !important; }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        border-bottom: 2px solid {CINZA_MED} !important;
        background: transparent !important;
        margin-bottom: 2rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: 'Inter', sans-serif !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        color: {CINZA} !important;
        padding: 12px 28px !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -2px !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: {PRETO} !important;
        font-weight: 700 !important;
        border-bottom: 2px solid {VERDE} !important;
    }}

    /* ── Filtros / Selectbox ── */
    div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        border-color: {CINZA_MED} !important;
        border-radius: 6px !important;
        color: {PRETO} !important;
    }}
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input {{
        color: {PRETO} !important;
    }}
    div[data-baseweb="popover"] > div,
    div[data-baseweb="menu"] {{
        background-color: #FFFFFF !important;
        border: 1px solid {CINZA_MED} !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }}
    div[data-baseweb="option"] {{
        background-color: #FFFFFF !important;
        color: {PRETO} !important;
    }}
    div[data-baseweb="option"]:hover,
    div[data-baseweb="option"][aria-selected="true"] {{
        background-color: #F0FDF4 !important;
        color: {VERDE_DARK} !important;
    }}
    div[data-baseweb="tag"] {{
        background-color: #C4B5FD !important;
        border: 1px solid #A78BFA !important;
        border-radius: 4px !important;
    }}
    div[data-baseweb="tag"] span {{ color: #5B21B6 !important; }}
    div[data-baseweb="tag"] button {{ color: #7C3AED !important; }}

    /* ── Expander — sem caixa, funde com o fundo ── */
    details summary {{
        color: {CINZA} !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }}
    details {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }}
    [data-testid="stExpander"] {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    [data-testid="stExpander"] > div,
    details, details > div, details > summary {{
        background-color: transparent !important;
        border: none !important;
    }}

    /* ── Plotly charts — sem caixa, funde com o fundo ── */
    .stPlotlyChart > div,
    .stPlotlyChart iframe {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}

    /* ── Misc ── */
    .stDataFrame {{ border: 1px solid {CINZA_MED} !important; border-radius: 8px !important; }}
    hr {{ border: none !important; border-top: 1px solid {CINZA_MED} !important; }}
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

# ── Header global na sidebar ───────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"""
<div style="padding-bottom:1.2rem;margin-bottom:0.5rem;border-bottom:2px solid {VERDE}">
  <span style="font-size:0.82rem;font-weight:700;text-transform:uppercase;
               letter-spacing:0.12em;color:{VERDE_DARK}">E-commerce Analytics</span>
  <div style="font-size:1.25rem;font-weight:800;color:{PRETO};margin-top:4px;
              font-family:'Merriweather',Georgia,serif;line-height:1.2">Relatório Analítico</div>
  <p style="color:{CINZA};margin:6px 0 0 0;font-size:0.78rem;line-height:1.5">
    Visão estratégica de vendas, clientes e pricing — dbt + Supabase.
  </p>
</div>
""", unsafe_allow_html=True)


# ── Página: Vendas ─────────────────────────────────────────────────────────────

def _delta(atual, anterior):
    """Retorna variação percentual ou None se anterior == 0."""
    if anterior and anterior != 0:
        return (atual - anterior) / abs(anterior) * 100
    return None

def pagina_vendas():
    st.title("Vendas — Diretor Comercial")

    df_all = get_data("SELECT * FROM public_gold_sales.vendas_temporais")
    df_all["data_venda"] = pd.to_datetime(df_all["data_venda"])

    # ── Filtros
    with st.sidebar:
        st.markdown("### 🛒 Filtros — Vendas")
        anos   = sorted(df_all["ano_venda"].dropna().unique().astype(int))
        meses  = sorted(df_all["mes_venda"].dropna().unique().astype(int))
        dias   = ORDEM_SEMANA

        ano_sel  = st.selectbox("Ano", ["Todos"] + anos)
        mes_sel  = st.selectbox("Mês", ["Todos"] + meses)
        dia_sel  = st.multiselect("Dia da Semana", dias)

    # ── Período atual
    df = df_all.copy()
    if ano_sel != "Todos":
        df = df[df["ano_venda"] == ano_sel]
    if mes_sel != "Todos":
        df = df[df["mes_venda"] == mes_sel]
    if dia_sel:
        df = df[df["dia_semana_nome"].isin(dia_sel)]

    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # ── Período anterior (YoY)
    ano_atual = int(ano_sel) if ano_sel != "Todos" else int(df_all["ano_venda"].max())
    ano_ant   = ano_atual - 1
    df_prev   = df_all[df_all["ano_venda"] == ano_ant]
    if mes_sel != "Todos":
        df_prev = df_prev[df_prev["mes_venda"] == mes_sel]
    if dia_sel:
        df_prev = df_prev[df_prev["dia_semana_nome"].isin(dia_sel)]

    prev_receita  = df_prev["receita_total"].sum()
    prev_vendas   = df_prev["total_vendas"].sum()
    prev_ticket   = prev_receita / prev_vendas if prev_vendas > 0 else 0
    prev_clientes = df_prev.groupby("data_venda")["total_clientes_unicos"].max().sum() if not df_prev.empty else 0
    prev_qtd      = df_prev["quantidade_total"].sum()

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
    kpi(c1, "💵 Receita Total",      fmt_brl(receita_total),  _delta(receita_total, prev_receita))
    kpi(c2, "🛒 Total de Vendas",    fmt_num(total_vendas),   _delta(total_vendas, prev_vendas))
    kpi(c3, "🎯 Ticket Médio",       fmt_brl(ticket_medio),   _delta(ticket_medio, prev_ticket))
    kpi(c4, "👤 Clientes Únicos",    fmt_num(clientes_unicos), _delta(clientes_unicos, prev_clientes))

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    kpi(c5, "📦 Itens Vendidos",     fmt_num(qtd_total), _delta(qtd_total, prev_qtd))
    kpi(c6, "⚡ Receita Hora Pico",  fmt_brl(receita_hora_pico))
    kpi(c7, "🕐 Hora de Pico",       f"{hora_pico}h")
    kpi(c8, "📅 Dias com Vendas",    fmt_num(dias_ativos))

    # ── Análise abaixo dos KPIs
    receita_dia_medio = receita_total / dias_ativos if dias_ativos > 0 else 0
    st.markdown(f"""
<p style="color:{CINZA}; font-size:0.92rem; line-height:1.7; margin:16px 0 24px 0;
   border-left:3px solid {CINZA_MED}; padding-left:14px;">
  No período selecionado, o negócio gerou <strong style="color:{PRETO};">{fmt_brl(receita_total)}</strong>
  em <strong style="color:{PRETO};">{fmt_num(total_vendas)}</strong> transações,
  com média de <strong style="color:{VERDE_DARK};">{fmt_brl(receita_dia_medio)}/dia</strong>.
  O pico de faturamento ocorre às <strong style="color:{PRETO};">{hora_pico}h</strong> —
  janela prioritária para campanhas e promoções relâmpago.
</p>
""", unsafe_allow_html=True)

    st.divider()

    # Gráfico 1 — Receita Diária
    df_dia = df.groupby("data_venda")["receita_total"].sum().reset_index()
    fig1 = px.area(df_dia, x="data_venda", y="receita_total", title="Receita Diária",
                   labels={"data_venda": "Data", "receita_total": "Receita (R$)"})
    fig1.update_traces(line=dict(color=VERDE, width=2), fillcolor="rgba(124,58,237,0.10)")
    apply_layout(fig1)
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("Picos indicam campanhas ou datas comemorativas. Quedas prolongadas merecem investigação de causa.")

    col1, col2 = st.columns(2)

    # Gráfico 2 — Receita por Dia da Semana
    dia_pico = df_semana = df.groupby("dia_semana_nome")["receita_total"].sum()
    df_semana = dia_pico.reset_index()
    df_semana["dia_semana_nome"] = pd.Categorical(df_semana["dia_semana_nome"], categories=ORDEM_SEMANA, ordered=True)
    df_semana = df_semana.sort_values("dia_semana_nome")
    dia_maior = df_semana.loc[df_semana["receita_total"].idxmax(), "dia_semana_nome"]
    fig2 = px.bar(df_semana, x="dia_semana_nome", y="receita_total", title="Receita por Dia da Semana",
                  labels={"dia_semana_nome": "Dia", "receita_total": "Receita (R$)"},
                  color="receita_total", color_continuous_scale=[[0, "#8B5CF6"], [1, "#3B0764"]])
    apply_layout(fig2, coloraxis_showscale=False)
    col1.plotly_chart(fig2, use_container_width=True)
    col1.caption(f"**{dia_maior}** é o dia de maior faturamento. Concentre budget de mídia nesse dia.")

    # Gráfico 3 — Volume por Hora
    df_hora = df.groupby("hora_venda")["total_vendas"].sum().reset_index()
    fig3 = px.bar(df_hora, x="hora_venda", y="total_vendas", title="Volume de Vendas por Hora",
                  labels={"hora_venda": "Hora", "total_vendas": "Vendas"},
                  color="total_vendas", color_continuous_scale=[[0, "#8B5CF6"], [1, "#3B0764"]])
    apply_layout(fig3, coloraxis_showscale=False)
    col2.plotly_chart(fig3, use_container_width=True)
    col2.caption(f"Horário de pico: **{hora_pico}h**. Envio de push/e-mail próximo a esse horário tende a converter melhor.")

    # Gráfico 4 — Receita Mensal
    df_mes = df.groupby(["ano_venda", "mes_venda"])["receita_total"].sum().reset_index()
    df_mes["periodo"] = df_mes["ano_venda"].astype(int).astype(str) + "-" + df_mes["mes_venda"].astype(int).astype(str).str.zfill(2)
    df_mes = df_mes.sort_values(["ano_venda", "mes_venda"])
    fig4 = px.bar(df_mes, x="periodo", y="receita_total", title="Receita por Mês",
                  labels={"periodo": "Mês", "receita_total": "Receita (R$)"},
                  color="receita_total", color_continuous_scale=[[0, "#8B5CF6"], [1, "#3B0764"]])
    apply_layout(fig4, coloraxis_showscale=False)
    st.plotly_chart(fig4, use_container_width=True)
    mes_top = df_mes.loc[df_mes["receita_total"].idxmax(), "periodo"]
    st.caption(f"Mês de maior receita: **{mes_top}**. Compare períodos equivalentes para identificar crescimento real.")

    # ── Editorial de Pricing
    st.divider()

    df_p = aplicar_labels(get_data("SELECT * FROM public_gold.precos_competitividade"))

    total_prod      = len(df_p)
    mais_caros      = len(df_p[df_p["classificacao_preco"] == "Mais Caro que Todos"])
    acima_media     = len(df_p[df_p["classificacao_preco"] == "Acima da Média"])
    abaixo_media    = len(df_p[df_p["classificacao_preco"].isin(["Abaixo da Média", "Mais Barato que Todos"])])
    dif_media       = df_p["diferenca_percentual_vs_media"].mean()
    receita_total_p = df_p["receita_total"].sum()
    receita_risco   = df_p[df_p["classificacao_preco"].isin(["Mais Caro que Todos", "Acima da Média"])]["receita_total"].sum()
    pct_risco       = (receita_risco / receita_total_p * 100) if receita_total_p > 0 else 0
    cat_mais_cara   = (df_p[df_p["classificacao_preco"] == "Mais Caro que Todos"]
                       .groupby("categoria")["receita_total"].sum()
                       .idxmax() if mais_caros > 0 else "N/A")
    pct_competitivo = (abaixo_media / total_prod * 100) if total_prod > 0 else 0

    sinal_dif = "acima" if dif_media > 0 else "abaixo"
    alerta_cor = "#FF4D4D" if pct_risco > 40 else "#FFA500" if pct_risco > 20 else VERDE

    st.markdown(f"""
<div style="border-left:3px solid {VERDE}; padding:0 0 0 28px; margin-top:2.5rem; margin-bottom:1rem;">
  <p style="font-size:0.70rem; font-weight:700; text-transform:uppercase; letter-spacing:0.12em;
            color:{VERDE_DARK}; margin:0 0 6px 0;">Análise — Inteligência de Preços</p>
  <h2 style="font-size:1.4rem; font-weight:700; color:{PRETO}; margin:0 0 18px 0; line-height:1.3;
             font-family:'Merriweather',Georgia,serif;">
    Precificação: onde estamos e o que está em risco
  </h2>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:14px;">
    O monitoramento cobre <strong style="color:{PRETO};">{fmt_num(total_prod)} produtos</strong> comparados
    diariamente com Mercado Livre, Amazon, Shopee e Magalu. Em média, nossos preços estão
    <strong style="color:{PRETO};">{abs(dif_media):.1f}% {sinal_dif}</strong> da média de mercado —
    um sinal de que a política de preços está {'desalinhada com a concorrência' if dif_media > 5 else 'razoavelmente calibrada'}.
  </p>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:14px;">
    O ponto crítico: <strong style="color:{alerta_cor};">{fmt_num(mais_caros)} produtos estão acima do preço
    máximo de todos os concorrentes</strong>. Somados aos {fmt_num(acima_media)} produtos acima da média,
    a receita exposta a risco competitivo chega a <strong style="color:{alerta_cor};">{fmt_brl(receita_risco)}</strong> —
    equivalente a <strong style="color:{alerta_cor};">{pct_risco:.1f}%</strong> da receita total do catálogo.
    A categoria <em>{cat_mais_cara}</em> concentra o maior volume de receita nessa situação.
  </p>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:0;">
    Por outro lado, <strong style="color:{VERDE_DARK};">{fmt_num(abaixo_media)} produtos
    ({pct_competitivo:.0f}% do catálogo)</strong> já estão posicionados abaixo da média ou como os mais
    baratos do mercado — vantagem que pode ser comunicada ativamente em campanhas de aquisição.
    A alavanca imediata está no repricing dos {fmt_num(mais_caros)} produtos em alerta,
    disponível em detalhes na aba <strong style="color:{VERDE_DARK};">💰 Pricing</strong>.
  </p>
</div>
""", unsafe_allow_html=True)


# ── Página: Clientes ───────────────────────────────────────────────────────────

def pagina_clientes():
    st.title("Clientes — Diretora de Customer Success")

    df = aplicar_labels(get_data("SELECT * FROM public_gold.clientes_segmentacao"))

    # ── Filtros
    with st.sidebar:
        st.markdown("### 👥 Filtros — Clientes")
        estados   = sorted(df["estado"].dropna().unique())
        segmentos = ["VIP", "Top Tier", "Regular"]

        seg_sel    = st.multiselect("Segmento", segmentos)
        estado_sel = st.multiselect("Estado", estados)
        top_n      = st.selectbox("Top N Clientes", [10, 20, 50])

    if seg_sel:
        df = df[df["segmento_cliente"].isin(seg_sel)]
    if estado_sel:
        df = df[df["estado"].isin(estado_sel)]

    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # ── KPIs
    total_clientes  = len(df)
    clientes_vip    = len(df[df["segmento_cliente"] == "VIP"])
    clientes_top    = len(df[df["segmento_cliente"] == "Top Tier"])
    receita_vip     = df[df["segmento_cliente"] == "VIP"]["receita_total"].sum()
    receita_total   = df["receita_total"].sum()
    pct_vip_receita = (receita_vip / receita_total * 100) if receita_total > 0 else 0
    ticket_medio    = df["ticket_medio"].mean()
    estados_ativos  = df["estado"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "👥 Total Clientes",    fmt_num(total_clientes))
    kpi(c2, "⭐ Clientes VIP",      fmt_num(clientes_vip))
    kpi(c3, "🥈 Top Tier",          fmt_num(clientes_top))
    kpi(c4, "💵 Receita Total",     fmt_brl(receita_total))

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    kpi(c5, "💰 Receita VIP",       fmt_brl(receita_vip))
    kpi(c6, "📊 % Receita VIP",     fmt_pct(pct_vip_receita))
    kpi(c7, "🎯 Ticket Médio",      fmt_brl(ticket_medio))
    kpi(c8, "🗺️ Estados Ativos",    fmt_num(estados_ativos))

    st.divider()

    col1, col2 = st.columns(2)

    # Gráfico 1 — Pizza Segmento
    df_seg = df.groupby("segmento_cliente").size().reset_index(name="total")
    fig1 = px.pie(df_seg, names="segmento_cliente", values="total",
                  title="Distribuição por Segmento", hole=0.45,
                  color="segmento_cliente", color_discrete_map=CORES_SEGMENTO,
                  labels={"segmento_cliente": "Segmento"},
                  category_orders={"segmento_cliente": ["VIP", "Top Tier", "Regular"]})
    fig1.update_traces(textinfo="percent+label", textfont_color=PRETO)
    apply_layout(fig1)
    col1.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2 — Receita por Segmento
    df_rec = df.groupby("segmento_cliente")["receita_total"].sum().reset_index()
    fig2 = px.bar(df_rec, x="segmento_cliente", y="receita_total", title="Receita por Segmento",
                  labels={"segmento_cliente": "Segmento", "receita_total": "Receita (R$)"},
                  color="segmento_cliente", color_discrete_map=CORES_SEGMENTO,
                  category_orders={"segmento_cliente": ["VIP", "Top Tier", "Regular"]})
    apply_layout(fig2)
    col2.plotly_chart(fig2, use_container_width=True)

    col3, col4 = st.columns(2)

    # Gráfico 3 — Top N Clientes
    df_top = df.nsmallest(top_n, "ranking_receita").sort_values("receita_total", ascending=True)
    fig3 = px.bar(df_top, x="receita_total", y="nome_cliente", orientation="h",
                  title=f"Top {top_n} Clientes por Receita",
                  labels={"receita_total": "Receita (R$)", "nome_cliente": ""},
                  color="receita_total",
                  color_continuous_scale=[[0, "#8B5CF6"], [1, "#3B0764"]])
    apply_layout(fig3, coloraxis_showscale=False)
    col3.plotly_chart(fig3, use_container_width=True)

    # Gráfico 4 — Clientes por Estado
    df_estado = df.groupby("estado").agg(total=("cliente_id","count"), receita=("receita_total","sum")).reset_index()
    df_estado = df_estado.sort_values("receita", ascending=False).head(15)
    fig4 = px.bar(df_estado, x="estado", y="receita", title="Receita por Estado (Top 15)",
                  labels={"estado": "Estado", "receita": "Receita (R$)"},
                  color="receita",
                  color_continuous_scale=[[0, "#8B5CF6"], [1, "#3B0764"]])
    apply_layout(fig4, showlegend=False, coloraxis_showscale=False)
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
    apply_layout(fig5)
    st.plotly_chart(fig5, use_container_width=True)

    st.divider()

    # Tabela Detalhada
    st.markdown("##### 📋 Tabela de Clientes")
    df_sorted = df.sort_values("ranking_receita")
    df_display = renomear_colunas(df_sorted)

    st.markdown(render_tabela(
        df_display,
        badges={
            "Segmento": {
                "VIP":      ("#DCFCE7", "#166534"),
                "Top Tier": ("#FEF3C7", "#92400E"),
                "Regular":  ("#FEE2E2", "#991B1B"),
            }
        },
        progress={
            "Receita Total (R$)": (float(df_sorted["receita_total"].max()), "R$ {:.0f}", "#7C3AED"),
            "Nº Compras":         (float(df_sorted["total_compras"].max()),  "{:.0f}",   "#60A5FA"),
            "Ticket Médio (R$)":  (float(df_sorted["ticket_medio"].max()),   "R$ {:.0f}","#A78BFA"),
        },
    ), unsafe_allow_html=True)

    # ── Editorial de Clientes
    st.divider()

    df_full = aplicar_labels(get_data("SELECT * FROM public_gold.clientes_segmentacao"))
    total_full      = len(df_full)
    vip_full        = len(df_full[df_full["segmento_cliente"] == "VIP"])
    top_full        = len(df_full[df_full["segmento_cliente"] == "Top Tier"])
    reg_full        = len(df_full[df_full["segmento_cliente"] == "Regular"])
    rec_vip         = df_full[df_full["segmento_cliente"] == "VIP"]["receita_total"].sum()
    rec_total_f     = df_full["receita_total"].sum()
    pct_vip_f       = (rec_vip / rec_total_f * 100) if rec_total_f > 0 else 0
    ticket_vip      = df_full[df_full["segmento_cliente"] == "VIP"]["ticket_medio"].mean()
    ticket_reg      = df_full[df_full["segmento_cliente"] == "Regular"]["ticket_medio"].mean()
    compras_vip     = df_full[df_full["segmento_cliente"] == "VIP"]["total_compras"].mean()
    compras_reg     = df_full[df_full["segmento_cliente"] == "Regular"]["total_compras"].mean()
    estado_top      = df_full.groupby("estado")["receita_total"].sum().idxmax()
    multiplo_ticket = (ticket_vip / ticket_reg) if ticket_reg > 0 else 1

    st.markdown(f"""
<div style="border-left:3px solid {VERDE}; padding:0 0 0 28px; margin-top:2.5rem; margin-bottom:1rem;">
  <p style="font-size:0.70rem; font-weight:700; text-transform:uppercase; letter-spacing:0.12em;
            color:{VERDE_DARK}; margin:0 0 6px 0;">Análise — Base de Clientes</p>
  <h2 style="font-size:1.4rem; font-weight:700; color:{PRETO}; margin:0 0 18px 0; line-height:1.3;
             font-family:'Merriweather',Georgia,serif;">
    Quem são nossos clientes e quanto vale cada segmento
  </h2>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:14px;">
    A base conta com <strong style="color:{PRETO};">{fmt_num(total_full)} clientes ativos</strong>, segmentados
    por receita acumulada em três tiers. Os <strong style="color:{PRETO};">{fmt_num(vip_full)} clientes VIP</strong>
    — apenas {vip_full/total_full*100:.0f}% da base — respondem por
    <strong style="color:{VERDE_DARK};">{pct_vip_f:.0f}% de toda a receita</strong>.
    É uma concentração clássica: poucos clientes sustentam a maior parte do negócio.
  </p>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:14px;">
    O ticket médio VIP é <strong style="color:{PRETO};">{fmt_brl(ticket_vip)}</strong>, contra
    <strong style="color:{PRETO};">{fmt_brl(ticket_reg)}</strong> dos clientes Regular —
    uma diferença de <strong style="color:{VERDE_DARK};">{multiplo_ticket:.1f}x</strong>.
    Além do ticket, clientes VIP compram em média <strong style="color:{PRETO};">{compras_vip:.0f} vezes</strong>,
    enquanto clientes Regular realizam <strong style="color:{PRETO};">{compras_reg:.0f} compras</strong>.
    A combinação de frequência e valor unitário é o que define o topo da pirâmide.
  </p>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:0;">
    Os {fmt_num(reg_full)} clientes Regular representam {reg_full/total_full*100:.0f}% da base e são o maior
    potencial de crescimento: uma estratégia de up-sell bem executada que converta 10% deles para Top Tier
    pode elevar significativamente a receita sem custo de aquisição. O estado
    <strong style="color:{VERDE_DARK};">{estado_top}</strong> lidera em receita e merece atenção
    prioritária em campanhas de retenção de VIPs.
  </p>
</div>
""", unsafe_allow_html=True)


# ── Página: Pricing ────────────────────────────────────────────────────────────

def pagina_pricing():
    st.title("Pricing — Diretor de Pricing")

    df = aplicar_labels(get_data("SELECT * FROM public_gold.precos_competitividade"))

    # ── Filtros
    with st.sidebar:
        st.markdown("### 💰 Filtros — Pricing")
        categorias  = sorted(df["categoria"].unique())
        marcas      = sorted(df["marca"].unique())
        classifs    = sorted(df["classificacao_preco"].unique())

        cat_sel     = st.multiselect("Categoria", categorias)
        marca_sel   = st.multiselect("Marca", marcas)
        class_sel   = st.multiselect("Classificação", classifs)

    if cat_sel:
        df = df[df["categoria"].isin(cat_sel)]
    if marca_sel:
        df = df[df["marca"].isin(marca_sel)]
    if class_sel:
        df = df[df["classificacao_preco"].isin(class_sel)]

    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        return

    # ── KPIs
    total_produtos  = len(df)
    mais_caros      = len(df[df["classificacao_preco"] == "Mais Caro que Todos"])
    mais_baratos    = len(df[df["classificacao_preco"] == "Mais Barato que Todos"])
    acima_media     = len(df[df["classificacao_preco"] == "Acima da Média"])
    dif_media       = df["diferenca_percentual_vs_media"].mean()
    receita_risco   = df[df["classificacao_preco"].isin(["Mais Caro que Todos","Acima da Média"])]["receita_total"].sum()
    receita_total   = df["receita_total"].sum()
    pct_risco       = (receita_risco / receita_total * 100) if receita_total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "📦 Produtos Monitorados", fmt_num(total_produtos))
    kpi(c2, "🔴 Mais Caros que Todos", fmt_num(mais_caros))
    kpi(c3, "🟢 Mais Baratos que Todos", fmt_num(mais_baratos))
    kpi(c4, "📈 Acima da Média",       fmt_num(acima_media))

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    kpi(c5, "📊 Dif. Média vs Mercado", fmt_pct(dif_media))
    kpi(c6, "💵 Receita Total",         fmt_brl(receita_total))
    kpi(c7, "⚠️ Receita em Risco",      fmt_brl(receita_risco))
    kpi(c8, "🎯 % Receita em Risco",    fmt_pct(pct_risco))

    # ── Editorial de Pricing
    sinal_p   = "acima" if dif_media > 0 else "abaixo"
    alerta_p  = "#DC2626" if pct_risco > 40 else "#D97706" if pct_risco > 20 else VERDE_DARK
    cat_risco = (df[df["classificacao_preco"] == "Mais Caro que Todos"]
                 .groupby("categoria")["receita_total"].sum().idxmax() if mais_caros > 0 else "N/A")

    st.markdown(f"""
<div style="border-left:3px solid {VERDE}; padding:0 0 0 28px; margin:2rem 0 2.5rem 0;">
  <p style="font-size:0.70rem; font-weight:700; text-transform:uppercase; letter-spacing:0.12em;
            color:{VERDE_DARK}; margin:0 0 6px 0;">Análise — Posicionamento Competitivo</p>
  <h2 style="font-size:1.4rem; font-weight:700; color:{PRETO}; margin:0 0 18px 0; line-height:1.3;
             font-family:'Merriweather',Georgia,serif;">
    Como nossos preços se comparam ao mercado
  </h2>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:14px;">
    Com <strong style="color:{PRETO};">{fmt_num(total_produtos)} produtos</strong> monitorados, o catálogo está
    em média <strong style="color:{PRETO};">{abs(dif_media):.1f}% {sinal_p}</strong> da média praticada por
    Mercado Livre, Amazon, Shopee e Magalu. Dos {fmt_num(total_produtos)} itens,
    <strong style="color:{alerta_p};">{fmt_num(mais_caros)} ({mais_caros/total_produtos*100:.0f}%) estão acima
    de todos os concorrentes</strong> simultaneamente — o cenário de maior risco de perda de conversão.
  </p>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:14px;">
    A receita concentrada nesses produtos em risco soma <strong style="color:{alerta_p};">{fmt_brl(receita_risco)}</strong>,
    o equivalente a {pct_risco:.0f}% do faturamento total do catálogo. A categoria
    <strong style="color:{PRETO};">{cat_risco}</strong> acumula a maior exposição.
    Não se trata de ajuste uniforme: cada produto exige análise de margem antes de qualquer repricing.
  </p>
  <p style="color:#374151; font-size:1.0rem; line-height:1.85; margin-bottom:0;">
    Os <strong style="color:{VERDE_DARK};">{fmt_num(mais_baratos)} produtos mais baratos que todos</strong>
    ({mais_baratos/total_produtos*100:.0f}% do catálogo) são um ativo subutilizado:
    posicionamento de preço competitivo raramente é comunicado nas páginas de produto.
    Destacar esse diferencial pode aumentar taxa de conversão sem alterar preços.
    Use os filtros abaixo para explorar categorias e marcas específicas.
  </p>
</div>
""", unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns(2)

    # Gráfico 1 — Pizza classificação
    df_class = df.groupby("classificacao_preco").size().reset_index(name="total")
    fig1 = px.pie(df_class, names="classificacao_preco", values="total", hole=0.4,
                  title="Posicionamento vs Concorrência",
                  color="classificacao_preco", color_discrete_map=CORES_CLASSIFICACAO)
    fig1.update_traces(textinfo="percent+label", textfont_color=PRETO)
    apply_layout(fig1)
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
    apply_layout(fig2)
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
    apply_layout(fig3)
    st.plotly_chart(fig3, use_container_width=True)

    # Gráfico 4 — Receita por Classificação
    df_rec_class = df.groupby("classificacao_preco")["receita_total"].sum().reset_index().sort_values("receita_total", ascending=False)
    fig4 = px.bar(df_rec_class, x="receita_total", y="classificacao_preco", orientation="h",
                  title="Receita por Classificação de Preço",
                  labels={"receita_total": "Receita (R$)", "classificacao_preco": ""},
                  color="classificacao_preco", color_discrete_map=CORES_CLASSIFICACAO)
    apply_layout(fig4)
    st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # Tabela de Alertas
    st.markdown("##### ⚠️ Produtos em Alerta — Mais caros que todos os concorrentes")
    df_alerta = df[df["classificacao_preco"] == "Mais Caro que Todos"][
        ["produto_id", "nome_produto", "categoria", "marca", "nosso_preco",
         "preco_maximo_concorrentes", "diferenca_percentual_vs_media", "receita_total"]
    ].sort_values("diferenca_percentual_vs_media", ascending=False)
    _PALETA_CAT = [
        ("#FEF3C7", "#92400E"), ("#EDE9FE", "#5B21B6"), ("#FCE7F3", "#9D174D"),
        ("#DBEAFE", "#1E40AF"), ("#D1FAE5", "#3B0764"), ("#FEE2E2", "#991B1B"),
        ("#E0F2FE", "#075985"), ("#F3E8FF", "#6B21A8"),
    ]
    _cats = sorted(df_alerta["categoria"].unique())
    _cat_badge_map = {c: _PALETA_CAT[i % len(_PALETA_CAT)] for i, c in enumerate(_cats)}

    df_alerta_display = renomear_colunas(df_alerta)
    st.markdown(render_tabela(
        df_alerta_display,
        badges={"Categoria": _cat_badge_map},
        progress={
            "Nosso Preço (R$)":      (float(df_alerta["nosso_preco"].max()),               "R$ {:.2f}", "#FB923C"),
            "Preço Máx. Conc. (R$)": (float(df_alerta["preco_maximo_concorrentes"].max()), "R$ {:.2f}", "#60A5FA"),
            "Dif. % vs Média":       (float(df_alerta["diferenca_percentual_vs_media"].max()), "{:.1f}%", "#F87171"),
            "Receita Total (R$)":    (float(df_alerta["receita_total"].max()),              "R$ {:.0f}", "#7C3AED"),
        },
    ), unsafe_allow_html=True)


# ── Navegação por tabs ────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["🛒 Vendas", "👥 Clientes", "💰 Pricing"])

with tab1:
    pagina_vendas()
with tab2:
    pagina_clientes()
with tab3:
    pagina_pricing()
