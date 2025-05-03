import os
import streamlit as st
from PIL import Image
import openai
import base64
import requests
import pandas as pd
import ta
from streamlit.errors import StreamlitAPIException


# 𝗔𝗣𝗜 𝗞𝗲𝘆 𝗛𝗮𝗿𝗱𝗰𝗼𝗱𝗲𝗱 𝗞𝗮𝗿𝗲𝗶𝗻 (Replace YOUR_KEY_HERE with actual key)
# 𝗪𝗔𝗥𝗡𝗜𝗡𝗚: Is key ko kabhi public nahi karna!
openai.api_key = "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"  # 👈 Replace this

# Binance API has no key for public klines

st.set_page_config(page_title="Chart Analyzer", layout="centered")
st.title("📈 Chart Analyzer with Screenshot or Coin Data")

# Inputs
coin_name = st.text_input("Coin Symbol (e.g., BTCUSDT)")
timeframe = st.selectbox("Timeframe", ["1m","3m","5m","15m","30m","1h","4h","1d","1w","1M"], index=3)
uploaded_file = st.file_uploader("Chart Screenshot (optional)", type=["png","jpg","jpeg"])

if st.button("Analyze 📊"):
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
        resp = openai.chat.completions.create(  # 👈 Updated OpenAI syntax
            model="gpt-4-turbo",  # ✅ Correct model name
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
        st.write(analysis.split("## Conclusion:")[-1].strip() if "## Conclusion:" in analysis else "Conclusion missing.")
    
    # ... (previous imports and OpenAI setup) ...

    elif coin_name and timeframe:
        st.subheader(f"Fetching data for {coin_name} on {timeframe}")
        url = f"https://api.binance.me/api/v3/klines?symbol={coin_name}&interval={timeframe}&limit=100"
        try:
            response = requests.get(url)
            response.raise_for_status()  # HTTP errors check karein
            data = response.json()
            
            # DataFrame banane se pehle data check karein
            if not data:
                st.error("Binance se koi data nahi mila! Symbol ya timeframe sahi hai?")
                st.stop()
                
            df = pd.DataFrame(data, columns=["open_time","open","high","low","close","volume","close_time",
                                            "qav","num_trades","taker_base_vol","taker_quote_vol","ignore"])
            df = df.astype({"open":"float","high":"float","low":"float","close":"float","volume":"float","qav":"float"})
            
            # SAR Indicator ko safe tarike se handle karein
            try:
                # High, Low, Close columns ka index 0 check karein
                if df['high'].empty or df['low'].empty or df['close'].empty:
                    raise ValueError("DataFrame mein columns khali hain")
                    
                # PSARIndicator ko calculate karein
                psar = ta.trend.PSARIndicator(
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    step=0.02,  # Default parameters specify karein
                    max_step=0.2
                )
                df['SAR'] = psar.psar()
                
            except Exception as e:
                st.error(f"SAR calculate nahi ho saka: {str(e)}")
                df['SAR'] = 0  # Default value assign karein
                
            # Baqi indicators (same as before) ...
            
        except requests.exceptions.RequestException as e:
            st.error(f"Binance API error: {str(e)}")
            st.stop()
        # Indicators (same as before)
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
        vals = {col: round(latest[col],6) for col in ['MA','EMA','BOLL_upper','BOLL_mid','BOLL_lower','SAR','AVL','VOL','MACD','RSI','K','D','J','OBV','WR','StochRSI']}
        prompt = f"Coin: {coin_name}\nTimeframe: {timeframe}\n" + "\n".join([f"{k}: {v}" for k,v in vals.items()])
        prompt += "\n\nFor each indicator above, explain what it indicates and then '## Conclusion:' summarizing overall trend in Roman Urdu. '##Suggestion:' Give Suggestion that We should Take Long Buy or Short Sell for Each Time Interval? '###Leverage:' Give Suggestion for leverage for better Profit if a user have $100. Suggest Take Profit Price: Entery Price: & Stop Loss."

        # GPT for reasoning
        resp = openai.ChatCompletion.create(
            model="gpt-4-turbo",  # ✅ Correct model
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
        st.write(analysis.split("## Conclusion:")[-1].strip() if "## Conclusion:" in analysis else "Conclusion missing.")
    
    else:
        st.error("Please provide either a chart screenshot or both Coin Symbol and Timeframe.")
