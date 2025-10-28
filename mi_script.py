# -*- coding: utf-8 -*-
# --- Merval unificado: diario o intradiario según hora Argentina ---
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Evita gráficos interactivos
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
import pytz
import requests  # Para enviar Telegram

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
hora_actual = ahora.hour + ahora.minute/60

# 🔹 Definir período histórico
hace_180_dias = ahora - timedelta(days=180)

# 🔹 Selección de modo: intradiario o cierre diario
if 11 <= hora_actual < 17:
    modo = "intradiario"
else:
    modo = "cierre"

print(f"Modo seleccionado: {modo} | Hora actual: {ahora.strftime('%H:%M')}")

# 🔹 Descargar datos
if modo == "intradiario":
    df_diario = yf.download("^MERV", start=hace_180_dias, end=ahora, auto_adjust=True)[['Close']].rename(columns={'Close':'Merval'})
    df_intradia = yf.download("^MERV", period="1d", interval="1m", auto_adjust=True)[['Close']].rename(columns={'Close':'Merval'})
    if not df_intradia.empty:
        ultimo_valor = df_intradia['Merval'].iloc[-1]
        fecha_actual = df_intradia.index[-1].normalize()
        df_diario.loc[fecha_actual] = ultimo_valor
        print(f"Último valor intradiario: {ultimo_valor}")
    df = df_diario.copy()
else:
    df = yf.download("^MERV", start=hace_180_dias, end=ahora, auto_adjust=True)[['Close']].rename(columns={'Close':'Merval'})

# 🔹 Función HMA
def HMA(series, period):
    half_length = int(period / 2)
    sqrt_length = int(np.sqrt(period))
    wma_half = series.rolling(half_length).mean()
    wma_full = series.rolling(period).mean()
    diff = 2 * wma_half - wma_full
    return diff.rolling(sqrt_length).mean()

df['HMA10'] = HMA(df['Merval'], 10)
df['MA15'] = df['Merval'].rolling(window=15).mean()

# 🔹 MACD
ema12 = df['Merval'].ewm(span=12, adjust=False).mean()
ema26 = df['Merval'].ewm(span=26, adjust=False).mean()
df['MACD'] = ema12 - ema26
df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
df['Histograma'] = df['MACD'] - df['Signal']

# 🔹 RSI
def RSI(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

df['RSI'] = RSI(df['Merval'])

# 🔹 Detectar sobrecompra y sobreventa
sobrecompra_fechas = df[df['RSI'] > 70].index
sobreventa_fechas = df[df['RSI'] < 30].index

# 🔹 --- GRAFICAR ---
fig, (ax1, ax2, ax3) = plt.subplots(
    3, 1, figsize=(14, 11), sharex=True,
    gridspec_kw={'height_ratios': [3, 1, 1]}
)

ax1.plot(df['Merval'], label='Merval', color='blue')
ax1.plot(df['HMA10'], label='HMA10', color='orange')
ax1.plot(df['MA15'], label='MA15', color='red')
ax1.set_title('Merval con HMA10, MA15, MACD (12,26,9), RSI (14)')
ax1.set_ylabel('Precio')
ax1.legend()
ax1.grid(True)

ax2.plot(df['MACD'], label='MACD', color='purple')
ax2.plot(df['Signal'], label='Señal', color='green')
ax2.bar(df.index, df['Histograma'], label='Histograma', color='gray', alpha=0.4)
ax2.axhline(0, color='black', linewidth=1)
ax2.set_ylabel('MACD')
ax2.legend()
ax2.grid(True)

ax3.plot(df['RSI'], label='RSI', color='blue', linewidth=1.5)
ax3.axhline(70, color='red', linestyle='--')
ax3.axhline(30, color='green', linestyle='--')
ax3.fill_between(df.index, 70, 100, color='red', alpha=0.1)
ax3.fill_between(df.index, 0, 30, color='green', alpha=0.1)
ax3.set_ylim(0, 100)
ax3.set_ylabel('RSI')
ax3.set_xlabel('Fecha')
ax3.legend()
ax3.grid(True)

color_sobrecompra = "green" if modo=="cierre" else "red"
color_sobreventa = "red" if modo=="cierre" else "green"

for fecha in sobrecompra_fechas:
    ax1.axvline(fecha, color=color_sobrecompra, linestyle=':', alpha=0.6, linewidth=3)
    ax2.axvline(fecha, color=color_sobrecompra, linestyle=':', alpha=0.6, linewidth=3)
    ax3.axvline(fecha, color=color_sobrecompra, linestyle=':', alpha=0.6, linewidth=3)

for fecha in sobreventa_fechas:
    ax1.axvline(fecha, color=color_sobreventa, linestyle=':', alpha=0.6, linewidth=3)
    ax2.axvline(fecha, color=color_sobreventa, linestyle=':', alpha=0.6, linewidth=3)
    ax3.axvline(fecha, color=color_sobreventa, linestyle=':', alpha=0.6, linewidth=3)

plt.tight_layout()

# 🔹 Guardar y enviar imagen por Telegram
ruta_imagen = "tendencias_merval.png"
plt.savefig(ruta_imagen)

ultimo_merval = float(df["Merval"].iloc[-1])
ultimo_rsi = float(df["RSI"].iloc[-1])
texto_info = f"MERVAL: {ultimo_merval:,.2f} | RSI: {ultimo_rsi:.2f}"

caption = f"Tendencias MERVAL {ahora.strftime('%d/%m/%Y %H:%M')}\n{texto_info}"
enviar_imagen(ruta_imagen, caption=caption)

# No es necesario mostrar la ventana gráfica
plt.close(fig)
