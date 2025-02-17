from flask import Flask, request, jsonify
import logging
from database import adicionar_requisicao

app = Flask(__name__)

# 🔹 Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@app.route("/processar_requisicao/", methods=["POST"])
def processar_requisicao():
    """Recebe requisições e armazena no banco de dados."""
    try:
        data = request.get_json()

        if not data or "tipo" not in data:
            return jsonify({"status": "erro", "mensagem": "Requisição inválida. Tipo não especificado."}), 400

        if data["tipo"] == "consulta_comprovante":
            nota_fiscal = data.get("nota_fiscal")
            data_emissao = data.get("data_emissao")

            if not nota_fiscal or not data_emissao:
                return jsonify({"status": "erro", "mensagem": "Dados incompletos para consulta de comprovante."}), 400

            # 🔹 Adiciona no banco de dados
            adicionar_requisicao(nota_fiscal, data_emissao)
            logging.info(f"📥 Requisição armazenada no banco: NF {nota_fiscal}, Data {data_emissao}")

            return jsonify({"status": "sucesso", "mensagem": "Requisição armazenada com sucesso!"})

        else:
            return jsonify({"status": "erro", "mensagem": "Tipo de requisição desconhecido."}), 400

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
