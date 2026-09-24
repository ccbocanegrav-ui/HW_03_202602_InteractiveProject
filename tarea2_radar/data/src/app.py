from pathlib import Path
import sys

import streamlit as st


# ============================================================
# RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR))


from search import search
from radar_engine import run_radar


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Radar de Procesos",
    page_icon="📡",
    layout="wide",
)


# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>
    .radar-card {
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-bottom: 1rem;
        background-color: #fafafa;
    }

    .score-high {
        color: #b91c1c;
        font-weight: bold;
    }

    .score-medium {
        color: #c2410c;
        font-weight: bold;
    }

    .score-low {
        color: #166534;
        font-weight: bold;
    }

    .signal {
        padding: 0.4rem 0.6rem;
        margin: 0.2rem 0;
        border-radius: 6px;
        background-color: #f3f4f6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TÍTULO
# ============================================================

st.title("📡 Radar de Procesos")

st.markdown(
    """
    Sistema de búsqueda híbrida y detección de señales
    sobre procesos de contratación pública.
    """
)


# ============================================================
# CONSULTA
# ============================================================

st.subheader("Consulta")

query = st.text_input(
    "Escribe una consulta",
    placeholder=(
        "Ejemplo: servicios de limpieza en Lima "
        "por más de 1 millón de soles"
    ),
)


# ============================================================
# EJEMPLOS
# ============================================================

st.caption("Ejemplos de consultas:")

examples = [
    "compra de medicamentos en Cusco",
    "servicios de limpieza en Lima por más de 1 millón de soles",
    "adquisición de equipos informáticos en Arequipa durante marzo",
    "procesos de construcción en enero",
]

cols = st.columns(4)

for col, example in zip(cols, examples):

    if col.button(
        example,
        use_container_width=True,
    ):
        st.session_state["query"] = example


if "query" in st.session_state and not query:
    query = st.session_state["query"]


# ============================================================
# EJECUTAR
# ============================================================

if st.button(
    "🔎 Ejecutar Radar",
    type="primary",
    use_container_width=True,
):

    if not query.strip():

        st.warning(
            "Ingresa una consulta antes de ejecutar el Radar."
        )

        st.stop()

    try:

        with st.spinner(
            "Analizando procesos..."
        ):

            response = search(
                query,
                top_k=5,
            )

            radar_response = run_radar(
                response["results"]
            )

    except Exception as e:

        st.error(
            "Ocurrió un error al ejecutar el Radar."
        )

        st.exception(e)

        st.stop()


    # ========================================================
    # INFORMACIÓN DE LA CONSULTA
    # ========================================================

    st.divider()

    st.subheader("Consulta procesada")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("**Consulta original**")

        st.write(
            response["query"]
        )

    with col2:

        st.markdown("**Consulta semántica**")

        st.write(
            response["semantic_query"]
        )


    # ========================================================
    # FILTROS
    # ========================================================

    st.subheader("Filtros detectados")

    filters = response["filters"]

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Departamento",
            filters["departamento"]
            or "Todos",
        )

    with col2:

        st.metric(
            "Mes",
            filters["mes_origen"]
            or "Todos",
        )

    with col3:

        st.metric(
            "Categoría",
            filters["categoria"]
            or "Todas",
        )

    with col4:

        if filters["monto_min"] is not None:

            amount_text = (
                f"S/ {filters['monto_min']:,.2f}"
            )

        else:

            amount_text = "Sin mínimo"

        st.metric(
            "Monto mínimo",
            amount_text,
        )


    # ========================================================
    # RESUMEN
    # ========================================================

    results = radar_response["results"]

    st.subheader("Resumen")

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Procesos analizados",
            len(results),
        )

    with col2:

        threshold = radar_response.get(
            "amount_threshold"
        )

        if threshold is not None:

            threshold_text = (
                f"S/ {threshold:,.2f}"
            )

        else:

            threshold_text = "No disponible"

        st.metric(
            "Umbral de monto alto",
            threshold_text,
        )


    # ========================================================
    # RESULTADOS
    # ========================================================

    st.divider()

    st.subheader("Resultados del Radar")

    if not results:

        st.info(
            "No se encontraron procesos "
            "para los filtros indicados."
        )

        st.stop()


    for result in results:

        score = result.get(
            "radar_score",
            0,
        )

        if score >= 30:

            score_class = "score-high"

        elif score > 0:

            score_class = "score-medium"

        else:

            score_class = "score-low"


        # ----------------------------------------------------
        # CABECERA
        # ----------------------------------------------------

        with st.container(
            border=True
        ):

            col1, col2, col3 = st.columns(
                [1, 5, 2]
            )

            with col1:

                st.markdown(
                    f"### #{result['rank']}"
                )

            with col2:

                st.markdown(
                    f"**{result['comprador']}**"
                )

                st.caption(
                    f"OCID: {result['ocid']}"
                )

            with col3:

                st.markdown(
                    f'<div class="{score_class}">'
                    f"Radar = {score}"
                    f"</div>",
                    unsafe_allow_html=True,
                )


            # ------------------------------------------------
            # DATOS
            # ------------------------------------------------

            col1, col2, col3, col4 = st.columns(4)

            with col1:

                st.markdown("**Departamento**")

                st.write(
                    result.get(
                        "departamento",
                        "No disponible",
                    )
                )

            with col2:

                st.markdown("**Categoría**")

                st.write(
                    result.get(
                        "categoria",
                        "No disponible",
                    )
                )

            with col3:

                st.markdown("**Monto**")

                monto = result.get(
                    "monto_pen"
                )

                if monto is not None:

                    st.write(
                        f"S/ {float(monto):,.2f}"
                    )

                else:

                    st.write(
                        "No disponible"
                    )

            with col4:

                st.markdown("**Postores**")

                postores = result.get(
                    "num_postores"
                )

                if postores is not None:

                    st.write(
                        postores
                    )

                else:

                    st.write(
                        "No disponible"
                    )


            # ------------------------------------------------
            # SIMILITUD
            # ------------------------------------------------

            similarity = result.get(
                "similarity"
            )

            if similarity is not None:

                st.markdown(
                    f"**Similitud semántica:** "
                    f"{similarity:.4f}"
                )


            # ------------------------------------------------
            # SEÑALES
            # ------------------------------------------------

            signals = result.get(
                "signals",
                [],
            )

            st.markdown("**Señales detectadas**")

            if not signals:

                st.caption(
                    "No se detectaron señales."
                )

            else:

                for signal in signals:

                    severity = signal.get(
                        "severity",
                        "informativo",
                    )

                    message = signal.get(
                        "message",
                        "",
                    )

                    if severity == "alto":

                        st.error(
                            f"[{severity}] {message}"
                        )

                    elif severity == "medio":

                        st.warning(
                            f"[{severity}] {message}"
                        )

                    else:

                        st.info(
                            f"[{severity}] {message}"
                        )


            # ------------------------------------------------
            # DETALLES
            # ------------------------------------------------

            with st.expander(
                "Ver detalles del proceso"
            ):

                st.write(
                    "**Procedimiento:**",
                    result.get(
                        "procedimiento",
                        "No disponible",
                    ),
                )

                st.write(
                    "**Fecha de publicación:**",
                    result.get(
                        "fecha_publicacion",
                        "No disponible",
                    ),
                )

                st.write(
                    "**Texto indexado:**"
                )

                st.write(
                    result.get(
                        "texto",
                        "No disponible",
                    )
                )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Radar de Procesos — Tarea 2"
)
