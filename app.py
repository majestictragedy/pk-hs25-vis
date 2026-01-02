import dash
from dash import dcc, html, Input, Output
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
import textwrap
import os

# --- 1. DATEN LADEN ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, 'data')
file_path_1 = os.path.join(data_dir, '2.6_Datensatz Visualisierung_V15.xls')
file_path_2 = os.path.join(data_dir, 'Module_Data.xlsx')

if os.path.exists(file_path_1):
    df = pd.read_excel(file_path_1)
elif os.path.exists(file_path_2):
    df = pd.read_excel(file_path_2)
else:
    print("FEHLER: Keine Excel-Datei gefunden!")
    exit()

df = df.fillna('')
df['Modul_ID'] = df['Modul_ID'].astype(str).str.strip()
df['ECTS'] = pd.to_numeric(df['ECTS'], errors='coerce').fillna(0)
valid_ids = set(df['Modul_ID'].unique())

def wrap_text(text, width=60):
    return '<br>'.join(textwrap.wrap(str(text), width=width))

all_tags = set()
for tags in df['Tags']:
    if tags:
        for t in str(tags).split(';'):
            all_tags.add(t.strip())
sorted_tags = sorted(list(all_tags))

semester_options = [{'label': f'Semester {i}', 'value': str(i)} for i in range(1, 7)]
semester_options.append({'label': 'Alle Semester', 'value': 'ALL'})

# --- DESIGN & FARBEN ---
external_stylesheets = ['https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap']

COLORS = {
    'gold_light': '#f4eee3',
    'gold_normal': '#b39048',
    'gold_dark': '#7a7760',
    'blue_light': '#bedae8',
    'blue_normal': '#4b92a4',
    'blue_dark': '#2b6777',
    'text': '#212529',
    'bg': '#ffffff'
}

GROUP_COLORS = {
    'Informatik': COLORS['blue_normal'],
    'Major GLAM': COLORS['gold_normal'],
    'Major IDMM': COLORS['blue_dark'],
    'Informationswissenschaft': COLORS['gold_dark'],
    'Vertiefungsstudium': '#6c757d',
    'Methodik': '#17a2b8',
    'Betriebsökonomie': '#343a40',
    'Common': '#adb5bd',
    'Arbeits- & Forschungs-Methodik': '#7B3F52',
    'Informationsmethodik': '#8DAA91',
    'Gesellschaft und Fremdsprachen': '#D18B60'
}

# --- 2. NETZWERK BERECHNEN ---
G = nx.DiGraph()
for index, row in df.iterrows():
    # HIER: 'resp' (Verantwortlich) hinzugefügt!
    G.add_node(row['Modul_ID'], 
               label=row['Modul_Name'], 
               group=row['Modulgruppe'], 
               desc=row['Kurzbeschreibung'], 
               goals=row['Lernziele'], 
               semester=row['Semester'],
               resp=row['Verantwortlich']) 

for index, row in df.iterrows():
    source = row['Modul_ID']
    if row['Voraussetzung_Hard']:
        for t in str(row['Voraussetzung_Hard']).split(';'):
            if t.strip() in valid_ids: G.add_edge(t.strip(), source, type='hard')
    if row['Voraussetzung_Soft']:
        for t in str(row['Voraussetzung_Soft']).split(';'):
            if t.strip() in valid_ids: G.add_edge(t.strip(), source, type='soft')

pos = nx.spring_layout(G, k=3.5, iterations=300, seed=42)

# --- 3. LAYOUT ---
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

tab_style = {'borderBottom': f'1px solid {COLORS["blue_light"]}', 'padding': '15px', 'fontWeight': 'bold', 'color': COLORS['text'], 'backgroundColor': 'white', 'fontFamily': 'Roboto, sans-serif'}
tab_selected_style = {'borderTop': f'4px solid {COLORS["gold_normal"]}', 'borderBottom': '1px solid white', 'backgroundColor': 'white', 'color': COLORS['gold_normal'], 'padding': '15px', 'fontWeight': 'bold', 'fontFamily': 'Roboto, sans-serif'}
content_style = {'border': '1px solid #ddd', 'borderTop': 'none', 'padding': '20px', 'backgroundColor': 'white', 'borderRadius': '0 0 5px 5px', 'boxShadow': '0 2px 5px rgba(0,0,0,0.05)'}

