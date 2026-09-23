# pip install dash pandas plotly gunicorn

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output

# -----------------------------------------------------------
# Paleta e tokens
# -----------------------------------------------------------
AZUL_ACO = "#4A5B79"
AZUL_ESCURO = "#2F3B52"
TERRACOTA = "#A05D22"
TERRACOTA_CLARO = "#F3E3D3"
DOURADO = "#CEAD63"
CREME = "#FAF7F2"
TEXTO = "#2D2A26"
TEXTO_SUAVE = "#8A8378"
PALETA_LINHAS = [AZUL_ACO, TERRACOTA, DOURADO, "#7A8B6F", "#8C6E5A", "#5C7A8A", "#B08968", "#3F5765"]

# -----------------------------------------------------------
# Dados
# -----------------------------------------------------------
df = pd.read_csv("resultado_final.csv", dtype={"CNES": str})
df["COMPETENCIA"] = df["ANO"].astype(str) + "-" + df["MES"].astype(str).str.zfill(2)

lista_ubs = sorted(df["NOME_ESTABELECIMENTO"].dropna().unique())
lista_anos = sorted(df["ANO"].dropna().unique().tolist())
lista_procedimentos = sorted(df["NO_PROCEDIMENTO"].dropna().unique())

UBS_PADRAO = ["UBS NOVO CAMINHO", "UBS VILA DAS BELEZAS ALBERTO AMBROSIO"]
ubs_padrao_validas = [u for u in UBS_PADRAO if u in lista_ubs]

if len(ubs_padrao_validas) < len(UBS_PADRAO):
    faltando = set(UBS_PADRAO) - set(ubs_padrao_validas)
    print(f"Aviso: não encontrei na base os nomes: {faltando}")


def competencias_completas(dados):
    periodos = pd.to_datetime(dados["COMPETENCIA"], format="%Y-%m")
    intervalo = pd.period_range(periodos.min(), periodos.max(), freq="M")
    return [p.strftime("%Y-%m") for p in intervalo]


def abreviar(texto, limite=35):
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0] + "…"


def aplicar_filtros(ubs_selecionadas, anos_selecionados, procedimentos_selecionados=None):
    dados = df.copy()
    if ubs_selecionadas:
        dados = dados[dados["NOME_ESTABELECIMENTO"].isin(ubs_selecionadas)]
    if anos_selecionados:
        dados = dados[dados["ANO"].isin(anos_selecionados)]
    if procedimentos_selecionados:
        dados = dados[dados["NO_PROCEDIMENTO"].isin(procedimentos_selecionados)]
    return dados


def calcular_impacto(dados, meses_completos):
    serie = dados.groupby(["NO_PROCEDIMENTO", "COMPETENCIA"])["QTD_APROVADA"].sum().reset_index()
    resultado = []
    for proc, grupo in serie.groupby("NO_PROCEDIMENTO"):
        completo = grupo.set_index("COMPETENCIA")["QTD_APROVADA"].reindex(meses_completos, fill_value=0)
        resultado.append({"NO_PROCEDIMENTO": proc, "DIFF_ABS": completo.iloc[-1] - completo.iloc[0]})
    return pd.DataFrame(resultado)


# -----------------------------------------------------------
# App
# -----------------------------------------------------------
app = Dash(__name__)
app.title = "Produção SIA — Evolução de Procedimentos"
server = app.server

app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; }
            body { margin: 0; }
            .stat-card { transition: transform 0.15s ease; }
            .stat-card:hover { transform: translateY(-2px); }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>
