import os
import sys
import subprocess
import base64
import json
import time
import re

# ---------- CHECAR E INSTALAR DEPENDÊNCIAS ----------
dependencias = ["requests"]  # adicione outras bibliotecas se precisar

for lib in dependencias:
    try:
        __import__(lib)
    except ImportError:
        print(f"Módulo '{lib}' não encontrado. Instalando automaticamente...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
        print(f"Módulo '{lib}' instalado com sucesso.")

import requests  # garante que requests esteja importado após a instalação

# ---------- CONFIGURAÇÕES ----------
REPO_NOME = "Lets-Go-Spooky"
PASTA_REPO = "images"
BRANCH = "main"
URL_PINTEREST = "https://pin.it/31jz4PBft"
LOG_ARQUIVO = "log_envio.txt"
INTERVALO = 600  # 10 minutos

# ---------- PEGAR TOKEN DO AMBIENTE ----------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise Exception("Variável de ambiente GITHUB_TOKEN não encontrada! Use export GITHUB_TOKEN='SEU_TOKEN' no Termux.")

headers_github = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

headers_http = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ---------- PEGAR USUÁRIO DO GITHUB ----------
def pegar_usuario_github():
    r = requests.get("https://api.github.com/user", headers=headers_github)
    if r.status_code == 200:
        return r.json().get("login")
    else:
        raise Exception(f"Erro ao pegar usuário: {r.status_code} {r.text}")

usuario = pegar_usuario_github()
REPO = f"{usuario}/{REPO_NOME}"
print(f"Usuário do GitHub detectado automaticamente: {usuario}")

# ---------- CHECAR OU CRIAR PASTA ----------
def criar_pasta_github(pasta):
    url = f"https://api.github.com/repos/{REPO}/contents/{pasta}"
    r = requests.get(url, headers=headers_github)
    if r.status_code == 404:
        data = {
            "message": f"Criar pasta {pasta}",
            "content": base64.b64encode(b"").decode("utf-8"),
            "branch": BRANCH
        }
        requests.put(url + "/.gitkeep", headers=headers_github, data=json.dumps(data))
        print(f"Pasta '{pasta}' criada no GitHub.")
    else:
        print(f"Pasta '{pasta}' já existe no GitHub.")

# ---------- PEGAR TODOS OS PINS ----------
def pegar_todos_pins(url):
    session = requests.Session()
    session.headers.update(headers_http)

    r = session.get(url, allow_redirects=True)
    url_long = r.url
    r = session.get(url_long)
    data = r.text

    pattern = re.compile(r'"url":"(https://i\.pinimg\.com/originals/[^"]+)"')
    urls = list(dict.fromkeys(pattern.findall(data)))
    return urls

# ---------- ATUALIZAR LOG NO GITHUB ----------
def atualizar_log_github(linhas):
    try:
        url_log = f"https://api.github.com/repos/{REPO}/contents/{LOG_ARQUIVO}"
        r = requests.get(url_log, headers=headers_github)
        sha = r.json().get("sha") if r.status_code == 200 else None

        content = "\n".join(linhas).encode("utf-8")
        data = {
            "message": "Atualizar log de envio",
            "content": base64.b64encode(content).decode("utf-8"),
            "branch": BRANCH
        }
        if sha:
            data["sha"] = sha

        requests.put(url_log, headers=headers_github, data=json.dumps(data))
        print("Log atualizado no GitHub.")
    except Exception as e:
        print(f"Erro ao atualizar log: {e}")

# ---------- ENVIAR IMAGEM AO GITHUB ----------
def enviar_imagem(url, idx, log):
    try:
        img_data = requests.get(url, headers=headers_http).content
        nome_arquivo = f"{PASTA_REPO}/spooky_{str(idx).zfill(3)}.jpg"

        check = requests.get(f"https://api.github.com/repos/{REPO}/contents/{nome_arquivo}", headers=headers_github)
        sha = check.json().get("sha") if check.status_code == 200 else None

        data = {
            "message": f"Adicionar {nome_arquivo}",
            "content": base64.b64encode(img_data).decode("utf-8"),
            "branch": BRANCH
        }
        if sha:
            data["sha"] = sha

        r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{nome_arquivo}", headers=headers_github, data=json.dumps(data))
        if r.status_code in [200, 201]:
            print(f"Enviado: {nome_arquivo}")
            log.append(f"SUCESSO: {nome_arquivo}")
        else:
            print(f"Falha ao enviar: {nome_arquivo}")
            log.append(f"FALHA: {nome_arquivo}")
        time.sleep(1)
    except Exception as e:
        print(f"Erro: {nome_arquivo} -> {e}")
        log.append(f"ERRO: {nome_arquivo} -> {e}")

# ---------- EXECUÇÃO CONTÍNUA ----------
criar_pasta_github(PASTA_REPO)
imagens_anteriores = []

while True:
    try:
        print("Verificando novos pins...")
        imagens_atual = pegar_todos_pins(URL_PINTEREST)
        novas_imagens = [img for img in imagens_atual if img not in imagens_anteriores]

        if novas_imagens:
            print(f"{len(novas_imagens)} novas imagens encontradas.")
            log = []
            for idx, url in enumerate(novas_imagens, start=1):
                enviar_imagem(url, len(imagens_anteriores)+idx, log)
            atualizar_log_github(log)
            imagens_anteriores += novas_imagens
        else:
            print("Nenhuma nova imagem encontrada.")

        print(f"Aguardando {INTERVALO} segundos para próxima verificação...")
        time.sleep(INTERVALO)

    except Exception as e:
        print(f"Erro geral: {e}")
        time.sleep(INTERVALO)