app.layout = html.Div([
    html.Div([
        html.H1("Curriculum Navigator 2026", style={'fontSize': '36px','color': 'white', 'margin': '0', 'fontWeight': '300', 'letterSpacing': '1px'}),
        html.P("BSc Information Science | FH Graubünden", style={'fontSize': '20px','color': COLORS['blue_light'], 'margin': '5px 0 0 0'})
    ], style={'backgroundColor': COLORS['blue_dark'], 'padding': '20px 40px', 'width': '100%', 'boxSizing': 'border-box'}),

    html.Div([
        dcc.Tabs([
            # TAB 1: NETZWERK
            dcc.Tab(label='Modul-Netzwerk', style=tab_style, selected_style=tab_selected_style, children=[
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span("Interaktives Curriculum Erlebnis", style={'fontSize': '18px', 'color': COLORS['blue_dark'], 'fontWeight': 'bold', 'display': 'inline-block'}),
                            html.Button('↺ Ansicht zurücksetzen', id='reset-btn', n_clicks=0, style={
                                'marginLeft': '20px', 'padding': '5px 10px', 'backgroundColor': 'white', 'border': '1px solid #ccc', 'cursor': 'pointer', 'borderRadius': '3px'
                            }),
                        ], style={'display': 'inline-block'}),
                        
                        html.Div([
                            html.Label("Verbindungen anzeigen:", style={'fontSize': '14px', 'marginRight': '10px'}),
                            dcc.Checklist(
                                id='network-mode-check',
                                options=[
                                    {'label': ' Voraussetzungen (Muss)', 'value': 'hard'},
                                    {'label': ' Eingangskompetenzen (Kann)', 'value': 'soft'}
                                ],
                                value=[], 
                                inline=True,
                                style={'display': 'inline-block', 'fontSize': '14px','fontWeight': 'bold'}
                            )
                        ], style={'float': 'right', 'marginTop': '5px'}),
                        
                        html.Br(), html.Br(),
                        html.Span("Klicken", style={'fontSize': '16px', 'fontWeight': 'bold', 'color': COLORS['gold_normal']}), " Sie auf ein Modul, um seine Vernetzung und deren Abhängigkeiten im Studium hervorzuheben.",
                        html.Br(),
                        html.Br(),
                        html.Span("Legende: ", style={'fontWeight': 'bold','fontSize': '12px', 'textTransform': 'uppercase', 'color': '#7a7760', 'marginTop': '10px', 'display': 'inline-block'}),
                        html.Span(" ───► Voraussetzungen (Muss)", style={'color': COLORS['text'], 'fontWeight': 'bold', 'fontSize': '14px', 'marginLeft': '5px'}),
                        html.Span(" ───► Eingangskompetenzen (Kann)", style={'color': '#bdc3c7', 'fontWeight': 'bold', 'fontSize': '14px', 'marginLeft': '10px'}),

                    ], style={'textAlign': 'left', 'padding': '15px', 'backgroundColor': '#f8f9fa', 'marginBottom': '20px', 'borderRadius': '4px', 'borderLeft': f'4px solid {COLORS["blue_normal"]}'}),
                    
                    dcc.Graph(id='network-graph', style={'height': '75vh'}, config={'displayModeBar': False})
                ], style=content_style)
            ]),

