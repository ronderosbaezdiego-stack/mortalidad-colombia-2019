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
divipola = divipola.rename(columns=lambda x: x.strip().upper())

if "COD_DEPARTAMENTO" not in df1.columns:
    raise Exception("No se encontró la columna COD_DEPARTAMENTO en el archivo principal.")

if "COD_DPTO" in divipola.columns:
    divipola["COD_DEPARTAMENTO"] = divipola["COD_DPTO"]

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
    html.H1("Mortalidad Colombia 2019", style={'textAlign': 'center'}),

    html.Label("Selecciona un departamento:"),
    dcc.Dropdown(
        id='departamento',
        options=[
            {'label': dep, 'value': cod}
            for cod, dep in zip(divipola_departamentos["COD_DEPARTAMENTO"], divipola_departamentos["DEPARTAMENTO"])
        ],
        value=int(divipola_departamentos["COD_DEPARTAMENTO"].iloc[0])
    ),

    dcc.Graph(id='grafico_sexo'),
    dcc.Graph(id='grafico_mes'),
    dcc.Graph(id='grafico_municipios'),

    html.Div(id='info')
])

# =======================
# Callbacks
# =======================
@app.callback(
    Output('grafico_sexo', 'figure'),
    Output('grafico_mes', 'figure'),
    Output('grafico_municipios', 'figure'),
    Output('info', 'children'),
    Input('departamento', 'value')
)
def actualizar(departamento):
    df_filtrado = df1[df1["COD_DEPARTAMENTO"] == int(departamento)]

    if df_filtrado.empty:
        empty_fig = px.scatter(title="Sin datos para este departamento")
        return empty_fig, empty_fig, empty_fig, "No hay datos disponibles."

    # Gráfico 1: Muertes por sexo
    fig_sexo = px.histogram(
        df_filtrado,
        x="SEXO",
        color="SEXO",
        title=f"Distribución de muertes por sexo — Departamento {departamento}"
    )

    # Gráfico 2: Muertes por mes
    df_mes = df_filtrado.groupby("MES")["COD_DANE"].count().reset_index()
    fig_mes = px.line(
        df_mes,
        x="MES",
        y="COD_DANE",
        markers=True,
        title=f"Muertes por mes — Departamento {departamento}",
        labels={"COD_DANE": "Total de muertes"}
    )

    # Gráfico 3: Top 5 municipios con más muertes
    df_mun = df_filtrado.groupby("COD_MUNICIPIO")["COD_DANE"].count().reset_index()
    df_mun = df_mun.sort_values(by="COD_DANE", ascending=False).head(5)
    fig_mun = px.bar(
        df_mun,
        x="COD_MUNICIPIO",
        y="COD_DANE",
        title=f"Top 5 municipios con más muertes — Departamento {departamento}",
        labels={"COD_DANE": "Total de muertes", "COD_MUNICIPIO": "Código Municipio"}
    )

    total = len(df_filtrado)
    return fig_sexo, fig_mes, fig_mun, f"Total de registros en este departamento: {total}"

# =======================
# Run
# =======================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)



