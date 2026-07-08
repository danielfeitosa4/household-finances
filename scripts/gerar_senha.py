"""Gera o hash de uma senha para colocar em .streamlit/secrets.toml.

Rode este script no SEU terminal (não peça para o assistente rodar):
    python scripts/gerar_senha.py

A senha digitada não fica visível na tela e não é enviada a lugar nenhum.
"""
import getpass

from streamlit_authenticator.utilities.hasher import Hasher

senha = getpass.getpass("Digite a senha desejada: ")
confirmacao = getpass.getpass("Confirme a senha: ")

if senha != confirmacao:
    raise SystemExit("As senhas não coincidem.")

print("\nHash gerado — copie o valor abaixo para 'password' em .streamlit/secrets.toml:\n")
print(Hasher.hash(senha))
