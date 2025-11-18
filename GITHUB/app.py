import streamlit as st
import pandas as pd
from datetime import datetime

# ===============================
#  TÍTULO
# ===============================
st.title("Bot para sacar STATS de turno")

# ===============================
#  SIDEBAR: archivos opcionales
# ===============================
st.sidebar.header("⚙️ Opciones adicionales")
st.sidebar.write("Aquí puedes actualizar los archivos base de datos:")

# 🔹 Primero: horario semanal (Connecteam)
connecteam_file = st.sidebar.file_uploader("Actualizar horario semanal (CSV)", type=["csv"])

# 🔹 Segundo: traducción de nombres (mapa_nombres)
mapa_file = st.sidebar.file_uploader("Actualizar traducción de nombres (Excel)", type=["xlsx"])

# ===============================
#  CARGA DE BASES DE DATOS
# ===============================
# Connecteam
try:
    df_connecteam = pd.read_pickle("connecteam.pkl")
except FileNotFoundError:
    df_connecteam = pd.DataFrame()

# Mapa de nombres
try:
    df_mapa_nombres = pd.read_pickle("mapa_nombres.pkl")
except FileNotFoundError:
    df_mapa_nombres = pd.DataFrame()

# ===============================
#  ACTUALIZAR BASES DE DATOS
# ===============================
if connecteam_file:
    df_connecteam = pd.read_csv(connecteam_file)
    df_connecteam["Date"] = pd.to_datetime(df_connecteam["Date"])
    df_connecteam.to_pickle("connecteam.pkl")
    st.sidebar.success("Horario semanal actualizado.")

if mapa_file:
    df_mapa_nombres = pd.read_excel(mapa_file)
    df_mapa_nombres.to_pickle("mapa_nombres.pkl")
    st.sidebar.success("Traducción de nombres actualizada.")

# ===============================
#  SELECCIÓN DE ARCHIVO LIVEAGENT
# ===============================
live_file = st.file_uploader("Sube el CSV exportado de LiveAgent (stats)", type=["csv"])

if live_file:
    df_live = pd.read_csv(live_file)

    # ===============================
    #  SELECCIÓN DE FECHA
    # ===============================
    if not df_connecteam.empty:
        fechas = df_connecteam['Date'].dt.date.unique()
        fecha_seleccionada = st.selectbox("Selecciona la fecha para generar los stats", fechas)
    else:
        st.warning("No hay archivo de Connecteam cargado para seleccionar fecha.")
        fecha_seleccionada = None

    # ===============================
    #  CREAR DICCIONARIO DE NOMBRES
    # ===============================
    map_dict = {}
    if not df_mapa_nombres.empty:
        map_dict = {
            f"{row['Nombre']} {row['Apellido']}": (row['Nombre Live'], row['Apellido Live'])
            for _, row in df_mapa_nombres.iterrows()
        }

    # ===============================
    #  FILTRAR POR FECHA Y TURNO
    # ===============================
    if fecha_seleccionada is not None:
        df_connecteam_fecha = df_connecteam[df_connecteam['Date'].dt.date == fecha_seleccionada]
        turnos = df_connecteam_fecha['Shift title'].unique()
        dfs_turnos = {}

        for turno in turnos:
            # Usuarios del turno
            users_row = df_connecteam_fecha[df_connecteam_fecha['Shift title'] == turno]['Users']
            users = []
            for val in users_row:
                if pd.isna(val):
                    continue
                users.extend([u.strip() for u in str(val).split(',')])

            # Mapear a nombres Live
            live_names = []
            for u in users:
                if u in map_dict:
                    live_names.append(map_dict[u])
                else:
                    # Si no está en el mapa, usar el nombre original como First Name
                    live_names.append((u, None))

            # Filtrar stats_live para estos usuarios
            df_turno = pd.DataFrame()
            for nombre_live, apellido_live in live_names:
                if apellido_live:
                    df_user = df_live[
                        (df_live['First Name'] == nombre_live) & (df_live['Last Name'] == apellido_live)
                    ]
                else:
                    # Coincidencia solo por First Name si no hay apellido
                    df_user = df_live[df_live['First Name'] == nombre_live]

                if not df_user.empty:
                    df_turno = pd.concat([df_turno, df_user], ignore_index=True)
                else:
                    st.warning(f"Usuario no encontrado en LiveAgent: {nombre_live} {apellido_live}")

            # Convertir segundos a minutos
            for col in ['Call seconds', 'Outgoing call seconds', 'Tiempo promedio de llamada', 'Tiempo de trabajo']:
                if col in df_turno.columns:
                    df_turno[col] = df_turno[col] / 60

            dfs_turnos[turno] = df_turno

        # ===============================
        #  GUARDAR XLSX FINAL
        # ===============================
        output_file = f"stats_por_turno_{fecha_seleccionada}.xlsx"
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            for turno, df in dfs_turnos.items():
                sheet_name = str(turno)[:31]  # Excel limita a 31 caracteres
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        st.success(f"✅ Archivo generado: {output_file}")
        st.download_button("📥 Descargar XLSX", data=open(output_file, "rb"), file_name=output_file)

else:
    st.info("Por favor, sube el archivo CSV exportado de LiveAgent para continuar.")

