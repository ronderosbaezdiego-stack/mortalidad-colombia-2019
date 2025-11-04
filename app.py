# app.py
"""
Dashboard Dash: Análisis de mortalidad Colombia 2019
Lee (desde /mnt/data o relative path):
 - Anexo1.NoFetal2019_CE_15-03-23.xlsx   (microdatos de defunciones 2019)
 - Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx (catálogo códigos CIE-10)
 - Divipola_CE_.xlsx                      (nombres y códigos de dpt/municipio)
Opcional:
 - /mnt/data/city_population.csv         (city,population) para índices por 100k
 - data/colombia_departments.geojson     (geojson para mapa por departamentos)
Uso: subir repo a GitHub + desplegar en Render/Railway/GCP/AWS.
"""

import os
import json
import pandas as pd
import numpy as np

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px

# ---------------------- RUTAS Y ARCHIVOS ----------------------
ANEXO1 = "/mnt/data/Anexo1.NoFetal2019_CE_15-03-23.xlsx"
ANEXO2 = "/mnt/data/Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx"
DIVIPOLA = "/mnt/data/Divipola_CE_.xlsx"
POP_CSV = "/mnt/data/city_population.csv"          # opcional
GEOJSON_PATH = "data/colombia_departments.geojson"  # opcional (mejor para mapa)

# ---------------------- UTILIDADES ----------------------
def find_column_like(cols, patterns):
    """Devuelve la primera columna cuyo nombre contenga alguna de las patterns (case-insensitive)."""
    lower = [c.lower() for c in cols]
    for p in patterns:
        for c, lc in zip(cols, lower):
            if p.lower() in lc:
                return c
    return None

# ---------------------- CARGA Y LIMPIEZA ----------------------
# Validar archivos obligatorios
for path in [ANEXO1, ANEXO2, DIVIPOLA]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No encontré el archivo requerido: {path}. Colócalo en /mnt/data/")

# Leer microdatos (Anexo1)
df_raw = pd.read_excel(ANEXO1, engine="openpyxl")
df_raw.columns = df_raw.columns.str.strip()

# Revisado: Anexo1 tiene (según lo que enviaste):
# COD_DANE,COD_DEPARTAMENTO,COD_MUNICIPIO,AREA_DEFUNCION,SITIO_DEFUNCION,AÑO,MES,HORA,MINUTOS,SEXO,ESTADO_CIVIL,
# GRUPO_EDAD1,NIVEL_EDUCATIVO,MANERA_MUERTE,COD_MUERTE,IDPROFESIONAL

# Columnas requeridas para análisis:
required = ["COD_DEPARTAMENTO", "COD_MUNICIPIO", "AÑO", "MES", "COD_MUERTE", "SEXO", "GRUPO_EDAD1"]
miss = [c for c in required if c not in df_raw.columns]
if miss:
    raise ValueError(f"Faltan columnas esenciales en Anexo1: {miss}")

# Normalizar y crear variables útiles
df = df_raw.copy()
df["year"] = pd.to_numeric(df["AÑO"], errors="coerce").astype("Int64")
df["month"] = pd.to_numeric(df["MES"], errors="coerce").astype("Int64")
df = df[df["year"] == 2019].copy()  # filtrar 2019

# Formato de códigos: depto 2 dígitos, municipio 5 dígitos (ajusta si necesario)
df["COD_DEPARTAMENTO"] = df["COD_DEPARTAMENTO"].astype(str).str.extract(r"(\d+)").fillna("").apply(lambda x: x[0].zfill(2) if x[0] != "" else "")
df["COD_MUNICIPIO"] = df["COD_MUNICIPIO"].astype(str).str.extract(r"(\d+)").fillna("").apply(lambda x: x[0].zfill(5) if x[0] != "" else "")

# causa y conteo
df["cause_code"] = df["COD_MUERTE"].astype(str).str.strip().str.upper()
df["deaths"] = 1  # cada fila = 1 muerte en microdatos

