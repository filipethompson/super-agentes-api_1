import time
import json
import logging
from database import buscar_requisicao_pendente, marcar_como_processada
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
import os
import requests

# 🔹 Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 🔹 Configuração do WebDriver
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
#chrome_options.add_argument("--headless")  # Modo sem interface gráfica

service = Service()
driver = webdriver.Chrome(service=service, options=chrome_options)

# 🔹 URL do `main.py` para enviar os resultados processados
MAIN_SERVER_URL = "http://127.0.0.1:5000/processar_requisicao"

def fazer_login():
    """Realiza login no sistema Brudam"""
    try:
        logging.info("🔹 Iniciando login no sistema...")
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

def acessar_minuta(nota_fiscal):
    """Acessa a minuta pelo número da Nota Fiscal"""
    try:
        logging.info(f"🔹 Acessando minuta NF {nota_fiscal}...")

        url_minuta = f"https://glilogistica.brudam.com.br/operacional/consulta_minuta.php?chave={nota_fiscal}"
        driver.get(url_minuta)
        time.sleep(5)

        if nota_fiscal in driver.current_url:
            logging.info(f"✅ Minuta {nota_fiscal} acessada!")
            return True
        else:
            logging.error(f"❌ Erro ao acessar minuta {nota_fiscal}.")
            return False

    except Exception as e:
        logging.error(f"❌ Erro ao acessar minuta: {str(e)}")
        return False

def baixar_comprovante():
    """Baixa o comprovante da entrega e retorna a imagem em Base64"""
    try:
        logging.info("🔹 Baixando comprovante...")

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

        logging.info("✅ Comprovante baixado e convertido para Base64.")
        return base64_string

    except Exception as e:
        logging.error(f"❌ Erro ao baixar comprovante: {str(e)}")
        return None

def enviar_resposta_para_main(resposta):
    """Envia os dados processados de volta para o `main.py`"""
    try:
        response = requests.post(MAIN_SERVER_URL, json=resposta)
        if response.status_code == 200:
            logging.info("✅ Resposta enviada com sucesso ao Main!")
        else:
            logging.error(f"❌ Erro ao enviar resposta ao Main. Status: {response.status_code}")
    except Exception as e:
        logging.error(f"❌ Erro ao conectar ao Main: {str(e)}")

def processar_requisicao(nota_fiscal, data_emissao):
    """Executa todo o fluxo e retorna os dados"""
    if acessar_minuta(nota_fiscal):
        comprovante_base64 = baixar_comprovante()

        resultado = {
            "status": "sucesso",
            "nota_fiscal": nota_fiscal,
            "data_emissao": data_emissao,
            "comprovante_base64": comprovante_base64
        }
    else:
        resultado = {"status": "erro", "mensagem": "Falha ao acessar a minuta."}

    logging.info(f"✅ Resposta final: {resultado}")
    return resultado

def loop_processamento():
    """Fica em loop verificando novas requisições"""
    if not fazer_login():
        logging.error("❌ Erro no login! Encerrando o subagente...")
        return

    while True:
        requisicao = buscar_requisicao_pendente()

        if requisicao:
            req_id, nota_fiscal, data_emissao = requisicao
            logging.info(f"📥 Nova requisição encontrada: NF {nota_fiscal}, Data {data_emissao}")

            resposta = processar_requisicao(nota_fiscal, data_emissao)

            # 🔹 Marcar como processada
            marcar_como_processada(req_id)
            logging.info(f"✅ Requisição processada: {resposta}")

            # 🔹 Enviar resultado de volta para o Main
            enviar_resposta_para_main(resposta)

        time.sleep(3)  # Espera 3 segundos antes de verificar novamente


if __name__ == "__main__":
    logging.info("🚀 Subagente de consulta de comprovante iniciado. Aguardando requisições...")
    loop_processamento()
