# CargoBridge AI

**CargoBridge AI** is a comprehensive logistics and supply chain intelligence platform built with Flask. It is designed to bridge the gap between MSME exporters, truck drivers, port workers, and data analysts by providing real-time insights, disruption reporting, slot recommendations, and resilience simulation.

## Features

- **Multi-Role Dashboards:** Customized views for Admin, Port Workers, Analysts, Truck Drivers, and Exporters.
- **Disruption Reporting:** Users can submit real-time disruption reports (traffic, weather, port congestion) which are AI-scored for confidence.
- **Smart Slot Recommendations:** Generates optimized terminal slot recommendations to reduce wait times and carbon emissions.
- **Predictive Analytics & Simulation:** Tools for analysts to simulate supply chain resilience and analyze disruption trends.
- **Gamification & Social Feed:** Users earn points and badges for on-time deliveries and confirmed reports. Includes a social feed for sharing trips.
- **Notifications & SMS Alerts:** Integrated with Twilio to send immediate alerts and updates via WhatsApp/SMS.
- **Real-Time Data Integration:** Pulls in real-time weather and AIS vessel data for accurate forecasting.

## Technology Stack

- **Backend:** Python, Flask, SQLAlchemy, PostgreSQL
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **AI & Data Processing:** NumPy, TextBlob, NLTK
- **Task Scheduling:** APScheduler
- **External Integrations:** Twilio (WhatsApp/SMS), Weather & AIS APIs

## Setup Instructions

### Prerequisites
- Python 3.9+
- PostgreSQL
- Twilio Account (for WhatsApp/SMS alerts)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd CargoBridge-AI
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Copy `.env.example` to `.env` and fill in your configurations:
   ```bash
   cp .env.example .env
   ```

5. **Initialize the database:**
   ```bash
   flask db upgrade
   ```

6. **Run the application:**
   ```bash
   flask run
   ```
   The application will be available at `http://127.0.0.1:5000/`.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.