# ---------------------- CATALOGOS: ANEXO2 (CIE-10) ----------------------
codes_df = pd.read_excel(ANEXO2, engine="openpyxl")
codes_df.columns = codes_df.columns.str.strip()
# Detectar la columna con código y la de descripción a 4 caracteres (según tu encabezado)
code_col = find_column_like(codes_df.columns, ["cuatro", "4", "4 caracteres", "cuatro caracteres", "código"])
desc_col = find_column_like(codes_df.columns, ["descripcion a cuatro", "Descripcion  de códigos mortalidad a cuatro caracteres", "descripcion", "descripcion  de", "descripcion de"])
# fallback: usar la tercera/quinta columna si las detectadas no existen
if code_col is None or desc_col is None:
    # buscar columnas que contengan 'CIE' o 'código'
    code_col = code_col or find_column_like(codes_df.columns, ["cie", "codigo", "cod"])
    desc_col = desc_col or find_column_like(codes_df.columns, ["desc", "descripcion", "descripcion  "])
# Renombrar a columnas limpias
if code_col and desc_col:
    codes_df = codes_df[[code_col, desc_col]].rename(columns={code_col: "cause_code", desc_col: "cause_desc"})
else:
    # fallback: crear columnas vacías
    codes_df = pd.DataFrame(columns=["cause_code", "cause_desc"])
codes_df["cause_code"] = codes_df["cause_code"].astype(str).str.strip().str.upper()
codes_df["cause_desc"] = codes_df["cause_desc"].astype(str)

# Unir descripción de causa al microdato
df = df.merge(codes_df, on="cause_code", how="left")

# ---------------------- DIVIPOLA: nombres de departamentos y municipios ----------------------
div = pd.read_excel(DIVIPOLA, engine="openpyxl")
div.columns = div.columns.str.strip()
# Detectar columnas
dept_code_col = find_column_like(div.columns, ["cod_depart", "cod_depa", "cod_dane", "cod_dpto", "coddpto", "cod_dane"])
dept_name_col = find_column_like(div.columns, ["departamento", "depart", "nombre_dept", "nombre"])
mun_code_col = find_column_like(div.columns, ["cod_mun", "cod_municipio", "cod_muni", "cod_dane_mun"])
mun_name_col = find_column_like(div.columns, ["municipio", "mun", "nombre_mun", "nombre"])

# En tu capture Divipola tiene: COD_DANE, COD_DEPARTAMENTO, DEPARTAMENTO, COD_MUNICIPIO, MUNICIPIO, FECHA1erFIS
# así que hacemos fallback directo:
if "COD_DEPARTAMENTO" in div.columns and "DEPARTAMENTO" in div.columns:
    dept_code_col = "COD_DEPARTAMENTO"
    dept_name_col = "DEPARTAMENTO"
if "COD_MUNICIPIO" in div.columns and "MUNICIPIO" in div.columns:
    mun_code_col = "COD_MUNICIPIO"
    mun_name_col = "MUNICIPIO"

# Construir df de mapping
if dept_code_col and dept_name_col:
    divipola_dept = div[[dept_code_col, dept_name_col]].drop_duplicates().rename(columns={dept_code_col: "dept_code_raw", dept_name_col: "dept_name"})
    # normalizar codigo
    divipola_dept["dept_code"] = divipola_dept["dept_code_raw"].astype(str).str.extract(r"(\d+)").fillna("").apply(lambda x: x[0].zfill(2) if x[0] != "" else "")
    divipola_dept = divipola_dept[["dept_code", "dept_name"]]
else:
    divipola_dept = pd.DataFrame(columns=["dept_code", "dept_name"])

