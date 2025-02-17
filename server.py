from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import time
import logging
import socket
import os
from pyngrok import ngrok

# 🔹 Defina seu token de autenticação do Ngrok aqui (somente localmente)
NGROK_AUTH_TOKEN = "2kAkypsMqkIscK9gi2H4jagZ4wD_4EpmWVEW3hKh4uf5epPye"

app = FastAPI()

# 🔹 Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# 🔹 Função para verificar porta disponível
def encontrar_porta_livre(porta_padrao=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if s.connect_ex(("0.0.0.0", porta_padrao)) != 0:
            return porta_padrao
        else:
            return 8001  # Usa outra porta caso a 8000 esteja ocupada


PORTA = encontrar_porta_livre()


# 🔹 Iniciar Ngrok somente em ambiente local
def iniciar_ngrok():
    if "RENDER" in os.environ:
        logging.info("🔹 Executando no Render, ignorando Ngrok.")
        return None

    try:
        logging.info("🔄 Iniciando Ngrok...")
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)
        public_url = ngrok.connect(PORTA).public_url
        logging.info(f"✅ Ngrok está rodando em: {public_url}")
        return public_url
    except Exception as e:
        logging.error(f"❌ Erro ao iniciar Ngrok: {str(e)}")
        return None


# 🔹 Captura a URL do Ngrok somente se não estiver no Render
NGROK_URL = iniciar_ngrok()
if not NGROK_URL:
    NGROK_URL = f"http://localhost:{PORTA}"  # Usa localhost como fallback


class ConsultaComprovanteRequest(BaseModel):
    nota_fiscal: str
    data_emissao: str


@app.get("/")
def home():
    return {"message": "API do Super Agentes está rodando no Render e se comunicando com o Subagente"}


@app.post("/consulta_comprovante/")
def consulta_comprovante(request: ConsultaComprovanteRequest):
    try:
        response = requests.post(
            f"{NGROK_URL}/consulta_comprovante/",
            json={"nota_fiscal": request.nota_fiscal, "data_emissao": request.data_emissao},
            timeout=10  # Timeout de 10 segundos para evitar travamento
        )
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar ao Subagente: {str(e)}")


# 🔹 Garante que o servidor rode na porta correta para Render
if __name__ == "__main__":
    import uvicorn

    logging.info(f"🚀 Iniciando servidor na porta {PORTA}")
    uvicorn.run(app, host="0.0.0.0", port=PORTA)
