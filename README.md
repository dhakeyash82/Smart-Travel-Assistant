🌍 Smart Travel Assistant

✈️ Plan Smarter. Travel Safer. Explore Better.

A web-based travel planning application that helps users analyze trips between two cities using weather forecasts, air quality information, travel mode recommendations, estimated travel costs, disaster-related news alerts, and nearby essential services.

🚀 Features

🌦️ Weather Analysis: View weather summaries, temperature, humidity, wind speed, and rain predictions for your source and destination.

🏆 Trip Score: Get an overall destination score based on weather conditions, air quality, news alerts, and configured location risk penalties.

📅 Best Day Recommendation: Identify a potentially suitable travel date based on available forecast data.

🚗 Travel Mode Recommendation: Compare road, train, and air travel options based on estimated distance and scoring logic.

💰 Time & Cost Estimates: View approximate travel distance, duration, and cost for different transportation modes.

🎒 Smart Packing Tips: Receive packing suggestions based on destination weather conditions.

📰 News & Safety Alerts: Retrieve disaster-related news and alerts associated with the destination.

🏥 Nearby Essentials: Find nearby ATMs, hospitals, and pharmacies.

🔗 Booking Assistance: Access external travel booking platforms for trains, flights, buses, and hotels.

🎨 Modern User Interface: Enjoy a clean, responsive interface with a sky-inspired theme, floating cards, and loading indicators.

🛠️ Tech Stack

Technology

Purpose

Python

Backend application logic

Flask

Web framework and REST API

HTML5

Application structure

CSS3

Responsive styling and visual design

JavaScript

Form handling and dynamic results

Requests

External API integration

OpenWeather API

Geocoding, weather forecasts, and air quality

Foursquare Places API

Nearby essential services

NewsAPI

Disaster-related news and alerts

OpenStreetMap Overpass API

Fallback search for nearby amenities

Gunicorn

Production WSGI server

🏗️ Application Architecture

The application follows a simple client-server architecture.

Frontend: Users enter their source city, destination city, and travel dates through the web interface.

API Request: JavaScript sends the trip details to the Flask backend through the /api/analyze endpoint.

Data Collection: The backend retrieves available weather, air quality, nearby places, and news information from external APIs.

Trip Analysis: Python functions calculate approximate travel distance, transportation estimates, packing suggestions, the best-day score, and the overall trip score.

Results Display: The backend returns a JSON response, which JavaScript renders dynamically on the webpage.

📂 Project Structure

smart-travel-assistant/
│
├── app.py                 # Flask backend and analysis logic
├── requirements.txt       # Python dependencies
├── Procfile               # Deployment startup command
├── templates/
│   └── index.html         # Main web interface
├── static/
│   ├── app.js             # Frontend interaction and API calls
│   └── style.css          # Styling and responsive layout
└── README.md              # Project documentation

⚙️ Installation and Setup

1. Clone the Repository

git clone https://github.com/YOUR_USERNAME/smart-travel-assistant.git
cd smart-travel-assistant

Replace YOUR_USERNAME with your GitHub username.

2. Create a Virtual Environment

python -m venv venv

Activate it:

Windows

venv\Scripts\activate

macOS / Linux

source venv/bin/activate

3. Install Dependencies

pip install -r requirements.txt

4. Configure API Keys

Configure your API credentials using environment variables rather than hardcoding secrets in the source code.

Required services include:

OpenWeather API

Foursquare Places API

NewsAPI

Ensure that app.py reads the corresponding environment variables before running the application.

5. Run the Application

python app.py

Open your browser and visit:

http://127.0.0.1:5000/

🔌 API Endpoint

Analyze a Trip

Endpoint: POST /api/analyze

Content-Type: application/json

Example request:

{
  "source_city": "Mumbai",
  "dest_city": "Pune",
  "from_date": "2026-10-20",
  "to_date": "2026-10-22"
}

The endpoint returns a JSON response containing source and destination weather summaries, trip scores, best-day recommendations, packing tips, travel estimates, news alerts, booking links, and nearby essentials.

Validation rules:

All four input fields are required.

Dates must use the YYYY-MM-DD format.

The start date cannot be later than the end date.

The selected trip duration cannot exceed seven days.

☁️ Deployment

The repository includes a Procfile configured to launch the Flask application using Gunicorn:

web: gunicorn app:app

Deploy to a compatible Python hosting platform by configuring the required environment variables, installing dependencies, and using the provided startup command.

🔒 Security and Limitations

Store API keys in environment variables and never commit credentials to GitHub.

The current implementation uses a limited weather forecast window; longer-range trip dates may rely on averaged available forecast data rather than actual forecasts for those dates.

Travel duration and cost figures are approximate estimates based on straight-line distance, not live road, train, or flight schedules.

The trip score is a rule-based estimate, not an official safety assessment.

External API availability, rate limits, and subscription restrictions may affect results.

Verify weather warnings, local safety information, and travel bookings with authoritative sources before travelling.

🔮 Future Enhancements

Integrate live maps and route-based distance calculations.

Add real-time transport schedules and more accurate fare estimates.

Improve weather-based recommendations for longer trips.

Introduce user accounts, saved trips, and itinerary management.

Add interactive destination maps and visual weather charts.

Enhance scoring with configurable user preferences and more comprehensive safety data.

🎯 Project Objective

The goal of the Smart Travel Assistant is to bring essential travel planning information together in one interface, helping users make more informed decisions about their travel dates, transportation options, packing needs, and destination conditions.
