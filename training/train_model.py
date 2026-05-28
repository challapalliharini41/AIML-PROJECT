import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
import joblib
import os

# --- 1. Fetch and Prepare Data ---
print("Fetching 5 years of 'AAPL' data...")
# We use a date in the past to ensure data is final
df = yf.download('AAPL', start='2020-01-01', end='2025-10-30')

# Select the 'Close' column. The double brackets [[]] ensure we get a
# DataFrame, which is what scaler.fit_transform expects.
# This method works for both simple columns ('Close') and 
# MultiIndex columns (('Close', 'AAPL')).
try:
    data = df[['Close']]
except KeyError:
    print(f"Error: Could not find 'Close' column. Available columns: {df.columns}")
    exit()
    
dataset = data.values
print("Successfully selected 'Close' column for training.")

training_data_len = int(np.ceil(len(dataset) * .95))

# --- 2. Scale the Data ---
scaler = MinMaxScaler(feature_range=(0,1))
scaled_data = scaler.fit_transform(dataset)

# --- 3. Create Training Data ---
train_data = scaled_data[0:int(training_data_len), :]
x_train = []
y_train = []

# Use 60 days of data to predict the 61st
for i in range(60, len(train_data)):
    # x_train will be a list of 60-day windows
    x_train.append(train_data[i-60:i, 0])
    # y_train will be the 61st day
    y_train.append(train_data[i, 0])
    
# Convert to numpy arrays. x_train will be (samples, 60)
x_train, y_train = np.array(x_train), np.array(y_train)

# --- 4. Build and Train Linear Regression Model ---
print("Building and training the LinearRegression model...")
model = LinearRegression()
model.fit(x_train, y_train)

# --- 5. Save the Model and Scaler ---
print("Saving model and scaler...")
backend_dir = '../backend'
if not os.path.exists(backend_dir):
    os.makedirs(backend_dir)

# Save the sklearn model using joblib (as a .pkl file)
joblib.dump(model, os.path.join(backend_dir, 'stock_model.pkl'))
joblib.dump(scaler, os.path.join(backend_dir, 'preprocessor.pkl'))

print("--- Training Complete! ---")
print(f"Model saved to: {os.path.join(backend_dir, 'stock_model.pkl')}")
print(f"Scaler saved to: {os.path.join(backend_dir, 'preprocessor.pkl')}")