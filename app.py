import os
import streamlit as st
from PIL import Image
import openai
import base64
import requests
import pandas as pd
import ta
from streamlit.errors import StreamlitAPIException

# Chart Analyzer with Screenshot or Binance API Data

# Load API keys
# OpenAI
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
except (AttributeError, KeyError, StreamlitAPIException):
    openai.api_key = os.getenv("OPENAI_API_KEY")
# Binance API has no key for public klines

if not openai.api_key:
    st.error("Missing OPENAI_API_KEY! Set in Streamlit secrets or env var.")
    st.stop()

st.set_page_config(page_title="Chart Analyzer", layout="centered")
st.title("📈 Chart Analyzer with Screenshot or Coin Data")

# Inputs
coin_name = st.text_input("Coin Symbol (e.g., BTCUSDT)")
timeframe = st.selectbox("Timeframe", ["1m","3m","5m","15m","30m","1h","4h","1d","1w","1M"], index=3)
uploaded_file = st.file_uploader("Chart Screenshot (optional)", type=["png","jpg","jpeg"])

# Button trigger
if st.button("Analyze 📊"):
    # Branch 1: Screenshot provided
    if uploaded_file:
        st.subheader(f"Analyzing screenshot for {coin_name or ''} on {timeframe}")
        uploaded_file.seek(0)
        img_bytes = uploaded_file.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{img_b64}"
        system_msg = (
            "You are an expert crypto analyst. Given a chart image, coin and timeframe, "
            "analyze MA, EMA, BOLL, SAR, AVL, VOL, MACD, RSI, KDJ, OBV, WR, StochRSI. "
            "Explain each indicator and end with '## Conclusion: in Roman Urdu'."
        )
        user_msg = [
            {"type":"text","text":f"Analyze chart for {coin_name} on {timeframe}."},
            {"type":"image_url","image_url":{"url":data_uri}}
        ]
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":system_msg},
                {"role":"user","content":user_msg}
            ],
            temperature=0.2,
            max_tokens=3000
        )
        analysis = resp.choices[0].message.content
        st.subheader("Detailed Analysis & Reasoning:")
        st.text_area("", analysis, height=400)
        st.subheader("Main Conclusion:")
        if "## Conclusion:" in analysis:
            st.write(analysis.split("## Conclusion:")[-1].strip())
        else:
            st.write("'## Conclusion:' section missing.")
    # Branch 2: No screenshot, use Binance API
    elif coin_name and timeframe:
        st.subheader(f"Fetching data for {coin_name} on {timeframe}")
        # Fetch klines
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={coin_name}&interval={timeframe}&limit=100"
        data = requests.get(url).json()
        df = pd.DataFrame(data, columns=["open_time","open","high","low","close","volume","close_time",
                                          "qav","num_trades","taker_base_vol","taker_quote_vol","ignore"])
        df = df.astype({"open":"float","high":"float","low":"float","close":"float","volume":"float","qav":"float"})
        # Indicators
        df['MA']  = df['close'].rolling(window=20).mean()
        df['EMA'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['BOLL_upper']  = bb.bollinger_hband()
        df['BOLL_mid']    = bb.bollinger_mavg()
        df['BOLL_lower']  = bb.bollinger_lband()
        df['SAR']         = ta.trend.PSARIndicator(df['high'], df['low'], df['close']).psar()
        df['AVL']         = df['volume'].rolling(window=20).mean()
        df['VOL']         = df['volume']
        macd = ta.trend.MACD(df['close'])
        df['MACD']        = macd.macd()
        df['RSI']         = ta.momentum.RSIIndicator(df['close']).rsi()
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        df['K']           = stoch.stoch()
        df['D']           = stoch.stoch_signal()
        df['J']           = 3*df['K'] - 2*df['D']
        df['OBV']         = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
        df['WR']          = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close']).williams_r()
        df['StochRSI']    = ta.momentum.StochRSIIndicator(df['close']).stochrsi()
        latest = df.iloc[-1]
        # Prepare prompt
        vals = {col: round(latest[col],6) for col in ['MA','EMA','BOLL_upper','BOLL_mid','BOLL_lower','SAR','AVL','VOL','MACD','RSI','K','D','J','OBV','WR','StochRSI']}
        prompt = f"Coin: {coin_name}\nTimeframe: {timeframe}\n"
        prompt += "\n".join([f"{k}: {v}" for k,v in vals.items()])
        prompt += "\n\nFor each indicator above, explain what it indicates and then '## Conclusion:' summarizing overall trend in Roman Urdu. '##Suggestion:' Give Suggestion that We should Take Long Buy or Short Sell for Each Time Interval? '###Leverage:' Give Suggestion for leverage for better Profit if a user have $100. Suggest Take Profit Price: Entery Price: & Stop Loss."
        # GPT for reasoning
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You are an expert crypto analyst."},
                {"role":"user","content":prompt}
            ],
            temperature=0.2,
            max_tokens=3000
        )
        analysis = resp.choices[0].message.content
        st.subheader("Detailed Analysis & Reasoning:")
        st.text_area("", analysis, height=400)
        st.subheader("Main Conclusion:")
        if "## Conclusion:" in analysis:
            st.write(analysis.split("## Conclusion:")[-1].strip())
        else:
            st.write("'## Conclusion:' section missing.")
    else:
        st.error("Please provide either a chart screenshot or both Coin Symbol and Timeframe.")
