<div align="center">
  <h1>🚢 CargoBridge AI</h1>
  <p><em>A Comprehensive Logistics and Supply Chain Intelligence Platform</em></p>
  
  <p>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
    <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
    <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
    <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript"/>
    <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5"/>
    <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3"/>
    <img src="https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap"/>
    <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI"/>
  </p>
</div>

---

**CargoBridge AI** is designed to bridge the gap between MSME exporters, truck drivers, port workers, and data analysts by providing real-time insights, disruption reporting, slot recommendations, and resilience simulation.

## Features

- 👥 **Multi-Role Dashboards:** Customized, high-end 3D scroll-effect views for Admin, Port Workers, Analysts, Truck Drivers, and Exporters.
- 🤖 **AI-Powered Disruption Intelligence (CrewAI):** Utilizes a sophisticated multi-agent pipeline (Disruption Analyst, Weather/AIS Validator, and Confidence Scorer) to analyze and score disruption reports.
  - *Graceful Degradation:* Automatically falls back to a deterministic expert system if CrewAI is unavailable or if run on an unsupported Python version.
- 🕒 **Smart Slot Recommendations:** Generates optimized terminal slot recommendations to reduce wait times and carbon emissions.
- 📊 **Predictive Analytics & Simulation:** Tools for analysts to simulate supply chain resilience and analyze disruption trends.
- 🎮 **Gamification & Social Feed:** Users earn points and badges for on-time deliveries and confirmed reports. Includes a social feed for sharing trips.
- 🔔 **Notifications & SMS Alerts:** Integrated with Twilio to send immediate alerts and updates via WhatsApp/SMS.
- 🌍 **Real-Time Data Integration:** Pulls in real-time weather and AISStream live feed data for accurate vessel tracking and forecasting.

## 🛠 Technology Stack

### Backend
- **Core:** Python, Flask
- **Database:** SQLAlchemy, PostgreSQL
- **Task Scheduling:** APScheduler

### Frontend
- **Languages:** HTML, CSS, JavaScript
- **Frameworks:** Bootstrap
- **Design:** Custom UI/UX with 3D scroll effects and animations

### AI & Data Processing
- **AI Frameworks:** CrewAI, LangChain, OpenAI
- **NLP & Data Math:** NumPy, TextBlob, NLTK

### External Integrations
- **Communications:** Twilio (WhatsApp/SMS)
- **Data APIs:** Weather APIs, MarineTraffic / AISStream

## 🚀 Setup Instructions

### Prerequisites
- Python 3.11 or 3.12 (Highly recommended for full CrewAI support)
- PostgreSQL
- Twilio Account (for WhatsApp/SMS alerts)
- OpenAI API Key (for CrewAI multi-agent pipeline)
- AISStream API Key (for live vessel tracking)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gojosatorou999/CargoBridge-AI.git
   cd CargoBridge-AI
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   > **Note on CrewAI:** To enable the full AI Crew pipeline, ensure you are using Python 3.11-3.12 and install the additional AI dependencies:
   > ```bash
   > pip install crewai crewai-tools langchain-openai
   > ```
   > If these are not installed or you are on Python 3.13+, the app will gracefully fall back to the built-in deterministic expert system.

4. **Set up environment variables:**
   Copy `.env.example` to `.env` and fill in your configurations:
   ```bash
   cp .env.example .env
   ```
   *Make sure to add your `OPENAI_API_KEY` and `AISSTREAM_API_KEY` if you want to use the advanced AI features.*

5. **Initialize the database:**
   ```bash
   flask db upgrade
   ```

6. **Run the application:**
   ```bash
   python app.py
   ```
   The application will be available at `http://127.0.0.1:5000/`.

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## 📄 License
This project is licensed under the MIT License.