if mun_code_col and mun_name_col:
    divipola_mun = div[[mun_code_col, mun_name_col, dept_code_col]].drop_duplicates().rename(columns={mun_code_col: "mun_code_raw", mun_name_col: "mun_name", dept_code_col: "dept_code_raw"})
    divipola_mun["mun_code"] = divipola_mun["mun_code_raw"].astype(str).str.extract(r"(\d+)").fillna("").apply(lambda x: x[0].zfill(5) if x[0] != "" else "")
    divipola_mun["dept_code"] = divipola_mun["dept_code_raw"].astype(str).str.extract(r"(\d+)").fillna("").apply(lambda x: x[0].zfill(2) if x[0] != "" else "")
    divipola_mun = divipola_mun[["mun_code", "mun_name", "dept_code"]]
else:
    divipola_mun = pd.DataFrame(columns=["mun_code", "mun_name", "dept_code"])

# Unir al microdato por códigos
df = df.merge(divipola_dept, left_on="COD_DEPARTAMENTO", right_on="dept_code", how="left")
df = df.merge(divipola_mun, left_on=["COD_MUNICIPIO", "COD_DEPARTAMENTO"], right_on=["mun_code", "dept_code"], how="left")

# Si mun_name es NaN, rellenar con el código para evitar valores vacíos en gráficos
df["city"] = df["mun_name"].fillna(df["COD_MUNICIPIO"].astype(str))
df["department"] = df["dept_name"].fillna(df["COD_DEPARTAMENTO"].astype(str))

# ---------------------- AGREGACIONES PARA VISUALIZACIONES ----------------------
# 1) Mapa (muertes por departamento)
dept_agg = df.groupby("department", as_index=False)["deaths"].sum().sort_values("deaths", ascending=False)

# 2) Serie por mes
monthly = df.groupby("month", as_index=False)["deaths"].sum().reindex(range(1,13), fill_value=0)
if "month" not in monthly.columns:
    # fallback si reindex no produjo la forma esperada
    monthly = df.groupby("month", as_index=False)["deaths"].sum()
all_months = pd.DataFrame({"month": list(range(1,13))})
monthly = all_months.merge(monthly, on="month", how="left").fillna(0)
monthly["deaths"] = monthly["deaths"].astype(int)

# 3) Top 5 ciudades más violentas (homicidios)
# Identificamos homicidios por códigos y por descripción (X93-X95, X85-Y09, palabras claves)
def is_homicide(code, desc):
    if pd.isna(code):
        code = ""
    code = str(code).upper().strip()
    desc = (str(desc) if not pd.isna(desc) else "").lower()
    # casos explícitos
    if any(code.startswith(prefix) for prefix in ["X93", "X94", "X95"]):
        return True
    # rango agresión X85-Y09 (approx): escoger por prefijo 'X' or 'Y' and numeric between 85 and 99/09
    if code.startswith(("X", "Y")):
        # Solo heurística: tratar X85..X99 y Y00..Y09
        try:
            num = int(''.join(filter(str.isdigit, code)))
            # Si extracción numérica produjo algo plausible, considerar como agresión si num >=85 (heurística)
            if num >= 85:
                return True
        except Exception:
            pass
    # palabras clave en la descripción
    keywords = ["homicidio", "agres", "disparo", "arma de fuego", "asesin", "lesión por arma"]
    for kw in keywords:
        if kw in desc:
            return True
    return False

df["is_homicide"] = df.apply(lambda r: is_homicide(r.get("cause_code",""), r.get("cause_desc","")), axis=1)
hom_df = df[df["is_homicide"]].copy()
top5_hom = hom_df.groupby("city", as_index=False)["deaths"].sum().sort_values("deaths", ascending=False).head(5)

