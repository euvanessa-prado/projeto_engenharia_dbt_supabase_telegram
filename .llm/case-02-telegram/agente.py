import os
import re
import logging
import urllib.request
import urllib.parse
from datetime import datetime

import anthropic
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from db import execute_query

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

CLIENT = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

SCHEMA = """
Tabelas disponíveis no banco PostgreSQL:

1. public_gold_sales.vendas_temporais
   Colunas: data_venda (DATE), ano_venda, mes_venda, dia_venda, dia_semana_nome (VARCHAR),
            hora_venda, receita_total (NUMERIC), quantidade_total, total_vendas,
            total_clientes_unicos, ticket_medio (NUMERIC)

2. public_gold.clientes_segmentacao
   Colunas: cliente_id (VARCHAR), nome_cliente, estado (VARCHAR(2)), receita_total (NUMERIC),
            total_compras, ticket_medio (NUMERIC), primeira_compra (DATE), ultima_compra (DATE),
            segmento_cliente (VIP | TOP_TIER | REGULAR), ranking_receita (INTEGER)

3. public_gold.precos_competitividade
   Colunas: produto_id (VARCHAR), nome_produto, categoria, marca, nosso_preco (NUMERIC),
            preco_medio_concorrentes, preco_minimo_concorrentes, preco_maximo_concorrentes,
            total_concorrentes, diferenca_percentual_vs_media (NUMERIC),
            diferenca_percentual_vs_minimo (NUMERIC),
            classificacao_preco (MAIS_CARO_QUE_TODOS | ACIMA_DA_MEDIA | NA_MEDIA | ABAIXO_DA_MEDIA | MAIS_BARATO_QUE_TODOS),
            receita_total (NUMERIC), quantidade_total
"""

TOOL = {
    "name": "executar_sql",
    "description": "Executa query SQL SELECT no banco PostgreSQL do e-commerce.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Query SQL SELECT para executar."
            }
        },
        "required": ["sql"]
    }
}


def _log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# ── Chat livre ────────────────────────────────────────────────────────────────

def chat(pergunta: str) -> str:
    _log(f"Chat recebido: {pergunta[:80]}")

    system = (
        "Você é um analista de dados de um e-commerce brasileiro.\n"
        "Responda perguntas usando os dados do banco PostgreSQL.\n"
        "Use a ferramenta executar_sql para consultar os dados necessários.\n"
        "Formate valores monetários em R$. Responda em português.\n"
        "Seja conciso e direto.\n\n"
        + SCHEMA
    )

    messages = [{"role": "user", "content": pergunta}]

    for _ in range(10):
        response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            tools=[TOOL],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "Não consegui gerar uma resposta."

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use" and block.name == "executar_sql":
                    try:
                        df = execute_query(block.input["sql"])
                        resultado = df.to_markdown(index=False) if not df.empty else "Sem resultados."
                    except Exception as e:
                        resultado = f"Erro ao executar SQL: {e}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": resultado,
                    })

            messages.append({"role": "user", "content": tool_results})

    return "Limite de iterações atingido. Tente reformular a pergunta."


# ── Relatório executivo ───────────────────────────────────────────────────────