# --- TAB 2: EXPLORER (Angepasste Version) ---
dcc.Tab(label='Modul-Explorer', style=tab_style, selected_style=tab_selected_style, children=[
    html.Div([
        # DIE GRAUE BOX
        html.Div([
            # Titel-Zeile
            html.Div([
                html.Span("Interaktiver Modul-Explorer", style={
                    'fontSize': '18px', 
                    'color': COLORS['blue_dark'], 
                    'fontWeight': 'bold', 
                    'display': 'inline-block'
                }),
            ], style={'marginBottom': '10px'}),
            
            # Erklärungstext (wie in Tab 1)
            html.Div([
                html.Span("Filtern", style={'fontSize': '16px', 'fontWeight': 'bold', 'color': COLORS['gold_normal']}), 
                " Sie das Curriculum nach verschiedenen Kriterien. Die Sunburst-Grafik zeigt die Verteilung der ",
                html.Span("ECTS-Punkte", style={'fontWeight': 'bold'}),
                " innerhalb der Modulgruppen.",
                html.Br(),
            ], style={'fontSize': '16px', 'color': COLORS['text'], 'marginBottom': '20px'}),
            
            # Die Filter-Elemente (Dropdowns) in einer Flex-Row
            html.Div([
                html.Div([
                    html.Label("Semester:", style={'fontSize': '12px', 'fontWeight': 'bold'}), 
                    dcc.Dropdown(id='filter-semester', options=semester_options, value='ALL', clearable=False)
                ], style={'width': '20%', 'marginRight': '2%'}),
                
                html.Div([
                    html.Label("Themen (Tags):", style={'fontSize': '12px', 'fontWeight': 'bold'}), 
                    dcc.Dropdown(id='filter-tags', options=[{'label': t, 'value': t} for t in sorted_tags], multi=True, placeholder="Nach Themen filtern...")
                ], style={'width': '37%', 'marginRight': '2%'}),
                
                html.Div([
                    html.Label("Modulgruppe:", style={'fontSize': '12px', 'fontWeight': 'bold'}), 
                    dcc.Dropdown(id='filter-group', options=[{'label': g, 'value': g} for g in sorted(list(set(df['Modulgruppe'])))], multi=True, placeholder="Nach Gruppen filtern...")
                ], style={'width': '37%'})
            ], style={'display': 'flex', 'alignItems': 'flex-end'})

        ], style={
            'textAlign': 'left', 
            'padding': '15px', 
            'backgroundColor': '#f8f9fa', 
            'marginBottom': '20px', 
            'borderRadius': '4px', 
            'borderLeft': f'4px solid {COLORS["blue_normal"]}'
        }),
        
        # Grafik-Bereich
        dcc.Graph(id='sunburst-graph', style={'height': '70vh'})
    ], style=content_style)
])
        ], style={'height': '44px', 'alignItems': 'center'})
    ], style={'width': '96%', 'margin': '20px auto', 'fontFamily': 'Roboto, sans-serif'})
], style={'backgroundColor': 'white', 'minHeight': '100vh', 'fontFamily': 'Roboto, sans-serif', 'margin': '0', 'padding': '0'})


# --- 4. CALLBACKS ---

