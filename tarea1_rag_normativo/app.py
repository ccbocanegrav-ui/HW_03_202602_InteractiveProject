"""
app.py — Fase 5, Task 1: interfaz Streamlit

ARQUITECTURA: esta app SOLO llama a engine.answer_question(). Nunca
habla directo con ChromaDB ni con el modelo de embeddings/generacion.
Toda la logica de RAG vive en src/engine.py (requisito del enunciado:
"the Streamlit app... only calls that function").

La app NUNCA reconstruye el indice al iniciar — solo lo lee (ya
construido por build_index.py).

Uso:
    streamlit run app.py
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from engine import answer_question, load_config  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"

st.set_page_config(page_title="RAG Normativo — Contrataciones Públicas", page_icon="⚖️", layout="wide")

# ---------- Estado de sesion ----------
st.session_state.setdefault("theme", "Oscuro")
st.session_state.setdefault("question_input", "")
st.session_state.setdefault("history", [])  # lista de dicts: pregunta, respuesta, fuentes, costo, hora


def set_question(text: str):
    st.session_state["question_input"] = text


# ---------- CSS: modo claro/oscuro (toggle en vivo, dentro de la app) ----------
# Se apunta explicitamente a los data-testid estables que usa Streamlit
# por dentro (no solo el fondo general), con !important, para que
# NINGUN texto quede invisible: labels de inputs, texto tipeado en
# cajas, botones, alertas (success/warning/error/info), metricas,
# captions, expanders y el contenido markdown normal.
def theme_css(bg, bg2, text, text2, border, accent):
    return f"""
    <style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: {bg} !important; color: {text} !important;
    }}
    [data-testid="stSidebar"] {{ background-color: {bg2} !important; color: {text} !important; }}
    [data-testid="stSidebar"] * {{ color: {text} !important; }}
    h1, h2, h3, h4, h5, h6, p, li, span, label,
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {{
        color: {text} !important;
    }}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{ color: {text2} !important; }}
    [data-testid="stTextInput"] input {{
        background-color: {bg2} !important; color: {text} !important; border: 1px solid {border} !important;
    }}
    [data-testid="stTextInput"] input::placeholder {{ color: {text2} !important; }}
    .stButton button, .stButton button * {{
        background-color: {bg2} !important; color: {text} !important; border: 1px solid {border} !important;
        outline: none !important; box-shadow: none !important;
    }}
    .stButton button:hover, .stButton button:hover * {{
        background-color: {accent} !important; border-color: {accent} !important; color: {text} !important;
    }}
    .stButton button:focus, .stButton button:focus-visible, .stButton button:active {{
        border-color: {border} !important; outline: none !important; box-shadow: none !important;
        color: {text} !important; background-color: {bg2} !important;
    }}
    [data-testid="stExpander"] {{ background-color: {bg2} !important; border: 1px solid {border} !important; }}
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {{ color: {text} !important; }}
    [data-testid="stMetric"] {{ background-color: {bg2} !important; border-radius: 8px; padding: 10px; }}
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{ color: {text} !important; }}
    [data-testid="stAlert"] {{ color: {text} !important; }}
    [data-testid="stAlert"] * {{ color: {text} !important; }}
    [data-testid="stDataFrame"] {{ border: 1px solid {border} !important; }}
    hr {{ border-color: {border} !important; }}
    </style>
    """


DARK_CSS = theme_css(
    bg="#0e1117", bg2="#1c2030", text="#fafafa", text2="#b0b4c0", border="#3d4560", accent="#3d4560",
)
LIGHT_CSS = theme_css(
    bg="#ffffff", bg2="#f0f2f6", text="#1a1a1a", text2="#5a5f6b", border="#d0d4de", accent="#e0e3ec",
)


@st.cache_data
def load_text_file(path: Path) -> str:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


@st.cache_data
def load_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


config = load_config()

# ---------- Sidebar ----------
st.markdown(DARK_CSS if st.session_state["theme"] == "Oscuro" else LIGHT_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configuración")
    st.radio("Tema", ["Oscuro", "Claro"], key="theme", horizontal=True)

    st.divider()
    st.header("❓ Preguntas frecuentes")
    eval_rows = load_csv_rows(BASE_DIR / "eval" / "preguntas.csv")
    faq_rows = [r for r in eval_rows if r.get("tipo") == "in_domain"][:6]
    if faq_rows:
        for r in faq_rows:
            st.button(r["pregunta"], key=f"faq_{r['id']}", on_click=set_question, args=(r["pregunta"],),
                       use_container_width=True)
    else:
        st.caption("No se encontró eval/preguntas.csv.")

    st.divider()
    st.header("🕘 Mis consultas anteriores")
    if st.session_state["history"]:
        for i, h in enumerate(reversed(st.session_state["history"])):
            with st.expander(f"{h['hora']} — {h['pregunta'][:40]}..."):
                st.caption(h["pregunta"])
                st.write(h["respuesta"])
                st.caption(f"Costo: ${h['costo']:.6f} | Abstuvo: {'Sí' if h['abstained'] else 'No'}")
        if st.button("🗑️ Borrar historial", use_container_width=True):
            st.session_state["history"] = []
            st.rerun()
    else:
        st.caption("Todavía no has hecho ninguna consulta.")

    st.divider()
    st.header("📊 Panel de calidad")
    with st.expander("Extracción — Fase 1", expanded=False):
        for doc_id in [d["id"] for d in config["documents"]]:
            report = load_text_file(LOGS_DIR / f"extraction_quality_report_{doc_id}.txt")
            st.subheader(doc_id)
            if report:
                st.text(report[:600] + ("..." if len(report) > 600 else ""))
            else:
                st.caption("Reporte no encontrado — corre extract.py y clean.py.")

    with st.expander("Evaluación — Fase 4", expanded=False):
        recall_rows = load_csv_rows(LOGS_DIR / "eval_recall_results.csv")
        if recall_rows:
            st.caption("Resultados detallados por pregunta (Recall@k, abstención)")
            st.dataframe(recall_rows, use_container_width=True, height=250)
        else:
            st.caption("Corre eval/eval_recall.py primero.")

        emb_rows = load_csv_rows(LOGS_DIR / "embeddings_comparison.csv")
        if emb_rows:
            st.caption("Comparación local vs. API")
            st.dataframe(emb_rows, use_container_width=True)
        else:
            st.caption("Corre eval/compare_embeddings.py primero.")

    st.divider()
    st.caption(f"Threshold actual: **{config['retrieval']['similarity_threshold']}**")
    st.caption(f"Modelo generador: **{config['generation']['model_name']}**")

# ---------- Panel principal ----------
st.title("⚖️ Asistente RAG — Contrataciones Públicas del Perú")
st.caption(
    "Responde preguntas sobre la Ley N.° 32069 y el Decreto Supremo N.° 001-2026-EF "
    "(que modifica su Reglamento), citando documento y página. Se abstiene cuando la "
    "pregunta está fuera del corpus indexado."
)

question = st.text_input(
    "Escribe tu pregunta:",
    key="question_input",
    placeholder="Ej: ¿Cuál es el plazo máximo para pagar al contratista?",
)
submitted = st.button("Preguntar", type="primary")

if submitted and question.strip():
    with st.spinner("Buscando en el corpus y generando respuesta..."):
        result = answer_question(question, config)

    if result["error"]:
        st.error(f"Error: {result['error']}")
    elif result["abstained"]:
        st.warning(result["answer"])
    else:
        st.success(result["answer"])

    col1, col2, col3 = st.columns(3)
    col1.metric("¿Se abstuvo?", "Sí" if result["abstained"] else "No")
    col2.metric("Costo de la consulta", f"${result['cost_usd']:.6f}")
    col3.metric("Tokens (in/out)", f"{result['tokens']['input']} / {result['tokens']['output']}")

    if result["sources"]:
        st.subheader("Fragmentos recuperados")
        st.dataframe(
            [
                {"Documento": s["documento"], "Página": s["pagina"], "Similitud": round(s["similarity"], 4)}
                for s in result["sources"]
            ],
            use_container_width=True,
        )
        with st.expander("Ver texto completo de los fragmentos"):
            for s in result["sources"]:
                st.markdown(f"**{s['documento']} — página {s['pagina']}** (similitud: {s['similarity']:.4f})")
                st.text(s["text"][:500] + ("..." if len(s["text"]) > 500 else ""))
                st.divider()

    if not result["error"]:
        st.session_state["history"].append({
            "pregunta": question,
            "respuesta": result["answer"],
            "costo": result["cost_usd"],
            "abstained": result["abstained"],
            "hora": datetime.now().strftime("%H:%M:%S"),
        })

elif submitted:
    st.info("Escribe una pregunta primero.")
