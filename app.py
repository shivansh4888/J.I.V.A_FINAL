from flask import Flask, render_template, request, send_file
import os
import re
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from io import BytesIO
from xhtml2pdf import pisa

app = Flask(__name__)

# Initialize Groq API Key
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("❌ Groq API Key is missing! Set it in your Render environment variables.")

# Groq AI Model Setup
llm_restro = ChatGroq(model="mixtral-8x7b-32768", temperature=0.7, groq_api_key=api_key)

# Function to calculate BMI
def calculate_bmi(weight, height):
    try:
        weight = float(weight)
        height = float(height)
        return round(weight / (height ** 2), 2)  # BMI Formula
    except ValueError:
        return None

# Function to categorize BMI
def bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight 🥺 – Time to bulk up!"
    elif 18.5 <= bmi < 24.9:
        return "Normal weight ✅ – Perfect balance!"
    elif 25 <= bmi < 29.9:
        return "Overweight 😅 – Let's shed a few!"
    else:
        return "Obese 😭 – Let's fix this ASAP!"

# Define Prompt for AI
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

    Here’s your customized plan:

    💖 **Daily Routine:**  
    - [Give 3-5 fun and sassy routine suggestions]  

    🍳 **Breakfast:**  
    - [List 3-4 delicious but healthy breakfast options]  

    🍽 **Dinner:**  
    - [Suggest 3-4 tasty yet balanced dinner ideas]  

    🏋️‍♀️ **Workout Plan:**  
    - [List 3-4 exercises for your fitness goals]
    """
)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.form

        # Extract Inputs
        age = data.get("age", "").strip()
        gender = data.get("gender", "").strip()
        weight = data.get("weight", "").strip()
        height = data.get("height", "").strip()
        disease = data.get("disease", "").strip()
        veg_or_nonveg = data.get("veg", "").strip()
        allergic = data.get("allergics", "").strip()
        food_type = data.get("foodtype", "").strip()

        # Validate Inputs
        if not all([age, gender, weight, height, disease, veg_or_nonveg, allergic, food_type]):
            return render_template("error.html", message="⚠️ Missing required fields!"), 400

        # Calculate BMI
        bmi = calculate_bmi(weight, height)
        if bmi is None:
            return render_template("error.html", message="⚠️ Invalid weight or height format!"), 400

        bmi_status = bmi_category(bmi)

        # Prepare Input for AI
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

        # Get AI Response
        chain = LLMChain(llm=llm_restro, prompt=prompt_template_resto)
        response = chain.run(input_data)

        # Extract AI Recommendations
        daily_routine = re.findall(r"💖\s*\*\*Daily Routine:\*\*\s*(.*?)(?=\n🍳|\Z)", response, re.DOTALL)
        breakfast_items = re.findall(r"🍳\s*\*\*Breakfast:\*\*\s*(.*?)(?=\n🍽|\Z)", response, re.DOTALL)
        dinner_items = re.findall(r"🍽\s*\*\*Dinner:\*\*\s*(.*?)(?=\n🏋️‍♀️|\Z)", response, re.DOTALL)
        workout_plans = re.findall(r"🏋️‍♀️\s*\*\*Workout Plan:\*\*\s*(.*?)(?=\Z)", response, re.DOTALL)

        # Render Result Page
        return render_template(
            "result.html",
            bmi=bmi,
            bmi_status=bmi_status,
            daily_routine=daily_routine[0].strip().split('\n') if daily_routine else ["⚠ No routine suggestions!"],
            breakfast_items=breakfast_items[0].strip().split('\n') if breakfast_items else ["⚠ No breakfast ideas!"],
            dinner_items=dinner_items[0].strip().split('\n') if dinner_items else ["⚠ No dinner ideas!"],
            workout_plans=workout_plans[0].strip().split('\n') if workout_plans else ["⚠ No workouts suggested!"]
        )

    except Exception as e:
        print("❌ Error:", e)
        return render_template("error.html", message=f"⚠️ Something went wrong: {str(e)}"), 500

@app.route('/download')
def download_pdf():
    try:
        # Get data from request
        bmi = request.args.get("bmi", "")
        bmi_status = request.args.get("bmi_status", "")
        daily_routine = request.args.getlist("daily_routine")
        breakfast_items = request.args.getlist("breakfast_items")
        dinner_items = request.args.getlist("dinner_items")
        workout_plans = request.args.getlist("workout_plans")

        # Render HTML to PDF
        pdf_html = render_template(
            "pdf_template.html",
            bmi=bmi,
            bmi_status=bmi_status,
            daily_routine=daily_routine,
            breakfast_items=breakfast_items,
            dinner_items=dinner_items,
            workout_plans=workout_plans
        )

        pdf_bytes = BytesIO()
        pisa.CreatePDF(pdf_html, dest=pdf_bytes)
        pdf_bytes.seek(0)

        return send_file(pdf_bytes, as_attachment=True, download_name="Diet_Workout_Recommendations.pdf", mimetype="application/pdf")

    except Exception as e:
        print("❌ PDF Error:", e)
        return render_template("error.html", message="⚠️ Failed to generate PDF!"), 500

# Run Flask App
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
