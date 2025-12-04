import streamlit as st
import plotly.graph_objects as go

import pandas as pd
import io
import base64
from groq import Groq
import time
from datetime import datetime

import markdown
from bs4 import BeautifulSoup
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from supabase import create_client

# streamlit run app_groq.py
# .\.venv\Scripts\activate

# -----------------------------
#       CONFIGURACIÓN
# -----------------------------
st.set_page_config(
    page_title="Fishualizer",
    page_icon="🐟",  # si quieres luego lo cambias a favicon.png
    layout="wide",
    initial_sidebar_state="auto",
)

# ===== CSS minimalista / profesional =====
custom_css = """
<style>
/* Fondo general y tipografía */
.stApp {
    background-color: #f3f4f6;
    color: #111827;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Contenedor principal centrado y más angosto */
.main .block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* Título principal genérico (por si lo usas en el contenido) */
h1 {
    font-size: 2.4rem;
    font-weight: 900;
    letter-spacing: 0.04em;
    color: #0f172a;
}

/* Subtítulos */
h2, h3 {
    font-weight: 900;
    color: #111827;
}

/* Tarjeta del formulario */
[data-testid="stForm"] {
    background-color: #ffffff;
    border-radius: 18px;
    padding: 1.8rem 1.9rem 2.0rem 1.9rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
}

/* Labels */
[data-testid="stWidgetLabel"] *,
[data-testid="stNumberInputLabel"] *,
[data-testid="stTextAreaLabel"] *,
[data-testid="stSelectboxLabel"] * {
    font-weight: 800 !important;
    font-size: 1rem !important;
    color: #111827 !important;
}

/* Inputs */
div[data-testid="stNumberInput"] > div,
div[data-baseweb="select"] > div,
textarea {
    border-radius: 10px !important;
}

/* Botones */
button {
    background-color: #3B82F6 !important;
    color: #ffffff !important;
    font-weight: 900 !important;
    font-size: 1rem !important;
    border-radius: 999px !important;
    border: none !important;
    padding: 0.65rem 1.9rem !important;
    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.35) !important;
    cursor: pointer !important;
    transition: transform 0.08s ease,
                box-shadow 0.12s ease,
                background 0.12s ease !important;
}
button:hover {
    background-color: #1d4ed8 !important;
    box-shadow: 0 10px 22px rgba(37, 99, 235, 0.45) !important;
    transform: translateY(-1px) !important;
}
button:active {
    background-color: #1e40af !important;
    box-shadow: 0 4px 10px rgba(30, 64, 175, 0.55) !important;
    transform: translateY(0) !important;
}

/* Alertas */
.stAlert {
    border-radius: 10px;
}

/* Gráficos */
.stPlotlyChart {
    background-color: #ffffff;
    border-radius: 16px;
    padding: 0.8rem;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    border: 1px solid #e5e7eb;
}

/* Ocultar el texto "Press Enter to submit form" */
div[data-testid="InputInstructions"] > span:nth-child(1) {
    visibility: hidden !important;
}

/* (por si acaso) matar cualquier instrucción completa */
div[data-testid="InputInstructions"] {
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}

/* ===== Header barra Fishualizer ===== */
.header-bar {
    background-color: #ffffff;
    border-radius: 18px;
    padding: 0.9rem 1.8rem;
    margin-bottom: 1.8rem;
    box-shadow: 0 14px 30px rgba(15, 23, 42, 0.10);
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.header-logo-fish {
    font-size: 2.6rem;   /* tamaño del emoji 🐟 */
}

.header-title {
    font-size: 1.9rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    color: #0f172a;
}

.header-right {
    display: flex;
    align-items: center;
}

.header-logo-ucn {
    height: 70px;   
    width: auto;
}
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# ===== HEADER BARRA PRINCIPAL =====
st.markdown(
    """
    <div class="header-bar">
        <div class="header-left">
            <span class="header-logo-fish">🐟</span>
            <span class="header-title">FISHUALIZER</span>
        </div>
        <div class="header-right">
            <img src="https://raw.githubusercontent.com/CelisBenjamin/fishualizer-dashboard/main/ucn_logo_completo.webp"
                 class="header-logo-ucn"
                 alt="Universidad Católica del Norte">
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ===== CLIENTE SUPABASE =====
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"],
)

# =====================================================
#  🔥 NUEVA CONFIGURACIÓN DEL CLIENTE — USANDO GROQ
# =====================================================
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# -----------------------------
#     VARIABLES AUXILIARES
# -----------------------------

with open("prompt actualizado.txt", "r", encoding="utf8") as f:
    prompt_principal = f.read()

