# Nutrition Agent

A responsive Flask web app for AI-powered nutrition guidance using IBM Watsonx.ai with Granite models.

## Features
- Chat-based nutrition coach
- BMI calculator
- Family profile support
- Meal planning suggestion UI
- Dark mode and responsive design
- Configurable AGENT_INSTRUCTIONS for customization

## Setup
1. Create a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your IBM credentials.
4. Run the app: `python app.py`

## IBM Watsonx.ai setup
- Set `IBM_API_KEY` to your IBM Cloud API key.
- Set `IBM_PROJECT_ID` to your Watsonx project ID.
- Optional: set `IBM_MODEL_ID` to a Granite model ID.

## Deployment
- Render / Railway / Heroku: set the same environment variables and start with `gunicorn app:app`.
