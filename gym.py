import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64
import requests
import json

# Configuração da página
st.set_page_config(
    page_title="Gym Progress Tracker",
    page_icon="🏋️‍♂️",
    layout="wide"
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
    </style>
""", unsafe_allow_html=True)

# 🔄 Configuração de armazenamento (GitHub como "banco de dados")
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")  # Adicione no Render.com > Settings > Secrets
GITHUB_REPO = "drygs/okok"  # Ex: "joaosilva/gym-data"
GITHUB_BRANCH = "main"
DATA_FILES = {
    "treinos": "data/treinos.csv",
    "progresso": "data/progresso.csv",
    "metas": "data/metas.csv"
}

def get_file_sha(path):
    """Obtém o SHA de um arquivo existente no repositório"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["sha"]
    return None

def load_data_from_github(file_key):
    """Carrega dados do arquivo CSV no GitHub ou retorna DataFrame vazio"""
    path = DATA_FILES[file_key]
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        content = response.json()["content"]
        decoded_content = base64.b64decode(content).decode("utf-8")
        return pd.read_csv(pd.compat.StringIO(decoded_content))
    elif response.status_code == 404:
        # Arquivo não existe, retorna DataFrame vazio
        if file_key == "treinos":
            return pd.DataFrame(columns=["Data", "Dia", "Grupo Muscular", "Exercício", "Carga (kg)", "Repetições", "Séries", "Observações"])
        elif file_key == "progresso":
            return pd.DataFrame(columns=["Data", "Peso (kg)", "Horas de Sono", "Cansaço", "Humor", "Calorias", "Água (copos)"])
        elif file_key == "metas":
            return pd.DataFrame(columns=["Meta", "Valor", "Atual"])
    else:
        st.error(f"Erro ao carregar dados do GitHub: {response.status_code}")
        return pd.DataFrame()

def save_data_to_github(df, file_key):
    """Salva DataFrame no arquivo CSV no GitHub"""
    path = DATA_FILES[file_key]
    content = df.to_csv(index=False)
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    
    sha = get_file_sha(path)
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {
        "message": f"Atualização de {file_key} via app",
        "content": encoded_content,
        "branch": GITHUB_BRANCH
    }
    
    if sha:
        data["sha"] = sha
    
    response = requests.put(url, headers=headers, data=json.dumps(data))
    
    if response.status_code not in [200, 201]:
        st.error(f"Erro ao salvar dados no GitHub: {response.status_code}")
        st.write(response.json())
        return False
    return True

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
                df_antigo = load_data_from_github("treinos")
                df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
                if save_data_to_github(df_total, "treinos"):
                    st.success("✅ Treino salvo com sucesso no GitHub!")
                    st.balloons()
        
        with col2:
            if st.button("📈 Ver Histórico"):
                df = load_data_from_github("treinos")
                if not df.empty:
                    st.dataframe(
                        df[df["Dia"] == dia_semana].sort_values("Data", ascending=False),
                        hide_index=True,
                        use_container_width=True
                    )
                    
                    # Gráfico de progresso para cada exercício
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
            
            df_antigo = load_data_from_github("progresso")
            df_total = pd.concat([df_antigo, df_novo], ignore_index=True)
            if save_data_to_github(df_total, "progresso"):
                st.success("✅ Progresso salvo com sucesso no GitHub!")
        
        st.divider()
        st.subheader("Histórico de Progresso")
        
        df_progresso = load_data_from_github("progresso")
        if not df_progresso.empty:
            df_progresso["Data"] = pd.to_datetime(df_progresso["Data"])
            
            # Mostrar métricas recentes
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
            
            # Gráficos
            fig = px.line(df_progresso, x="Data", y=["Peso (kg)", "Horas de Sono", "Água (copos)"],
                         title="Progresso ao Longo do Tempo")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_progresso.sort_values("Data", ascending=False), hide_index=True)
        else:
            st.warning("Nenhum progresso registrado ainda.")
    
    with tab2:
        st.subheader("Evolução de Cargas")
        df_treinos = load_data_from_github("treinos")
        
        if not df_treinos.empty:
            # Selecionar exercício para análise
            exercicio_selecionado = st.selectbox("Escolha um exercício", df_treinos["Exercício"].unique())
            
            df_exercicio = df_treinos[df_treinos["Exercício"] == exercicio_selecionado].sort_values("Data")
            
            if not df_exercicio.empty:
                # Gráfico de progresso
                fig = px.line(df_exercicio, x="Data", y="Carga (kg)", 
                             title=f"Progresso no {exercicio_selecionado}",
                             markers=True)
                st.plotly_chart(fig, use_container_width=True)
                
                # Estatísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Maior Carga", f"{df_exercicio['Carga (kg)'].max()} kg")
                with col2:
                    st.metric("Média Recente", f"{df_exercicio.tail(3)['Carga (kg)'].mean():.1f} kg")
                with col3:
                    progresso = df_exercicio['Carga (kg)'].iloc[-1] - df_exercicio['Carga (kg)'].iloc[0]
                    st.metric("Progresso Total", f"{progresso:.1f} kg")
                
                # Tabela com todos os registros
                st.dataframe(df_exercicio, hide_index=True)
            else:
                st.warning("Nenhum dado encontrado para este exercício.")
        else:
            st.warning("Nenhum treino registrado ainda.")
    
    with tab3:
        st.subheader("Frequência de Treinos")
        df_treinos = load_data_from_github("treinos")
        
        if not df_treinos.empty:
            df_treinos["Data"] = pd.to_datetime(df_treinos["Data"])
            
            # Contagem de treinos por dia
            df_frequencia = df_treinos.groupby("Dia").size().reset_index(name="Contagem")
            fig = px.bar(df_frequencia, x="Dia", y="Contagem", 
                         title="Treinos por Dia da Semana",
                         color="Dia")
            st.plotly_chart(fig, use_container_width=True)
            
            # Calendário de treinos (últimos 30 dias)
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

