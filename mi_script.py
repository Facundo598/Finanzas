import requests
import os

# 🔑 Configuración (poné tu token y chat_id en Secrets de GitHub)
TELEGRAM_TOKEN = os.getenv("8120402417:AAGzPpQ-ylO-dqS_hB9gHxYkrB0x_pHpwOI")
TELEGRAM_CHAT_ID = os.getenv("1914342776")

# API de cotización del dólar
url = "https://dolarapi.com/v1/dolares/oficial"

try:
    response = requests.get(url, timeout=10)
    data = response.json()

    precio = data.get("venta", "N/A")
    fecha = data.get("fecha", "N/A")

    mensaje = f"💵 Dólar oficial\nPrecio venta: ${precio}\nFecha: {fecha}"

except Exception as e:
    mensaje = f"Error al consultar la API: {e}"

# Enviar a Telegram
telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
requests.post(telegram_url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje})
