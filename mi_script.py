import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
from datetime import datetime, timedelta

# 📌 Configuración de Telegram desde Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

def enviar_mensaje(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": texto})

# 🔹 Archivo de estado
archivo_estado = "estado.json"
if os.path.exists(archivo_estado):
    with open(archivo_estado, "r") as f:
        estado = json.load(f)
else:
    estado = {"RSI_estado": "normal", "HMA_estado": "normal"}

# 🔹 Fechas: último año hasta hoy
hoy = datetime.today()
hace_un_ano = hoy - timedelta(days=365)

# 🔹 Descargar datos del Merval
merval = yf.download("^MERV", start=hace_un_ano, end=hoy)['Close']
df = pd.DataFrame(merval)
df.columns = ['Merval']

# 🔹 Función para calcular Hull Moving Average (HMA)
def HMA(series, period):
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    wma_half = series.rolling(half_length).mean()
    wma_full = series.rolling(period).mean()
    diff = 2 * wma_half - wma_full
    hma = diff.rolling(sqrt_length).mean()
    return hma

# 🔹 Calcular HMA10 y MA15
df['HMA10'] = HMA(df['Merval'], 10)
df['MA15'] = df['Merval'].rolling(window=15).mean()

# 🔹 Detectar cruce en el último período
ultimos = df.tail(2)
hma_anterior = ultimos['HMA10'].iloc[0]
hma_actual = ultimos['HMA10'].iloc[1]
ma_anterior = ultimos['MA15'].iloc[0]
ma_actual = ultimos['MA15'].iloc[1]

# 🔹 Mensaje solo si cruza y cambia de estado
if hma_anterior < ma_anterior and hma_actual > ma_actual:
    if estado.get("HMA_estado") != "alcista":
        enviar_mensaje("📈 ¡MERVAL Cruce alcista! La HMA10 cruzó hacia arriba la MA15.")
        estado["HMA_estado"] = "alcista"
elif hma_anterior > ma_anterior and hma_actual < ma_actual:
    if estado.get("HMA_estado") != "bajista":
        enviar_mensaje("📉 ¡MERVAL Cruce bajista! La HMA10 cruzó hacia abajo la MA15.")
        estado["HMA_estado"] = "bajista"
else:
    estado["HMA_estado"] = "normal"

# 🔹 Función para calcular RSI
def RSI(series, period=14):
    delta = series.diff()
    ganancias = delta.where(delta > 0, 0)
    perdidas = -delta.where(delta < 0, 0)
    media_gan = ganancias.rolling(period).mean()
    media_perd = perdidas.rolling(period).mean()
    rs = media_gan / media_perd
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 🔹 Calcular RSI 14
df['RSI'] = RSI(df['Merval'], 14)
rsi_actual = df['RSI'].iloc[-1]

# 🔹 Mensaje solo en primer cruce de sobrecompra/sobreventa
if rsi_actual > 70:
    if estado["RSI_estado"] != "sobrecompra":
        enviar_mensaje(f"⚠️ ¡MERVAL RSI {rsi_actual:.2f}! Sobrecompra → posible señal bajista")
        estado["RSI_estado"] = "sobrecompra"
elif rsi_actual < 30:
    if estado["RSI_estado"] != "sobreventa":
        enviar_mensaje(f"✅ ¡MERVAL RSI {rsi_actual:.2f}! Sobreventa → posible señal alcista")
        estado["RSI_estado"] = "sobreventa"
else:
    estado["RSI_estado"] = "normal"

# 🔹 Guardar estado actualizado
with open(archivo_estado, "w") as f:
    json.dump(estado, f)


