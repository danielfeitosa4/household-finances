"""Geração da planilha Excel com os gastos e resumo mensal."""
from pathlib import Path

import pandas as pd


def gerar_planilha(gastos: list, caminho_saida: Path) -> Path:
    df = pd.DataFrame(
        [dict(g) for g in gastos],
        columns=["id", "data", "descricao", "categoria", "valor"],
    )

    if df.empty:
        df = pd.DataFrame(columns=["id", "data", "descricao", "categoria", "valor"])

    with pd.ExcelWriter(caminho_saida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Gastos", index=False)

        if not df.empty:
            df["mes"] = df["data"].str.slice(0, 7)

            resumo_mensal = (
                df.groupby("mes")["valor"].sum().reset_index().sort_values("mes")
            )
            resumo_mensal.to_excel(writer, sheet_name="Resumo Mensal", index=False)

            resumo_categoria = (
                df.groupby("categoria")["valor"].sum().reset_index().sort_values(
                    "valor", ascending=False
                )
            )
            resumo_categoria.to_excel(writer, sheet_name="Resumo por Categoria", index=False)

    return caminho_saida
