import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import time
import sqlite3
from contextlib import closing
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import psycopg2
from urllib.parse import urlparse
import requests
from github import Github
import base64
from cryptography.fernet import Fernet

# 🔐 Configuração de Segurança
def generate_key():
    return Fernet.generate_key()

def encrypt_data(data, key):
    fernet = Fernet(key)
    return fernet.encrypt(data.encode())

def decrypt_data(encrypted_data, key):
    fernet = Fernet(key)
    return fernet.decrypt(encrypted_data).decode()

# 🔄 Configuração de Armazenamento (ESCOLHA UMA OPÇÃO)
STORAGE_TYPE = st.secrets.get("STORAGE_TYPE", "google_sheets")  # Opções: google_sheets, postgresql, sqlite

# 1. Google Sheets
if STORAGE_TYPE == "google_sheets":
    def get_gspread_client():
        scope = ["https://spreadsheets.google.com/feeds", 
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["google_credentials"], scope)
        return gspread.authorize(creds)

    def load_data(sheet_name, worksheet_index=0):
        try:
            gc = get_gspread_client()
            sh = gc.open(sheet_name)
            worksheet = sh.get_worksheet(worksheet_index)
            return pd.DataFrame(worksheet.get_all_records())
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame()

    def save_data(df, sheet_name, worksheet_index=0):
        try:
            gc = get_gspread_client()
            sh = gc.open(sheet_name)
            worksheet = sh.get_worksheet(worksheet_index)
            worksheet.clear()
            worksheet.update([df.columns.values.tolist()] + df.values.tolist())
            return True
        except Exception as e:
            st.error(f"Erro ao salvar dados: {e}")
            return False

# 2. PostgreSQL (Render)
elif STORAGE_TYPE == "postgresql":
    def get_conn():
        try:
            conn = psycopg2.connect(st.secrets["DATABASE_URL"])
            return conn
        except Exception as e:
            st.error(f"Erro ao conectar ao PostgreSQL: {e}")
            return None

    def init_db():
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # Tabela de treinos
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS treinos (
                            id SERIAL PRIMARY KEY,
                            data DATE NOT NULL,
                            dia VARCHAR(20) NOT NULL,
                            grupo_muscular VARCHAR(50) NOT NULL,
                            exercicio VARCHAR(50) NOT NULL,
                            carga DECIMAL(5,2),
                            repeticoes INTEGER,
                            series INTEGER,
                            observacoes TEXT
                        )
                    """)
                    # Tabela de progresso
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS progresso (
                            id SERIAL PRIMARY KEY,
                            data DATE NOT NULL,
                            peso DECIMAL(5,2),
                            horas_sono DECIMAL(3,1),
                            cansaco INTEGER,
                            humor VARCHAR(10),
                            calorias DECIMAL(7,2),
                            agua INTEGER
                        )
                    """)
                    # Tabela de metas
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS metas (
                            id SERIAL PRIMARY KEY,
                            meta VARCHAR(50) NOT NULL,
                            valor DECIMAL(7,2),
                            atual DECIMAL(7,2)
                        )
                    """)
                    conn.commit()
        except Exception as e:
            st.error(f"Erro ao inicializar banco de dados: {e}")

    def load_data(table_name):
        try:
            with get_conn() as conn:
                return pd.read_sql(f"SELECT * FROM {table_name}", conn)
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame()

    def save_data(df, table_name, mode="replace"):
        try:
            with get_conn() as conn:
                if mode == "replace":
                    conn.cursor().execute(f"DELETE FROM {table_name}")
                df.to_sql(table_name, conn, if_exists="append", index=False)
                return True
        except Exception as e:
            st.error(f"Erro ao salvar dados: {e}")
            return False

# 3. SQLite com Backup no GitHub
elif STORAGE_TYPE == "sqlite":
    DATA_DIR = "gym_data"
    os.makedirs(DATA_DIR, exist_ok=True)
    DB_PATH = os.path.join(DATA_DIR, "gym_data.db")
    
    def init_db():
        try:
            with closing(sqlite3.connect(DB_PATH)) as conn:
                cursor = conn.cursor()
                # Tabela de treinos
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS treinos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data TEXT,
                        dia TEXT,
                        grupo_muscular TEXT,
                        exercicio TEXT,
                        carga REAL,
                        repeticoes INTEGER,
                        series INTEGER,
                        observacoes TEXT
                    )
                """)
                # Tabela de progresso
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS progresso (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data TEXT,
                        peso REAL,
                        horas_sono REAL,
                        cansaco INTEGER,
                        humor TEXT,
                        calorias REAL,
                        agua INTEGER
                    )
                """)
                # Tabela de metas
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS metas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meta TEXT,
                        valor REAL,
                        atual REAL
                    )
                """)
                conn.commit()
        except Exception as e:
            st.error(f"Erro ao inicializar banco de dados: {e}")

    def load_data(table_name):
        try:
            with closing(sqlite3.connect(DB_PATH)) as conn:
                return pd.read_sql(f"SELECT * FROM {table_name}", conn)
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return pd.DataFrame()

    def save_data(df, table_name, mode="replace"):
        try:
            with closing(sqlite3.connect(DB_PATH)) as conn:
                if mode == "replace":
                    conn.cursor().execute(f"DELETE FROM {table_name}")
                df.to_sql(table_name, conn, if_exists="append", index=False)
                return True
        except Exception as e:
            st.error(f"Erro ao salvar dados: {e}")
            return False

    def backup_to_github():
        try:
            if "github_token" in st.secrets and "github_repo" in st.secrets:
                g = Github(st.secrets["github_token"])
                repo = g.get_repo(st.secrets["github_repo"])
                
                with open(DB_PATH, "rb") as f:
                    content = f.read()
                
                repo.create_file(
                    path=f"backups/gym_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                    message=f"Backup automático em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                    content=content,
                    branch="main"
                )
                return True
        except Exception as e:
            st.error(f"Erro ao fazer backup: {e}")
            return False

