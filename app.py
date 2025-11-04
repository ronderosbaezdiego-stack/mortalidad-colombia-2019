import os
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, dash_table

# =========================
# CARGA DE DATOS
# =========================
anexo1 = pd.read_excel("data/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
anexo2 = pd.read_excel("data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
divipola = pd.read_excel("data/Divipola_CE_.xlsx")

# Limpieza de nombres de columnas
anexo1.columns = anexo1.columns.str.upper().str.strip()
anexo2.columns = anexo2.columns.str.upper().str.strip()
divipola.columns = divipola.columns.str.upper().str.strip()

# Identificar columnas relevantes
col_cod_muerte = "CÓDIGO DE LA CIE-10 TRES CARACTERES"
if col_cod_muerte not in anexo2.columns:
    col_cod_muerte = next((c for c in anexo2.columns if "CIE" in c), None)

# Renombrar para unir
if col_cod_muerte:
    anexo2 = anexo2.rename(columns={col_cod_muerte: "COD_MUERTE"})
else:
    raise KeyError(f"No se encontró columna de código de muerte en Anexo2. Columnas: {anexo2.columns.tolist()}")

if "COD_MUERTE" not in anexo1.columns:
    # Si no existe en Anexo1, crearla vacía o usar alguna aproximación
    anexo1["COD_MUERTE"] = anexo1["COD_MUERTE"] if "COD_MUERTE" in anexo1.columns else None

# Asegurar formato de códigos
anexo1["COD_DEPARTAMENTO"] = anexo1["COD_DEPARTAMENTO"].astype(str).str.zfill(2)
anexo1["COD_MUNICIPIO"] = anexo1["COD_MUNICIPIO"].astype(str).str.zfill(3)

# Renombrar columnas principales en Divipola
divipola = divipola.rename(columns={
    "COD_DEPTO": "COD_DEPARTAMENTO" if "COD_DEPTO" in divipola.columns else "COD_DEPTO",
    "COD_MPIO": "COD_MUNICIPIO" if "COD_MPIO" in divipola.columns else "COD_MPIO"
})
divipola["COD_DEPTO"] = divipola["COD_DEPTO"].astype(str).str.zfill(2)
divipola["COD_MPIO"] = divipola["COD_MPIO"].astype(str).str.zfill(3)

# =========================
# UNIÓN DE DATOS
# =========================
df = anexo1.merge(anexo2, on="COD_MUERTE", how="left")
df = df.merge(divipola, left_on=["COD_DEPARTAMENTO", "COD_MUNICIPIO"],
              right_on=["COD_DEPTO", "COD_MPIO"], how="left")

# =========================
# GRÁFICOS
# =========================
mapa = df.groupby("NOMBRE_DPT").size().reset_index(name="TOTAL_MUERTES")
fig_mapa = px.bar(mapa, x="NOMBRE_DPT", y="TOTAL_MUERTES", title="Total de muertes por departamento (2019)")

muertes_mes = df.groupby("MES").size().reset_index(name="TOTAL")
fig_lineas = px.line(muertes_mes, x="MES", y="TOTAL", title="Muertes por mes en Colombia (2019)")

# =========================
# APLICACIÓN DASH
# =========================
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Análisis de Mortalidad en Colombia - 2019", style={"textAlign": "center"}),

    dcc.Graph(figure=fig_mapa),
    dcc.Graph(figure=fig_lineas),

    html.H3("Vista previa de datos combinados"),
    dash_table.DataTable(
        data=df.head(10).to_dict("records"),
        columns=[{"name": i, "id": i} for i in df.columns],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left"}
    )
])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)

