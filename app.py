import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px

# =======================
# Cargar datos
# =======================
df1 = pd.read_excel("data/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
df2 = pd.read_excel("data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
divipola = pd.read_excel("data/Divipola_CE_.xlsx")

# =======================
# Limpieza básica
# =======================
# Normalizamos columnas de nombres de departamento en Divipola
divipola = divipola.rename(columns=lambda x: x.strip().upper())

# Aseguramos que las columnas claves existen
if "COD_DEPARTAMENTO" not in df1.columns:
    raise Exception("⚠️ No se encontró la columna COD_DEPARTAMENTO en el archivo principal.")

if "COD_DPTO" in divipola.columns:
    divipola["COD_DEPARTAMENTO"] = divipola["COD_DPTO"]

# Eliminamos duplicados de departamentos
divipola_departamentos = divipola[["COD_DEPARTAMENTO", "DEPARTAMENTO"]].drop_duplicates()

# =======================
# Crear la app Dash
# =======================
app = Dash(__name__)
server = app.server

# =======================
# Layout
# =======================
app.layout = html.Div([
    html.H1("📊 Mortalidad Colombia 2019", style={'textAlign': 'center'}),

    html.Label("Selecciona un departamento:"),
    dcc.Dropdown(
        id='departamento',
        options=[
            {'label': dep, 'value': cod}
            for cod, dep in zip(divipola_departamentos["COD_DEPARTAMENTO"], divipola_departamentos["DEPARTAMENTO"])
        ],
        value=int(divipola_departamentos["COD_DEPARTAMENTO"].iloc[0])
    ),

    dcc.Graph(id='grafico_mortalidad'),

    html.Div(id='info')
])

# =======================
# Callbacks
# =======================
@app.callback(
    Output('grafico_mortalidad', 'figure'),
    Output('info', 'children'),
    Input('departamento', 'value')
)
def actualizar(departamento):
    # Filtrar datos
    df_filtrado = df1[df1["COD_DEPARTAMENTO"] == int(departamento)]

    if df_filtrado.empty:
        return px.scatter(title="Sin datos para este departamento"), "⚠️ No hay datos disponibles."

    # Ejemplo de gráfico: muertes por sexo
    fig = px.histogram(
        df_filtrado,
        x="SEXO",
        title=f"Distribución de muertes por sexo — Departamento {departamento}",
        color="SEXO"
    )

    total = len(df_filtrado)
    return fig, f"Total de registros en este departamento: {total}"

# =======================
# Run
# =======================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)