# 4) Bottom 10 ciudades por índice de mortalidad (por 100k si hay población)
city_agg = df.groupby("city", as_index=False)["deaths"].sum()
if os.path.exists(POP_CSV):
    pop = pd.read_csv(POP_CSV)
    pop.columns = pop.columns.str.strip()
    city_col = find_column_like(pop.columns, ["city", "municipio", "nombre"])
    pop_col = find_column_like(pop.columns, ["pop", "population", "poblacion"])
    if city_col and pop_col:
        pop = pop[[city_col, pop_col]].rename(columns={city_col: "city", pop_col: "population"})
        pop["city_key"] = pop["city"].astype(str).str.lower().str.strip()
        city_agg["city_key"] = city_agg["city"].astype(str).str.lower().str.strip()
        merged = city_agg.merge(pop[["city_key", "population"]], on="city_key", how="left")
        merged["population"] = pd.to_numeric(merged["population"], errors="coerce")
        merged["mortality_per_100k"] = (merged["deaths"] / merged["population"]) * 100000
        merged["rank_metric"] = merged["mortality_per_100k"].fillna(merged["deaths"])
        bottom10 = merged.sort_values("rank_metric", ascending=True).head(10)
    else:
        bottom10 = city_agg.sort_values("deaths", ascending=True).head(10)
else:
    bottom10 = city_agg.sort_values("deaths", ascending=True).head(10)

# 5) Tabla top 10 causas (codigo + descripcion + total)
cause_agg = df.groupby(["cause_code", "cause_desc"], as_index=False)["deaths"].sum().sort_values("deaths", ascending=False)
top10_causes = cause_agg.head(10).copy()

# 6) Barras apiladas: muertes por sexo en cada departamento
sex_dept = df.groupby(["department", "SEXO"], as_index=False)["deaths"].sum()
# Asegurar que 'SEXO' tenga valores consistentes (M/F/o otros)
sex_dept["SEXO"] = sex_dept["SEXO"].astype(str).str.strip().replace({"M":"Masculino","F":"Femenino","m":"Masculino","f":"Femenino"})

# 7) Histograma por GRUPO_EDAD1 según la tabla de referencia
# Mapear GRUPO_EDAD1 a etiqueta textual
age_map = {
    # num codes per your mapping; keys are strings or ints depending column type
    0: "0? (desconocido)",
    1: "0-4: Mortalidad neonatal? (ver tabla)",  # placeholder if codes differ
    # We'll implement the mapping according to the table you gave:
    # Códigos DANE (GRUPO_EDAD1) -> rango aproximado
}
# Mejor: codificamos explicitamente las categorías si GRUPO_EDAD1 va de 0..29 (según tu tabla)
# Crearemos una función que mapea el entero a la etiqueta apropiada:
def map_age_group(code):
    try:
        c = int(code)
    except Exception:
        return "Sin info"
    if c in [0, 4]:
        return "Mortalidad neonatal (menor 1 mes)"
    if c in [5,6]:
        return "Mortalidad infantil (1-11 meses)"
    if c in [7,8]:
        return "Primera infancia (1-4 años)"
    if c in [9,10]:
        return "Niñez (5-14 años)"
    if c == 11:
        return "Adolescencia (15-19)"
    if c in [12,13]:
        return "Juventud (20-29)"
    if c in [14,15,16]:
        return "Adultez temprana (30-44)"
    if c in [17,18,19]:
        return "Adultez intermedia (45-59)"
    if c in [20,21,22,23,24]:
        return "Vejez (60-84)"
    if c in [25,26,27,28]:
        return "Longevidad (85+)"
    if c == 29:
        return "Edad desconocida"
    return "Otro"

df["age_group_label"] = df["GRUPO_EDAD1"].apply(map_age_group)

# ---------------------- FIGURAS PLOTLY ----------------------
# MAPA / CHOROPLETH
map_fig = None
if os.path.exists(GEOJSON_PATH):
    try:
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            gj = json.load(f)
        # detectar featureidkey (property con nombre departamento)
        sample_props = gj.get("features", [])[0].get("properties", {}) if gj.get("features") else {}
        possible = ["NOMBRE_DPT", "NOM_DPT", "departamento", "NAME_1", "NOMBRE", "name"]
        featureidkey = None
        for p in possible:
            if p in sample_props:
                featureidkey = f"properties.{p}"
                break
        featureidkey = featureidkey or "properties.name"
        # crear fig
        map_fig = px.choropleth(
            dept_agg,
            geojson=gj,
            locations="department",
            color="deaths",
            featureidkey=featureidkey,
            projection="mercator",
            title="Muertes totales por departamento (2019)",
            hover_name="department"
        )
        map_fig.update_geos(fitbounds="locations", visible=False)
        map_fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    except Exception as e:
        print("Error cargando GeoJSON para mapa:", e)
        map_fig = None