# 🎯 ABA DE METAS
elif aba == "🏆 Metas":
    st.title("🏆 Metas e Objetivos")
    
    # Carregar metas salvas ou usar padrão
    df_metas = load_data_from_github("metas")
    
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
            if save_data_to_github(df_metas, "metas"):
                st.success("Metas atualizadas com sucesso no GitHub!")
    
    with col2:
        st.subheader("Progresso das Metas")
        
        # Atualizar valores atuais
        df_progresso = load_data_from_github("progresso")
        df_treinos = load_data_from_github("treinos")
        
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
        
        # Mostrar progresso
        for _, row in df_metas.iterrows():
            with st.container(border=True):
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
    
    # Editor de treinos
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
    
    st.divider()
    st.subheader("Exportar/Importar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Exportar dados
        df_treinos = load_data_from_github("treinos")
        if not df_treinos.empty:
            st.download_button(
                label="📤 Exportar Dados de Treino",
                data=df_treinos.to_csv(index=False).encode("utf-8"),
                file_name="treinos_backup.csv",
                mime="text/csv"
            )
        else:
            st.warning("Nenhum dado de treino para exportar")
    
    with col2:
        # Importar dados
        uploaded_file = st.file_uploader("📥 Importar Dados", type=["csv"])
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                # Verificar se é um arquivo válido
                if "Exercício" in df.columns and "Carga (kg)" in df.columns:
                    if save_data_to_github(df, "treinos"):
                        st.success("Dados de treino importados com sucesso para o GitHub!")
                elif "Peso (kg)" in df.columns and "Horas de Sono" in df.columns:
                    if save_data_to_github(df, "progresso"):
                        st.success("Dados de progresso importados com sucesso para o GitHub!")
                else:
                    st.error("Formato de arquivo não reconhecido")
                
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"Erro ao carregar arquivo: {e}")