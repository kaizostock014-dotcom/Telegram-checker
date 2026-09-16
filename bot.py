import os
import re
import time
import threading
import requests

from flask import Flask, jsonify


# ============================================================
# CONFIGURACIÓN
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)


# ============================================================
# SERVIDOR WEB PARA RENDER
# ============================================================

@app.route("/")
def inicio():
    return jsonify({
        "bot": "Bill Cypher Chk",
        "estado": "Online",
        "modo": "Sandbox",
        "version": "2.0"
    })


@app.route("/health")
def salud():
    return jsonify({
        "estado": "OK",
        "telegram": "activo"
    })


# ============================================================
# TELEGRAM
# ============================================================

def telegram(metodo, datos=None):
    try:
        respuesta = requests.post(
            f"{API}/{metodo}",
            json=datos or {},
            timeout=30
        )

        return respuesta.json()

    except Exception as e:
        print(f"[TELEGRAM] Error: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


def enviar_mensaje(chat_id, texto, teclado=None):
    datos = {
        "chat_id": chat_id,
        "text": texto,
        "parse_mode": "HTML"
    }

    if teclado:
        datos["reply_markup"] = teclado

    return telegram("sendMessage", datos)


def editar_mensaje(chat_id, mensaje_id, texto, teclado=None):
    datos = {
        "chat_id": chat_id,
        "message_id": mensaje_id,
        "text": texto,
        "parse_mode": "HTML"
    }

    if teclado:
        datos["reply_markup"] = teclado

    return telegram("editMessageText", datos)


def responder_callback(callback_id):
    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# ============================================================
# TECLADOS
# ============================================================

TECLADO_INICIO = {
    "inline_keyboard": [
        [
            {
                "text": "⚡ Analizar BIN",
                "callback_data": "check"
            },
            {
                "text": "⚙️ Comandos",
                "callback_data": "comandos"
            }
        ],
        [
            {
                "text": "👤 Cuenta",
                "callback_data": "cuenta"
            },
            {
                "text": "💎 Premium",
                "callback_data": "premium"
            }
        ],
        [
            {
                "text": "📚 Referencias",
                "callback_data": "referencias"
            },
            {
                "text": "📢 Actualizaciones",
                "callback_data": "actualizaciones"
            }
        ]
    ]
}


TECLADO_COMANDOS = {
    "inline_keyboard": [
        [
            {
                "text": "⚡ Analizar",
                "callback_data": "check"
            }
        ],
        [
            {
                "text": "👤 Cuenta",
                "callback_data": "cuenta"
            },
            {
                "text": "💎 Premium",
                "callback_data": "premium"
            }
        ],
        [
            {
                "text": "🏠 Inicio",
                "callback_data": "inicio"
            }
        ]
    ]
}


# ============================================================
# INTERFAZ
# ============================================================

def pantalla_inicio(nombre):
    return (
        "╔══════════════════════════════╗\n"
        "        <b>⚡ BILL CYPHER CHK ⚡</b>\n"
        "╚══════════════════════════════╝\n\n"
        f"👋 Hola, <b>{nombre}</b>\n\n"
        "🧪 <b>Motor:</b> Sandbox\n"
        "🟢 <b>Estado:</b> Online\n"
        "⚙️ <b>Versión:</b> 2.0\n\n"
        "Este bot analiza la estructura de un BIN "
        "o número de tarjeta sin enviarlo a servicios externos.\n\n"
        "Usa <code>/cmds</code> para ver los comandos."
    )


def pantalla_comandos():
    return (
        "╔══════════════════════════════╗\n"
        "       <b>⚙️ PANEL DE COMANDOS</b>\n"
        "╚══════════════════════════════╝\n\n"
        "⚡ <b>/check</b> — Analizar BIN o tarjeta\n"
        "🏠 <b>/start</b> — Menú principal\n"
        "⚙️ <b>/cmds</b> — Panel de comandos\n"
        "👤 <b>/cuenta</b> — Información de cuenta\n"
        "💎 <b>/premium</b> — Información Premium\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🧪 <b>Modo Sandbox</b>\n"
        "🔒 Los datos no se envían a procesadores de pago."
    )


# ============================================================
# DETECCIÓN DE MARCA
# ============================================================

def detectar_marca(numero):
    """
    Detecta la red/marca utilizando el prefijo.
    No consulta bancos ni procesadores.
    """

    numero = re.sub(r"\D", "", numero)

    # Visa
    if numero.startswith("4"):
        return "Visa"

    # Mastercard
    if len(numero) >= 2:
        prefijo_2 = int(numero[:2])

        if 51 <= prefijo_2 <= 55:
            return "Mastercard"

    if len(numero) >= 4:
        prefijo_4 = int(numero[:4])

        if 2221 <= prefijo_4 <= 2720:
            return "Mastercard"

    # American Express
    if numero.startswith("34") or numero.startswith("37"):
        return "American Express"

    # Discover
    if numero.startswith("6011"):
        return "Discover"

    if numero.startswith("65"):
        return "Discover"

    if len(numero) >= 3:
        prefijo_3 = int(numero[:3])

        if 644 <= prefijo_3 <= 649:
            return "Discover"

    # JCB
    if len(numero) >= 4:
        prefijo_4 = int(numero[:4])

        if 3528 <= prefijo_4 <= 3589:
            return "JCB"

    # UnionPay
    if numero.startswith("62"):
        return "UnionPay"

    return "Desconocida"


# ============================================================
# ALGORITMO DE LUHN
# ============================================================

def validar_luhn(numero):
    """
    Comprueba únicamente la estructura matemática
    mediante el algoritmo de Luhn.
    """

    numero = re.sub(r"\D", "", numero)

    if not numero:
        return False

    suma = 0
    duplicar = False

    for digito in reversed(numero):

        valor = int(digito)

        if duplicar:
            valor *= 2

            if valor > 9:
                valor -= 9

        suma += valor
        duplicar = not duplicar

    return suma % 10 == 0


# ============================================================
# OCULTAR TARJETA
# ============================================================

def ocultar_numero(numero):
    """
    Nunca mostramos el número completo.
    """

    numero = re.sub(r"\D", "", numero)

    if len(numero) <= 4:
        return "•" * len(numero)

    ultimos = numero[-4:]

    return "•" * (len(numero) - 4) + ultimos


# ============================================================
# ANALIZADOR
# ============================================================

def analizar_dato(entrada):

    limpio = re.sub(r"\D", "", entrada)

    if not limpio:
        return {
            "tipo": "Inválido",
            "marca": "Desconocida",
            "luhn": False,
            "bin": "N/A",
            "longitud": 0
        }

    # --------------------------------------------------------
    # BIN
    # --------------------------------------------------------

    if len(limpio) <= 8:

        marca = detectar_marca(limpio)

        return {
            "tipo": "BIN",
            "marca": marca,
            "luhn": None,
            "bin": limpio[:6],
            "longitud": len(limpio)
        }

    # --------------------------------------------------------
    # TARJETA
    # --------------------------------------------------------

    marca = detectar_marca(limpio)
    luhn = validar_luhn(limpio)

    return {
        "tipo": "Tarjeta",
        "marca": marca,
        "luhn": luhn,
        "bin": limpio[:6],
        "longitud": len(limpio),
        "oculta": ocultar_numero(limpio)
    }


# ============================================================
# FORMATO DEL RESULTADO
# ============================================================

def resultado_analisis(resultado):

    if resultado["tipo"] == "BIN":

        return (
            "╔══════════════════════════════╗\n"
            "        <b>⚡ ANÁLISIS BIN</b>\n"
            "╚══════════════════════════════╝\n\n"
            f"🔢 <b>BIN:</b> <code>{resultado['bin']}</code>\n"
            f"💳 <b>Marca:</b> {resultado['marca']}\n"
            f"📏 <b>Dígitos recibidos:</b> {resultado['longitud']}\n\n"
            "🧪 <b>Modo:</b> Sandbox\n"
            "🔒 <b>Sin consulta financiera</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ El BIN permite identificar la red "
            "por su prefijo, pero no comprueba fondos "
            "ni validez bancaria."
        )

    if resultado["tipo"] == "Tarjeta":

        if resultado["luhn"]:
            estado_luhn = "✅ Válida matemáticamente"
        else:
            estado_luhn = "❌ No válida matemáticamente"

        return (
            "╔══════════════════════════════╗\n"
            "      <b>⚡ ANÁLISIS DE TARJETA</b>\n"
            "╚══════════════════════════════╝\n\n"
            f"💳 <b>Número:</b> <code>{resultado['oculta']}</code>\n"
            f"🔢 <b>BIN:</b> <code>{resultado['bin']}</code>\n"
            f"🏦 <b>Marca:</b> {resultado['marca']}\n"
            f"📏 <b>Longitud:</b> {resultado['longitud']}\n\n"
            f"🔐 <b>Luhn:</b> {estado_luhn}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🧪 <b>Modo:</b> Sandbox\n"
            "🔒 No se realizó ninguna autorización "
            "ni consulta de fondos."
        )

    return (
        "❌ <b>Dato inválido</b>\n\n"
        "Introduce un BIN o un número compuesto "
        "únicamente por dígitos."
    )


# ============================================================
# ANIMACIÓN DEL CHECK
# ============================================================

def animacion_check(chat_id, entrada):

    mensaje = enviar_mensaje(
        chat_id,
        "⚡ <b>Bill Cypher Chk</b>\n\n"
        "🔄 Preparando análisis..."
    )

    if not mensaje.get("ok"):
        return

    mensaje_id = mensaje["result"]["message_id"]

    pasos = [
        "🔎 Leyendo entrada...",
        "🔢 Extrayendo BIN...",
        "💳 Detectando marca...",
        "🧮 Ejecutando algoritmo de Luhn...",
        "🔒 Preparando resultado seguro...",
        "✅ Análisis terminado."
    ]

    for paso in pasos:

        editar_mensaje(
            chat_id,
            mensaje_id,
            (
                "╔══════════════════════════════╗\n"
                "       <b>⚡ BILL CYPHER CHK</b>\n"
                "╚══════════════════════════════╝\n\n"
                f"{paso}\n\n"
                "🧪 <b>Motor:</b> Sandbox"
            )
        )

        time.sleep(0.45)

    resultado = analizar_dato(entrada)

    editar_mensaje(
        chat_id,
        mensaje_id,
        resultado_analisis(resultado),
        TECLADO_COMANDOS
    )


# ============================================================
# PROCESAMIENTO DE MENSAJES
# ============================================================

def procesar_mensaje(mensaje):

    chat = mensaje.get("chat", {})
    chat_id = chat.get("id")

    texto = mensaje.get("text", "")

    if not chat_id or not texto:
        return

    nombre = mensaje.get("from", {}).get("first_name", "Usuario")

    texto = texto.strip()

    print(
        f"[MENSAJE] Usuario={chat_id} "
        f"Texto={texto[:50]}"
    )

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if texto.startswith("/start"):

        enviar_mensaje(
            chat_id,
            pantalla_inicio(nombre),
            TECLADO_INICIO
        )

        return

    # --------------------------------------------------------
    # COMANDOS
    # --------------------------------------------------------

    if texto.startswith("/cmds"):

        enviar_mensaje(
            chat_id,
            pantalla_comandos(),
            TECLADO_COMANDOS
        )

        return

    # --------------------------------------------------------
    # CUENTA
    # --------------------------------------------------------

    if texto.startswith("/cuenta"):

        enviar_mensaje(
            chat_id,
            (
                "╔══════════════════════════════╗\n"
                "          <b>👤 CUENTA</b>\n"
                "╚══════════════════════════════╝\n\n"
                f"👤 <b>Usuario:</b> {nombre}\n"
                f"🆔 <b>ID:</b> <code>{chat_id}</code>\n"
                "💎 <b>Plan:</b> Free\n"
                "🧪 <b>Motor:</b> Sandbox"
            ),
            TECLADO_COMANDOS
        )

        return

    # --------------------------------------------------------
    # PREMIUM
    # --------------------------------------------------------

    if texto.startswith("/premium"):

        enviar_mensaje(
            chat_id,
            (
                "╔══════════════════════════════╗\n"
                "          <b>💎 PREMIUM</b>\n"
                "╚══════════════════════════════╝\n\n"
                "🚀 Funciones Premium próximamente.\n\n"
                "🧪 El análisis actual funciona en "
                "modo Sandbox."
            ),
            TECLADO_COMANDOS
        )

        return

    # --------------------------------------------------------
    # CHECK SIN ARGUMENTO
    # --------------------------------------------------------

    if texto == "/check":

        enviar_mensaje(
            chat_id,
            (
                "⚡ <b>Analizador Bill Cypher</b>\n\n"
                "Escribe un BIN o número para analizarlo.\n\n"
                "Ejemplo de BIN:\n"
                "<code>/check 424242</code>\n\n"
                "Ejemplo de tarjeta de prueba:\n"
                "<code>/check 4242424242424242</code>\n\n"
                "🔒 El análisis es local y no se envían "
                "los datos a ningún procesador."
            )
        )

        return

    # --------------------------------------------------------
    # CHECK CON ARGUMENTO
    # --------------------------------------------------------

    if texto.startswith("/check "):

        entrada = texto[7:].strip()

        if not entrada:

            enviar_mensaje(
                chat_id,
                "❌ Debes proporcionar un BIN o número."
            )

            return

        # Evitamos que se procese texto arbitrario
        # y solo permitimos dígitos.
        if not re.fullmatch(r"[0-9 ]+", entrada):

            enviar_mensaje(
                chat_id,
                (
                    "❌ <b>Formato inválido.</b>\n\n"
                    "Utiliza únicamente números."
                )
            )

            return

        # No permitimos entradas absurdamente grandes.
        limpio = re.sub(r"\s+", "", entrada)

        if len(limpio) > 19:

            enviar_mensaje(
                chat_id,
                "❌ La entrada supera la longitud permitida."
            )

            return

        threading.Thread(
            target=animacion_check,
            args=(chat_id, limpio),
            daemon=True
        ).start()

        return

    # --------------------------------------------------------
    # TEXTO DESCONOCIDO
    # --------------------------------------------------------

    enviar_mensaje(
        chat_id,
        (
            "🤖 No reconocí ese comando.\n\n"
            "Usa <code>/cmds</code> para ver "
            "los comandos disponibles."
        ),
        TECLADO_COMANDOS
    )


# ============================================================
# CALLBACKS DE BOTONES
# ============================================================

def procesar_callback(callback):

    callback_id = callback.get("id")

    responder_callback(callback_id)

    datos = callback.get("data", "")
    mensaje = callback.get("message", {})

    chat_id = mensaje.get("chat", {}).get("id")
    mensaje_id = mensaje.get("message_id")

    if not chat_id or not mensaje_id:
        return

    # --------------------------------------------------------
    # INICIO
    # --------------------------------------------------------

    if datos == "inicio":

        nombre = callback.get("from", {}).get(
            "first_name",
            "Usuario"
        )

        editar_mensaje(
            chat_id,
            mensaje_id,
            pantalla_inicio(nombre),
            TECLADO_INICIO
        )

        return

    # --------------------------------------------------------
    # COMANDOS
    # --------------------------------------------------------

    if datos == "comandos":

        editar_mensaje(
            chat_id,
            mensaje_id,
            pantalla_comandos(),
            TECLADO_COMANDOS
        )

        return

    # --------------------------------------------------------
    # CHECK
    # --------------------------------------------------------

    if datos == "check":

        enviar_mensaje(
            chat_id,
            (
                "⚡ <b>ANALIZADOR</b>\n\n"
                "Utiliza:\n"
                "<code>/check 424242</code>\n\n"
                "o una tarjeta de prueba:\n"
                "<code>/check 4242424242424242</code>"
            )
        )

        return

    # --------------------------------------------------------
    # CUENTA
    # --------------------------------------------------------

    if datos == "cuenta":

        usuario = callback.get("from", {})

        enviar_mensaje(
            chat_id,
            (
                "╔══════════════════════════════╗\n"
                "          <b>👤 CUENTA</b>\n"
                "╚══════════════════════════════╝\n\n"
                f"👤 <b>Nombre:</b> "
                f"{usuario.get('first_name', 'Usuario')}\n"
                f"🆔 <b>ID:</b> "
                f"<code>{usuario.get('id', 'N/A')}</code>\n"
                "💎 <b>Plan:</b> Free\n"
                "🟢 <b>Estado:</b> Activo"
            ),
            TECLADO_COMANDOS
        )

        return

    # --------------------------------------------------------
    # PREMIUM
    # --------------------------------------------------------

    if datos == "premium":

        enviar_mensaje(
            chat_id,
            (
                "💎 <b>PREMIUM</b>\n\n"
                "Funciones Premium próximamente.\n\n"
                "Actualmente el motor funciona "
                "completamente en Sandbox."
            ),
            TECLADO_COMANDOS
        )

        return

    # --------------------------------------------------------
    # REFERENCIAS
    # --------------------------------------------------------

    if datos == "referencias":

        enviar_mensaje(
            chat_id,
            (
                "📚 <b>REFERENCIAS</b>\n\n"
                "• Python\n"
                "• Telegram Bot API\n"
                "• HTTP/JSON\n"
                "• Expresiones regulares\n"
                "• Algoritmo de Luhn\n\n"
                "🧪 El motor de análisis no realiza "
                "consultas financieras."
            ),
            TECLADO_COMANDOS
        )

        return

    # --------------------------------------------------------
    # ACTUALIZACIONES
    # --------------------------------------------------------

    if datos == "actualizaciones":

        enviar_mensaje(
            chat_id,
            (
                "📢 <b>ACTUALIZACIONES</b>\n\n"
                "⚡ Bill Cypher Chk v2.0\n"
                "🧪 Motor Sandbox\n"
                "💳 Detector de marca\n"
                "🧮 Validador Luhn\n"
                "🎨 Interfaz renovada"
            ),
            TECLADO_COMANDOS
        )

        return


# ============================================================
# POLLING
# ============================================================

def borrar_webhook():

    print("[TG] Eliminando webhook...")

    resultado = telegram(
        "deleteWebhook",
        {
            "drop_pending_updates": False
        }
    )

    print(
        "[TG] deleteWebhook:",
        resultado
    )


def comprobar_bot():

    resultado = telegram("getMe")

    if resultado.get("ok"):

        usuario = resultado["result"]

        print(
            f"[TG] Conectado como "
            f"@{usuario.get('username', 'sin_username')}"
        )

        return True

    print(
        "[TG] ERROR getMe:",
        resultado
    )

    return False


def polling():

    print("[TG] Iniciando polling...")

    offset = None

    while True:

        try:

            datos = {
                "timeout": 30,
                "limit": 100
            }

            if offset is not None:
                datos["offset"] = offset

            respuesta = requests.post(
                f"{API}/getUpdates",
                json=datos,
                timeout=40
            )

            resultado = respuesta.json()

            if not resultado.get("ok"):

                print(
                    "[TG] Error getUpdates:",
                    resultado
                )

                time.sleep(5)
                continue

            actualizaciones = resultado.get(
                "result",
                []
            )

            for actualizacion in actualizaciones:

                offset = actualizacion["update_id"] + 1

                try:

                    if "message" in actualizacion:

                        procesar_mensaje(
                            actualizacion["message"]
                        )

                    elif "callback_query" in actualizacion:

                        procesar_callback(
                            actualizacion["callback_query"]
                        )

                except Exception as e:

                    print(
                        "[UPDATE] Error:",
                        repr(e)
                    )

        except Exception as e:

            print(
                "[POLLING] Error:",
                repr(e)
            )

            time.sleep(5)


# ============================================================
# ARRANQUE
# ============================================================

def iniciar():

    print("=" * 50)
    print("⚡ BILL CYPHER CHK")
    print("🧪 Motor Sandbox")
    print("=" * 50)

    if not BOT_TOKEN:

        print(
            "[BOOT] ERROR: BOT_TOKEN no está configurado."
        )

        return

    print("[BOOT] BOT_TOKEN: OK")

    borrar_webhook()

    if not comprobar_bot():

        print(
            "[BOOT] No se pudo autenticar con Telegram."
        )

        return

    hilo = threading.Thread(
        target=polling,
        daemon=True
    )

    hilo.start()

    print("[BOOT] Polling iniciado.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    iniciar()

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )
