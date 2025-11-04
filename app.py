import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px

# Cargar los datos
df1 = pd.read_excel("data/Anexo1.NoFetal2019_CE_15-03-23.xlsx")
df2 = pd.read_excel("data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
df3 = pd.read_excel("data/Divipola_CE_.xlsx")

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Mortalidad Colombia 2019"),
    dcc.Dropdown(
        id="departamento",
        options=[{"label": dep, "value": dep} for dep in sorted(df3["DEPARTAMENTO"].unique())],
        value=sorted(df3["DEPARTAMENTO"].unique())[0]
    ),
    dcc.Graph(id="grafico")
])

@app.callback(
    Output("grafico", "figure"),
    Input("departamento", "value")
)
def actualizar(departamento):
    df_filtrado = df1[df1["DPTO"] == departamento]
    fig = px.bar(df_filtrado, x="MUNICIPIO", y="DEFUNCIONES", title=f"Defunciones en {departamento}")
    return fig

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8080, debug=True)