# fallback: barras por departamento
if map_fig is None:
    map_fig = px.bar(dept_agg.sort_values("deaths", ascending=True),
                     x="deaths", y="department", orientation="h",
                     title="(Fallback) Muertes por departamento - 2019",
                     labels={"deaths":"Muertes", "department":"Departamento"})

# Linea por mes
line_fig = px.line(monthly, x="month", y="deaths", markers=True,
                   title="Muertes por mes en Colombia (2019)",
                   labels={"month":"Mes", "deaths":"Muertes"})
line_fig.update_xaxes(tickmode="array", tickvals=list(range(1,13)),
                      ticktext=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"])

# Top5 homicidios (barras)
if top5_hom.empty:
    bar_hom = px.bar(title="No se identificaron homicidios con los criterios actuales")
else:
    bar_hom = px.bar(top5_hom, x="city", y="deaths",
                     title="Top 5 ciudades más violentas (homicidios) - 2019",
                     labels={"city":"Ciudad", "deaths":"Muertes por homicidio"})

# Pie bottom10
if isinstance(bottom10, pd.DataFrame) and not bottom10.empty:
    if "mortality_per_100k" in bottom10.columns:
        pie_values = bottom10["mortality_per_100k"].fillna(0)
        pie_labels = bottom10["city"]
        pie_title = "10 ciudades con menor índice de mortalidad (por 100k) - 2019"
    else:
        pie_values = bottom10["deaths"]
        pie_labels = bottom10["city"]
        pie_title = "10 ciudades con menos muertes absolutas - 2019"
    pie_fig = px.pie(names=pie_labels, values=pie_values, title=pie_title, hole=0.3)
else:
    pie_fig = px.pie(title="No hay datos suficientes para gráfico circular")

# Tabla top10 causas (DataTable)
table_top10 = top10_causes.copy()
table_top10["cause_desc"] = table_top10["cause_desc"].fillna("Sin descripción")

# Stacked bar by sex and department
stack_fig = px.bar(sex_dept, x="department", y="deaths", color="SEXO",
                   title="Muertes por sexo en cada departamento (2019)",
                   labels={"department":"Departamento", "deaths":"Muertes", "SEXO":"Sexo"})
stack_fig.update_layout(barmode="stack", xaxis={"tickangle":-45})

# Histograma por grupos de edad (categorías definidas)
hist_fig = px.histogram(df, x="age_group_label", color="age_group_label",
                        title="Distribución de muertes por grupo de edad (GRUPO_EDAD1)",
                        labels={"age_group_label":"Grupo etario", "count":"Número de muertes"})
hist_fig.update_xaxes(tickangle=-45)
hist_fig.update_layout(showlegend=False)

# ---------------------- DASH APP ----------------------
app = dash.Dash(__name__)
server = app.server  # para render/gunicorn

app.layout = html.Div(style={"fontFamily":"Arial, sans-serif","margin":"12px"}, children=[
    html.H1("Dashboard: Mortalidad en Colombia — 2019", style={"textAlign":"center"}),
    html.P("Explora las diferentes visualizaciones. Usa los filtros para inspeccionar departamentos o municipios.",
           style={"textAlign":"center","color":"#555"}),

    # Controles globales: filtro por departamento y ciudad
    html.Div(style={"display":"flex","gap":"12px","flexWrap":"wrap","justifyContent":"center"}, children=[
        html.Div(style={"minWidth":"240px"}, children=[
            html.Label("Departamento"),
            dcc.Dropdown(
                id="dept-filter",
                options=[{"label": d, "value": d} for d in sorted(df["department"].dropna().unique())],
                placeholder="Selecciona departamento",
                clearable=True
            )
        ]),
        html.Div(style={"minWidth":"240px"}, children=[
            html.Label("Ciudad / Municipio"),
            dcc.Dropdown(
                id="city-filter",
                options=[{"label": c, "value": c} for c in sorted(df["city"].dropna().unique())],
                placeholder="Selecciona ciudad",
                clearable=True
            )
        ]),
        html.Div(style={"minWidth":"160px"}, children=[
            html.Label("Mostrar homicidios solamente"),
            dcc.Checklist(id="homicide-only", options=[{"label":"Solo homicidios", "value":"YES"}], value=[])
        ])
    ]),

    html.Hr(),

    # Primera fila: Mapa + Linea
    html.Div(style={"display":"flex","gap":"16px","flexWrap":"wrap"}, children=[
        html.Div(style={"flex":"1 1 600px","minWidth":"320px","background":"#fafafa","padding":"8px","borderRadius":"8px"}, children=[
            html.H3("Mapa / distribución por departamento"),
            dcc.Graph(id="map-graph", figure=map_fig)
        ]),
        html.Div(style={"flex":"1 1 400px","minWidth":"300px","background":"#fafafa","padding":"8px","borderRadius":"8px"}, children=[
            html.H3("Serie: muertes por mes"),
            dcc.Graph(id="line-graph", figure=line_fig)
        ])
    ]),

    # Segunda fila: barras homicidios + pie bottom10
    html.Div(style={"display":"flex","gap":"16px","flexWrap":"wrap","marginTop":"12px"}, children=[
        html.Div(style={"flex":"1 1 450px","minWidth":"300px","background":"#fafafa","padding":"8px","borderRadius":"8px"}, children=[
            html.H3("Top 5 ciudades más violentas (homicidios)"),
            dcc.Graph(id="bar-hom-graph", figure=bar_hom)
        ]),
        html.Div(style={"flex":"1 1 350px","minWidth":"300px","background":"#fafafa","padding":"8px","borderRadius":"8px"}, children=[
            html.H3("10 ciudades con menor índice de mortalidad"),
            dcc.Graph(id="pie-bottom10", figure=pie_fig)
        ])
    ]),

    # Tercera fila: tabla top10 causas + stacked sex
    html.Div(style={"display":"flex","gap":"16px","flexWrap":"wrap","marginTop":"12px"}, children=[
        html.Div(style={"flex":"1 1 500px","minWidth":"320px","background":"#fafafa","padding":"8px","borderRadius":"8px"}, children=[
            html.H3("Top 10 causas de muerte"),
            dash_table.DataTable(
                id="top10-causes-table",
                columns=[{"name":"Código","id":"cause_code"},{"name":"Descripción","id":"cause_desc"},{"name":"Total","id":"deaths"}],
                data=table_top10.to_dict("records"),
                page_size=10,
                style_table={"overflowX":"auto"},
                style_cell={"textAlign":"left", "padding":"6px"},
                style_header={"backgroundColor":"#003366","color":"white"}
            )
        ]),
        html.Div(style={"flex":"1 1 500px","minWidth":"320px","background":"#fafafa","padding":"8px","borderRadius":"8px"}, children=[
            html.H3("Muertes por sexo y departamento"),
            dcc.Graph(id="stack-sex-dept", figure=stack_fig)
        ])
    ]),

    # Cuarta fila: histograma por grupo de edad
    html.Div(style={"marginTop":"12px","background":"#fafafa","padding":"8px","borderRadius":"8px"}, children=[
        html.H3("Distribución por grupo de edad (GRUPO_EDAD1)"),
        dcc.Graph(id="age-hist", figure=hist_fig)
    ]),

    html.Div(style={"marginTop":"14px","fontSize":"13px","color":"#444"}, children=[
        html.P("Notas: El dashboard intenta inferir columnas y unir catálogos automáticamente. "
               "Para mapa geográfico real, añade un archivo GeoJSON en: 'data/colombia_departments.geojson'."),
        html.P("Para calcular índices por 100k habitantes, añade '/mnt/data/city_population.csv' con columnas 'city' y 'population'.")
    ])
])

# ---------------------- CALLBACKS (interactividad) ----------------------
@app.callback(
    Output("city-filter", "options"),
    Input("dept-filter", "value")
)
def update_cities(dept):
    if dept:
        cities = df[df["department"] == dept]["city"].dropna().unique()
        return [{"label": c, "value": c} for c in sorted(cities)]
    else:
        return [{"label": c, "value": c} for c in sorted(df["city"].dropna().unique())]

@app.callback(
    Output("map-graph", "figure"),
    [Input("dept-filter", "value"), Input("city-filter", "value"), Input("homicide-only", "value")]
)
def update_map(dept, city, homicide_only):
    dff = df.copy()
    if homicide_only:
        dff = dff[dff["is_homicide"]]
    if dept:
        dff = dff[dff["department"] == dept]
    if city:
        dff = dff[dff["city"] == city]
    agg = dff.groupby("department", as_index=False)["deaths"].sum().sort_values("deaths", ascending=False)
    # intentar usar geojson si existe
    if os.path.exists(GEOJSON_PATH):
        try:
            with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
                gj = json.load(f)
            sample_props = gj.get("features", [])[0].get("properties", {}) if gj.get("features") else {}
            for key in ["NOMBRE_DPT","NOM_DPT","departamento","NAME_1","NOMBRE","name"]:
                if key in sample_props:
                    featureidkey = f"properties.{key}"
                    break
            else:
                featureidkey = "properties.name"
            fig = px.choropleth(agg, geojson=gj, locations="department", color="deaths", featureidkey=featureidkey,
                                projection="mercator", hover_name="department", title="Muertes por departamento (filtro)")
            fig.update_geos(fitbounds="locations", visible=False)
            fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
            return fig
        except Exception:
            pass
    # fallback barras
    return px.bar(agg.sort_values("deaths", ascending=True), x="deaths", y="department", orientation="h",
                  title="Muertes por departamento (fallback)", labels={"deaths":"Muertes","department":"Departamento"})

@app.callback(
    Output("line-graph", "figure"),
    [Input("dept-filter", "value"), Input("city-filter", "value"), Input("homicide-only", "value")]
)
def update_line(dept, city, homicide_only):
    dff = df.copy()
    if homicide_only:
        dff = dff[dff["is_homicide"]]
    if dept:
        dff = dff[dff["department"] == dept]
    if city:
        dff = dff[dff["city"] == city]
    m = dff.groupby("month", as_index=False)["deaths"].sum()
    allm = pd.DataFrame({"month": list(range(1,13))})
    m = allm.merge(m, on="month", how="left").fillna(0)
    m["deaths"] = m["deaths"].astype(int)
    fig = px.line(m, x="month", y="deaths", markers=True, title="Muertes por mes (filtro)")
    fig.update_xaxes(tickmode="array", tickvals=list(range(1,13)),
                     ticktext=["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"])
    return fig

@app.callback(
    Output("bar-hom-graph", "figure"),
    [Input("dept-filter", "value"), Input("city-filter", "value")]
)
def update_hom_bar(dept, city):
    dff = df[df["is_homicide"]].copy()
    if dept:
        dff = dff[dff["department"] == dept]
    if city:
        dff = dff[dff["city"] == city]
    top5 = dff.groupby("city", as_index=False)["deaths"].sum().sort_values("deaths", ascending=False).head(5)
    if top5.empty:
        return px.bar(title="No se identificaron homicidios con el filtro aplicado")
    return px.bar(top5, x="city", y="deaths", title="Top 5 ciudades más violentas (homicidios)")

@app.callback(
    Output("pie-bottom10", "figure"),
    [Input("dept-filter", "value"), Input("city-filter", "value")]
)
def update_pie_bottom(dept, city):
    dff = df.copy()
    if dept:
        dff = dff[dff["department"] == dept]
    if city:
        dff = dff[dff["city"] == city]
    city_agg_local = dff.groupby("city", as_index=False)["deaths"].sum()
    if os.path.exists(POP_CSV):
        try:
            pop = pd.read_csv(POP_CSV)
            pop.columns = pop.columns.str.strip()
            city_col = find_column_like(pop.columns, ["city","municipio","nombre"])
            pop_col = find_column_like(pop.columns, ["pop","population","poblacion"])
            if city_col and pop_col:
                pop = pop[[city_col, pop_col]].rename(columns={city_col:"city", pop_col:"population"})
                pop["city_key"] = pop["city"].astype(str).str.lower().str.strip()
                city_agg_local["city_key"] = city_agg_local["city"].astype(str).str.lower().str.strip()
                merged = city_agg_local.merge(pop[["city_key","population"]], on="city_key", how="left")
                merged["mortality_per_100k"] = (merged["deaths"]/merged["population"])*100000
                merged["metric"] = merged["mortality_per_100k"].fillna(merged["deaths"])
                bottom10_local = merged.sort_values("metric", ascending=True).head(10)
                labels = bottom10_local["city"]
                values = bottom10_local["mortality_per_100k"].fillna(bottom10_local["deaths"])
                return px.pie(names=labels, values=values, title="10 ciudades con menor índice de mortalidad (filtro)", hole=0.3)
        except Exception:
            pass
    bottom10_local = city_agg_local.sort_values("deaths", ascending=True).head(10)
    return px.pie(names=bottom10_local["city"], values=bottom10_local["deaths"], title="10 ciudades con menos muertes (filtro)", hole=0.3)

@app.callback(
    Output("top10-causes-table", "data"),
    [Input("dept-filter", "value"), Input("city-filter", "value"), Input("homicide-only", "value")]
)
def update_causes_table(dept, city, homicide_only):
    dff = df.copy()
    if homicide_only:
        dff = dff[dff["is_homicide"]]
    if dept:
        dff = dff[dff["department"] == dept]
    if city:
        dff = dff[dff["city"] == city]
    agg = dff.groupby(["cause_code", "cause_desc"], as_index=False)["deaths"].sum().sort_values("deaths", ascending=False).head(10)
    agg["cause_desc"] = agg["cause_desc"].fillna("Sin descripción")
    return agg.to_dict("records")

@app.callback(
    Output("stack-sex-dept", "figure"),
    [Input("dept-filter", "value"), Input("homicide-only", "value")]
)
def update_stack(dept, homicide_only):
    dff = df.copy()
    if homicide_only:
        dff = dff[dff["is_homicide"]]
    if dept:
        dff = dff[dff["department"] == dept]
    sagg = dff.groupby(["department", "SEXO"], as_index=False)["deaths"].sum()
    sagg["SEXO"] = sagg["SEXO"].astype(str).str.strip().replace({"M":"Masculino","F":"Femenino","m":"Masculino","f":"Femenino"})
    if sagg.empty:
        return px.bar(title="Sin datos para mostrar")
    fig = px.bar(sagg, x="department", y="deaths", color="SEXO", title="Muertes por sexo y departamento (filtro)")
    fig.update_layout(barmode="stack", xaxis={"tickangle":-45})
    return fig

@app.callback(
    Output("age-hist", "figure"),
    [Input("dept-filter", "value"), Input("city-filter", "value")]
)
def update_hist(dept, city):
    dff = df.copy()
    if dept:
        dff = dff[dff["department"] == dept]
    if city:
        dff = dff[dff["city"] == city]
    if dff.empty:
        return px.histogram(title="Sin datos")
    fig = px.histogram(dff, x="age_group_label", color="age_group_label", title="Distribución por grupo de edad (filtro)")
    fig.update_layout(showlegend=False)
    fig.update_xaxes(tickangle=-45)
    return fig

# ---------------------- RUN ----------------------
if __name__ == "__main__":
    # debug=True para desarrollo; en producción Render usará gunicorn y no entrará aquí
    app.run_server(host="0.0.0.0", port=8050, debug=True)

