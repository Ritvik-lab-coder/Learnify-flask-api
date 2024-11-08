from flask import Flask, request, jsonify
from groq import Groq
import requests
import PyPDF2
import os
from io import BytesIO
from PyPDF2 import PdfReader
import requests
import re
import json

app = Flask(__name__)
client = Groq()

# GRADE API 
@app.route('/grade', methods=['POST'])
def grade():
    data = request.get_json()

    # Check if required fields are present
    if not data or 'pdf_url' not in data or 'criteria' not in data:
        return jsonify({"error": "Missing 'pdf_url' or 'criteria' in the request."}), 400
    pdf_url = data['pdf_url']
    print(pdf_url)
    criteria = data['criteria']

    # Download the PDF from the given URL

    try:
        # Download the PDF content
        response = requests.get(pdf_url)
        response.raise_for_status()  # Ensure the request was successful
        
        # Load the PDF content into memory using BytesIO
        file = BytesIO(response.content)
        
        # Use PyPDF2 to read and extract text from the PDF
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""  # Extract text from each page
        text
    except requests.exceptions.RequestException as e:
        return f"Failed to download PDF: {str(e)}"
    except Exception as e:
        return f"Failed to extract text from PDF: {str(e)}"

    # Create a prompt with the criteria
    criteria_list = ", ".join(criteria)
    prompt = f"""
    You are a grading assistant. Grade the assignment based on the following criteria: {criteria_list}.
    Provide a grade between 1 and 10 for the overall quality of the PDF content, followed by one line descriptions for each criterion.

    Output the result in the following JSON format
    {{
        "grade": (1-10),
        "{criteria[0]}": "Description for criterion {criteria[0]}",
        "{criteria[1]}": "Description for criterion {criteria[1]}",
        "{criteria[2]}": "Description for criterion {criteria[2]}"
    }}

    PDF text:
    {text}
    """

    # Create a completion request to grade the assignment
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
        stop=None,
    )
    message_content = completion.choices[0].message.content    
    # If the content is in JSON format, parse it
    try:
        json_response = json.loads(message_content)  # Parse the string into a JSON object
        return jsonify(json_response)  # Return the JSON response
    except json.JSONDecodeError:
        return jsonify({"error": "Response is not valid JSON."}), 500

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""  # Handle potential None values
    return text

@app.route('/quiz', methods=['POST'])
def quiz():
    data = request.get_json()

    # Check if required fields are present
    if not data or 'description' not in data:
        return jsonify({"error": "Missing 'description' in the request."}), 400

    text = data['description']
    # Create a prompt with the criteria
    prompt = f"""
    Generate five multiple-choice questions based on the provided topics mentioned in following desciption {text}. For each question, provide exactly four options labeled "a", "b", "c", and "d". The answer should be one of the four options: "a", "b", "c", or "d". 

    Output the result in valid JSON format with double quotes around all keys and values. The JSON format should be an array of question objects, as follows:

    quiz:[
    {{
        "question": "Question text",
        "options": {{
            "a": "Option A text", 
            "b": "Option B text", 
            "c": "Option C text", 
            "d": "Option D text"
        }},
        "answer": "Correct answer (a, b, c, or d)"
    }},
    {{
        "question": "Question text 2",
        "options": {{
            "a": "Option A text 2", 
            "b": "Option B text 2", 
            "c": "Option C text 2", 
            "d": "Option D text 2"
        }},
        "answer": "Correct answer 2 (a, b, c, or d)"
    }},
    ...
    ]
    """

    # Create a completion request to grade the assignment
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
        stop=None,
    )
    message_content = completion.choices[0].message.content
        
        # If the content is in JSON format, parse it
    try:
        json_response = json.loads(message_content)  # Parse the string into a JSON object
        return jsonify(json_response)  # Return the JSON response
    except json.JSONDecodeError:
        return jsonify({"error": "Response is not valid JSON."}), 500

@app.route('/quiz/feedback', methods=['POST'])
def quiz_feedback():
    data = request.get_json()

    # Check if required fields are present
    if not data or 'questions' not in data:
        return jsonify({"error": "Missing required fields in the request."}), 400

    questions = data['questions']  # Expecting a list of question objects
    feedback_list = []  # To store feedback for each question

    for item in questions:
        question = item.get('question')
        options = item.get('options')
        correct_answer = item.get('answer')
        user_answer = item.get('user_answer')

        # Validate each question item
        if not question or not options or correct_answer is None or user_answer is None:
            return jsonify({"error": "Missing fields in one or more question items."}), 400

        # Create a prompt for generating AI feedback with JSON template
        prompt = f"""
        You are an AI grading assistant. Provide feedback based on the following question, options, correct answer, and user's answer.

        Question: {question}
        Options: {options}
        Correct Answer: {correct_answer}
        User's Answer: {user_answer}

        Generate the feedback in valid JSON format, structured as follows:

        {{
            "feedback": "Your feedback message here."
        }}

        only give feedback no need and make it polite.
        Provide constructive feedback on the user's answer, indicating whether it was correct or not and offering tips for improvement.
        """

        # Create a completion request to generate feedback
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_tokens=150,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None
        )
        message_content = completion.choices[0].message.content

        # If the content is in JSON format, parse it
        try:
            feedback_response = json.loads(message_content.strip())  # Parse the string into a JSON object
            feedback_list.append(feedback_response)  # Add feedback to the list
        except json.JSONDecodeError:
            return jsonify({"error": "Response is not valid JSON."}), 500

    return jsonify({"feedback": feedback_list})  # Return the list of feedback responses

@app.route('/roadmap', methods=['POST'])
def roadmap():
    data = request.get_json()

    # Check if required fields are present
    if not data or 'description' not in data:
        return jsonify({"error": "Missing 'description' in the request."}), 400

    text = data['description']
    # Create a prompt with the criteria
    prompt = f"""
You are a tutor. Generate a roadmap for a course in a proper structure. 
Following is the course description: {text} 
Output the result in valid JSON format with double quotes around all keys and values. The JSON format should be an array named "roadmap" consisting of 10 objects, where each object contains a "title" and a "description."

Example format (keep the name of keys the same and title as "roadmap"; don't change anything):
{{
  "roadmap": [
    {{
      "title": "Introduction to the Course",
      "description": "Overview of the course objectives and structure."
    }},
    ...
  ]
}}

Return a valid JSON output without any other lines of text.
"""



    # Create a completion request to grade the assignment
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        response_format={"type": "json_object"},
        stop=None,
    )
    message_content = completion.choices[0].message.content
        
        # If the content is in JSON format, parse it
    try:
        json_response = json.loads(message_content)  # Parse the string into a JSON object
        return jsonify(json_response)  # Return the JSON response
    except json.JSONDecodeError:
        return jsonify({"error": "Response is not valid JSON."}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)