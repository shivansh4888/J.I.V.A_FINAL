from flask import Flask, request, jsonify
import os
import re
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Initialize Flask App
app = Flask(__name__)

# Use Groq API Key from Environment Variable (Set in Render Dashboard)
api_key = os.getenv("GROQ_API_KEY")

# Check if API key exists
if not api_key:
    raise ValueError("❌ Groq API Key is missing! Set it in your Render environment variables.")

# Initialize Groq model
llm_restro = ChatGroq(model="mixtral-8x7b-32768", temperature=0.7, groq_api_key=api_key)

# Function to calculate BMI
def calculate_bmi(weight, height):
    try:
        weight = float(weight)
        height = float(height)
        bmi = round(weight / (height ** 2), 2)  # BMI Formula
        return bmi
    except ValueError:
        return None

# Function to categorize BMI
def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight 🥺 – Girl, we need to feed you!"
    elif 18.5 <= bmi < 24.9:
        return "Normal weight ✨ – Look at you! Just the right balance!"
    elif 25 <= bmi < 29.9:
        return "Overweight 😅 – Alright, time to move that cute body!"
    else:
        return "Obese 😭 – Sweetie, we need to fix this ASAP!"

# Define Prompt Template
prompt_template_resto = PromptTemplate(
    input_variables=["age", "weight", "height", "gender", "veg_or_nonveg", "disease", "allergics", "foodtype", "bmi", "bmi_category"],
    template="""
    Hey! Based on your details:
    - Age: {age}
    - Weight: {weight}
    - Height: {height}
    - Gender: {gender}
    - Dietary Preference: {veg_or_nonveg}
    - Medical Condition: {disease}
    - Allergies: {allergics}
    - Food Type: {foodtype}
    - BMI: {bmi} ({bmi_category})

    Here’s my fabulous advice for you! 

    💖 **Daily Routine:**  
    - [Give 3-5 routine suggestions with a fun and sassy touch]  

    🍳 **Breakfast:**  
    - [List 3-4 yummy but healthy breakfast items]  

    🍽 **Dinner:**  
    - [Suggest 3-4 tasty yet balanced dinner ideas]  

    🏋️‍♀️ **Workout Plan:**  
    - [List 3-4 exercises to keep that body in shape]
    """
)

@app.route('/')
def home():
    return jsonify({"message": "Welcome to the BMI-based diet and workout recommendation API!"})

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.json

        # Extract fields from request
        age = data.get("age", "").strip()
        gender = data.get("gender", "").strip()
        weight = data.get("weight", "").strip()
        height = data.get("height", "").strip()
        disease = data.get("disease", "").strip()
        veg_or_nonveg = data.get("veg_or_nonveg", "").strip()
        allergic = data.get("allergics", "").strip()
        food_type = data.get("foodtype", "").strip()

        # Validate inputs
        if not all([age, gender, weight, height, disease, veg_or_nonveg, allergic, food_type]):
            return jsonify({"error": "⚠️ Missing required fields!"}), 400

        # Calculate BMI
        bmi = calculate_bmi(weight, height)
        if bmi is None:
            return jsonify({"error": "⚠️ Invalid weight or height format!"}), 400

        bmi_status = bmi_category(bmi)

        # Prepare input for AI
        input_data = {
            "age": age,
            "weight": weight,
            "height": height,
            "bmi": bmi,
            "bmi_category": bmi_status,
            "gender": gender,
            "veg_or_nonveg": veg_or_nonveg,
            "disease": disease,
            "allergics": allergic,
            "foodtype": food_type
        }

        # Debugging
        print("📡 Sending Data to Groq API:", input_data)

        # Get response from AI model
        chain = LLMChain(llm=llm_restro, prompt=prompt_template_resto)
        response = chain.run(input_data)

        # Debugging AI response
        print("🤖 AI Response:", response)

        if not response.strip():
            return jsonify({"error": "⚠️ AI response was empty. Please try again!"}), 500

        # Extract recommendations using regex
        daily_routine = re.findall(r"💖\s*\*\*Daily Routine:\*\*\s*(.*?)(?=\n🍳|\Z)", response, re.DOTALL)
        breakfast_items = re.findall(r"🍳\s*\*\*Breakfast:\*\*\s*(.*?)(?=\n🍽|\Z)", response, re.DOTALL)
        dinner_items = re.findall(r"🍽\s*\*\*Dinner:\*\*\s*(.*?)(?=\n🏋️‍♀️|\Z)", response, re.DOTALL)
        workout_plans = re.findall(r"🏋️‍♀️\s*\*\*Workout Plan:\*\*\s*(.*?)(?=\Z)", response, re.DOTALL)

        # Format the response
        result = {
            "bmi": bmi,
            "bmi_status": bmi_status,
            "daily_routine": daily_routine[0].strip().split('\n') if daily_routine else ["⚠ No routine suggestions!"],
            "breakfast_items": breakfast_items[0].strip().split('\n') if breakfast_items else ["⚠ No breakfast ideas!"],
            "dinner_items": dinner_items[0].strip().split('\n') if dinner_items else ["⚠ No dinner ideas!"],
            "workout_plans": workout_plans[0].strip().split('\n') if workout_plans else ["⚠ No workouts suggested!"]
        }

        return jsonify(result)

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"error": f"⚠️ Something went wrong: {str(e)}"}), 500

# Run API
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
