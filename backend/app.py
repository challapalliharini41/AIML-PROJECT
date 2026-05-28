from flask import Flask, request, jsonify, session
from flask_cors import CORS
import yfinance as yf
import numpy as np
import pandas as pd
import joblib
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

app = Flask(__name__)
# Allow requests from your frontend
# Make sure your Live Server port matches (e.g., 5500)
CORS(app, supports_credentials=True)

# --- Load Models (Error handling) ---
try:
    model = joblib.load('stock_model.pkl')
    scaler = joblib.load('preprocessor.pkl')
    sentiment_analyzer = SentimentIntensityAnalyzer()
    print("* Model, scaler, and sentiment analyzer loaded successfully.")
except Exception as e:
    print(f"* CRITICAL ERROR loading models: {e}")
    model = None
    scaler = None
    sentiment_analyzer = None

# --- Helper Function for Sentiment ---
def get_sentiment(text):
    if not text:
        return 'Neutral'
    score = sentiment_analyzer.polarity_scores(text)['compound']
    if score > 0.05:
        return 'Positive'
    elif score < -0.05:
        return 'Negative'
    else:
        return 'Neutral'

# --- Main Analysis Route ---
@app.route('/get_stock_data', methods=['POST'])
def get_stock_data():
    if not model or not scaler or not sentiment_analyzer:
        return jsonify({'error': 'Backend models not loaded or failed to load.'}), 500

    try:
        data = request.get_json()
        ticker_symbol = data['ticker']
        # Default to 1 year of data
        hist_period_days = int(data.get('period_days', 365)) 
        
        ticker = yf.Ticker(ticker_symbol)

        # --- 1. Get History (for prediction AND charting) ---
        # Fetch 2 years to ensure we have enough data for 50-day SMA
        hist_df = ticker.history(period="2y") 
        if hist_df.empty:
            return jsonify({'error': 'Could not fetch historical data for ticker'}), 400
        
        # --- 2. Make Prediction ---
        # Select 'Close' column safely
        try:
            close_prices_df = hist_df[['Close']]
        except KeyError:
            return jsonify({'error': f"Could not find 'Close' column for {ticker_symbol}"}), 400
        
        # Get last 60 days for prediction
        close_prices = close_prices_df.values[-60:].reshape(-1, 1)
        scaled_input = scaler.transform(close_prices)
        X_test = scaled_input.reshape(1, 60)
        raw_prediction = model.predict(X_test)
        predicted_price = scaler.inverse_transform(raw_prediction.reshape(-1, 1))[0][0]
        
        # ** NEW: Get current price for Bullish/Bearish signal **
        current_price = close_prices_df.iloc[-1]['Close']
        
        # --- 3. Get Company Info ---
        info = ticker.info
        company_info = {
            'name': info.get('longName', 'N/A'),
            'summary': info.get('longBusinessSummary', 'N/A'),
            'marketCap': info.get('marketCap', 'N/A'),
            'averageVolume': info.get('averageVolume', 'N/A'),
            'trailingPE': info.get('trailingPE', 'N/A'),
            'forwardPE': info.get('forwardPE', 'N/A'),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 'N/A'),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 'N/A'),
            'dividendYield': info.get('dividendYield', 'N/A')
        }

        # --- 4. Get News & Sentiment ---
        news = ticker.news
        news_with_sentiment = []
        for item in news[:8]:
            title = item.get('title')
            if not title: continue
            sentiment = get_sentiment(title)
            news_with_sentiment.append({
                'title': title,
                'publisher': item.get('publisher', 'No Publisher'),
                'link': item.get('link', '#'),
                'sentiment': sentiment
            })
        
        sentiments = [n['sentiment'] for n in news_with_sentiment]
        overall_sentiment = 'Neutral'
        if sentiments.count('Positive') > sentiments.count('Negative'): overall_sentiment = 'Positive'
        elif sentiments.count('Negative') > sentiments.count('Positive'): overall_sentiment = 'Negative'

        # --- 5. Prepare Charting Data (based on requested period) ---
        chart_df = hist_df.tail(hist_period_days) # Filter to requested period
        chart_df.reset_index(inplace=True) # Make 'Date' a column
        chart_df['Date'] = chart_df['Date'].dt.strftime('%Y-%m-%d') # Format date
        # Send OHLC (Open, High, Low, Close) data for candlestick chart
        history_data = chart_df[['Date', 'Open', 'High', 'Low', 'Close']].to_dict('records')

        # --- 6. Send All Data Back ---
        return jsonify({
            'predicted_price': float(predicted_price),
            'current_price': float(current_price), # <-- NEW
            'company_info': company_info,
            'news': news_with_sentiment,
            'overall_sentiment': overall_sentiment,
            'history': history_data
        })

    except Exception as e:
        print(f"Error on /get_stock_data: {e}")
        if 'No data found' in str(e) or 'object has no attribute' in str(e) or 'history' in str(e):
             return jsonify({'error': f'Invalid or delisted ticker: {ticker_symbol}'}), 404
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# --- Main Runner ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)

