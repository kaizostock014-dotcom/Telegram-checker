import os
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 1. Comando de bienvenida /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = (
        "╔═════════════════════════════════╗\n"
        "  ⚡ SISTEMA OPERATIVO ACTIVO ⚡\n"
        "╚═════════════════════════════════╝\n\n"
        "» Estado: ONLINE 🟢\n"
        "» Servidor: Render Cloud\n\n"
        "💡 Usa el comando /ping para verificar la velocidad."
    )
    await update.message.reply_text(mensaje)

# 2. Comando /ping para medir la velocidad de respuesta
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inicio = time.time()
    mensaje_espera = await update.message.reply_text("⚡ midiendo...")
    
    latencia = round((time.time() - inicio) * 1000, 2)
    
    resultado = (
        "📊 RESULTADO DEL TEST\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 Respuesta: PONG 🏓\n"
        f"🔹 Tiempo: {latencia} ms\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    await mensaje_espera.edit_text(resultado)

# 3. Función de inicio del bot
def main():
    # Obtiene el token guardado en la pestaña 'Environment' de Render
    token_seguro = os.environ.get("BOT_TOKEN")
    
    if not token_seguro:
        print("❌ Error: Falta configurar la variable 'BOT_TOKEN' en Render.")
        return

    # Construcción de la aplicación del bot
    app = ApplicationBuilder().token(token_seguro).build()

    # Enlace de comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))

    # Arranca el bot en modo escucha
    print("🤖 Bot encendido con éxito...")
    app.run_polling()

if __name__ == '__main__':
    main()