# RANGOS
rangos_boxplot_chile = pd.DataFrame({
    "Variable": ["Temperatura", "pH", "Saturación de oxígeno (%)", "Oxígeno disuelto (mg/L)", "Alcalinidad", "Amonio Total"],
    "min": [13.050, 7.820, 95.100, 8.154, 150.000, -0.300],
    "q1": [17.100, 8.360, 98.100, 9.020, 180.000, 0.000],
    "median": [18.450, 8.540, 99.100, 9.309, 190.000, 0.100],
    "q3": [19.800, 8.720, 100.100, 9.598, 200.000, 0.200],
    "max": [23.850, 9.260, 103.100, 10.464, 230.000, 0.500]
})

rangos_boxplot_arg = pd.DataFrame({
    "Variable": ["Temperatura", "pH", "Saturación de oxígeno (%)", "Oxígeno disuelto (mg/L)", "Alcalinidad", "Amonio Total"],
    "min": [12.950, 7.855, 92.050, 7.885, 100.500, -0.545],
    "q1": [17.000, 8.290, 96.400, 8.860, 159.000, 0.032],
    "median": [18.350, 8.435, 97.850, 9.185, 178.500, 0.225],
    "q3": [19.700, 8.580, 99.300, 9.510, 198.000, 0.418],
    "max": [23.750, 9.095, 103.650, 10.485, 256.500, 0.995]
})

def eliminar_think(texto):
    soup = BeautifulSoup(texto, "html.parser")
    for tag in soup.find_all("think"):
        tag.decompose()
    return str(soup)

if "datos" not in st.session_state:
    st.session_state.datos = pd.DataFrame(
        columns=["Temperatura", "pH", "Saturación de oxígeno (%)", "Oxígeno disuelto (mg/L)", "Alcalinidad", "Amonio Total", "Observaciones"]
    )

# -----------------------------
#       FORMULARIO
# -----------------------------
with st.form("formulario"):
    st.subheader("Ingrese los valores de calidad del agua")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1: var1 = st.number_input("Temperatura (°C)", value=15.0)
    with col2: var2 = st.number_input("pH", value=7.0)
    with col3: var3 = st.number_input("Saturación de oxígeno (%)", value=98.0)
    with col4: var4 = st.number_input("Oxígeno disuelto (mg/L)", value=9.0)
    with col5: var5 = st.number_input("Alcalinidad", value=150)
    with col6: var6 = st.number_input("Amonio Total", value=0.0)

    tipo_pez = st.selectbox("Que especie de pejerrey es", ("Chileno", "Argentino"))
    observaciones = st.text_area("Observaciones adicionales")
    submit = st.form_submit_button("🔍 Generar reporte")

# -----------------------------
#      PROCESAMIENTO
# -----------------------------
if submit:

    rangos = rangos_boxplot_chile if tipo_pez == "Chileno" else rangos_boxplot_arg

    valores_usuario = {
        "Temperatura": var1,
        "pH": var2,
        "Saturación de oxígeno (%)": var3,
        "Oxígeno disuelto (mg/L)": var4,
        "Alcalinidad": var5,
        "Amonio Total": var6,
    }

    comparaciones = []

    for _, fila in rangos.iterrows():
        variable = fila["Variable"]
        valor = valores_usuario[variable]

        minimo = fila["min"]
        q1 = fila["q1"]
        mediana = fila["median"]
        q3 = fila["q3"]
        maximo = fila["max"]

        if valor < minimo:
            estado = "bajo mínimo histórico"
        elif valor < q1:
            estado = "bajo IQR"
        elif q1 <= valor <= q3:
            estado = "dentro de IQR"
        elif valor > q3 and valor <= maximo:
            estado = "sobre IQR"
        elif valor > maximo:
            estado = "sobre máximo histórico"
        else:
            estado = "valor no clasificado"

        comparaciones.append(
            f"{variable}: {valor} → {estado} "
            f"(min={minimo}, q1={q1}, mediana={mediana}, q3={q3}, max={maximo})"
        )

    texto_comparaciones = "\n".join(comparaciones)

    observaciones_procesadas = (
        "Comparación con estadísticas históricas del sistema:\n"
        + texto_comparaciones
        + "\n\n - Observaciones del usuario: "
        + observaciones
    )

    # Guarda también en la sesión local (por si después quieres usarlo)
    nuevo_registro = {
        "Temperatura": var1,
        "pH": var2,
        "Saturación de oxígeno (%)": var3,
        "Oxígeno disuelto (mg/L)": var4,
        "Alcalinidad": var5,
        "Amonio Total": var6,
        "Tipo pejerrey": tipo_pez,
        "Observaciones": observaciones_procesadas,
    }

    st.session_state.datos = pd.concat(
        [st.session_state.datos, pd.DataFrame([nuevo_registro])],
        ignore_index=True,
    )

    # =====================
    #   TIMESTAMP + OBS
    # =====================
    ahora = datetime.now()
    fecha = ahora.date().isoformat()          # YYYY-MM-DD
    hora = ahora.time().strftime("%H:%M:%S")  # HH:MM:SS

    texto_observacion = observaciones.strip() if observaciones.strip() != "" else None

    # -------------------------
    #    LLAMADA AL MODELO GROQ (CON LOADING)
    # -------------------------
    with st.spinner("⏳ Analizando datos del estanque y generando informe..."):
        start = time.time()

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": f"""
{prompt_principal}

Tipo de pez: {tipo_pez}
Datos del estanque:
- Temperatura: {var1} °C  
- pH: {var2}  
- Saturación de oxígeno (%): {var3}  
- Oxígeno disuelto (mg/L): {var4}  
- Amonio (TAN): {var6} mg/L  
- Alcalinidad: {var5} mg/L CaCO₃  
- Observaciones adicionales: {observaciones_procesadas}

Presenta el resultado final en secciones con formato claro y conciso:
Interpretación, Problemas detectados y Recomendaciones.
"""
                }
            ],
            max_tokens=600,
            temperature=0.2,
        )

        resultado = completion.choices[0].message.content
        resultado_limpio = eliminar_think(resultado)

        inicio = resultado_limpio.lower().find("informe técnico")
        resultado_final = (
            resultado_limpio[inicio:] if inicio != -1 else resultado_limpio
        )

        # =====================
        #  GUARDAR EN SUPABASE
        # =====================
        try:
            supabase.table("mediciones").insert(
                {
                    "fecha": fecha,
                    "hora": hora,
                    "especie": tipo_pez,
                    "temperatura": float(var1),
                    "ph": float(var2),
                    "sat_pct": float(var3),
                    "oxigeno_mg": float(var4),
                    "alcalinidad": float(var5),
                    "amonio_total": float(var6),
                    "observacion": texto_observacion,
                }
            ).execute()

            st.info("📡 Registro guardado en la base histórica.")

        except Exception as e:
            st.warning("⚠️ Error al guardar en Supabase.")
            print("Error Supabase:", e)

        elapsed = time.time() - start

    st.success(f"⚡ Reporte generado en {elapsed:.2f} segundos")
    st.markdown("🧠 Resultado del análisis")
    st.markdown(resultado_final)
 
# ==========================
#        FOOTER
# ==========================
st.markdown(
    """
    <hr style="margin-top:3rem; margin-bottom:1rem;">
    <div style="text-align:center; color:#6b7280; font-size:0.85rem;">
        Fishualizer v1.0 — Proyecto desarrollado en la Universidad Católica del Norte<br>
        © 2025 — Fernando Véliz & Benjamín Celis
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")
st.subheader("📊 Historial de mediciones")

st.markdown("---")
st.subheader("📊 Historial de mediciones")

# Estado de autenticación para descargas
if "hist_autorizado" not in st.session_state:
    st.session_state.hist_autorizado = False

with st.expander("🔒 Zona solo para personal autorizado"):
    if not st.session_state.hist_autorizado:
        pwd = st.text_input("Ingresa la contraseña", type="password")
        if st.button("✅ Validar acceso"):
            if pwd == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.hist_autorizado = True
                st.success("Acceso concedido. Ahora puedes descargar el histórico.")
            else:
                st.error("Contraseña incorrecta.")
    else:
        st.success("Acceso autorizado. Puedes descargar el histórico.")

        if st.button("📥 Descargar histórico en Excel"):
            try:
                res = (
                    supabase.table("mediciones")
                    .select("*")
                    .order("fecha", desc=True)
                    .order("hora", desc=True)
                    .execute()
                )
                data = res.data

                if not data:
                    st.info("Aún no hay registros.")
                else:
                    df = pd.DataFrame(data)

                    df = df.rename(columns={
                        "fecha": "Fecha",
                        "hora": "Hora",
                        "especie": "Especie",
                        "temperatura": "T°",
                        "ph": "pH",
                        "sat_pct": "%SAT",
                        "oxigeno_mg": "OD",
                        "alcalinidad": "ALC",
                        "amonio_total": "TAN",
                        "observacion": "Observación",
                    })

                    df = df[["Fecha","Hora","Especie","T°","pH","%SAT","OD","ALC","TAN","Observación"]]

                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer) as writer:
                        df.to_excel(writer, index=False, sheet_name="Histórico")
                    buffer.seek(0)

                    st.download_button(
                        label="⬇️ Descargar Excel",
                        data=buffer,
                        file_name="historico_fishualizer.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

            except Exception as e:
                st.warning("⚠️ Error al obtener el historial.")
                print(e)
