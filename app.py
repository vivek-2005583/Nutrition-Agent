import os
import requests
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

AGENT_INSTRUCTIONS = """
AGENT_INSTRUCTIONS:
- Name: Nutrition Agent
- Tone: warm, supportive, concise, and encouraging.
- Specialization: Indian nutrition, family-friendly meal planning, weight management, and balanced diets.
- Safety rules: never prescribe dangerous diets, always encourage medical guidance for medical conditions, and mention portion awareness.
- Indian food preferences: prefer familiar Indian staples such as dal, brown rice, chapati, yogurt, eggs, paneer, vegetables, lentils, and seasonal fruits.
- Goals: generate personalized nutrition plans, calorie analysis, healthy meal suggestions, and family diet recommendations.
"""


@app.get('/')
def index():
    return render_template('index.html', agent_instructions=AGENT_INSTRUCTIONS)


@app.post('/api/chat')
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get('message', '')
    profile = data.get('profile', {})

    if not message:
        return jsonify({'response': 'Please share your nutrition goal or meal preference.'})

    try:
        response_text = generate_agent_response(message, profile)
    except Exception as exc:
        response_text = f"I couldn't reach the AI service right now. {exc}"

    return jsonify({'response': response_text})


@app.get('/api/health')
def health():
    return jsonify({'status': 'ok', 'agent': 'Nutrition Agent'})


def generate_agent_response(message, profile):
    goal = profile.get('goal', 'general wellness')
    activity = profile.get('activity', 'moderate')
    family = profile.get('familyMembers', 1)
    message_lower = (message or '').lower()
    needs_detailed_plan = any(keyword in message_lower for keyword in ['detailed', 'diet plan', 'meal plan', '1-day', 'day plan', 'full day'])
    wants_calories = any(keyword in message_lower for keyword in ['calorie', 'calories', 'kcal'])
    wants_swaps = any(keyword in message_lower for keyword in ['swap', 'swaps', 'substitute'])

    api_key = os.getenv('IBM_API_KEY')
    project_id = os.getenv('IBM_PROJECT_ID')
    model_id = os.getenv('IBM_MODEL_ID', 'ibm/granite-3-2b-instruct')

    if api_key and project_id:
        prompt = (
            f"You are a warm nutrition coach. Help with {goal} and activity {activity}. "
            f"The household size is {family}. "
            f"{'Provide a detailed 1-day diet plan with Breakfast, Lunch, Dinner, Snack, hydration, and meal swap ideas.' if needs_detailed_plan else 'Provide a practical nutrition answer in 120-180 words.'} "
            f"Prefer Indian food choices and mention portion awareness. User request: {message}"
        )
        payload = {
            'input': prompt,
            'model_id': model_id,
            'parameters': {
                'decoding_method': 'greedy',
                'max_new_tokens': 220,
                'temperature': 0.7
            },
            'project_id': project_id,
        }
        try:
            response = requests.post(
                'https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                },
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            return extract_text_from_watsonx(data)
        except Exception:
            pass

    if needs_detailed_plan:
        breakfast, lunch, dinner, snack1, snack2 = build_varied_meal_plan(goal, activity, family)
        plan_parts = [
            f"Detailed 1-day diet plan for {goal}:",
            f"- Breakfast: {breakfast}",
            f"- Mid-morning Snack: {snack1}",
            f"- Lunch: {lunch}",
            f"- Evening Snack: {snack2}",
            f"- Dinner: {dinner}",
            f"- Hydration: 2.5-3 liters of water and a 15-minute walk after dinner.",
        ]
        if wants_calories:
            calorie_target = estimate_calories(goal, activity, family)
            plan_parts.append(f"- Calories: about {calorie_target} kcal for this plan.")
        if wants_swaps:
            plan_parts.append("- Meal swaps: use upma instead of poha, tofu instead of paneer, or millet roti instead of regular chapati.")
        plan_parts.append(f"- Portion awareness: keep the plate colorful and balanced for a household of {family}.")
        return "\n".join(plan_parts)

    return (
        f"I can help with {goal} and activity level {activity}. "
        f"For a household of {family}, I recommend a balanced Indian-style plan with protein, fiber, and hydration. "
        f"Try a meal pattern with dal, brown rice or chapati, vegetables, yogurt, and a fruit serving. "
        f"Your message was: {message}"
    )


def build_varied_meal_plan(goal, activity, family):
    goal_key = (goal or '').lower()
    activity_key = (activity or '').lower()

    if 'weight' in goal_key:
        breakfast = 'Spinach omelette with 2 slices whole-grain toast and a kiwi'
        lunch = 'Moong dal, cucumber salad, and a small bowl of jeera rice'
        dinner = 'Grilled fish or tofu tikka with roasted vegetables and millet roti'
        snack1 = 'Roasted chana with a glass of buttermilk'
        snack2 = 'A small bowl of berries and a few almonds'
    elif 'muscle' in goal_key:
        breakfast = 'Egg bhurji with oats, banana, and a spoon of peanut butter'
        lunch = 'Chicken or chickpea pulao with raita and mixed greens'
        dinner = 'Paneer curry with brown rice and sautéed green beans'
        snack1 = 'Sprouts chaat with lemon and roasted peanuts'
        snack2 = 'Yogurt with walnuts and dates'
    else:
        breakfast = 'Vegetable poha with a boiled egg and papaya slices'
        lunch = 'Dal khichdi with curd and a side of stir-fried spinach'
        dinner = 'Mixed veg curry with 2 chapatis and a bowl of yogurt'
        snack1 = 'Cucumber slices with hummus or chaat masala'
        snack2 = 'A banana with a handful of sunflower seeds'

    if activity_key == 'active':
        lunch = lunch.replace('small bowl of jeera rice', '1 bowl of jeera rice') if 'weight' in goal_key else lunch
        dinner = dinner.replace('2 chapatis', '3 chapatis') if 'maintenance' in goal_key or 'general' in goal_key else dinner
    elif activity_key == 'light':
        lunch = lunch.replace('jeera rice', 'quinoa') if 'weight' in goal_key else lunch
        dinner = dinner.replace('millet roti', '1 multigrain chapati') if 'weight' in goal_key else dinner

    if family > 4:
        snack2 = 'A tray of sliced fruit with yogurt dip for the family'

    return breakfast, lunch, dinner, snack1, snack2


def estimate_calories(goal, activity, family):
    base = 1600
    if 'weight' in (goal or '').lower():
        base = 1700
    elif 'muscle' in (goal or '').lower():
        base = 2200
    else:
        base = 1900

    if (activity or '').lower() == 'active':
        base += 200
    elif (activity or '').lower() == 'light':
        base -= 150

    if family > 3:
        base += 150

    return base


def extract_text_from_watsonx(data):
    if isinstance(data, dict):
        if 'results' in data and data['results']:
            first = data['results'][0]
            if isinstance(first, dict):
                if 'generated_text' in first:
                    return first['generated_text']
                if 'text' in first:
                    return first['text']
        if 'generated_text' in data:
            return data['generated_text']
    return str(data)


if __name__ == '__main__':
    app.run(
        debug=True,
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000))
    )
