# -*- coding: utf-8 -*-
# --- Merval unificado: diario o intradiario según hora Argentina ---
import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import matplotlib
matplotlib.use('Agg')  # Evita gráficos interactivos
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# 📌 Configuración de Telegram desde Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

def enviar_imagen(ruta_imagen, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(ruta_imagen, "rb") as foto:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, files={"photo": foto})

# 🔹 Hora actual en Argentina
argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
ahora = datetime.now(argentina_tz)
#hora_actual = ahora.hour + ahora.minute/60

# 🔹 Definir período histórico
hace_180_dias = ahora - timedelta(days=180)

# 🔹 MERVAL diario
df = yf.download("^MERV", start=hace_180_dias, end=ahora, auto_adjust=True)[['Close']]
df = df.rename(columns={'Close': 'Merval'})

# 🔹 DÓLAR diario
df_usd = yf.download("ARS=X", start=hace_180_dias, end=ahora, auto_adjust=True)[['Close']]
df_usd = df_usd.rename(columns={'Close': 'USD'})

# 🔹 Unir
df = df.join(df_usd, how="inner")

# 🔹 MERVAL intradiario
df_intradia = yf.download("^MERV", period="1d", interval="1m", auto_adjust=True)[['Close']]
df_intradia = df_intradia.rename(columns={'Close': 'Merval'})

if not df_intradia.empty:
    ultimo_valor = float(df_intradia['Merval'].iloc[-1])
    # Normalizar fecha y quitar timezone
    fecha_actual = df_intradia.index[-1].tz_localize(None).normalize()
    df.loc[fecha_actual, 'Merval'] = ultimo_valor

# ================= INDICADORES =================

def HMA(series, period):
    half = int(period / 2)
    sqrt = int(np.sqrt(period))
    wma_half = series.rolling(half).mean()
    wma_full = series.rolling(period).mean()
    return (2 * wma_half - wma_full).rolling(sqrt).mean()

df['HMA10'] = HMA(df['Merval'], 10)
df['MA15'] = df['Merval'].rolling(15).mean()

# 🔹 MACD
ema12 = df['Merval'].ewm(span=12, adjust=False).mean()
ema26 = df['Merval'].ewm(span=26, adjust=False).mean()
df['MACD'] = ema12 - ema26
df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
df['Histograma'] = df['MACD'] - df['Signal']

hist = df['Histograma']
delta = hist.diff()
cond = [
    (hist >= 0) & (delta > 0),
    (hist >= 0) & (delta <= 0),
    (hist < 0) & (delta < 0),
    (hist < 0) & (delta >= 0)
]
face = np.select(cond, ['green','none','red','none'], default='gray')
edge = np.select(cond, ['green','green','red','red'], default='black')

# 🔹 RSI
def RSI(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

df['RSI_Merval'] = RSI(df['Merval'])
df['RSI_USD'] = RSI(df['USD'])

# 🔹 Eventos RSI (solo Merval)
sobrecompra_fechas = df[df['RSI_Merval'] > 70].index
sobreventa_fechas = df[df['RSI_Merval'] < 30].index

# ================= GRAFICOS =================

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 11), sharex=True)

# Precio
ax1.plot(df['Merval'], label='Merval', color='blue')
ax1.plot(df['HMA10'], label='HMA10', color='orange')
ax1.plot(df['MA15'], label='MA15', color='red')
ax1.set_title('Merval – HMA, MACD y RSI')
ax1.legend()
ax1.grid(True)

# MACD
ax2.bar(df.index, hist, width=0.9, edgecolor=edge, facecolor=face)
ax2.plot(df['MACD'], label='MACD', color='purple')
ax2.plot(df['Signal'], label='Señal', color='green')
ax2.axhline(0, color='black')
ax2.legend()
ax2.grid(True)

# RSI (AQUÍ VA EL DÓLAR)
ax3.plot(df['RSI_Merval'], label='RSI Merval', color='blue', linewidth=1.7)
ax3.plot(df['RSI_USD'], label='RSI Dólar', color='green', linestyle='--', linewidth=1.7)
ax3.axhline(70, color='red', linestyle='--')
ax3.axhline(30, color='green', linestyle='--')
ax3.set_ylim(0, 100)
ax3.legend()
ax3.grid(True)

# Líneas verticales
for f in sobrecompra_fechas:
    ax1.axvline(f, color='red', linestyle=':', alpha=0.5)
    ax2.axvline(f, color='red', linestyle=':', alpha=0.5)
    ax3.axvline(f, color='red', linestyle=':', alpha=0.5)

for f in sobreventa_fechas:
    ax1.axvline(f, color='green', linestyle=':', alpha=0.5)
    ax2.axvline(f, color='green', linestyle=':', alpha=0.5)
    ax3.axvline(f, color='green', linestyle=':', alpha=0.5)

plt.tight_layout()

# ================= TELEGRAM =================

ruta_imagen = "tendencias_merval.png"
plt.savefig(ruta_imagen)

caption = (
    f"Tendencias MERVAL + DÓLAR\n"
    f"{ahora.strftime('%d/%m/%Y %H:%M')}\n"
    f"MERVAL: {df['Merval'].iloc[-1]:,.2f} | "
    f"RSI: {df['RSI_Merval'].iloc[-1]:.2f}"
)

enviar_imagen(ruta_imagen, caption)
plt.close(fig)
