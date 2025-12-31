# -*- coding: utf-8 -*-
# --- Merval unificado: diario + intradiario | RSI con Dólar ---
import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# ===================== TELEGRAM =====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

def enviar_imagen(ruta_imagen, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(ruta_imagen, "rb") as foto:
        requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption},
            files={"photo": foto}
        )

# ===================== TIEMPO =====================
argentina_tz = pytz.timezone("America/Argentina/Buenos_Aires")
ahora = datetime.now(argentina_tz)
hace_180_dias = ahora - timedelta(days=180)

# ===================== MERVAL =====================
df = yf.download("^MERV", start=hace_180_dias, end=ahora, auto_adjust=True)[['Close']]
df = df.rename(columns={'Close': 'Merval'})

df_intradia = yf.download("^MERV", period="1d", interval="1m", auto_adjust=True)[['Close']]
df_intradia = df_intradia.rename(columns={'Close': 'Merval'})

if not df_intradia.empty:
    ultimo_valor = float(df_intradia['Merval'].iloc[-1])
    fecha_actual = df_intradia.index[-1].tz_localize(None).normalize()
    df.loc[fecha_actual] = ultimo_valor

# ===================== DÓLAR =====================
df_dolar = yf.download(
    "ARS=X",
    start=hace_180_dias,
    end=ahora,
    auto_adjust=True
)[['Close']]

df_dolar = df_dolar.rename(columns={'Close': 'Dolar'})

# ===================== INDICADORES =====================
def HMA(series, period):
    half = int(period / 2)
    sqrt = int(np.sqrt(period))
    wma_half = series.rolling(half).mean()
    wma_full = series.rolling(period).mean()
    diff = 2 * wma_half - wma_full
    return diff.rolling(sqrt).mean()

df['HMA10'] = HMA(df['Merval'], 10)
df['MA15'] = df['Merval'].rolling(15).mean()

ema12 = df['Merval'].ewm(span=12, adjust=False).mean()
ema26 = df['Merval'].ewm(span=26, adjust=False).mean()
df['MACD'] = ema12 - ema26
df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
df['Histograma'] = df['MACD'] - df['Signal']

hist = df['Histograma']
delta = hist.diff()
condiciones = [
    (hist >= 0) & (delta > 0),
    (hist >= 0) & (delta <= 0),
    (hist < 0) & (delta < 0),
    (hist < 0) & (delta >= 0)
]

face = np.select(condiciones, ['green','none','red','none'], default='gray')
edge = np.select(condiciones, ['green','green','red','red'], default='black')

def RSI(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

df['RSI'] = RSI(df['Merval'])

sobrecompra_fechas = df[df['RSI'] > 70].index
sobreventa_fechas = df[df['RSI'] < 30].index

# ===================== GRAFICOS =====================
fig, (ax1, ax2, ax3) = plt.subplots(
    3, 1, figsize=(14, 11), sharex=True,
    gridspec_kw={'height_ratios': [1, 1, 1]}
)

# --- Precio
ax1.plot(df['Merval'], label='Merval', color='blue')
ax1.plot(df['HMA10'], label='HMA10', color='orange')
ax1.plot(df['MA15'], label='MA15', color='red')
ax1.set_title('Merval con HMA10, MA15, MACD y RSI + Dólar')
ax1.legend()
ax1.grid(True)

# --- MACD
ax2.bar(df.index, hist, width=0.9, edgecolor=edge, facecolor=face)
ax2.plot(df['MACD'], label='MACD', color='purple')
ax2.plot(df['Signal'], label='Señal', color='green')
ax2.axhline(0, color='black')
ax2.legend()
ax2.grid(True)

# --- RSI + DÓLAR
ax3.plot(df['RSI'], label='RSI', color='blue', linewidth=1.5)
ax3.axhline(70, color='red', linestyle='--')
ax3.axhline(30, color='green', linestyle='--')
ax3.fill_between(df.index, 70, 100, color='red', alpha=0.1)
ax3.fill_between(df.index, 0, 30, color='green', alpha=0.1)
ax3.set_ylim(0, 100)
ax3.grid(True)

ax3b = ax3.twinx()
ax3b.plot(
    df_dolar.index,
    df_dolar['Dolar'],
    label='Dólar',
    color='black',
    alpha=0.5,
    linewidth=1.2
)

lines1, labels1 = ax3.get_legend_handles_labels()
lines2, labels2 = ax3b.get_legend_handles_labels()
ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

# --- Líneas verticales
for fecha in sobrecompra_fechas:
    ax1.axvline(fecha, color='red', linestyle=':', alpha=0.6)
    ax2.axvline(fecha, color='red', linestyle=':', alpha=0.6)
    ax3.axvline(fecha, color='red', linestyle=':', alpha=0.6)

for fecha in sobreventa_fechas:
    ax1.axvline(fecha, color='green', linestyle=':', alpha=0.6)
    ax2.axvline(fecha, color='green', linestyle=':', alpha=0.6)
    ax3.axvline(fecha, color='green', linestyle=':', alpha=0.6)

plt.tight_layout()

# ===================== TELEGRAM =====================
ruta_imagen = "tendencias_merval.png"
plt.savefig(ruta_imagen)

ultimo_merval = float(df['Merval'].iloc[-1])
ultimo_rsi = float(df['RSI'].iloc[-1])
ultimo_dolar = float(df_dolar['Dolar'].iloc[-1])

caption = (
    f"Tendencias MERVAL + DÓLAR\n"
    f"{ahora.strftime('%d/%m/%Y %H:%M')}\n"
    f"MERVAL: {ultimo_merval:,.2f} | "
    f"RSI: {ultimo_rsi:.2f} | "
    f"DÓLAR: {ultimo_dolar:,.2f}"
)

enviar_imagen(ruta_imagen, caption)
plt.close(fig)
