"""App de controle de finanças: gastos diários, mensais e contas fixas."""
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth

from database import (
    CATEGORIAS_PADRAO,
    adicionar_gasto,
    adicionar_gasto_fixo,
    gastos_fixos_pendentes,
    init_db,
    listar_gastos,
    listar_gastos_fixos,
    remover_gasto,
    remover_gasto_fixo,
)
from export import gerar_planilha

st.set_page_config(page_title="Controle de Finanças", page_icon="💰", layout="wide")

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def rotulo_mes(ano: int, mes: int) -> str:
    return f"{MESES_PT[mes - 1]}/{ano}"


def lista_meses(voltar: int = 6, avancar: int = 6) -> list[tuple[int, int]]:
    """Lista de (ano, mês) em torno do mês atual, para o seletor de gastos fixos."""
    hoje = date.today()
    base = hoje.year * 12 + (hoje.month - 1)
    resultado = []
    for delta in range(-voltar, avancar + 1):
        total = base + delta
        resultado.append((total // 12, total % 12 + 1))
    return resultado


def moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def css_tema(tema: str) -> str:
    escuro = tema == "dark"
    card_bg = "#1e293b" if escuro else "#ffffff"
    borda = "#334155" if escuro else "#e2e8f0"
    valor = "#2dd4bf" if escuro else "#0f766e"
    sombra = "rgba(0,0,0,0.35)" if escuro else "rgba(15, 23, 42, 0.06)"
    campo_bg = "#0b1220" if escuro else "#f8fafc"
    campo_borda = "#3f4d63" if escuro else "#cbd5e1"
    return f"""
<style>
.block-container {{ padding-top: 2rem; max-width: 1120px; }}

.app-header {{
    background: linear-gradient(120deg, #0d9488 0%, #0f766e 55%, #115e59 100%);
    color: #ffffff;
    padding: 26px 30px;
    border-radius: 18px;
    margin-bottom: 8px;
    box-shadow: 0 10px 25px -12px rgba(13, 148, 136, 0.55);
}}
.app-header h1 {{ margin: 0; font-size: 1.9rem; font-weight: 800; letter-spacing: -0.5px; }}
.app-header p {{ margin: 6px 0 0; opacity: 0.9; font-size: 0.98rem; }}

[data-testid="stMetric"] {{
    background: {card_bg};
    border: 1px solid {borda};
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 1px 3px {sombra};
}}
[data-testid="stMetricValue"] {{ font-weight: 700; color: {valor}; }}
[data-testid="stMetricLabel"] {{ opacity: 0.75; }}

.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {{
    border-radius: 10px;
    font-weight: 600;
    border: 1px solid transparent;
}}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{
    border-radius: 10px 10px 0 0;
    padding: 8px 16px;
    font-weight: 600;
}}
div[data-testid="stForm"] {{
    border: 1px solid {borda};
    border-radius: 16px;
    padding: 8px 20px 4px;
    background: {card_bg};
}}

/* Campos de entrada com cor destacada do fundo */
.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea,
div[data-baseweb="input"],
div[data-baseweb="base-input"],
.stSelectbox div[data-baseweb="select"],
.stSelectbox div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div {{
    background-color: {campo_bg} !important;
    border-color: {campo_borda} !important;
    border-radius: 8px !important;
}}
div[data-baseweb="input"]:focus-within,
div[data-baseweb="select"] > div:focus-within,
.stDateInput div[data-baseweb="input"]:focus-within {{
    border-color: #2dd4bf !important;
    box-shadow: 0 0 0 1px #2dd4bf !important;
}}
</style>
"""


st.markdown(css_tema("dark"), unsafe_allow_html=True)

# --- Autenticação ---
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

# Usa o banco permanente (Postgres) se configurado; senão, SQLite local.
if "database" in st.secrets and st.secrets["database"].get("url"):
    os.environ["DATABASE_URL"] = st.secrets["database"]["url"]

init_db()

# --- Dados base ---
gastos = listar_gastos()
df = pd.DataFrame([dict(g) for g in gastos])
if not df.empty:
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.strftime("%Y-%m")

hoje = date.today()
mes_atual_str = hoje.strftime("%Y-%m")
total_mes_atual = 0.0 if df.empty else df.loc[df["mes"] == mes_atual_str, "valor"].sum()

# --- Sidebar ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state['name']}")
    st.metric(f"Gasto em {rotulo_mes(hoje.year, hoje.month)}", moeda(total_mes_atual))
    st.divider()
    authenticator.logout("Sair", "sidebar")

# --- Cabeçalho ---
st.markdown(
    """
    <div class="app-header">
        <h1>💰 Controle de Finanças</h1>
        <p>Seus gastos diários, mensais e contas fixas em um só lugar.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_painel, tab_lancar, tab_fixos, tab_exportar = st.tabs(
    ["📊 Painel", "➕ Lançar gasto", "📌 Gastos fixos", "📥 Exportar"]
)

# ============================ PAINEL ============================
with tab_painel:
    if df.empty:
        st.info("Nenhum gasto cadastrado ainda. Use a aba **➕ Lançar gasto** para começar.")
    else:
        meses = sorted(df["mes"].unique(), reverse=True)
        mes_selecionado = st.selectbox("Filtrar por mês", ["Todos"] + meses)
        df_filtrado = df if mes_selecionado == "Todos" else df[df["mes"] == mes_selecionado]

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total no período", moeda(df_filtrado["valor"].sum()))
        col_b.metric("Nº de gastos", len(df_filtrado))
        media_diaria = (
            df_filtrado.groupby(df_filtrado["data"].dt.date)["valor"].sum().mean()
        )
        col_c.metric(
            "Média diária", moeda(media_diaria) if not pd.isna(media_diaria) else moeda(0)
        )

        col_esq, col_dir = st.columns(2)
        with col_esq:
            st.subheader("Gastos por categoria")
            st.bar_chart(df_filtrado.groupby("categoria")["valor"].sum())
        with col_dir:
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

# ========================= LANÇAR GASTO =========================
with tab_lancar:
    with st.form("novo_gasto", clear_on_submit=True):
        st.subheader("Novo gasto")
        col1, col2 = st.columns(2)
        with col1:
            data_gasto = st.date_input(
                "Data", value=date.today(), format="DD/MM/YYYY"
            )
            categoria = st.selectbox("Categoria", CATEGORIAS_PADRAO)
        with col2:
            descricao = st.text_input("Descrição")
            valor = st.number_input(
                "Valor (R$)", min_value=0.0, step=0.01, format="%.2f"
            )

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

# ========================= GASTOS FIXOS =========================
with tab_fixos:
    st.subheader("Contas recorrentes")
    st.caption(
        "Cadastre uma vez cada conta fixa. Depois, escolha o mês e lance todas de uma vez."
    )

    with st.form("novo_gasto_fixo", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            nome_fixo = st.text_input("Nome (ex: Internet, Fatura do Cartão)")
        with col2:
            categoria_fixo = st.selectbox(
                "Categoria", CATEGORIAS_PADRAO, key="categoria_fixo"
            )
        with col3:
            valor_fixo = st.number_input(
                "Valor esperado (R$)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                key="valor_fixo",
            )

        if st.form_submit_button("Cadastrar gasto fixo"):
            if not nome_fixo.strip():
                st.warning("Informe um nome.")
            elif valor_fixo <= 0:
                st.warning("Informe um valor maior que zero.")
            else:
                adicionar_gasto_fixo(nome_fixo.strip(), categoria_fixo, valor_fixo)
                st.success("Gasto fixo cadastrado!")
                st.rerun()

    gastos_fixos = listar_gastos_fixos()

    if not gastos_fixos:
        st.info("Nenhum gasto fixo cadastrado ainda.")
    else:
        df_fixos = pd.DataFrame([dict(g) for g in gastos_fixos])
        st.dataframe(
            df_fixos[["id", "nome", "categoria", "valor_esperado"]],
            use_container_width=True,
            hide_index=True,
        )

        id_remover_fixo = st.number_input(
            "ID do gasto fixo para remover",
            min_value=0,
            step=1,
            value=0,
            key="id_remover_fixo",
        )
        if st.button("Remover gasto fixo"):
            if id_remover_fixo > 0:
                remover_gasto_fixo(int(id_remover_fixo))
                st.success(f"Gasto fixo {id_remover_fixo} removido.")
                st.rerun()

        st.divider()
        st.markdown("#### Lançar contas do mês")

        opcoes_meses = lista_meses()
        indice_atual = opcoes_meses.index((hoje.year, hoje.month))
        ano_mes = st.selectbox(
            "Mês de referência",
            opcoes_meses,
            index=indice_atual,
            format_func=lambda am: rotulo_mes(am[0], am[1]),
        )
        ano_sel, mes_sel = ano_mes
        primeiro_dia = date(ano_sel, mes_sel, 1)

        pendentes = gastos_fixos_pendentes(ano_sel, mes_sel)

        if not pendentes:
            st.success(
                f"Todas as contas fixas já foram lançadas em {rotulo_mes(ano_sel, mes_sel)}."
            )
        else:
            st.write(
                f"**Contas pendentes em {rotulo_mes(ano_sel, mes_sel)}** "
                "(ajuste valor/data e desmarque o que não quiser lançar):"
            )
            df_pendentes = pd.DataFrame(
                {
                    "lancar": [True for _ in pendentes],
                    "gasto_fixo_id": [p["id"] for p in pendentes],
                    "nome": [p["nome"] for p in pendentes],
                    "categoria": [p["categoria"] for p in pendentes],
                    "data": [primeiro_dia for _ in pendentes],
                    "valor": [p["valor_esperado"] for p in pendentes],
                }
            )
            edicao = st.data_editor(
                df_pendentes,
                column_config={
                    "lancar": st.column_config.CheckboxColumn("Lançar?"),
                    "nome": "Conta",
                    "categoria": "Categoria",
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                },
                column_order=["lancar", "nome", "categoria", "data", "valor"],
                disabled=["gasto_fixo_id", "nome", "categoria"],
                hide_index=True,
                use_container_width=True,
                key=f"editor_pendentes_{ano_sel}_{mes_sel}",
            )

            if st.button("Lançar contas selecionadas", type="primary"):
                selecionadas = edicao[edicao["lancar"]]
                for _, linha in selecionadas.iterrows():
                    data_linha = linha["data"]
                    if not isinstance(data_linha, date):
                        data_linha = pd.to_datetime(data_linha).date()
                    adicionar_gasto(
                        data_linha,
                        linha["nome"],
                        linha["categoria"],
                        float(linha["valor"]),
                        gasto_fixo_id=int(linha["gasto_fixo_id"]),
                    )
                st.success(f"{len(selecionadas)} conta(s) lançada(s)!")
                st.rerun()

# =========================== EXPORTAR ===========================
with tab_exportar:
    st.subheader("Exportar planilha Excel")
    st.caption(
        "Gera um arquivo .xlsx com todos os gastos, resumo mensal e resumo por categoria."
    )
    if st.button("Gerar planilha Excel"):
        caminho = gerar_planilha(gastos, Path("gastos.xlsx"))
        with open(caminho, "rb") as f:
            st.download_button(
                "Baixar planilha (gastos.xlsx)",
                data=f.read(),
                file_name="gastos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
