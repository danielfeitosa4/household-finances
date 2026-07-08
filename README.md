# Controle de Finanças

App simples em Streamlit para lançar gastos diários/mensais, ver resumos e exportar uma planilha Excel.

## Rodar localmente

1. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
2. Configure o login (uma vez só):
   ```
   copy .streamlit\secrets.toml.example .streamlit\secrets.toml
   python scripts\gerar_senha.py
   ```
   Copie o hash impresso para o campo `password` em `.streamlit/secrets.toml`.
3. Rode o app:
   ```
   streamlit run app.py
   ```

## Deploy no Streamlit Community Cloud

1. Suba este projeto para um repositório no GitHub (o arquivo `.streamlit/secrets.toml` real **não** vai junto — está no `.gitignore`).
2. Em https://share.streamlit.io, clique em "New app" e aponte para o repositório, branch `main` e arquivo `app.py`.
3. Em "Advanced settings" → "Secrets", cole o mesmo conteúdo do seu `.streamlit/secrets.toml` local.
4. Deploy. O app pedirá usuário/senha antes de mostrar qualquer dado.

**Atenção:** o Streamlit Community Cloud reinicia o container periodicamente e não garante disco persistente — o arquivo `finances.db` pode ser perdido em redeploys. Para uso contínuo em produção, migrar para um banco externo (ex: Postgres no Supabase/Neon) é o próximo passo recomendado.