# Callback 1: Netzwerk
@app.callback(
    Output('network-graph', 'figure'),
    [Input('network-graph', 'clickData'),
     Input('network-mode-check', 'value'),
     Input('reset-btn', 'n_clicks')]
)
def update_network(clickData, mode_values, n_clicks):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    highlight_nodes = set()
    is_reset = False

    if trigger_id == 'reset-btn':
        clickData = None
        is_reset = True
    
    if clickData and not is_reset:
        try:
            sel = clickData['points'][0]['text']
            highlight_nodes.add(sel)
            highlight_nodes.update(nx.ancestors(G, sel))
            highlight_nodes.update(nx.descendants(G, sel))
        except: pass

    traces, annotations = [], []
    for edge in G.edges(data=True):
        src, tgt, attr = edge
        x0, y0 = pos[src]
        x1, y1 = pos[tgt]
        
        is_highlighted = (clickData is not None and not is_reset) and (src in highlight_nodes and tgt in highlight_nodes)
        
        show_line = False
        opac = 0.1
        
        if clickData and not is_reset:
            if is_highlighted:
                show_line = True
                opac = 1.0
        else:
            if attr['type'] in mode_values:
                show_line = True
                opac = 0.6 if attr['type'] == 'hard' else 0.4

        if show_line:
            color = '#2c3e50' if attr['type'] == 'hard' else '#bdc3c7'
            width = 2.0
        else:
            color = '#ecf0f1'
            width = 1.0

        traces.append(go.Scatter(x=[x0, x1, None], y=[y0, y1, None], mode='lines', 
                                 line=dict(width=width, color=color, dash='solid'), opacity=opac, hoverinfo='none', showlegend=False))
        
        if show_line:
            annotations.append(dict(ax=x0, ay=y0, axref='x', ayref='y', x=x1, y=y1, xref='x', yref='y',
                showarrow=True, arrowhead=2, arrowsize=1.0, arrowwidth=width, arrowcolor=color, opacity=opac,
                standoff=15, startstandoff=5))

    all_groups = sorted(list(set(nx.get_node_attributes(G, 'group').values())))
    for group in all_groups:
        grp_nodes = [n for n, a in G.nodes(data=True) if a['group'] == group]
        nx_list, ny_list, txt_list, hov_list, op_list, sz_list = [], [], [], [], [], []
        
        for node in grp_nodes:
            x, y = pos[node]
            nx_list.append(x); ny_list.append(y); txt_list.append(node)
            inf = G.nodes[node]
            
            # HOVER TEXT AUFGEBAUT (Korrigiert)
            resp = str(inf.get('resp', 'Unbekannt'))
            desc = str(inf['desc']) if inf['desc'] else "Keine Beschreibung"
            goals = str(inf['goals']) if inf['goals'] else "Keine Lernziele"

            hov_list.append(
                f"<b>{inf['label']}</b><br>" +
                f"Semester: {inf['semester']}<br>" +
                f"Verantwortlich: {resp}<br><br>" +
                f"<i>{wrap_text(desc)}</i><br><br>" +
                f"<b>Lernziele:</b><br>{wrap_text(goals)}"
            )
            
            if (not clickData or is_reset) or node in highlight_nodes:
                op_list.append(1); sz_list.append(30)
            else:
                op_list.append(0.15); sz_list.append(15)
        
        traces.append(go.Scatter(x=nx_list, y=ny_list, mode='markers+text', text=txt_list, textposition="top center",
                                 hoverinfo='text', hovertext=hov_list, name=group,
                                 textfont=dict(family='Roboto, sans-serif', size=12, color='black' if (not clickData or is_reset) else None),
                                 marker=dict(color=GROUP_COLORS.get(group, '#999'), size=sz_list, opacity=op_list, line=dict(width=2, color='white'))))

    return go.Figure(data=traces, layout=go.Layout(
        showlegend=True, hovermode='closest', margin=dict(b=0,l=0,r=0,t=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white', annotations=annotations,
        legend=dict(title=dict(text="Modulgruppen", font=dict(family="Roboto, sans-serif", size=14, color=COLORS['text'])), 
                    font=dict(family="Roboto, sans-serif"), bgcolor='rgba(255,255,255,0.9)', bordercolor='#eee', borderwidth=1)
    ))

# Callback 2: Sunburst (Mit Hack gegen das Fragezeichen)
@app.callback(Output('sunburst-graph', 'figure'),
              [Input('filter-semester', 'value'), Input('filter-tags', 'value'), Input('filter-group', 'value')])
def update_sunburst(sem, tags, groups):
    dff = df.copy()
    if sem and sem != 'ALL': dff = dff[dff['Semester'].astype(str).str.contains(sem)]
    if groups: dff = dff[dff['Modulgruppe'].isin(groups)]
    if tags: dff = dff[dff.apply(lambda x: any(t in [i.strip() for i in str(x['Tags']).split(';')] for t in tags), axis=1)]

    if dff.empty:
        fig = go.Figure(); fig.update_layout(title="Keine Daten entsprechen den Filtern")
        return fig

    # 1. Figur erstellen
    fig = px.sunburst(
        dff, 
        path=['Modulgruppe', 'Modul_ID'], 
        values='ECTS', 
        color='Modulgruppe', 
        color_discrete_map=GROUP_COLORS,
        # Wir übergeben erst mal nur die ID als Customdata Platzhalter
        custom_data=['Modul_Name'] 
    )
    
    # 2. HACK: Customdata patchen, damit Gruppen einen Namen haben
    # Wir iterieren durch die Daten der Figur
    # fig.data[0] ist der Sunburst-Trace
    
    # Wir holen uns die Labels (IDs), die Plotly generiert hat
    labels = fig.data[0]['labels']
    
    # Wir bauen eine neue Liste für customdata[0] (den Namen)
    new_names = []
    
    # Mapping erstellen: ID -> Name (aus unserem DataFrame)
    id_to_name = pd.Series(dff.Modul_Name.values, index=dff.Modul_ID).to_dict()
    
    for label in labels:
        if label in id_to_name:
            # Es ist ein Modul -> Nimm den echten Namen
            new_names.append(id_to_name[label])
        else:
            # Es ist eine Gruppe (oder Root) -> Nimm das Label selbst als Namen!
            # Damit verschwindet das (?)
            new_names.append(label)
            
    # Das gepatchte Array zurück in die Figur schieben
    # Plotly erwartet customdata als Liste von Listen (für mehrere Spalten)
    # Wir haben nur eine Spalte (Name), also wrappen wir es
    fig.update_traces(customdata=list(zip(new_names)))

    # 3. Hover Template setzen
    fig.update_traces(
        hovertemplate='<b>%{customdata[0]}</b><br>ECTS: %{value}<extra></extra>',
        textfont=dict(size=14),
        insidetextorientation='radial'
    )
    
    fig.update_layout(margin=dict(t=0, l=0, r=0, b=0), font=dict(family="Roboto, sans-serif"))
    return fig
if __name__ == "__main__":
    app.run(debug=True, port=8050)