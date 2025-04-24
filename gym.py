import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import requests
import base64

# Forçar tema escuro GLOBALMENTE (funciona no Render)
os.environ["STREAMLIT_THEME_BASE"] = "dark"  # Força via variável de ambiente
st.set_page_config(
    page_title="Gym Tracker",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)
st._config.set_option("theme.base", "dark")  # Configuração interna

# 🔄 Configuração de armazenamento (GitHub como "banco de dados")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = "drygs/okok"
GITHUB_BRANCH = "main"
DATA_FILES = {
    "treinos": "treinos.csv",
    "progresso": "progresso.csv",
    "metas": "metas.csv"
}

# 🎨 Estilos CSS personalizados
st.markdown("""
    <style>
    :root {
        --primary-color: #ff4b4b;
        --background-color: #0e1117;
        --secondary-background-color: #262730;
        --text-color: #fafafa;
    }
    
    .stApp, .main {
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
    }
    
    .stButton>button {
        width: 100%;
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
    }
    
    .stNumberInput, .stTextInput, .stSelectbox {
        width: 100%;
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
    }
    
    .metric-card {
        border-radius: 10px;
        padding: 15px;
        background-color: var(--secondary-background-color) !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        border: 1px solid #444 !important;
    }
    
    .progress-header {
        color: #2e86ab;
        border-bottom: 2px solid #2e86ab;
    }
    
    .stContainer {
        border: 1px solid #444;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
        color: var(--text-color) !important;
    }
    </style>
""", unsafe_allow_html=True)

# ======================================
# 🔄 FUNÇÕES DE ARMAZENAMENTO (GitHub)
# ======================================
def load_from_github(filename):
    """Carrega dados de um arquivo CSV no GitHub"""
    if not GITHUB_TOKEN:
        return pd.DataFrame()
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/gym_data/{filename}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        content = base64.b64decode(response.json()["content"]).decode("utf-8")
        return pd.read_csv(pd.compat.StringIO(content))
    except:
        return pd.DataFrame()

def save_to_github(filename, df):
    """Salva DataFrame num arquivo CSV no GitHub"""
    if not GITHUB_TOKEN:
        return False
    
    content = df.to_csv(index=False)
    content_base64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/gym_data/{filename}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers)
        sha = response.json()["sha"] if response.status_code == 200 else None
    except:
        sha = None
    
    data = {
        "message": f"Update {filename}",
        "content": content_base64,
        "branch": GITHUB_BRANCH,
        **({"sha": sha} if sha else {})
    }
    
    upload_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/gym_data/{filename}"
    response = requests.put(upload_url, headers=headers, json=data)
    return response.status_code == 200

def load_data(file_key, default_columns=None):
    """Carrega dados do GitHub ou local"""
    filename = DATA_FILES[file_key]
    
    if GITHUB_TOKEN:
        df = load_from_github(filename)
    else:
        local_path = os.path.join("gym_data", filename)
        if os.path.exists(local_path):
            df = pd.read_csv(local_path)
        else:
            df = pd.DataFrame()
    
    if df.empty and default_columns:
        return pd.DataFrame(columns=default_columns)
    return df

def save_data(file_key, df):
    """Salva dados no GitHub ou local"""
    filename = DATA_FILES[file_key]
    
    if GITHUB_TOKEN:
        return save_to_github(filename, df)
    else:
        os.makedirs("gym_data", exist_ok=True)
        df.to_csv(os.path.join("gym_data", filename), index=False)
        return True

# ======================================
# 🏋️‍♂️ CÓDIGO PRINCIPAL
# ======================================
# 🧭 Navegação por abas
aba = st.sidebar.selectbox("📂 Navegação", ["📅 Treino Diário", "📊 Progresso", "🏆 Metas", "⚙️ Configurações"])

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

# 📋 Exercícios por dia (configurável)
if 'treino_por_dia' not in st.session_state:
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

# Custom container function (substitute for border parameter)
def bordered_container():
    return st.container().markdown(
        """<style>div[data-testid="stVerticalBlock"]{border: 1px solid #444; border-radius: 8px; padding: 1rem;}</style>""",
        unsafe_allow_html=True
    )

# 🏋️‍♂️ ABA DE TREINO DIÁRIO
if aba == "📅 Treino Diário":
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
                    with bordered_container():
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
                df_antigo = load_data("treinos")
                df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
                if save_data("treinos", df_total):
                    st.success("✅ Treino salvo com sucesso!")
                    st.balloons()
                else:
                    st.error("Erro ao salvar treino")
        
        with col2:
            if st.button("📈 Ver Histórico"):
                df = load_data("treinos")
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

# 📊 ABA DE PROGRESSO
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
            
            df_antigo = load_data("progresso")
            df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
            if save_data("progresso", df_total):
                st.success("✅ Progresso salvo com sucesso!")
            else:
                st.error("Erro ao salvar progresso")
        
        st.markdown("---")
        st.subheader("Histórico de Progresso")
        
        df_progresso = load_data("progresso")
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
        df_treinos = load_data("treinos")
        
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
        df_treinos = load_data("treinos")
        
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
                    with bordered_container():
                        st.write(f"**{row['Data'].strftime('%d/%m')}** - {row['Dia']}")
                        st.write(f"{row['Grupo Muscular']}: {row['Exercício']} ({row['Carga (kg)']}kg)")
            else:
                st.info("Nenhum treino registrado nos últimos 30 dias.")
        else:
            st.warning("Nenhum treino registrado ainda.")

# 🎯 ABA DE METAS
elif aba == "🏆 Metas":
    st.title("🏆 Metas e Objetivos")
    
    df_metas = load_data("metas", default_columns=["Meta", "Valor", "Atual"])
    
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
            if save_data("metas", df_metas):
                st.success("Metas atualizadas com sucesso!")
            else:
                st.error("Erro ao salvar metas")
    
    with col2:
        st.subheader("Progresso das Metas")
        
        df_progresso = load_data("progresso")
        df_treinos = load_data("treinos")
        
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
            with bordered_container():
                st.write(f"**{row['Meta']}**")
                if pd.notna(row["Atual"]):
                    progresso = (row["Atual"] / row["Valor"]) * 100
                    st.progress(min(int(progresso), 100), 
                              f"{row['Atual']} / {row['Valor']} ({min(progresso, 100):.1f}%)")
                else:
                    st.info("Dados insuficientes para calcular progresso")

# ⚙️ ABA DE CONFIGURAÇÕES
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
        st.success("Plano de treino atualizado com sucesso!")
    
    st.markdown("---")
    st.subheader("Exportar/Importar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if os.path.exists(os.path.join("gym_data", "treinos.csv")):
            with open(os.path.join("gym_data", "treinos.csv"), "rb") as f:
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
                    if save_data("treinos", df):
                        st.success("Dados de treino importados com sucesso!")
                    else:
                        st.error("Erro ao salvar dados importados")
                elif "Peso (kg)" in df.columns and "Horas de Sono" in df.columns:
                    if save_data("progresso", df):
                        st.success("Dados de progresso importados com sucesso!")
                    else:
                        st.error("Erro ao salvar dados importados")
                else:
                    st.error("Formato de arquivo não reconhecido")
                
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Erro ao carregar arquivo: {e}")