document.addEventListener('DOMContentLoaded', () => {
    // --- Get All DOM Elements ---
    const tickerInput = document.getElementById('ticker-input');
    const predictBtn = document.getElementById('predict-btn');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    // --- Result Containers ---
    const resultsGrid = document.getElementById('results-grid');
    const newsContainer = document.getElementById('news-container');
    
    // --- Card 1: Prediction ---
    const resultTicker = document.getElementById('result-ticker');
    const resultPrice = document.getElementById('result-price');
    const resultSentiment = document.getElementById('result-sentiment');
    
    // --- Card 2: Company Info ---
    const infoList = document.getElementById('company-info-list');
    const companySummary = document.getElementById('company-summary');

    // --- Card 3: Chart ---
    const chartCanvas = document.getElementById('stock-chart');
    const periodControls = document.querySelector('.chart-controls');
    
    // --- Card 4: News ---
    const newsList = document.getElementById('news-list');

    let myChart = null; // To hold the chart instance
    let currentTicker = ''; // To store the last valid ticker

    // --- Main Event Listener ---
    predictBtn.addEventListener('click', fetchData);
    
    // Allow pressing Enter to search
    tickerInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            fetchData();
        }
    });

    // --- Listen for Chart Period Changes ---
    periodControls.addEventListener('change', (e) => {
        if (e.target.name === 'hist-period' && currentTicker) {
            // Only fetch new data if a ticker has been searched
            fetchData(currentTicker, e.target.value);
        }
    });

    // --- Main Data Fetching Function ---
    function fetchData(ticker = null, period = null) {
        if (!ticker) {
            ticker = tickerInput.value.trim().toUpperCase();
        }
        if (!ticker) {
            alert('Please enter a stock ticker.');
            return;
        }

        // Get selected period, default to 6mo if not provided
        if (!period) {
            period = document.querySelector('input[name="hist-period"]:checked').value || '6mo';
        }

        // --- Show loading, hide old results ---
        loadingSpinner.style.display = 'block';
        resultsGrid.style.display = 'none';
        newsContainer.style.display = 'none';

        // --- Call the new Backend API ---
        fetch('http://127.0.0.1:5000/get_stock_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ ticker: ticker, period: period }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { 
                    throw new Error(err.error || 'Server error') 
                });
            }
            return response.json();
        })
        .then(data => {
            // --- Success: Populate All Page Elements ---
            loadingSpinner.style.display = 'none';
            resultsGrid.style.display = 'grid'; // Show grid
            newsContainer.style.display = 'block'; // Show news
            
            currentTicker = data.ticker; // Store valid ticker

            // 1. Populate Prediction Card
            resultTicker.textContent = data.company_info.name;
            resultPrice.textContent = `$${data.predicted_price.toFixed(2)}`;
            resultSentiment.textContent = data.overall_sentiment;
            resultSentiment.className = `sentiment ${data.overall_sentiment}`; // For styling

            // 2. Populate Info Card
            populateInfoCard(data.company_info);
            
            // 3. Update Chart
            updateChart(data.history);

            // 4. Populate News Card
            populateNewsCard(data.news);
        })
        .catch(error => {
            // --- Error: Display Error ---
            loadingSpinner.style.display = 'none';
            alert(`Error: ${error.message}`);
            console.error('Error:', error);
            currentTicker = ''; // Reset current ticker on error
        });
    }
    
    // --- Helper Function: Populate Info Card ---
    function populateInfoCard(info) {
        infoList.innerHTML = ''; // Clear old info
        
        const marketCap = (info.marketCap / 1_000_000_000).toFixed(2);
        
        infoList.innerHTML += `
            <li>Sector: <span>${info.sector}</span></li>
            <li>Industry: <span>${info.industry}</span></li>
            <li>Market Cap: <span>$${marketCap}B</span></li>
        `;
        companySummary.textContent = info.summary;
    }

    // --- Helper Function: Populate News Card ---
    function populateNewsCard(news) {
        newsList.innerHTML = ''; // Clear old news
        
        if (news.length === 0) {
            newsList.innerHTML = '<p>No recent news found.</p>';
            return;
        }

        news.forEach(item => {
            newsList.innerHTML += `
                <div class="news-item">
                    <div>
                        <a href="${item.link}" target="_blank">${item.title}</a>
                        <p>${item.publisher}</p>
                    </div>
                    <div class="news-sentiment ${item.sentiment}">
                        ${item.sentiment}
                    </div>
                </div>
            `;
        });
    }

    // --- Helper Function: Update Chart ---
    function updateChart(history) {
        if (myChart) {
            myChart.destroy();
        }

        const labels = history.map(item => item.Date);
        const data = history.map(item => item.Close);

        const ctx = chartCanvas.getContext('2d');
        myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Close Price',
                    data: data,
                    borderColor: '#007aff',
                    backgroundColor: 'rgba(0,122,255,0.1)',
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
});