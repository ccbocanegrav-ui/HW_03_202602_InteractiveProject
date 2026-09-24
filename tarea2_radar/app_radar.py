"""
app_radar.py — Task 2, Phase 4: dashboard Streamlit

ARQUITECTURA: solo llama a radar_engine.answer_question() para la
parte de preguntas — nunca logica de RAG directa. Lee archivos ya
precomputados (oece_clean.csv, risk_*.csv, data_quality_report.json)
— nunca descarga datos ni reconstruye el indice al iniciar.

DECISION DE "MAPA": por restriccion de tiempo, la vista geografica usa
un grafico de barras por departamento en vez de un choropleth real
(que necesita un archivo de poligonos/GeoJSON de los departamentos del
Peru). Si ya tienes ese GeoJSON de un proyecto anterior (ej. el
proyecto de accesibilidad geoespacial "Golden Hour"), se puede
reemplazar facilmente por plotly.express.choropleth — ver comentario
en choropleth_placeholder() mas abajo.

Uso:
    streamlit run app_radar.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from radar_engine import answer_question, load_config  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUTS_DIR = BASE_DIR / "data" / "outputs"
LOGS_DIR = BASE_DIR / "logs"

st.set_page_config(page_title="RAG Radar — Contrataciones Públicas", page_icon="📡", layout="wide")

st.session_state.setdefault("theme", "Oscuro")


def theme_css(bg, bg2, text, text2, border, accent):
    return f"""
    <style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background-color: {bg} !important; color: {text} !important; }}
    [data-testid="stSidebar"] {{ background-color: {bg2} !important; }}
    [data-testid="stSidebar"] * {{ color: {text} !important; }}
    h1,h2,h3,h4,h5,h6,p,li,span,label,[data-testid="stMarkdownContainer"],[data-testid="stMarkdownContainer"] * {{ color: {text} !important; }}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{ color: {text2} !important; }}
    [data-testid="stTextInput"] input {{ background-color: {bg2} !important; color: {text} !important; border: 1px solid {border} !important; }}
    .stButton button, .stButton button *, .stButton button:hover, .stButton button:hover *,
    .stButton button:focus, .stButton button:focus-visible, .stButton button:active {{
        background-color: {bg2} !important; color: {text} !important; border: none !important; outline: none !important; box-shadow: none !important;
    }}
    .stButton button:hover {{ background-color: {accent} !important; }}
    [data-testid="stExpander"] {{ background-color: {bg2} !important; border: 1px solid {border} !important; }}
    [data-testid="stMetric"] {{ background-color: {bg2} !important; border-radius: 8px; padding: 10px; }}
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{ color: {text} !important; }}
    [data-testid="stAlert"], [data-testid="stAlert"] * {{ color: {text} !important; }}
    hr {{ border-color: {border} !important; }}
    </style>
    """


DARK_CSS = theme_css("#0e1117", "#1c2030", "#fafafa", "#b0b4c0", "#3d4560", "#3d4560")
LIGHT_CSS = theme_css("#ffffff", "#f0f2f6", "#1a1a1a", "#5a5f6b", "#d0d4de", "#e0e3ec")


@st.cache_data
def load_clean_data():
    path = PROCESSED_DIR / "oece_clean.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, low_memory=False)


@st.cache_data
def load_csv(path: Path):
    if not path.exists():
        return None
    return pd.read_csv(path)


@st.cache_data
def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


config = load_config()
df = load_clean_data()

st.markdown(DARK_CSS if st.session_state["theme"] == "Oscuro" else LIGHT_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuración")
    st.radio("Tema", ["Oscuro", "Claro"], key="theme", horizontal=True)
    st.divider()

    st.header("🔎 Filtros")
    if df is not None:
        departments = sorted(df["department_normalizado"].dropna().unique().tolist())
        categories = sorted(df["category"].dropna().unique().tolist()) if "category" in df.columns else []

        sel_department = st.selectbox("Departamento", ["(todos)"] + departments)
        sel_category = st.selectbox("Categoría", ["(todas)"] + categories) if categories else None
        amount_min, amount_max = float(df["amount"].min()), float(df["amount"].max())
        sel_amount = st.slider("Rango de monto (S/)", amount_min, amount_max, (amount_min, amount_max))
        sel_threshold = st.slider("Umbral de similitud (búsqueda)", 0.0, 1.0,
                                   float(config["retrieval"]["similarity_threshold"]), 0.05)
    else:
        st.warning("No hay datos cargados todavía. Corre load_data.py → validate.py primero.")
        sel_department, sel_category, sel_amount, sel_threshold = None, None, (0, 0), 0.7

st.title("📡 RAG Radar — ¿Qué compra el Estado y dónde?")
st.caption("Explora procesos de contratación pública del Perú combinando filtros estructurados y búsqueda semántica.")

if df is None:
    st.error("No se encontró `data/processed/oece_clean.csv`. Corre `python src/load_data.py` y "
             "`python src/validate.py` primero (con tus archivos de OECE en `data/raw/`).")
    st.stop()

# ---------- Aplicar filtros a la vista (no al indice) ----------
df_filtered = df.copy()
if sel_department and sel_department != "(todos)":
    df_filtered = df_filtered[df_filtered["department_normalizado"] == sel_department]
if sel_category and sel_category != "(todas)":
    df_filtered = df_filtered[df_filtered["category"] == sel_category]
df_filtered = df_filtered[(df_filtered["amount"] >= sel_amount[0]) & (df_filtered["amount"] <= sel_amount[1])]

# ---------- KPIs ----------
risk_summary = load_json(LOGS_DIR / "risk_summary.json")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Procesos", f"{len(df_filtered):,}")
col2.metric("Monto total", f"S/ {df_filtered['amount'].sum():,.0f}")
col3.metric("Departamentos", df_filtered["department_normalizado"].nunique())
col4.metric("% single-bidder (global)",
            f"{risk_summary['pct_single_bidder_global']}%" if risk_summary else "—")

st.divider()

# ---------- "Mapa" (bar chart por departamento — ver nota arriba) ----------
st.subheader("📍 Procesos por departamento")


def choropleth_placeholder(df_filtered: pd.DataFrame):
    """Sustituto de un choropleth real. Para un mapa geografico de
    verdad: import plotly.express as px, cargar un GeoJSON de
    departamentos del Peru, y usar px.choropleth_mapbox(...)."""
    by_dept = df_filtered.groupby("department_normalizado").agg(
        procesos=("ocid", "count"), monto=("amount", "sum"),
    ).reset_index().sort_values("procesos", ascending=False)
    st.bar_chart(by_dept.set_index("department_normalizado")["procesos"])
    return by_dept


by_dept_table = choropleth_placeholder(df_filtered)

st.divider()

# ---------- Búsqueda RAG híbrida ----------
st.subheader("💬 Pregunta sobre estos procesos")
question = st.text_input("Ej: obras de agua potable, servicios de limpieza...")
if st.button("Buscar", type="primary") and question.strip():
    filters = {}
    if sel_department and sel_department != "(todos)":
        filters["department"] = sel_department
    if sel_category and sel_category != "(todas)":
        filters["category"] = sel_category
    filters["min_amount"] = sel_amount[0]
    filters["max_amount"] = sel_amount[1]

    cfg = dict(config)
    cfg["retrieval"] = dict(config["retrieval"])
    cfg["retrieval"]["similarity_threshold"] = sel_threshold

    with st.spinner("Buscando..."):
        result = answer_question(question, cfg, filters=filters)

    if result["error"]:
        st.error(result["error"])
    elif result["abstained"]:
        st.warning(result["answer"])
    else:
        st.success(result["answer"])
        st.caption(f"Costo: ${result['cost_usd']:.6f} | Tokens: {result['tokens']}")
        st.dataframe(
            [{"ocid": s["ocid"], "Departamento": s["department"], "Monto": s["amount"],
              "Entidad": s["buyer"], "Similitud": s["similarity"]} for s in result["sources"]],
            use_container_width=True,
        )

st.divider()

# ---------- Tabla + descarga ----------
st.subheader("📋 Procesos filtrados")
st.dataframe(df_filtered, use_container_width=True, height=300)
st.download_button("⬇️ Descargar CSV", df_filtered.to_csv(index=False), "procesos_filtrados.csv")

st.divider()

# ---------- Distribución ----------
st.subheader("📊 Distribución por categoría")
if "category" in df_filtered.columns:
    by_cat = df_filtered.groupby("category")["ocid"].count()
    st.bar_chart(by_cat)

st.divider()

# ---------- Indicador de riesgo ----------
st.subheader("⚠️ Indicador de riesgo — Single-bidder")
st.caption("Un % alto es motivo para mirar más de cerca, NO evidencia de irregularidad.")
risk_top = load_csv(OUTPUTS_DIR / "risk_top_buyers.csv")
if risk_top is not None:
    st.dataframe(risk_top, use_container_width=True)
else:
    st.caption("Corre `python src/risk.py` primero.")

st.divider()

# ---------- Panel de calidad de datos ----------
with st.expander("📊 Panel de calidad de datos (Fase 2)"):
    quality_report = load_json(LOGS_DIR / "data_quality_report.json")
    if quality_report:
        st.json(quality_report)
    else:
        st.caption("Corre `python src/validate.py` primero.")