def gerar_relatorio() -> str:
    _log("Iniciando geração do relatório...")

    _log("Consultando vendas...")
    dados_vendas = execute_query("""
        SELECT data_venda, dia_semana_nome,
            SUM(receita_total) AS receita,
            SUM(total_vendas) AS vendas,
            SUM(total_clientes_unicos) AS clientes,
            AVG(ticket_medio) AS ticket_medio
        FROM public_gold_sales.vendas_temporais
        GROUP BY data_venda, dia_semana_nome
        ORDER BY data_venda DESC
        LIMIT 7
    """)

    _log("Consultando clientes...")
    dados_clientes = execute_query("""
        SELECT segmento_cliente,
            COUNT(*) AS total_clientes,
            SUM(receita_total) AS receita_total,
            AVG(ticket_medio) AS ticket_medio_avg,
            AVG(total_compras) AS compras_avg
        FROM public_gold.clientes_segmentacao
        GROUP BY segmento_cliente
        ORDER BY receita_total DESC
    """)

    _log("Consultando pricing...")
    dados_pricing = execute_query("""
        SELECT classificacao_preco,
            COUNT(*) AS total_produtos,
            AVG(diferenca_percentual_vs_media) AS dif_media_pct,
            SUM(receita_total) AS receita_impactada
        FROM public_gold.precos_competitividade
        GROUP BY classificacao_preco
        ORDER BY total_produtos DESC
    """)

    _log("Consultando produtos_criticos...")
    dados_criticos = execute_query("""
        SELECT nome_produto, categoria, nosso_preco,
            preco_medio_concorrentes,
            diferenca_percentual_vs_media,
            receita_total
        FROM public_gold.precos_competitividade
        WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'
        ORDER BY diferenca_percentual_vs_media DESC
        LIMIT 10
    """)

    _log("Enviando para Claude API...")

    prompt = f"""Gere o relatório diário com base nos dados abaixo.

## Dados de Vendas (últimos 7 dias)
{dados_vendas.to_markdown(index=False)}

## Segmentação de Clientes
{dados_clientes.to_markdown(index=False)}

## Posicionamento de Preços
{dados_pricing.to_markdown(index=False)}

## Produtos Críticos (mais caros que todos os concorrentes)
{dados_criticos.to_markdown(index=False)}

Gere o relatório com 3 seções:
1. Comercial (para o Diretor Comercial)
2. Customer Success (para a Diretora de CS)
3. Pricing (para o Diretor de Pricing)

Comece com um resumo executivo de 3 linhas antes das seções."""

    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=(
            "Você é um analista de dados senior de um e-commerce.\n"
            "Sua função é gerar um relatório executivo diário para 3 diretores.\n"
            "Cada diretor tem necessidades diferentes:\n\n"
            "1. Diretor Comercial: receita, vendas, ticket médio e tendências.\n"
            "2. Diretora de Customer Success: segmentação de clientes, VIPs e riscos.\n"
            "3. Diretor de Pricing: posicionamento de preço vs concorrência e alertas.\n\n"
            "Regras do relatório:\n"
            "- Seja direto e acionável. Cada insight deve sugerir uma ação.\n"
            "- Use números reais dos dados fornecidos.\n"
            "- Formate valores monetários em reais (R$).\n"
            "- Destaque alertas críticos no início.\n"
            "- O relatório deve ter no máximo 1 página por diretor.\n"
            "- Use formato Markdown."
        ),
        messages=[{"role": "user", "content": prompt}],
    )

    relatorio = response.content[0].text
    hoje = datetime.now().strftime("%Y-%m-%d")
    arquivo = os.path.join(os.path.dirname(__file__), f"relatorio_{hoje}.md")

    with open(arquivo, "w", encoding="utf-8") as f:
        f.write(relatorio)

    _log(f"Relatório salvo em: relatorio_{hoje}.md")
    return relatorio


# ── Envio Telegram (direto via HTTP) ─────────────────────────────────────────

def enviar_telegram(texto: str, chat_id: str = None):
    token = os.getenv("TELEGRAM")
    chat_id = chat_id or os.getenv("CHAT_ID")

    if not chat_id:
        _log("CHAT_ID não configurado. Inicie o bot e envie /start primeiro.")
        return

    partes = [texto[i:i+4096] for i in range(0, len(texto), 4096)]
    for parte in partes:
        _enviar_parte(token, chat_id, parte)

    _log(f"Mensagem enviada para chat_id={chat_id}")


def _enviar_parte(token: str, chat_id: str, texto: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for parse_mode in ["Markdown", None]:
        payload = {"chat_id": chat_id, "text": texto}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(url, data=data, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return
        except Exception:
            if parse_mode is None:
                _log("Falha ao enviar mensagem para o Telegram.")


# ── Auto-registro CHAT_ID ─────────────────────────────────────────────────────

def salvar_chat_id(chat_id: int):
    chat_id_str = str(chat_id)
    if os.getenv("CHAT_ID", "") == chat_id_str:
        return

    os.environ["CHAT_ID"] = chat_id_str
    log.info(f"CHAT_ID={chat_id_str} registrado em memória")


# ── Handlers do bot ───────────────────────────────────────────────────────────

async def _enviar_longo(update: Update, texto: str):
    partes = [texto[i:i+4096] for i in range(0, len(texto), 4096)]
    for parte in partes:
        try:
            await update.message.reply_text(parte, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(parte)


async def handler_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_text(
        "Olá! Sou o assistente de dados do e-commerce 📊\n\n"
        "Comandos disponíveis:\n"
        "/relatorio — gera o relatório executivo diário\n\n"
        "Ou faça qualquer pergunta sobre vendas, clientes ou pricing!"
    )


async def handler_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_chat_action(ChatAction.TYPING)
    await update.message.reply_text("Gerando relatório... Aguarde um momento ⏳")
    try:
        texto = gerar_relatorio()
        await _enviar_longo(update, texto)
    except Exception as e:
        await update.message.reply_text(f"Erro ao gerar relatório: {e}")


async def handler_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salvar_chat_id(update.message.chat_id)
    await update.message.reply_chat_action(ChatAction.TYPING)
    try:
        resposta = chat(update.message.text)
        await _enviar_longo(update, resposta)
    except Exception as e:
        await update.message.reply_text(f"Erro ao processar pergunta: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    token = os.getenv("TELEGRAM")
    if not token:
        raise RuntimeError("Variável TELEGRAM não configurada no .env")

    log.info("Iniciando bot @SupDbtTelegrambot...")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", handler_start))
    app.add_handler(CommandHandler("relatorio", handler_relatorio))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler_mensagem))

    log.info("Bot rodando! Ctrl+C para parar.")
    app.run_polling()
