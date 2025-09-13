import requests
import os

# 🔑 Configuración (tomamos token y chat_id de Secrets)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Mensaje de prueba
mensaje = "Hola grupo, esto es un mensaje de prueba 🚀"

# Enviar a Telegram
telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
response = requests.post(telegram_url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje})

# Mostrar resultado
if response.status_code == 200:
    print("Mensaje enviado correctamente ✅")
else:
    print("Error al enviar mensaje ❌", response.text)