# Configuração da página
st.set_page_config(
    page_title="Gym Progress Tracker Pro",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 Estilos CSS personalizados
st.markdown("""
    <style>
    :root {
        --primary-color: #2e86ab;
        --secondary-color: #f18f01;
        --background-color: #f5f5f5;
        --card-color: #ffffff;
    }
    
    .main {
        background-color: var(--background-color);
        color: #333333;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        border-radius: 12px;
        padding: 20px;
        background-color: var(--card-color);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        transition: all 0.3s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    
    .progress-header {
        color: var(--primary-color);
        border-bottom: 2px solid var(--primary-color);
        padding-bottom: 5px;
    }
    
    /* Dark mode */
    [data-theme="dark"] {
        --primary-color: #3a86ff;
        --secondary-color: #ffbe0b;
        --background-color: #121212;
        --card-color: #1e1e1e;
    }
    
    [data-theme="dark"] .main {
        color: #f0f0f0;
    }
    
    [data-theme="dark"] .metric-card {
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

# 🌙 Toggle Dark Mode
if st.sidebar.toggle("🌙 Modo Escuro", value=False, key="dark_mode"):
    st.markdown('<style>[data-testid="stAppViewContainer"] { background-color: #121212; }</style>', unsafe_allow_html=True)

# 🔐 Sistema de Login Simples
if "github_token" in st.secrets:
    senha = st.sidebar.text_input("🔒 Senha de Acesso", type="password")
    if senha != st.secrets.get("APP_PASSWORD", "gym123"):
        st.error("🔐 Senha incorreta. Acesso negado.")
        st.stop()

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

# ⏱️ Timer de Descanso
def timer_descanso(segundos=90):
    with st.empty():
        for sec in range(segundos, 0, -1):
            mins, secs = divmod(sec, 60)
            timer = f"⏳ {mins:02d}:{secs:02d}"
            st.markdown(f"<h1 style='text-align: center; color: var(--secondary-color);'>{timer}</h1>", 
                        unsafe_allow_html=True)
            time.sleep(1)
        st.success("🏋️‍♂️ Próxima série!")
        st.balloons()

# 🏋️‍♂️ Calculadora de 1RM
def calcular_1rm(peso, reps):
    return peso * (36 / (37 - reps)) if reps > 0 else 0

# 🧭 Navegação por abas
aba = st.sidebar.selectbox("📂 Navegação", 
                          ["🏠 Dashboard", "📅 Treino Diário", "📊 Progresso", "🏆 Metas", 
                           "🍎 Nutrição", "📸 Progresso Físico", "⚙️ Configurações"])

# 🏠 ABA DASHBOARD
if aba == "🏠 Dashboard":
    st.title("🏠 Dashboard de Progresso")
    
    # Carregar dados
    df_treinos = load_data("treinos")
    df_progresso = load_data("progresso")
    df_metas = load_data("metas")
    
    # Métricas Principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card"><h3>Último Treino</h3>', unsafe_allow_html=True)
        if not df_treinos.empty:
            ultimo_treino = df_treinos.iloc[-1]
            st.metric("Dia", ultimo_treino["dia"])
            st.metric("Exercício", ultimo_treino["exercicio"])
        else:
            st.info("Nenhum treino registrado")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card"><h3>Progresso Físico</h3>', unsafe_allow_html=True)
        if not df_progresso.empty:
            ultimo_peso = df_progresso.iloc[-1]["peso"]
            st.metric("Peso Atual", f"{ultimo_peso} kg")
            
            if len(df_progresso) > 1:
                variacao = ultimo_peso - df_progresso.iloc[-2]["peso"]
                st.metric("Variação", f"{variacao:+.1f} kg")
        else:
            st.info("Nenhum dado físico")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card"><h3>Metas</h3>', unsafe_allow_html=True)
        if not df_metas.empty():
            for _, meta in df_metas.iterrows():
                if pd.notna(meta["atual"]):
                    progresso = (meta["atual"] / meta["valor"]) * 100
                    st.progress(min(int(progresso), 100), 
                              f"{meta['meta']}: {meta['atual']}/{meta['valor']}")
        else:
            st.info("Nenhuma meta definida")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card"><h3>Estatísticas</h3>', unsafe_allow_html=True)
        if not df_treinos.empty:
            st.metric("Total Treinos", len(df_treinos))
            st.metric("Dias Únicos", df_treinos["data"].nunique())
            
            # Próximo treino sugerido
            if dia_semana in st.session_state.treino_por_dia:
                st.success(f"💪 Hoje é dia de {dia_semana}")
            else:
                st.info("📴 Hoje é dia de descanso")
        else:
            st.info("Nenhuma estatística")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Gráficos de Progresso
    if not df_treinos.empty and not df_progresso.empty:
        tab1, tab2 = st.tabs(["📈 Progresso de Cargas", "📊 Correlações"])
        
        with tab1:
            exercicio_selecionado = st.selectbox("Selecione um exercício", 
                                               df_treinos["exercicio"].unique())
            
            df_exercicio = df_treinos[df_treinos["exercicio"] == exercicio_selecionado]
            if not df_exercicio.empty:
                fig = px.line(df_exercicio, x="data", y="carga", 
                             title=f"Progresso no {exercicio_selecionado}",
                             markers=True,
                             color_discrete_sequence=["var(--primary-color)"])
                st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            df_merged = pd.merge(df_progresso, df_treinos, on="data", how="inner")
            if not df_merged.empty:
                variavel = st.selectbox("Selecione uma variável", 
                                      ["peso", "horas_sono", "cansaco", "agua"])
                
                fig = px.scatter(df_merged, x=variavel, y="carga", 
                               trendline="ols",
                               title=f"Relação entre {variavel} e carga levantada",
                               color_discrete_sequence=["var(--secondary-color)"])
                st.plotly_chart(fig, use_container_width=True)
    
    # Lembretes
    with st.expander("🔔 Lembretes e Notas"):
        lembrete = st.text_input("Adicionar novo lembrete")
        if st.button("Salvar Lembrete"):
            st.session_state.lembretes = st.session_state.get("lembretes", []) + [lembrete]
            st.success("Lembrete adicionado!")
        
        if "lembretes" in st.session_state:
            for i, lembrete in enumerate(st.session_state.lembretes):
                st.checkbox(f"📌 {lembrete}", key=f"lembrete_{i}")

# 📅 ABA DE TREINO DIÁRIO
elif aba == "📅 Treino Diário":
    st.title(f"🏋️‍♂️ Treino - {dia_semana}-feira")
    st.subheader(f"{data_atual}")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Dia da Semana", dia_semana)
        if dia_semana in st.session_state.treino_por_dia:
            st.success("💪 Dia de treino!")
        else:
            st.info("📴 Dia de descanso")
        
        # Timer de Descanso
        if st.button("⏱️ Timer de Descanso (90s)"):
            timer_descanso()
        st.markdown('</div>', unsafe_allow_html=True)
    
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
                        
                        # Calculadora de 1RM
                        if carga > 0 and repeticoes > 0:
                            rm1 = calcular_1rm(carga, repeticoes)
                            st.metric("1RM Estimado", f"{rm1:.1f} kg")
                        
                        # Técnicas avançadas
                        tecnica = st.selectbox("Técnica", 
                                             ["Normal", "Dropset", "Falha", "Rest-Pause"],
                                             key=f"{exercicio}_tecnica")
                        
                        observacoes = st.text_input("Observações", key=f"{exercicio}_obs")
                        
                        registros.append({
                            "data": datetime.now().strftime("%Y-%m-%d"),
                            "dia": dia_semana,
                            "grupo_muscular": grupo,
                            "exercicio": exercicio,
                            "carga": carga,
                            "repeticoes": repeticoes,
                            "series": series,
                            "tecnica": tecnica,
                            "observacoes": observacoes
                        })

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Salvar Treino", type="primary"):
                df_novo = pd.DataFrame(registros)
                df_antigo = load_data("treinos")
                df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
                if save_data(df_total, "treinos"):
                    st.success("✅ Treino salvo com sucesso!")
                    st.balloons()
                    if STORAGE_TYPE == "sqlite":
                        backup_to_github()
        
        with col2:
            if st.button("📈 Ver Histórico"):
                df = load_data("treinos")
                if not df.empty:
                    st.dataframe(
                        df[df["dia"] == dia_semana].sort_values("data", ascending=False),
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Gráfico de progresso para cada exercício
                    exercicios_dia = [ex for grupo in st.session_state.treino_por_dia[dia_semana].values() for ex in grupo]
                    for exercicio in exercicios_dia:
                        df_ex = df[df["exercicio"] == exercicio]
                        if not df_ex.empty:
                            fig = px.line(df_ex, x="data", y="carga", 
                                        title=f"Progresso - {exercicio}",
                                        color_discrete_sequence=["var(--primary-color)"])
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Ainda não há registros salvos.")

# 📊 ABA DE PROGRESSO
elif aba == "📊 Progresso":
    st.title("📊 Progresso Corporal & Estilo de Vida")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Métricas Diárias", "🏋️‍♂️ Evolução de Cargas", 
                                     "📅 Calendário de Treinos", "🔄 Correlações"])
    
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
                "data": datetime.now().strftime("%Y-%m-%d"),
                "peso": peso,
                "horas_sono": sono,
                "cansaco": cansaco,
                "humor": humor,
                "calorias": calorias if calorias > 0 else None,
                "agua": agua
            }])
            
            df_antigo = load_data("progresso")
            df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
            if save_data(df_total, "progresso"):
                st.success("✅ Progresso salvo com sucesso!")
        
        st.divider()
        st.subheader("Histórico de Progresso")
        
        df_progresso = load_data("progresso")
        if not df_progresso.empty:
            df_progresso["data"] = pd.to_datetime(df_progresso["data"])
            
            # Mostrar métricas recentes
            ultimo_registro = df_progresso.iloc[-1]
            cols = st.columns(4)
            with cols[0]:
                st.metric("Último Peso", f"{ultimo_registro['peso']} kg")
            with cols[1]:
                st.metric("Média de Sono", f"{df_progresso['horas_sono'].mean():.1f} horas")
            with cols[2]:
                st.metric("Média de Água", f"{df_progresso['agua'].mean():.1f} copos/dia")
            with cols[3]:
                st.metric("Dias Registrados", len(df_progresso))
            
            # Gráficos
            fig = px.line(df_progresso, x="data", y=["peso", "horas_sono", "agua"],
                         title="Progresso ao Longo do Tempo",
                         color_discrete_sequence=[px.colors.qualitative.Plotly[0], 
                                                px.colors.qualitative.Plotly[1],
                                                px.colors.qualitative.Plotly[2]])
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_progresso.sort_values("data", ascending=False), hide_index=True)
        else:
            st.warning("Nenhum progresso registrado ainda.")
    
    with tab2:
        st.subheader("Evolução de Cargas")
        df_treinos = load_data("treinos")
        
        if not df_treinos.empty:
            # Selecionar exercício para análise
            exercicio_selecionado = st.selectbox("Escolha um exercício", df_treinos["exercicio"].unique())
            
            df_exercicio = df_treinos[df_treinos["exercicio"] == exercicio_selecionado].sort_values("data")
            
            if not df_exercicio.empty:
                # Gráfico de progresso
                fig = px.line(df_exercicio, x="data", y="carga", 
                             title=f"Progresso no {exercicio_selecionado}",
                             markers=True,
                             color_discrete_sequence=["var(--primary-color)"])
                st.plotly_chart(fig, use_container_width=True)
                
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Maior Carga", f"{df_exercicio['carga'].max()} kg")
                with col2:
                    st.metric("Média Recente", f"{df_exercicio.tail(3)['carga'].mean():.1f} kg")
                with col3:
                    progresso = df_exercicio['carga'].iloc[-1] - df_exercicio['carga'].iloc[0]
                    st.metric("Progresso Total", f"{progresso:.1f} kg")
                
                # Tabela com todos os registros
                st.dataframe(df_exercicio, hide_index=True)
            else:
                st.warning("Nenhum dado encontrado para este exercício.")
        else:
            st.warning("Nenhum treino registrado ainda.")
    
    with tab3:
        st.subheader("Frequência de Treinos")
        df_treinos = load_data("treinos")
        
        if not df_treinos.empty:
            df_treinos["data"] = pd.to_datetime(df_treinos["data"])
            
            # Contagem de treinos por dia
            df_frequencia = df_treinos.groupby("dia").size().reset_index(name="contagem")
            fig = px.bar(df_frequencia, x="dia", y="contagem", 
                         title="Treinos por Dia da Semana",
                         color="dia",
                         color_discrete_sequence=px.colors.qualitative.Plotly)
            st.plotly_chart(fig, use_container_width=True)
            
            # Calendário de treinos (últimos 30 dias)
            data_limite = datetime.now() - timedelta(days=30)
            df_recente = df_treinos[df_treinos["data"] >= data_limite]
            
            if not df_recente.empty:
                st.write("**Últimos Treinos:**")
                for _, row in df_recente.sort_values("data", ascending=False).iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['data'].strftime('%d/%m')}** - {row['dia']}")
                        st.write(f"{row['grupo_muscular']}: {row['exercicio']} ({row['carga']}kg)")
            else:
                st.info("Nenhum treino registrado nos últimos 30 dias.")
        else:
            st.warning("Nenhum treino registrado ainda.")
    
    with tab4:
        st.subheader("Análise de Correlações")
        df_treinos = load_data("treinos")
        df_progresso = load_data("progresso")
        
        if not df_treinos.empty and not df_progresso.empty:
            df_merged = pd.merge(df_progresso, df_treinos, on="data", how="inner")
            
            variavel = st.selectbox("Selecione uma métrica para análise", 
                                  ["peso", "horas_sono", "cansaco", "agua"])
            
            fig = px.scatter(df_merged, x=variavel, y="carga", 
                           trendline="ols",
                           title=f"Relação entre {variavel} e desempenho",
                           color="exercicio",
                           color_discrete_sequence=px.colors.qualitative.Plotly)
            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar estatísticas de correlação
            correlacao = df_merged[[variavel, "carga"]].corr().iloc[0,1]
            st.metric(f"Coeficiente de Correlação ({variavel} x Carga)", f"{correlacao:.2f}")
        else:
            st.warning("Dados insuficientes para análise de correlação.")

# 🏆 ABA DE METAS
elif aba == "🏆 Metas":
    st.title("🏆 Metas e Objetivos")
    
    # Carregar metas salvas ou usar padrão
    df_metas = load_data("metas")
    
    if df_metas.empty:
        metas_padrao = [
            {"meta": "Peso", "valor": 75.0, "atual": None},
            {"meta": "Agachamento", "valor": 120.0, "atual": None},
            {"meta": "Supino", "valor": 80.0, "atual": None},
            {"meta": "Dias de Treino", "valor": 4, "atual": None}
        ]
        df_metas = pd.DataFrame(metas_padrao)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Definir Metas")
        
        metas_editaveis = []
        for _, row in df_metas.iterrows():
            novo_valor = st.number_input(
                f"{row['meta']} (alvo)", 
                value=row["valor"],
                key=f"meta_{row['meta']}"
            )
            metas_editaveis.append({
                "meta": row["meta"],
                "valor": novo_valor,
                "atual": row["atual"]
            })
        
        if st.button("Salvar Metas"):
            df_metas = pd.DataFrame(metas_editaveis)
            if save_data(df_metas, "metas", mode="replace"):
                st.success("Metas atualizadas com sucesso!")
    
    with col2:
        st.subheader("Progresso das Metas")
        
        # Atualizar valores atuais
        df_progresso = load_data("progresso")
        df_treinos = load_data("treinos")
        
        for i, row in df_metas.iterrows():
            if row["meta"] == "Peso" and not df_progresso.empty:
                df_metas.at[i, "atual"] = df_progresso["peso"].iloc[-1]
            elif row["meta"] == "Agachamento" and not df_treinos.empty:
                if "Agachamento" in df_treinos["exercicio"].values:
                    df_metas.at[i, "atual"] = df_treinos[df_treinos["exercicio"] == "Agachamento"]["carga"].max()
            elif row["meta"] == "Supino" and not df_treinos.empty:
                if "Supino Plano" in df_treinos["exercicio"].values:
                    df_metas.at[i, "atual"] = df_treinos[df_treinos["exercicio"] == "Supino Plano"]["carga"].max()
            elif row["meta"] == "Dias de Treino" and not df_treinos.empty:
                df_metas.at[i, "atual"] = df_treinos["data"].nunique()
        
        # Mostrar progresso
        for _, row in df_metas.iterrows():
            with st.container(border=True):
                st.write(f"**{row['meta']}**")
                if pd.notna(row["atual"]):
                    progresso = (row["atual"] / row["valor"]) * 100
                    st.progress(min(int(progresso), 100), 
                              f"{row['atual']} / {row['valor']} ({min(progresso, 100):.1f}%)")
                else:
                    st.info("Dados insuficientes para calcular progresso")

# 🍎 ABA DE NUTRIÇÃO
elif aba == "🍎 Nutrição":
    st.title("🍎 Acompanhamento Nutricional")
    
    tab1, tab2 = st.tabs(["📊 Registro Diário", "🍽️ Calculadora de Macros"])
    
    with tab1:
        st.subheader("Registro Nutricional Diário")
        
        col1, col2 = st.columns(2)
        
        with col1:
            proteina = st.number_input("Proteínas (g)", min_value=0, step=1)
            carboidratos = st.number_input("Carboidratos (g)", min_value=0, step=1)
        
        with col2:
            gorduras = st.number_input("Gorduras (g)", min_value=0, step=1)
            fibras = st.number_input("Fibras (g)", min_value=0, step=1)
            fibras = st.number_input("Fibras (g)", min_value=0, step=1)
        
        calorias_total = (proteina * 4) + (carboidratos * 4) + (gorduras * 9)
        st.metric("Total de Calorias", f"{calorias_total} kcal")
        
        if st.button("💾 Salvar Registro Nutricional"):
            df_novo = pd.DataFrame([{
                "data": datetime.now().strftime("%Y-%m-%d"),
                "proteina": proteina,
                "carboidratos": carboidratos,
                "gorduras": gorduras,
                "fibras": fibras,
                "calorias": calorias_total
            }])
            
            # Carregar dados existentes e salvar
            df_antigo = load_data("nutricao")
            df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
            if save_data(df_total, "nutricao"):
                st.success("✅ Registro nutricional salvo!")
        
        st.divider()
        st.subheader("Histórico Nutricional")
        
        df_nutricao = load_data("nutricao")
        if not df_nutricao.empty:
            # Mostrar métricas recentes
            ultimo_registro = df_nutricao.iloc[-1]
            cols = st.columns(4)
            with cols[0]:
                st.metric("Média Proteína", f"{df_nutricao['proteina'].mean():.1f}g")
            with cols[1]:
                st.metric("Média Carboidratos", f"{df_nutricao['carboidratos'].mean():.1f}g")
            with cols[2]:
                st.metric("Média Gorduras", f"{df_nutricao['gorduras'].mean():.1f}g")
            with cols[3]:
                st.metric("Média Calorias", f"{df_nutricao['calorias'].mean():.0f}kcal")
            
            # Gráfico de evolução
            fig = px.line(df_nutricao, x="data", y=["proteina", "carboidratos", "gorduras"],
                         title="Evolução Nutricional",
                         labels={"value": "Gramas", "variable": "Macronutriente"},
                         color_discrete_map={
                             "proteina": "#1f77b4",
                             "carboidratos": "#ff7f0e",
                             "gorduras": "#2ca02c"
                         })
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela completa
            st.dataframe(df_nutricao.sort_values("data", ascending=False), hide_index=True)
        else:
            st.warning("Nenhum registro nutricional encontrado.")
    
    with tab2:
        st.subheader("Calculadora de Macronutrientes")
        
        peso = st.number_input("Seu peso (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1)
        objetivo = st.selectbox("Objetivo", ["Manter peso", "Perder gordura", "Ganhar massa muscular"])
        nivel_atividade = st.selectbox("Nível de Atividade", [
            "Sedentário", "Levemente ativo", "Moderadamente ativo", 
            "Muito ativo", "Extremamente ativo"
        ])
        
        if st.button("Calcular Macros"):
            # Cálculo de calorias base (Harris-Benedict simplificado)
            tmb = peso * 24  # Taxa Metabólica Basal simplificada
            
            # Fator de atividade
            fatores = {
                "Sedentário": 1.2,
                "Levemente ativo": 1.375,
                "Moderadamente ativo": 1.55,
                "Muito ativo": 1.725,
                "Extremamente ativo": 1.9
            }
            tdee = tmb * fatores[nivel_atividade]
            
            # Ajuste por objetivo
            if objetivo == "Perder gordura":
                tdee *= 0.85  # Déficit de 15%
            elif objetivo == "Ganhar massa muscular":
                tdee *= 1.15  # Superávit de 15%
            
            # Distribuição de macros
            proteina = peso * 2.2  # 2.2g/kg para ganho muscular
            gordura = (tdee * 0.25) / 9  # 25% de calorias de gordura
            carboidratos = (tdee - (proteina * 4) - (gordura * 9)) / 4
            
            # Exibir resultados
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Calorias Diárias", f"{tdee:.0f} kcal")
            with col2:
                st.metric("Proteínas", f"{proteina:.1f}g")
            with col3:
                st.metric("Carboidratos", f"{carboidratos:.1f}g")
            
            st.metric("Gorduras", f"{gordura:.1f}g")
            
            # Gráfico de distribuição
            macros = {
                "Proteína": proteina * 4,
                "Carboidratos": carboidratos * 4,
                "Gorduras": gordura * 9
            }
            fig = px.pie(
                names=list(macros.keys()),
                values=list(macros.values()),
                title="Distribuição de Macronutrientes",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig, use_container_width=True)

# 📸 ABA DE PROGRESSO FÍSICO
elif aba == "📸 Progresso Físico":
    st.title("📸 Registro de Progresso Físico")
    
    tab1, tab2 = st.tabs(["📷 Adicionar Foto", "📊 Comparação Visual"])
    
    with tab1:
        st.subheader("Registrar Foto de Progresso")
        
        data_foto = st.date_input("Data da Foto", datetime.now())
        angulo = st.selectbox("Ângulo", ["Frontal", "Lateral", "Posterior", "Superior"])
        uploaded_file = st.file_uploader("Escolha uma imagem", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None and st.button("Salvar Foto"):
            # Salvar a foto no sistema de armazenamento selecionado
            try:
                if STORAGE_TYPE == "google_sheets":
                    # Implementar lógica para salvar no Google Drive e registrar no Sheets
                    pass
                elif STORAGE_TYPE in ["postgresql", "sqlite"]:
                    # Converter imagem para bytes
                    bytes_data = uploaded_file.getvalue()
                    
                    # Criar registro no banco de dados
                    df_novo = pd.DataFrame([{
                        "data": data_foto.strftime("%Y-%m-%d"),
                        "angulo": angulo,
                        "imagem": bytes_data,
                        "observacoes": st.text_area("Observações")
                    }])
                    
                    df_antigo = load_data("fotos")
                    df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
                    if save_data(df_total, "fotos"):
                        st.success("Foto salva com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar foto: {e}")
    
    with tab2:
        st.subheader("Comparação Visual ao Longo do Tempo")
        
        df_fotos = load_data("fotos")
        if not df_fotos.empty:
            # Agrupar fotos por ângulo
            angulos = df_fotos["angulo"].unique()
            angulo_selecionado = st.selectbox("Selecione um ângulo", angulos)
            
            # Filtrar fotos para o ângulo selecionado
            df_filtrado = df_fotos[df_fotos["angulo"] == angulo_selecionado]
            
            # Mostrar slider para selecionar datas para comparação
            datas = pd.to_datetime(df_filtrado["data"]).dt.strftime("%d/%m/%Y")
            if len(datas) >= 2:
                col1, col2 = st.columns(2)
                
                with col1:
                    data1 = st.selectbox("Primeira Data", datas, index=0)
                    idx1 = datas.tolist().index(data1)
                    img1 = df_filtrado.iloc[idx1]["imagem"]
                    st.image(img1, caption=data1, use_column_width=True)
                
                with col2:
                    data2 = st.selectbox("Segunda Data", datas, index=min(1, len(datas)-1))
                    idx2 = datas.tolist().index(data2)
                    img2 = df_filtrado.iloc[idx2]["imagem"]
                    st.image(img2, caption=data2, use_column_width=True)
            else:
                st.warning("Número insuficiente de fotos para comparação.")
        else:
            st.warning("Nenhuma foto registrada ainda.")

# ⚙️ ABA DE CONFIGURAÇÕES
elif aba == "⚙️ Configurações":
    st.title("⚙️ Configurações do Aplicativo")
    
    tab1, tab2, tab3 = st.tabs(["📝 Plano de Treino", "🔒 Segurança", "🗃️ Dados"])
    
    with tab1:
        st.subheader("Personalizar Plano de Treino")
        
        dias_treino = st.multiselect(
            "Dias de Treino na Semana",
            ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"],
            default=["Segunda", "Quarta", "Quinta", "Sexta"]
        )
        
        # Editor de plano de treino
        st.write("**Defina os exercícios para cada dia:**")
        
        novo_plano = {}
        for dia in dias_treino:
            with st.expander(f"Treino de {dia}"):
                grupos = st.text_input(
                    f"Grupos musculares para {dia} (separados por vírgula)",
                    value=", ".join(st.session_state.treino_por_dia.get(dia, {}).keys()),
                    key=f"grupos_{dia}"
                )
                
                grupos_lista = [g.strip() for g in grupos.split(",") if g.strip()]
                grupo_exercicios = {}
                
                for grupo in grupos_lista:
                    exercicios = st.text_input(
                        f"Exercícios para {grupo} (separados por vírgula)",
                        value=", ".join(st.session_state.treino_por_dia.get(dia, {}).get(grupo, [])),
                        key=f"exerc_{dia}_{grupo}"
                    )
                    grupo_exercicios[grupo] = [e.strip() for e in exercicios.split(",") if e.strip()]
                
                novo_plano[dia] = grupo_exercicios
        
        if st.button("Salvar Plano de Treino"):
            st.session_state.treino_por_dia = novo_plano
            st.success("Plano de treino atualizado com sucesso!")
    
    with tab2:
        st.subheader("Configurações de Segurança")
        
        if "github_token" in st.secrets:
            st.warning("A autenticação está ativada via GitHub.")
        else:
            nova_senha = st.text_input("Definir Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
            
            if st.button("Atualizar Senha"):
                if nova_senha and nova_senha == confirmar_senha:
                    # Em produção, você usaria um método seguro para armazenar a senha
                    st.session_state.app_password = nova_senha
                    st.success("Senha atualizada com sucesso!")
                else:
                    st.error("As senhas não coincidem ou estão vazias.")
        
        st.divider()
        st.write("**Criptografia de Dados**")
        
        if "encryption_key" not in st.session_state:
            st.session_state.encryption_key = generate_key()
        
        st.code(f"Chave de criptografia: {st.session_state.encryption_key.decode()}")
        
        if st.button("Gerar Nova Chave"):
            st.session_state.encryption_key = generate_key()
            st.warning("⚠️ ATENÇÃO: Uma nova chave irá invalidar todos os dados criptografados anteriormente!")
    
    with tab3:
        st.subheader("Gerenciamento de Dados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Exportar Dados**")
            formato = st.selectbox("Formato de Exportação", ["CSV", "Excel", "JSON"])
            
            if st.button("Exportar Todos os Dados"):
                try:
                    tabelas = {
                        "treinos": load_data("treinos"),
                        "progresso": load_data("progresso"),
                        "metas": load_data("metas"),
                        "nutricao": load_data("nutricao")
                    }
                    
                    if formato == "CSV":
                        for nome, df in tabelas.items():
                            if not df.empty:
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    f"Baixar {nome}.csv",
                                    data=csv,
                                    file_name=f"{nome}.csv",
                                    mime="text/csv"
                                )
                    elif formato == "Excel":
                        with pd.ExcelWriter("dados_gym.xlsx") as writer:
                            for nome, df in tabelas.items():
                                if not df.empty:
                                    df.to_excel(writer, sheet_name=nome, index=False)
                        with open("dados_gym.xlsx", "rb") as f:
                            st.download_button(
                                "Baixar dados_gym.xlsx",
                                data=f,
                                file_name="dados_gym.xlsx",
                                mime="application/vnd.ms-excel"
                            )
                    elif formato == "JSON":
                        for nome, df in tabelas.items():
                            if not df.empty:
                                json = df.to_json(orient="records", indent=2)
                                st.download_button(
                                    f"Baixar {nome}.json",
                                    data=json,
                                    file_name=f"{nome}.json",
                                    mime="application/json"
                                )
                except Exception as e:
                    st.error(f"Erro ao exportar dados: {e}")
        
        with col2:
            st.write("**Importar Dados**")
            arquivo = st.file_uploader("Selecione um arquivo", type=["csv", "xlsx", "json"])
            tabela_destino = st.selectbox("Tabela de Destino", ["treinos", "progresso", "metas", "nutricao"])
            
            if arquivo and st.button("Importar Dados"):
                try:
                    if arquivo.name.endswith(".csv"):
                        df = pd.read_csv(arquivo)
                    elif arquivo.name.endswith(".xlsx"):
                        df = pd.read_excel(arquivo)
                    elif arquivo.name.endswith(".json"):
                        df = pd.read_json(arquivo)
                    
                    if save_data(df, tabela_destino, mode="append"):
                        st.success(f"Dados importados com sucesso para a tabela {tabela_destino}!")
                except Exception as e:
                    st.error(f"Erro ao importar dados: {e}")
            st.divider()
            st.write("**Limpar Dados**")
            tabela_limpar = st.selectbox("Tabela para Limpar", ["treinos", "progresso", "metas", "nutricao", "fotos"])
            
            if st.button("Limpar Tabela", type="secondary"):
                if save_data(pd.DataFrame(), tabela_limpar, mode="replace"):
                    st.warning(f"Todos os dados da tabela {tabela_limpar} foram removidos!")

# Rodapé
st.sidebar.divider()
st.sidebar.markdown("""
    <div style="text-align: center; font-size: small; color: #666;">
    Gym Progress Tracker Pro v1.0<br>
    Desenvolvido com ❤️ e Streamlit
    </div>
""", unsafe_allow_html=True)

# Inicialização do banco de dados
if STORAGE_TYPE in ["postgresql", "sqlite"]:
    init_db()
            