"""

FONTE_TITULO = "'Fredoka', sans-serif"
FONTE_CORPO = "'Inter', sans-serif"


def kpi_card(valor_id, rotulo, cor_fundo, cor_texto):
    return html.Div(
        className="stat-card",
        style={"background": cor_fundo, "borderRadius": "20px", "padding": "20px 24px",
               "flex": "1", "minWidth": "180px"},
        children=[
            html.Div(id=valor_id, style={
                "fontFamily": FONTE_TITULO, "fontSize": "32px", "fontWeight": "600", "color": cor_texto,
            }),
            html.Div(rotulo, style={
                "fontFamily": FONTE_CORPO, "fontSize": "13px", "color": cor_texto, "opacity": 0.85, "marginTop": "2px",
            }),
        ],
    )


app.layout = html.Div(
    style={"fontFamily": FONTE_CORPO, "background": CREME, "minHeight": "100vh"},
    children=[

        # ---------- Cabeçalho ----------
        html.Div(
            style={"maxWidth": "1200px", "margin": "0 auto", "padding": "44px 32px 20px"},
            children=[
                html.Div(style={"display": "flex", "gap": "8px", "marginBottom": "12px"}, children=[
                    html.Div("SIA-SUS", style={
                        "display": "inline-block", "background": DOURADO, "color": TEXTO,
                        "fontFamily": FONTE_TITULO, "fontWeight": "600", "fontSize": "12px",
                        "padding": "4px 12px", "borderRadius": "999px",
                    }),
                    html.Div("MVP — versão piloto", style={
                        "display": "inline-block", "background": "transparent", "color": TEXTO_SUAVE,
                        "fontFamily": FONTE_CORPO, "fontWeight": "500", "fontSize": "12px",
                        "padding": "4px 12px", "border": f"1px solid {TEXTO_SUAVE}", "borderRadius": "999px",
                    }),
                ]),
                html.H1("Evolução de Procedimentos SUS", style={
                    "fontFamily": FONTE_TITULO, "fontWeight": "700", "fontSize": "40px", "margin": "0",
                    "color": AZUL_ACO,
                }),
                html.P("Como a produção variou no tempo e quais procedimentos mais mudaram",
                       style={"color": TEXTO_SUAVE, "fontSize": "15px", "marginTop": "8px", "marginBottom": "0"}),
            ],
        ),

        html.Div(style={"maxWidth": "1200px", "margin": "0 auto", "padding": "0 32px 48px"}, children=[

            # ---------- KPIs ----------
            html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "24px"}, children=[
                kpi_card("kpi-total", "Quantidade de procedimentos realizados",
                         f"linear-gradient(135deg, {AZUL_ESCURO}, {AZUL_ACO})", "#ffffff"),
                kpi_card("kpi-estabelecimentos", "Estabelecimentos selecionados",
                         f"linear-gradient(135deg, {DOURADO}, #E4C079)", TEXTO),
                kpi_card("kpi-procedimentos-distintos", "Procedimentos distintos",
                         f"linear-gradient(135deg, {TERRACOTA}, #7A431A)", "#ffffff"),
            ]),

            # ---------- Fonte dos dados ----------
            html.Div(
                style={"background": "#fbf8f2", "borderLeft": f"5px solid {DOURADO}",
                       "borderRadius": "16px", "padding": "16px 24px", "marginBottom": "24px"},
                children=[
                    html.H3("Dados extraídos do SIA-SUS (Sistema de Informações Ambulatoriais do SUS)", style={
                        "fontFamily": FONTE_TITULO, "color": TEXTO, "fontWeight": "600",
                        "fontSize": "16px", "margin": "0",
                    }),
                ],
            ),

            # ---------- Filtros ----------
            html.Div(
                style={"background": "#ffffff", "borderRadius": "16px", "padding": "20px 24px",
                       "marginBottom": "24px", "border": "1px solid rgba(0,0,0,0.06)"},
                children=[
                    html.Div(style={"display": "flex", "gap": "24px", "flexWrap": "wrap"}, children=[
                        html.Div(style={"flex": "2", "minWidth": "280px"}, children=[
                            html.Label("Estabelecimento(s)", style={
                                "fontFamily": FONTE_TITULO, "fontWeight": "600", "color": TEXTO, "fontSize": "14px",
                            }),
                            dcc.Dropdown(
                                id="filtro-ubs",
                                options=[{"label": u, "value": u} for u in lista_ubs],
                                value=ubs_padrao_validas, multi=True,
                                placeholder="Selecione um ou mais estabelecimentos",
                            ),
                        ]),
                        html.Div(style={"flex": "1", "minWidth": "200px"}, children=[
                            html.Label("Ano", style={
                                "fontFamily": FONTE_TITULO, "fontWeight": "600", "color": TEXTO, "fontSize": "14px",
                            }),
                            dcc.Checklist(
                                id="filtro-ano",
                                options=[{"label": f" {a}", "value": a} for a in lista_anos],
                                value=lista_anos, inline=True,
                                style={"marginTop": "10px"},
                                inputStyle={"marginRight": "5px", "marginLeft": "10px"},
                            ),
                        ]),
                        html.Div(style={"flex": "2", "minWidth": "280px"}, children=[
                            html.Label("Procedimento(s)", style={
                                "fontFamily": FONTE_TITULO, "fontWeight": "600", "color": TEXTO, "fontSize": "14px",
                            }),
                            dcc.Dropdown(
                                id="filtro-procedimento",
                                options=[{"label": p, "value": p} for p in lista_procedimentos],
                                value=[], multi=True,
                                placeholder="Todos os procedimentos (deixe em branco para não filtrar)",
                            ),
                        ]),
                    ]),
                ],
            ),

            # ---------- Tendência geral ----------
            html.Div(
                style={"background": "#ffffff", "borderRadius": "16px", "padding": "24px",
                       "marginBottom": "24px", "borderLeft": f"5px solid {AZUL_ACO}"},
                children=[
                    html.H3("Tendência geral por estabelecimento", style={
                        "fontFamily": FONTE_TITULO, "color": TEXTO, "marginTop": "0", "fontWeight": "600",
                    }),
                    dcc.Graph(id="grafico-tendencia-geral"),
                ],
            ),

            # ---------- Ranking de impacto ----------
            html.Div(
                style={"background": "#ffffff", "borderRadius": "16px", "padding": "24px",
                       "marginBottom": "24px", "borderLeft": f"5px solid {TERRACOTA}"},
                children=[
                    html.Div(
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center",
                               "flexWrap": "wrap", "gap": "12px"},
                        children=[
                            html.H3("Procedimentos mais impactados", style={
                                "fontFamily": FONTE_TITULO, "color": TEXTO, "margin": "0", "fontWeight": "600",
                            }),
                            html.Div(style={"minWidth": "220px"}, children=[
                                dcc.Slider(id="top-n", min=5, max=15, step=5, value=10,
                                           marks={5: "5", 10: "10", 15: "15"}),
                            ]),
                        ],
                    ),
                    html.P("Variação absoluta entre o primeiro e o último mês do período selecionado",
                           style={"color": TEXTO_SUAVE, "fontSize": "13px", "marginTop": "4px"}),
                    dcc.Graph(id="grafico-ranking-impacto"),
                ],
            ),

            # ---------- Small multiples ----------
            html.Div(
                style={"background": "#ffffff", "borderRadius": "16px", "padding": "24px",
                       "borderTop": f"5px solid {DOURADO}"},
                children=[
                    html.H3("Tendência individual dos mais impactados", style={
                        "fontFamily": FONTE_TITULO, "color": TEXTO, "marginTop": "0", "fontWeight": "600",
                    }),
                    dcc.Graph(id="grafico-small-multiples"),
                ],
            ),
        ]),
    ],
)


# -----------------------------------------------------------
# Callbacks
# -----------------------------------------------------------
@app.callback(
    Output("kpi-total", "children"),
    Output("kpi-estabelecimentos", "children"),
    Output("kpi-procedimentos-distintos", "children"),
    Input("filtro-ubs", "value"),
    Input("filtro-ano", "value"),
    Input("filtro-procedimento", "value"),
)
def atualizar_kpis(ubs_selecionadas, anos_selecionados, procedimentos_selecionados):
    dados = aplicar_filtros(ubs_selecionadas, anos_selecionados, procedimentos_selecionados)
    if dados.empty:
        return "0", "0", "0"
    total = f"{dados['QTD_APROVADA'].sum():,.0f}".replace(",", ".")
    n_estab = str(len(ubs_selecionadas or []))
    n_procedimentos_distintos = str(dados["NO_PROCEDIMENTO"].nunique())
    return total, n_estab, n_procedimentos_distintos


@app.callback(
    Output("grafico-tendencia-geral", "figure"),
    Input("filtro-ubs", "value"),
    Input("filtro-ano", "value"),
    Input("filtro-procedimento", "value"),
)
def atualizar_tendencia_geral(ubs_selecionadas, anos_selecionados, procedimentos_selecionados):
    dados = aplicar_filtros(ubs_selecionadas, anos_selecionados, procedimentos_selecionados)
    if dados.empty:
        return go.Figure()
    meses = competencias_completas(dados)

    fig = go.Figure()
    for i, ubs in enumerate(ubs_selecionadas or []):
        serie = (
            dados[dados["NOME_ESTABELECIMENTO"] == ubs]
            .groupby("COMPETENCIA")["QTD_APROVADA"].sum()
            .reindex(meses, fill_value=0).reset_index()
        )
        serie.columns = ["COMPETENCIA", "QTD_APROVADA"]
        fig.add_trace(go.Scatter(
            x=serie["COMPETENCIA"], y=serie["QTD_APROVADA"],
            mode="lines+markers", name=ubs,
            line=dict(color=PALETA_LINHAS[i % len(PALETA_LINHAS)], width=2.5, shape="spline"),
            marker=dict(size=7),
        ))

    fig.update_layout(
        template="plotly_white", height=420, hovermode="x unified",
        font=dict(family=FONTE_CORPO, color=TEXTO),
        xaxis_title="Competência", yaxis_title="Quantidade",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


@app.callback(
    Output("grafico-ranking-impacto", "figure"),
    Input("filtro-ubs", "value"),
    Input("filtro-ano", "value"),
    Input("filtro-procedimento", "value"),
    Input("top-n", "value"),
)
def atualizar_ranking(ubs_selecionadas, anos_selecionados, procedimentos_selecionados, top_n):
    dados = aplicar_filtros(ubs_selecionadas, anos_selecionados, procedimentos_selecionados)
    if dados.empty:
        return go.Figure()
    meses = competencias_completas(dados)
    impacto = calcular_impacto(dados, meses)
    if impacto.empty:
        return go.Figure()

    top = impacto.reindex(impacto["DIFF_ABS"].abs().sort_values(ascending=False).index).head(top_n)
    top = top.sort_values("DIFF_ABS")
    top["NOME_ABREVIADO"] = top["NO_PROCEDIMENTO"].apply(lambda t: abreviar(t, limite=45))
    cores = [TERRACOTA if v >= 0 else AZUL_ACO for v in top["DIFF_ABS"]]

    fig = go.Figure(go.Bar(
        x=top["DIFF_ABS"], y=top["NOME_ABREVIADO"], orientation="h",
        marker_color=cores, marker_cornerradius=8,
        text=[f"{v:+.0f}" for v in top["DIFF_ABS"]], textposition="outside",
        customdata=top["NO_PROCEDIMENTO"],
        hovertemplate="<b>%{customdata}</b><br>Variação: %{x:+.0f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", height=100 + top_n * 35,
        font=dict(family=FONTE_CORPO, color=TEXTO),
        margin=dict(l=20, r=20, t=10, b=20), showlegend=False,
        xaxis_title="Variação absoluta (último mês − primeiro mês)",
    )
    return fig


@app.callback(
    Output("grafico-small-multiples", "figure"),
    Input("filtro-ubs", "value"),
    Input("filtro-ano", "value"),
    Input("filtro-procedimento", "value"),
    Input("top-n", "value"),
)
def atualizar_small_multiples(ubs_selecionadas, anos_selecionados, procedimentos_selecionados, top_n):
    dados = aplicar_filtros(ubs_selecionadas, anos_selecionados, procedimentos_selecionados)
    if dados.empty:
        return go.Figure()
    meses = competencias_completas(dados)
    impacto = calcular_impacto(dados, meses)
    if impacto.empty:
        return go.Figure()

    top_procs = impacto.reindex(
        impacto["DIFF_ABS"].abs().sort_values(ascending=False).index
    ).head(min(top_n, 8))["NO_PROCEDIMENTO"].tolist()

    n_cols = 4
    n_rows = (len(top_procs) + n_cols - 1) // n_cols
    fig = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=[abreviar(p, limite=28) for p in top_procs])

    for i, proc in enumerate(top_procs):
        serie = (
            dados[dados["NO_PROCEDIMENTO"] == proc]
            .groupby("COMPETENCIA")["QTD_APROVADA"].sum()
            .reindex(meses, fill_value=0).reset_index()
        )
        serie.columns = ["COMPETENCIA", "QTD_APROVADA"]
        row, col = (i // n_cols) + 1, (i % n_cols) + 1
        fig.add_trace(
            go.Scatter(x=serie["COMPETENCIA"], y=serie["QTD_APROVADA"],
                       mode="lines+markers", line=dict(color=DOURADO, width=2, shape="spline"),
                       marker=dict(size=4), fill="tozeroy", fillcolor="rgba(206,173,99,0.15)",
                       showlegend=False),
            row=row, col=col,
        )

    fig.update_layout(template="plotly_white", height=200 * n_rows,
                       font=dict(family=FONTE_CORPO, color=TEXTO, size=11),
                       margin=dict(l=20, r=20, t=40, b=20))
    fig.update_annotations(font_size=11, font_family=FONTE_CORPO)
    fig.update_xaxes(showticklabels=False)
    return fig


if __name__ == "__main__":
    app.run(debug=False)