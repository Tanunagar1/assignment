from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import os
import sqlite3
from PyPDF2 import PdfReader
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key in production
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_pdf(file_path):
    text = ""
    with open(file_path, "rb") as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""

    # Divide text into quadrants
    num_quadrants = 4
    chunk_size = len(text) // num_quadrants
    quadrants = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    # Save each quadrant to the database
    save_quadrants_to_db(quadrants)
    return quadrants

def save_quadrants_to_db(quadrants):
    conn = sqlite3.connect('quadrants.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quadrants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT
        )
    ''')
    cursor.executemany('INSERT INTO quadrants (content) VALUES (?)', [(q,) for q in quadrants])
    conn.commit()
    conn.close()

def get_chatmodel_response(question):
    retries = 5
    for attempt in range(retries):
        try:
            # Fetch all quadrant content from the database
            conn = sqlite3.connect('quadrants.db')
            cursor = conn.cursor()
            cursor.execute('SELECT content FROM quadrants')
            rows = cursor.fetchall()
            conn.close()

            # Debug print
            print(f"Fetched rows from database: {rows}")

            # Find the most relevant quadrant
            best_match = ""
            best_count = 0
            for quadrant in rows:
                # Count the number of keyword matches in the quadrant
                text = quadrant[0]
                keywords = re.findall(r'\b\w+\b', question.lower())
                match_count = sum(text.lower().count(keyword) for keyword in keywords)

                if match_count > best_count:
                    best_count = match_count
                    best_match = text

            # Return the best matching quadrant content
            if best_count > 0:
                return best_match
            else:
                return "Sorry, I couldn't find relevant information."

        except Exception as e:
            print(f"Error: {e}")  # Debug print
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return "Sorry, I'm unavailable right now. Please try again later."

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['pdf']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Process PDF and save quadrants to the database
            process_pdf(file_path)

            return redirect(url_for('query'))

    return render_template('upload.html')

@app.route('/query', methods=['GET', 'POST'])
def query():
    if request.method == 'POST':
        question = request.form['question']
        response = get_chatmodel_response(question)
        return render_template('query.html', response=response)

    return render_template('query.html')

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
