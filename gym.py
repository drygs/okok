import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
from pathlib import Path
import json

# Configuração da página
st.set_page_config(
    page_title="Gym Progress Tracker",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 Estilos CSS personalizados
st.markdown("""
    <style>
    .main {background-color: #f5f5f5;}
    .stButton>button {width: 100%;}
    .stNumberInput {width: 100%;}
    .metric-card {border-radius: 10px; padding: 15px; background-color: white; 
                  box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px;}
    .progress-header {color: #2e86ab; border-bottom: 2px solid #2e86ab;}
    .dashboard-title {font-size: 2.5rem; color: #2e86ab; text-align: center;}
    .dashboard-subtitle {font-size: 1.5rem; color: #4a4a4a; text-align: center;}
    </style>
""", unsafe_allow_html=True)

# 📂 Configuração da pasta de dados - Render
DATA_DIR = "/var/lib/render/data/gym_tracker"
os.makedirs(DATA_DIR, exist_ok=True)

# Caminhos dos arquivos
TREINOS_CSV = os.path.join(DATA_DIR, "treinos.csv")
PROGRESSO_CSV = os.path.join(DATA_DIR, "progresso.csv")
METAS_CSV = os.path.join(DATA_DIR, "metas.csv")
CONFIG_JSON = os.path.join(DATA_DIR, "config.json")

# Funções para manipulação de dados
@st.cache_data(ttl=300)
def load_data(file_path, default_columns=None):
    """Carrega dados do arquivo CSV ou retorna DataFrame vazio com colunas padrão"""
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return pd.read_csv(file_path)
    except Exception as e:
        st.error(f"Erro ao carregar {file_path}: {e}")
    
    if default_columns:
        return pd.DataFrame(columns=default_columns)
    return pd.DataFrame()

def save_data(df, file_path):
    """Salva DataFrame no arquivo CSV"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar {file_path}: {e}")
        return False

# 🧭 Navegação por abas
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=Gym+Tracker", use_column_width=True)
    aba = st.radio("📂 Navegação", 
                  ["🏠 Dashboard", "📅 Treino Diário", "📊 Progresso", "🏆 Metas", "⚙️ Configurações"],
                  index=0)
    
    # Mostrar resumo rápido no sidebar
    st.markdown("---")
    st.markdown("### 📊 Resumo Rápido")
    
    try:
        df_treinos = load_data(TREINOS_CSV)
        df_progresso = load_data(PROGRESSO_CSV)
        df_metas = load_data(METAS_CSV)
        
        if not df_treinos.empty:
            ultimo_treino = pd.to_datetime(df_treinos['Data']).max()
            dias_desde_ultimo = (datetime.now() - ultimo_treino).days
            st.metric("Último Treino", f"{ultimo_treino.strftime('%d/%m')} ({dias_desde_ultimo}d atrás)")
        
        if not df_progresso.empty:
            ultimo_peso = df_progresso['Peso (kg)'].iloc[-1]
            st.metric("Último Peso", f"{ultimo_peso} kg")
        
        if not df_metas.empty and 'Atual' in df_metas.columns and 'Valor' in df_metas.columns:
            meta_peso = df_metas[df_metas['Meta'] == 'Peso']
            if not meta_peso.empty and pd.notna(meta_peso['Atual'].iloc[0]):
                progresso = (meta_peso['Atual'].iloc[0] / meta_peso['Valor'].iloc[0]) * 100
                st.metric("Progresso Meta Peso", f"{progresso:.1f}%")
    except Exception as e:
        st.error(f"Erro ao carregar resumo: {e}")

# 📅 Dias da semana
dias = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo"
}
hoje = datetime.now().weekday()
dia_semana = dias[hoje]
data_atual = datetime.now().strftime("%d/%m/%Y")

# Carregar configurações de treino
if 'treino_por_dia' not in st.session_state:
    try:
        if os.path.exists(CONFIG_JSON):
            with open(CONFIG_JSON, 'r') as f:
                st.session_state.treino_por_dia = json.load(f)
        else:
            st.session_state.treino_por_dia = {
                "Segunda": {
                    "Costas": ["Serrote", "Remada Baixa", "Puxada Frontal", "Puxada Traseira"],
                    "Bíceps": ["Bíceps Martelo", "Bíceps na Polia"]
                },
                "Quarta": {
                    "Peito": ["Supino Plano", "Supino Inclinado", "Aberturas Planas", "Peck Deck"],
                    "Tríceps": ["Tríceps Francês na Polia", "Tríceps Corda"]
                },
                "Quinta": {
                    "Ombros": ["Press Militar", "Elevação Lateral", "Elevação Frontal"],
                    "Abdômen": ["Elevação das Pernas", "Prancha", "Abdominais"]
                },
                "Sexta": {
                    "Pernas": ["Agachamento", "Leg Press", "Extensora", "Adutora", "Mesa Flexora", "Gêmeos na Máquina"]
                }
            }
    except Exception as e:
        st.error(f"Erro ao carregar configurações: {e}")
        st.session_state.treino_por_dia = {}

# 🏠 DASHBOARD PRINCIPAL
if aba == "🏠 Dashboard":
    st.markdown('<h1 class="dashboard-title">🏋️‍♂️ Gym Progress Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<h2 class="dashboard-subtitle">Resumo Completo do Seu Progresso</h2>', unsafe_allow_html=True)
    
    # Carregar todos os dados
    df_treinos = load_data(TREINOS_CSV)
    df_progresso = load_data(PROGRESSO_CSV)
    df_metas = load_data(METAS_CSV)
    
    # Seção de métricas rápidas
    st.markdown("---")
    st.markdown("### 📈 Métricas Principais")
    
    if not df_treinos.empty and not df_progresso.empty and not df_metas.empty:
        df_treinos['Data'] = pd.to_datetime(df_treinos['Data'])
        df_progresso['Data'] = pd.to_datetime(df_progresso['Data'])
        
        ultimo_treino = df_treinos['Data'].max()
        dias_sem_treinar = (datetime.now() - ultimo_treino).days
        total_treinos = df_treinos['Data'].nunique()
        treinos_ultimo_mes = df_treinos[df_treinos['Data'] >= (datetime.now() - timedelta(days=30))]['Data'].nunique()
        
        ultimo_peso = df_progresso['Peso (kg)'].iloc[-1]
        variacao_peso = ultimo_peso - df_progresso['Peso (kg)'].iloc[0] if len(df_progresso) > 1 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Último Peso", f"{ultimo_peso:.1f} kg", f"{variacao_peso:+.1f} kg")
        with col2:
            st.metric("Total de Treinos", total_treinos)
        with col3:
            st.metric("Treinos (últimos 30 dias)", treinos_ultimo_mes)
        with col4:
            st.metric("Dias sem Treinar", dias_sem_treinar)
        
        # Gráficos principais
        st.markdown("---")
        st.markdown("### 📊 Progresso ao Longo do Tempo")
        
        tab1, tab2, tab3 = st.tabs(["📈 Peso e Sono", "🏋️‍♂️ Desempenho nos Treinos", "📅 Frequência"])
        
        with tab1:
            if len(df_progresso) > 1:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                fig.add_trace(
                    go.Scatter(x=df_progresso['Data'], y=df_progresso['Peso (kg)'], name="Peso (kg)"),
                    secondary_y=False,
                )
                
                if 'Horas de Sono' in df_progresso.columns:
                    fig.add_trace(
                        go.Bar(x=df_progresso['Data'], y=df_progresso['Horas de Sono'], name="Horas de Sono", opacity=0.5),
                        secondary_y=True,
                    )
                
                if 'Água (copos)' in df_progresso.columns:
                    fig.add_trace(
                        go.Scatter(x=df_progresso['Data'], y=df_progresso['Água (copos)'], name="Água (copos)", mode='lines+markers'),
                        secondary_y=True,
                    )
                
                fig.update_layout(
                    title="Progresso de Peso, Sono e Hidratação",
                    xaxis_title="Data",
                    hovermode="x unified"
                )
                
                fig.update_yaxes(title_text="Peso (kg)", secondary_y=False)
                fig.update_yaxes(title_text="Sono/Água", secondary_y=True)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Dados insuficientes para mostrar gráfico de progresso")
        
        with tab2:
            if not df_treinos.empty:
                exercicios_populares = df_treinos['Exercício'].value_counts().nlargest(5).index.tolist()
                exercicio_selecionado = st.selectbox("Selecione um exercício para análise", exercicios_populares)
                
                df_exercicio = df_treinos[df_treinos['Exercício'] == exercicio_selecionado].sort_values('Data')
                
                if len(df_exercicio) > 1:
                    fig = px.line(df_exercicio, x='Data', y='Carga (kg)', 
                                title=f"Progresso no {exercicio_selecionado}",
                                markers=True,
                                hover_data=['Repetições', 'Séries'])
                    
                    df_exercicio['Media Movel'] = df_exercicio['Carga (kg)'].rolling(window=3, min_periods=1).mean()
                    fig.add_trace(
                        go.Scatter(x=df_exercicio['Data'], y=df_exercicio['Media Movel'], 
                                 name='Média Móvel (3 treinos)', line=dict(dash='dot'))
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Maior Carga", f"{df_exercicio['Carga (kg)'].max():.1f} kg")
                    with col2:
                        st.metric("Progresso Total", 
                                f"{df_exercicio['Carga (kg)'].iloc[-1] - df_exercicio['Carga (kg)'].iloc[0]:.1f} kg")
                    with col3:
                        st.metric("Média Recente", 
                                f"{df_exercicio.tail(3)['Carga (kg)'].mean():.1f} kg")
                else:
                    st.warning("Dados insuficientes para este exercício")
            else:
                st.warning("Nenhum dado de treino disponível")
        
        with tab3:
            if not df_treinos.empty:
                df_treinos['Dia da Semana'] = pd.to_datetime(df_treinos['Data']).dt.day_name()
                
                dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                df_treinos['Dia da Semana'] = pd.Categorical(df_treinos['Dia da Semana'], 
                                                            categories=dias_ordem, 
                                                            ordered=True)
                
                df_freq_dia = df_treinos.groupby('Dia da Semana').size().reset_index(name='Treinos')
                
                fig1 = px.bar(df_freq_dia, x='Dia da Semana', y='Treinos', 
                             title='Treinos por Dia da Semana',
                             color='Treinos',
                             color_continuous_scale='Blues')
                st.plotly_chart(fig1, use_container_width=True)
                
                df_treinos['Ano-Mês'] = df_treinos['Data'].dt.to_period('M').astype(str)
                df_freq_mes = df_treinos.groupby('Ano-Mês').size().reset_index(name='Treinos')
                
                fig2 = px.line(df_freq_mes, x='Ano-Mês', y='Treinos', 
                              title='Treinos por Mês',
                              markers=True)
                fig2.update_traces(line_color='#2e86ab', line_width=2)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.warning("Nenhum dado de treino disponível")
        
        st.markdown("---")
        st.markdown("### 🎯 Progresso nas Metas")
        
        if not df_metas.empty:
            for i, row in df_metas.iterrows():
                if row['Meta'] == 'Peso' and not df_progresso.empty:
                    df_metas.at[i, 'Atual'] = df_progresso['Peso (kg)'].iloc[-1]
                elif row['Meta'] == 'Agachamento' and not df_treinos.empty:
                    if 'Agachamento' in df_treinos['Exercício'].values:
                        df_metas.at[i, 'Atual'] = df_treinos[df_treinos['Exercício'] == 'Agachamento']['Carga (kg)'].max()
                elif row['Meta'] == 'Supino' and not df_treinos.empty:
                    if 'Supino Plano' in df_treinos['Exercício'].values:
                        df_metas.at[i, 'Atual'] = df_treinos[df_treinos['Exercício'] == 'Supino Plano']['Carga (kg)'].max()
                elif row['Meta'] == 'Dias de Treino' and not df_treinos.empty:
                    df_metas.at[i, 'Atual'] = df_treinos['Data'].nunique()
            
            cols = st.columns(len(df_metas))
            for idx, (col, (_, meta)) in enumerate(zip(cols, df_metas.iterrows())):
                with col:
                    if pd.notna(meta['Atual']):
                        progresso = (meta['Atual'] / meta['Valor']) * 100
                        st.metric(
                            label=meta['Meta'],
                            value=f"{meta['Atual']} / {meta['Valor']}",
                            delta=f"{progresso:.1f}%"
                        )
                        st.progress(min(int(progresso), 100))
                    else:
                        st.metric(
                            label=meta['Meta'],
                            value=f"Meta: {meta['Valor']}",
                            help="Dados insuficientes para calcular progresso"
                        )
        else:
            st.warning("Nenhuma meta definida")
    
    else:
        st.warning("Dados insuficientes para mostrar o dashboard completo")
        st.info("Comece registrando seus treinos e progresso para ver análises detalhadas")

# 📅 ABA DE TREINO DIÁRIO (original mantido)
elif aba == "📅 Treino Diário":
    st.title(f"🏋️‍♂️ Treino - {dia_semana}-feira")
    st.subheader(f"{data_atual}")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.metric("Dia da Semana", dia_semana)
        if dia_semana in st.session_state.treino_por_dia:
            st.success("💪 Dia de treino!")
        else:
            st.info("📴 Dia de descanso")
    
    if dia_semana in st.session_state.treino_por_dia:
        with st.expander("🔍 Ver plano de treino completo"):
            for dia, grupos in st.session_state.treino_por_dia.items():
                st.write(f"**{dia}:**")
                for grupo, exercicios in grupos.items():
                    st.write(f"- {grupo}: {', '.join(exercicios)}")
        
        registros = []
        for grupo, exercicios in st.session_state.treino_por_dia[dia_semana].items():
            st.markdown(f"### {grupo}")
            cols = st.columns(3)
            
            for i, exercicio in enumerate(exercicios):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.write(f"**{exercicio}**")
                        carga = st.number_input("Carga (kg)", min_value=0.0, step=2.5, key=f"{exercicio}_carga")
                        repeticoes = st.number_input("Repetições", min_value=0, step=1, key=f"{exercicio}_rep")
                        series = st.number_input("Séries", min_value=0, step=1, key=f"{exercicio}_series", value=3)
                        observacoes = st.text_input("Observações", key=f"{exercicio}_obs")
                        
                        registros.append({
                            "Data": datetime.now().strftime("%Y-%m-%d"),
                            "Dia": dia_semana,
                            "Grupo Muscular": grupo,
                            "Exercício": exercicio,
                            "Carga (kg)": carga,
                            "Repetições": repeticoes,
                            "Séries": series,
                            "Observações": observacoes
                        })

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Salvar Treino", type="primary"):
                df_novo = pd.DataFrame(registros)
                df_antigo = load_data(TREINOS_CSV)
                df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
                if save_data(df_total, TREINOS_CSV):
                    st.success("✅ Treino salvo com sucesso!")
                    st.balloons()
        
        with col2:
            if st.button("📈 Ver Histórico"):
                df = load_data(TREINOS_CSV)
                if not df.empty:
                    st.dataframe(
                        df[df["Dia"] == dia_semana].sort_values("Data", ascending=False),
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    exercicios_dia = [ex for grupo in st.session_state.treino_por_dia[dia_semana].values() for ex in grupo]
                    for exercicio in exercicios_dia:
                        df_ex = df[df["Exercício"] == exercicio]
                        if not df_ex.empty:
                            fig = px.line(df_ex, x="Data", y="Carga (kg)", title=f"Progresso - {exercicio}")
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Ainda não há registros salvos.")

# 📊 ABA DE PROGRESSO (original mantido)
elif aba == "📊 Progresso":
    st.title("📊 Progresso Corporal & Estilo de Vida")
    
    tab1, tab2, tab3 = st.tabs(["📈 Métricas Diárias", "🏋️‍♂️ Evolução de Cargas", "📅 Calendário de Treinos"])
    
    with tab1:
        st.subheader("Registro Diário")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            peso = st.number_input("Peso (kg)", min_value=0.0, step=0.1)
            sono = st.number_input("Horas de sono (últimas 24h)", min_value=0.0, max_value=24.0, step=0.5)
        
        with col2:
            cansaco = st.slider("Nível de cansaço (0-10)", 0, 10)
            humor = st.select_slider("Humor", options=["😭", "😞", "😐", "🙂", "😁"])
        
        with col3:
            calorias = st.number_input("Calorias ingeridas (opcional)", min_value=0.0, step=50.0)
            agua = st.number_input("Copos de água (250ml)", min_value=0, step=1)
        
        if st.button("💾 Salvar Progresso Diário"):
            df_novo = pd.DataFrame([{
                "Data": datetime.now().strftime("%Y-%m-%d"),
                "Peso (kg)": peso,
                "Horas de Sono": sono,
                "Cansaço": cansaco,
                "Humor": humor,
                "Calorias": calorias if calorias > 0 else None,
                "Água (copos)": agua
            }])
            
            df_antigo = load_data(PROGRESSO_CSV)
            df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
            if save_data(df_total, PROGRESSO_CSV):
                st.success("✅ Progresso salvo com sucesso!")
        
        st.divider()
        st.subheader("Histórico de Progresso")
        
        df_progresso = load_data(PROGRESSO_CSV)
        if not df_progresso.empty:
            df_progresso["Data"] = pd.to_datetime(df_progresso["Data"])
            
            ultimo_registro = df_progresso.iloc[-1]
            cols = st.columns(4)
            with cols[0]:
                st.metric("Último Peso", f"{ultimo_registro['Peso (kg)']} kg")
            with cols[1]:
                st.metric("Média de Sono", f"{df_progresso['Horas de Sono'].mean():.1f} horas")
            with cols[2]:
                st.metric("Média de Água", f"{df_progresso['Água (copos)'].mean():.1f} copos/dia")
            with cols[3]:
                st.metric("Dias Registrados", len(df_progresso))
            
            fig = px.line(df_progresso, x="Data", y=["Peso (kg)", "Horas de Sono", "Água (copos)"],
                         title="Progresso ao Longo do Tempo")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_progresso.sort_values("Data", ascending=False), hide_index=True)
        else:
            st.warning("Nenhum progresso registrado ainda.")
    
    with tab2:
        st.subheader("Evolução de Cargas")
        df_treinos = load_data(TREINOS_CSV)
        
        if not df_treinos.empty:
            exercicio_selecionado = st.selectbox("Escolha um exercício", df_treinos["Exercício"].unique())
            
            df_exercicio = df_treinos[df_treinos["Exercício"] == exercicio_selecionado].sort_values("Data")
            
            if not df_exercicio.empty:
                fig = px.line(df_exercicio, x="Data", y="Carga (kg)", 
                             title=f"Progresso no {exercicio_selecionado}",
                             markers=True)
                st.plotly_chart(fig, use_container_width=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Maior Carga", f"{df_exercicio['Carga (kg)'].max()} kg")
                with col2:
                    st.metric("Média Recente", f"{df_exercicio.tail(3)['Carga (kg)'].mean():.1f} kg")
                with col3:
                    progresso = df_exercicio['Carga (kg)'].iloc[-1] - df_exercicio['Carga (kg)'].iloc[0]
                    st.metric("Progresso Total", f"{progresso:.1f} kg")
                
                st.dataframe(df_exercicio, hide_index=True)
            else:
                st.warning("Nenhum dado encontrado para este exercício.")
        else:
            st.warning("Nenhum treino registrado ainda.")
    
    with tab3:
        st.subheader("Frequência de Treinos")
        df_treinos = load_data(TREINOS_CSV)
        
        if not df_treinos.empty:
            df_treinos["Data"] = pd.to_datetime(df_treinos["Data"])
            
            df_frequencia = df_treinos.groupby("Dia").size().reset_index(name="Contagem")
            fig = px.bar(df_frequencia, x="Dia", y="Contagem", 
                         title="Treinos por Dia da Semana",
                         color="Dia")
            st.plotly_chart(fig, use_container_width=True)
            
            data_limite = datetime.now() - timedelta(days=30)
            df_recente = df_treinos[df_treinos["Data"] >= data_limite]
            
            if not df_recente.empty:
                st.write("**Últimos Treinos:**")
                for _, row in df_recente.sort_values("Data", ascending=False).iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['Data'].strftime('%d/%m')}** - {row['Dia']}")
                        st.write(f"{row['Grupo Muscular']}: {row['Exercício']} ({row['Carga (kg)']}kg)")
            else:
                st.info("Nenhum treino registrado nos últimos 30 dias.")
        else:
            st.warning("Nenhum treino registrado ainda.")

# 🎯 ABA DE METAS (original mantido)
elif aba == "🏆 Metas":
    st.title("🏆 Metas e Objetivos")
    
    df_metas = load_data(METAS_CSV, default_columns=["Meta", "Valor", "Atual"])
    
    if df_metas.empty:
        metas_padrao = [
            {"Meta": "Peso", "Valor": 75.0, "Atual": None},
            {"Meta": "Agachamento", "Valor": 120.0, "Atual": None},
            {"Meta": "Supino", "Valor": 80.0, "Atual": None},
            {"Meta": "Dias de Treino", "Valor": 4, "Atual": None}
        ]
        df_metas = pd.DataFrame(metas_padrao)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Definir Metas")
        
        metas_editaveis = []
        for _, row in df_metas.iterrows():
            novo_valor = st.number_input(
                f"{row['Meta']} (alvo)", 
                value=row["Valor"],
                key=f"meta_{row['Meta']}"
            )
            metas_editaveis.append({
                "Meta": row["Meta"],
                "Valor": novo_valor,
                "Atual": row["Atual"]
            })
        
        if st.button("Salvar Metas"):
            df_metas = pd.DataFrame(metas_editaveis)
            if save_data(df_metas, METAS_CSV):
                st.success("Metas atualizadas com sucesso!")
    
    with col2:
        st.subheader("Progresso das Metas")
        
        df_progresso = load_data(PROGRESSO_CSV)
        df_treinos = load_data(TREINOS_CSV)
        
        for i, row in df_metas.iterrows():
            if row["Meta"] == "Peso" and not df_progresso.empty:
                df_metas.at[i, "Atual"] = df_progresso["Peso (kg)"].iloc[-1]
            elif row["Meta"] == "Agachamento" and not df_treinos.empty:
                if "Agachamento" in df_treinos["Exercício"].values:
                    df_metas.at[i, "Atual"] = df_treinos[df_treinos["Exercício"] == "Agachamento"]["Carga (kg)"].max()
            elif row["Meta"] == "Supino" and not df_treinos.empty:
                if "Supino Plano" in df_treinos["Exercício"].values:
                    df_metas.at[i, "Atual"] = df_treinos[df_treinos["Exercício"] == "Supino Plano"]["Carga (kg)"].max()
            elif row["Meta"] == "Dias de Treino" and not df_treinos.empty:
                df_metas.at[i, "Atual"] = df_treinos["Data"].nunique()
        
        for _, row in df_metas.iterrows():
            with st.container(border=True):
                st.write(f"**{row['Meta']}**")
                if pd.notna(row["Atual"]):
                    progresso = (row["Atual"] / row["Valor"]) * 100
                    st.progress(min(int(progresso), 100), 
                              f"{row['Atual']} / {row['Valor']} ({min(progresso, 100):.1f}%)")
                else:
                    st.info("Dados insuficientes para calcular progresso")

# ⚙️ ABA DE CONFIGURAÇÕES (original mantido)
elif aba == "⚙️ Configurações":
    st.title("⚙️ Configurações do Treino")
    
    st.subheader("Personalizar Plano de Treino")
    
    dias_treino = st.multiselect(
        "Dias de Treino", 
        ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"],
        default=list(st.session_state.treino_por_dia.keys())
    )
    
    novo_treino = {}
    for dia in dias_treino:
        st.markdown(f"### {dia}")
        grupos = st.text_input(f"Grupos musculares (separados por vírgula)", 
                              value=", ".join(st.session_state.treino_por_dia.get(dia, {}).keys()),
                              key=f"grupos_{dia}")
        
        grupos_lista = [g.strip() for g in grupos.split(",") if g.strip()]
        grupo_exercicios = {}
        
        for grupo in grupos_lista:
            exercicios = st.text_input(f"Exercícios para {grupo} (separados por vírgula)",
                                     value=", ".join(st.session_state.treino_por_dia.get(dia, {}).get(grupo, [])),
                                     key=f"exerc_{dia}_{grupo}")
            grupo_exercicios[grupo] = [e.strip() for e in exercicios.split(",") if e.strip()]
        
        novo_treino[dia] = grupo_exercicios
    
    if st.button("Salvar Configurações"):
        st.session_state.treino_por_dia = novo_treino
        try:
            with open(CONFIG_JSON, 'w') as f:
                json.dump(st.session_state.treino_por_dia, f)
            st.success("Plano de treino atualizado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar configurações: {e}")
    
    st.divider()
    st.subheader("Exportar/Importar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists(TREINOS_CSV):
            with open(TREINOS_CSV, "rb") as f:
                st.download_button(
                    label="📤 Exportar Dados de Treino",
                    data=f,
                    file_name="treinos_backup.csv",
                    mime="text/csv"
                )
        else:
            st.warning("Nenhum dado de treino para exportar")
    
    with col2:
        uploaded_file = st.file_uploader("📥 Importar Dados", type=["csv"])
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                if "Exercício" in df.columns and "Carga (kg)" in df.columns:
                    if save_data(df, TREINOS_CSV):
                        st.success("Dados de treino importados com sucesso!")
                elif "Peso (kg)" in df.columns and "Horas de Sono" in df.columns:
                    if save_data(df, PROGRESSO_CSV):
                        st.success("Dados de progresso importados com sucesso!")
                else:
                    st.error("Formato de arquivo não reconhecido")
                
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Erro ao carregar arquivo: {e}")