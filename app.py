"""App simples de controle de finanças e gastos diários/mensais."""
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth

from database import (
    CATEGORIAS_PADRAO,
    adicionar_gasto,
    init_db,
    listar_gastos,
    remover_gasto,
)
from export import gerar_planilha

st.set_page_config(page_title="Controle de Finanças", page_icon="💰", layout="wide")

if "credentials" not in st.secrets:
    st.error(
        "Autenticação não configurada. Copie .streamlit/secrets.toml.example para "
        ".streamlit/secrets.toml e gere sua senha com scripts/gerar_senha.py."
    )
    st.stop()

authenticator = stauth.Authenticate(
    st.secrets["credentials"].to_dict(),
    st.secrets["cookie"]["name"],
    st.secrets["cookie"]["key"],
    st.secrets["cookie"]["expiry_days"],
)

authenticator.login()

if st.session_state.get("authentication_status") is False:
    st.error("Usuário ou senha incorretos.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Informe usuário e senha para acessar.")
    st.stop()

with st.sidebar:
    st.write(f"Logado como **{st.session_state['name']}**")
    authenticator.logout("Sair", "sidebar")

init_db()

st.title("💰 Controle de Finanças")

with st.form("novo_gasto", clear_on_submit=True):
    st.subheader("Novo gasto")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        data_gasto = st.date_input("Data", value=date.today())
    with col2:
        descricao = st.text_input("Descrição")
    with col3:
        categoria = st.selectbox("Categoria", CATEGORIAS_PADRAO)
    with col4:
        valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")

    enviado = st.form_submit_button("Adicionar gasto")
    if enviado:
        if not descricao.strip():
            st.warning("Informe uma descrição para o gasto.")
        elif valor <= 0:
            st.warning("Informe um valor maior que zero.")
        else:
            adicionar_gasto(data_gasto, descricao.strip(), categoria, valor)
            st.success("Gasto adicionado!")
            st.rerun()

st.divider()

gastos = listar_gastos()
df = pd.DataFrame([dict(g) for g in gastos])

if df.empty:
    st.info("Nenhum gasto cadastrado ainda. Adicione o primeiro gasto acima.")
else:
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.strftime("%Y-%m")

    meses = sorted(df["mes"].unique(), reverse=True)
    mes_selecionado = st.selectbox("Filtrar por mês", ["Todos"] + meses)

    df_filtrado = df if mes_selecionado == "Todos" else df[df["mes"] == mes_selecionado]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total no período", f"R$ {df_filtrado['valor'].sum():,.2f}")
    col_b.metric("Nº de gastos", len(df_filtrado))
    media_diaria = df_filtrado.groupby(df_filtrado["data"].dt.date)["valor"].sum().mean()
    col_c.metric("Média diária", f"R$ {media_diaria:,.2f}" if not pd.isna(media_diaria) else "R$ 0,00")

    st.subheader("Gastos por categoria")
    st.bar_chart(df_filtrado.groupby("categoria")["valor"].sum())

    st.subheader("Evolução diária")
    st.line_chart(df_filtrado.groupby(df_filtrado["data"].dt.date)["valor"].sum())

    st.subheader("Lista de gastos")
    tabela = df_filtrado[["id", "data", "descricao", "categoria", "valor"]].copy()
    tabela["data"] = tabela["data"].dt.strftime("%d/%m/%Y")
    st.dataframe(tabela, use_container_width=True, hide_index=True)

    id_remover = st.number_input(
        "ID do gasto para remover", min_value=0, step=1, value=0
    )
    if st.button("Remover gasto"):
        if id_remover > 0:
            remover_gasto(int(id_remover))
            st.success(f"Gasto {id_remover} removido.")
            st.rerun()

st.divider()
st.subheader("Exportar planilha")
if st.button("Gerar planilha Excel"):
    caminho = gerar_planilha(gastos, Path("gastos.xlsx"))
    with open(caminho, "rb") as f:
        st.download_button(
            "Baixar planilha (gastos.xlsx)",
            data=f.read(),
            file_name="gastos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
