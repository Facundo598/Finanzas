import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
import matplotlib.pyplot as plt
from datetime import datetime, timezone, timedelta

# 📌 Configuración de Telegram desde Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

def enviar_mensaje(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": texto})

def enviar_imagen(ruta, caption="📊 Gráfico"):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(ruta, "rb") as img:
        files = {"photo": img}
        data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        requests.post(url, files=files, data=data)

# 🔹 Archivo de estado
archivo_estado = "estado.json"
if os.path.exists(archivo_estado):
    with open(archivo_estado, "r") as f:
        estado = json.load(f)
else:
    estado = {"HMA_estado": "normal"}

# 🔹 Fechas: último año hasta hoy (hora Argentina UTC-3)
hoy_arg = datetime.now(timezone.utc) - timedelta(hours=3)
hoy = hoy_arg.replace(hour=0, minute=0, second=0, microsecond=0)
hace_un_ano = hoy - timedelta(days=365)

# 🔹 Descargar datos del Merval
merval = yf.download("^MERV", start=hace_un_ano, end=hoy)['Close']
df = pd.DataFrame(merval)
df.columns = ['Merval']

# 🔹 Función Hull Moving Average
def HMA(series, period):
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    wma_half = series.rolling(half_length).mean()
    wma_full = series.rolling(period).mean()
    diff = 2 * wma_half - wma_full
    hma = diff.rolling(sqrt_length).mean()
    return hma

# 🔹 Calcular medias
df['HMA10'] = HMA(df['Merval'], 10)
df['MA15'] = df['Merval'].rolling(window=15).mean()

# 🔹 Detectar cruce de medias móviles
ultimos = df.tail(2)
hma_anterior = ultimos['HMA10'].iloc[0]
hma_actual = ultimos['HMA10'].iloc[1]
ma_anterior = ultimos['MA15'].iloc[0]
ma_actual = ultimos['MA15'].iloc[1]

# 🔹 Mensaje solo si hay cruce
if hma_anterior < ma_anterior and hma_actual > ma_actual:
    if estado.get("HMA_estado") != "alcista":
        enviar_mensaje("📈 ¡MERVAL Cruce alcista! La HMA10 cruzó hacia arriba la MA15.")
        estado["HMA_estado"] = "alcista"

        # Gráfico de medias móviles
        plt.figure(figsize=(10,5))
        plt.plot(df.index, df['Merval'], label="Merval", color="black")
        plt.plot(df.index, df['HMA10'], label="HMA10", color="blue")
        plt.plot(df.index, df['MA15'], label="MA15", color="orange")
        plt.title("MERVAL con HMA10 y MA15")
        plt.legend()
        plt.grid(True)
        ruta_mm = "merval_medias.png"
        plt.savefig(ruta_mm)
        plt.close()
        enviar_imagen(ruta_mm, caption="📊 MERVAL con medias móviles (Cruce alcista)")

elif hma_anterior > ma_anterior and hma_actual < ma_actual:
    if estado.get("HMA_estado") != "bajista":
        enviar_mensaje("📉 ¡MERVAL Cruce bajista! La HMA10 cruzó hacia abajo la MA15.")
        estado["HMA_estado"] = "bajista"

        # Gráfico de medias móviles
        plt.figure(figsize=(10,5))
        plt.plot(df.index, df['Merval'], label="Merval", color="black")
        plt.plot(df.index, df['HMA10'], label="HMA10", color="blue")
        plt.plot(df.index, df['MA15'], label="MA15", color="orange")
        plt.title("MERVAL con HMA10 y MA15")
        plt.legend()
        plt.grid(True)
        ruta_mm = "merval_medias.png"
        plt.savefig(ruta_mm)
        plt.close()
        enviar_imagen(ruta_mm, caption="📊 MERVAL con medias móviles (Cruce bajista)")

else:
    estado["HMA_estado"] = "normal"

# 🔹 Guardar estado actualizado
with open(archivo_estado, "w") as f:
    json.dump(estado, f)

