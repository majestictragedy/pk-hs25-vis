import dash
from dash import dcc, html, Input, Output, no_update
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# --- 1. DATEN LADEN ---
file_path = 'dashboard-pk/data/Module_Data.xlsx'

try:
    df = pd.read_excel(file_path)
except Exception as e:
    print(f"Fehler: {e}")
    exit()

df = df.fillna('')
df['Modul_ID'] = df['Modul_ID'].astype(str).str.strip()
valid_ids = set(df['Modul_ID'].unique())

# --- 2. NETZWERK BERECHNEN ---
G = nx.DiGraph()

# Knoten mit Attributen
for index, row in df.iterrows():
    G.add_node(row['Modul_ID'], 
               label=row['Modul_Name'],
               group=row['Modulgruppe'],
               desc=row['Kurzbeschreibung'],
               goals=row['Lernziele'],
               semester=row['Semester'])

# Kanten
for index, row in df.iterrows():
    source = row['Modul_ID']
    # Hard
    if row['Voraussetzung_Hard']:
        for target in str(row['Voraussetzung_Hard']).split(';'):
            target = target.strip()
            if target in valid_ids:
                G.add_edge(target, source, type='hard')
    # Soft
    if row['Voraussetzung_Soft']:
        for target in str(row['Voraussetzung_Soft']).split(';'):
            target = target.strip()
            if target in valid_ids:
                G.add_edge(target, source, type='soft')

# Layout fixieren (damit die Punkte nicht springen beim Klicken)
pos = nx.spring_layout(G, k=0.6, iterations=60, seed=42)

# --- 3. DASH APP SETUP ---
app = dash.Dash(__name__)

# Farben für die Modulgruppen (manuell definiert für schönes Design)
GROUP_COLORS = {
    'Informatik': '#3498db',        # Blau
    'Major GLAM': '#e74c3c',        # Rot
    'Major IDMM': '#9b59b6',        # Lila
    'Informationswissenschaft': '#2ecc71', # Grün
    'Vertiefungsstudium': '#f1c40f',# Gelb/Orange
    'Methodik': '#95a5a6',          # Grau
    'Betriebsökonomie': '#34495e',  # Dunkelblau
    'Common': '#7f8c8d'             # Fallback
}

app.layout = html.Div([
    html.H1("Curriculum Navigator 2026", style={'font-family': 'sans-serif', 'textAlign': 'center'}),
    
    html.Div([
        html.Span("🔍 Klicke auf ein Modul, um den Lernpfad zu sehen.", style={'fontWeight': 'bold'}),
        html.Br(),
        html.Span("Legende Linien: "),
        html.Span("─── Hart (Pflicht)", style={'color': '#2c3e50', 'fontWeight': 'bold'}),
        html.Span("  . . . .  Soft (Empfohlen)", style={'color': '#95a5a6', 'marginLeft': '10px'}),
    ], style={'textAlign': 'center', 'padding': '10px', 'backgroundColor': '#f0f2f5', 'borderRadius': '5px'}),

    # Der Graph Container
    dcc.Graph(id='network-graph', style={'height': '85vh'}, config={'displayModeBar': False})
])

# --- 4. INTERAKTIONS-LOGIK (CALLBACK) ---
@app.callback(
    Output('network-graph', 'figure'),
    Input('network-graph', 'clickData')
)
def update_graph(clickData):
    # Standard-Werte (kein Fokus)
    highlight_nodes = set()
    if clickData:
        # Ein Knoten wurde geklickt!
        selected_node = clickData['points'][0]['text'] # Das ist die Modul_ID
        
        # Wir finden alle Vorgänger (Ancestors) und Nachfolger (Descendants)
        ancestors = nx.ancestors(G, selected_node)
        descendants = nx.descendants(G, selected_node)
        
        # Menge aller hervorzuhebenden Knoten
        highlight_nodes.add(selected_node)
        highlight_nodes.update(ancestors)
        highlight_nodes.update(descendants)

    # -- TRACES ERSTELLEN --
    traces = []

    # A) KANTEN (Linien)
    edge_x_hard, edge_y_hard = [], []
    edge_x_soft, edge_y_soft = [], []

    for edge in G.edges(data=True):
        source, target, attr = edge
        
        # Logik: Ist diese Kante Teil des ausgewählten Pfades?
        # Ja, wenn Start UND Ende im Highlight-Set sind (oder gar nichts ausgewählt ist)
        is_relevant = (not clickData) or (source in highlight_nodes and target in highlight_nodes)
        
        # Farbe/Transparenz setzen
        if is_relevant:
            color = '#2c3e50' if attr['type'] == 'hard' else '#95a5a6'
            width = 2 if attr['type'] == 'hard' else 1
            opacity = 1
        else:
            color = '#ecf0f1' # Sehr hellgrau
            width = 1
            opacity = 0.2

        x0, y0 = pos[source]
        x1, y1 = pos[target]
        
        # Wir bauen separate Listen für Hard/Soft, um Legende zu ermöglichen (Trick)
        # Hier zeichnen wir aber jede Linie einzeln für volle Kontrolle über Farbe/Opazität
        trace = go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode='lines',
            line=dict(width=width, color=color, dash='solid' if attr['type']=='hard' else 'dot'),
            opacity=opacity,
            hoverinfo='none',
            showlegend=False
        )
        traces.append(trace)

    # B) KNOTEN (Punkte) - Gruppiert für die Legende
    # Wir holen alle Gruppen, die wir haben
    all_groups = sorted(list(set(nx.get_node_attributes(G, 'group').values())))

    for group in all_groups:
        # Finde alle Knoten dieser Gruppe
        group_nodes = [n for n, attr in G.nodes(data=True) if attr['group'] == group]
        
        node_x = []
        node_y = []
        node_text_ids = []
        node_hover = []
        node_opacities = []
        node_sizes = []

        for node in group_nodes:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text_ids.append(node) # Beschriftung im Bild
            
            # Hover Text
            info = G.nodes[node]
            hover_str = (
                f"<b>{info['label']} ({node})</b><br>" +
                f"Semester: {info['semester']}<br><br>" +
                f"<i>{info['desc']}</i><br><br>" +
                f"<b>Ziele:</b> {str(info['goals'])[:200]}..."
            )
            node_hover.append(hover_str)

            # Highlighting Logik
            if not clickData or node in highlight_nodes:
                node_opacities.append(1)
                node_sizes.append(25) # Gross und sichtbar
            else:
                node_opacities.append(0.1) # Ausgegraut
                node_sizes.append(15) # Kleiner

        # Trace für diese Gruppe erstellen
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text_ids,
            textposition="top center",
            hoverinfo='text',
            hovertext=node_hover,
            name=group, # Das erscheint in der Legende!
            marker=dict(
                color=GROUP_COLORS.get(group, '#7f8c8d'),
                size=node_sizes,
                opacity=node_opacities,
                line=dict(width=2, color='white')
            )
        )
        traces.append(node_trace)

    # Layout
    layout = go.Layout(
        showlegend=True,
        legend=dict(title="Modulgruppen", x=1, y=1),
        hovermode='closest',
        margin=dict(b=0,l=0,r=0,t=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white'
    )

    return {'data': traces, 'layout': layout}

if __name__ == "__main__":
    app.run(debug=True, port=8050)