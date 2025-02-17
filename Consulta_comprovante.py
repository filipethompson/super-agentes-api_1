import time
import json
import logging
import base64
import os
import requests
import subprocess
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 🔹 Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🔹 Função para iniciar o Ngrok automaticamente
def iniciar_ngrok():
    try:
        logging.info("🔄 Iniciando Ngrok...")
        subprocess.Popen(["ngrok", "http", "8000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)  # Espera alguns segundos para garantir que o túnel está ativo
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        ngrok_url = response.json()["tunnels"][0]["public_url"]
        logging.info(f"✅ Ngrok rodando em: {ngrok_url}")
        return ngrok_url
    except Exception as e:
        logging.error(f"❌ Erro ao iniciar Ngrok: {str(e)}")
        return None

NGROK_URL = iniciar_ngrok()

# 🔹 Configuração do WebDriver (Rodando em segundo plano para evitar travamentos)
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--headless")  # ✅ Agora rodando SEM interface gráfica

service = Service()
driver = webdriver.Chrome(service=service, options=chrome_options)

# 🔹 Inicializa o FastAPI
app = FastAPI()

# 🔹 Modelo esperado na requisição
class ConsultaComprovanteRequest(BaseModel):
    nota_fiscal: str
    data_emissao: str

# 🔹 Função de login no Brudam
def fazer_login():
    """Realiza login no sistema Brudam"""
    try:
        logging.info("🔹 Iniciando login no sistema Brudam...")
        driver.get("https://glilogistica.brudam.com.br/index.php")

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, '//*[@id="user"]'))).send_keys("FILIPE")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, '//*[@id="password"]'))).send_keys("Filipeif12345@")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="acessar"]'))).click()

        time.sleep(5)
        if "inicio.php" in driver.current_url:
            logging.info("✅ Login realizado com sucesso!")
            return True
        else:
            logging.error("❌ Falha no login.")
            return False

    except Exception as e:
        logging.error(f"❌ Erro no login: {str(e)}")
        return False

# 🔹 Função para acessar a minuta
def acessar_minuta(nota_fiscal):
    """Acessa a minuta pelo número da Nota Fiscal"""
    try:
        logging.info(f"📌 Consultando Comprovante: NF {nota_fiscal}")

        url_minuta = f"https://glilogistica.brudam.com.br/operacional/consulta_minuta.php?chave={nota_fiscal}"
        driver.get(url_minuta)
        time.sleep(5)

        if nota_fiscal in driver.current_url:
            logging.info(f"✅ Minuta {nota_fiscal} acessada com sucesso!")
            return True
        else:
            logging.error(f"❌ Erro ao acessar minuta {nota_fiscal}.")
            return False

    except Exception as e:
        logging.error(f"❌ Erro ao acessar minuta: {str(e)}")
        return False

# 🔹 Função para baixar o comprovante
def baixar_comprovante(nota_fiscal, data_emissao):
    """Baixa o comprovante da entrega e retorna a imagem em Base64"""
    try:
        logging.info(f"📥 Iniciando download do comprovante para NF {nota_fiscal}, Data {data_emissao}...")

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="anexo_128663"]/td[6]'))).click()
        time.sleep(5)

        pasta_download = os.path.expanduser("~\\Downloads")
        arquivos = os.listdir(pasta_download)
        arquivos.sort(key=lambda x: os.path.getmtime(os.path.join(pasta_download, x)), reverse=True)
        arquivo_baixado = arquivos[0]
        caminho_origem = os.path.join(pasta_download, arquivo_baixado)

        # Converte a imagem para Base64
        with open(caminho_origem, "rb") as imagem_file:
            base64_string = base64.b64encode(imagem_file.read()).decode('utf-8')

        os.remove(caminho_origem)  # Remove o arquivo após conversão

        logging.info(f"✅ Comprovante baixado e convertido para Base64: NF {nota_fiscal}, Data {data_emissao}")
        return base64_string

    except Exception as e:
        logging.error(f"❌ Erro ao baixar comprovante para NF {nota_fiscal}, Data {data_emissao}: {str(e)}")
        return None

# 🔹 Endpoint para receber requisição do Super Agentes
@app.post("/consulta_comprovante/")
def consulta_comprovante(request: ConsultaComprovanteRequest):
    """Recebe requisição do Super Agentes e processa o comprovante"""
    if not fazer_login():
        raise HTTPException(status_code=500, detail="Erro no login no Brudam")

    if acessar_minuta(request.nota_fiscal):
        comprovante_base64 = baixar_comprovante(request.nota_fiscal, request.data_emissao)

        resultado = {
            "status": "sucesso",
            "nota_fiscal": request.nota_fiscal,
            "data_emissao": request.data_emissao,
            "comprovante_base64": comprovante_base64
        }
    else:
        resultado = {"status": "erro", "mensagem": f"Falha ao acessar a minuta NF {request.nota_fiscal}."}

    logging.info(f"📌 Resultado Final: {resultado}")
    return resultado

# 🔹 Executa o servidor FastAPI
if __name__ == "__main__":
    import uvicorn
    logging.info("🚀 Subagente de consulta de comprovante iniciado. Aguardando requisições...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
