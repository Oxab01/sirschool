# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
import fitz  # PyMuPDF for PDF extraction
from report import generate_report  # Import the report generation function

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)  # Initialize SQLAlchemy

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'admin' or 'student'

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    questions = db.relationship("Question", back_populates="test")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    options = db.Column(db.String(500), nullable=False)  # Store options as semicolon-separated
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    test = db.relationship("Test", back_populates="questions")

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    answer_data = db.Column(db.Text, nullable=False)  # Store JSON-like structure
    report_path = db.Column(db.String(200), nullable=True)  # Path to generated report

    # Relationships to access related user and test details
    user = db.relationship("User", backref="responses")
    test = db.relationship("Test", backref="responses")

    # New relationship to access test details
    test = db.relationship("Test", backref="responses")

def parse_pdf(file_path):
    """Parse questions and options from the PDF file."""
    questions = []
    with fitz.open(file_path) as pdf:
        text = ""
        for page in pdf:
            text += page.get_text()  # Extract text from each page

    # Regular expressions to detect questions and options
    import re
    question_pattern = re.compile(r"^\d+\.\s+(.+)")
    option_pattern = re.compile(r"^\((a|b|c|d)\)\s+(.+)")

    lines = text.splitlines()
    current_question = None
    options = []
    for line in lines:
        question_match = question_pattern.match(line)
        option_match = option_pattern.match(line)

        if question_match:
            if current_question:
                questions.append({
                    "question": current_question,
                    "options": options
                })
            current_question = question_match.group(1).strip()
            options = []
        elif option_match:
            options.append(f"{option_match.group(1)}. {option_match.group(2).strip()}")

    if current_question:
        questions.append({
            "question": current_question,
            "options": options
        })

    return questions

@app.route('/')
def select_role():
    return render_template('select_role.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password, role=role).first()
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials! Please try again.')
    return render_template('login.html', role=role)

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' in session and session['role'] == 'admin':
        tests = Test.query.all()
        responses = Response.query.all()
        return render_template('admin_dashboard.html', tests=tests, responses=responses)
    return redirect(url_for('login', role='admin'))

@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' in session and session['role'] == 'student':
        tests = Test.query.all()
        responses = Response.query.filter_by(user_id=session['user_id']).all()
        return render_template('dashboard.html', tests=tests, responses=responses)
    return redirect(url_for('login', role='student'))

@app.route('/upload_test', methods=['POST'])
def upload_test():
    if 'user_id' in session and session['role'] == 'admin':
        file = request.files['file']
        test_name = request.form['test_name']
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Parse the PDF to extract questions and options
            parsed_questions = parse_pdf(file_path)

            # Create a new test entry
            new_test = Test(name=test_name, file_path=file_path)
            db.session.add(new_test)
            db.session.commit()

            # Save each question to the database
            for item in parsed_questions:
                question_text = item['question']
                options_text = ';'.join(item['options'])  # Store options as a semicolon-separated string
                question = Question(text=question_text, options=options_text, test_id=new_test.id)
                db.session.add(question)
            db.session.commit()

            flash('Test uploaded and questions extracted successfully.')
            return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login', role='admin'))

@app.route('/test/<int:test_id>')
def view_test(test_id):
    if 'user_id' in session and session['role'] == 'student':
        test = Test.query.get(test_id)
        questions = Question.query.filter_by(test_id=test_id).all()
        return render_template('test.html', test=test, questions=questions)
    return redirect(url_for('login', role='student'))

@app.route('/submit_response/<int:test_id>', methods=['POST'])
def submit_response(test_id):
    if 'user_id' in session and session['role'] == 'student':
        answers = request.form.to_dict()
        user_id = session['user_id']
        
        response = Response(user_id=user_id, test_id=test_id, answer_data=str(answers))
        db.session.add(response)
        db.session.commit()

        # Generate the report after saving the response
        user = User.query.get(user_id)
        test = Test.query.get(test_id)
        questions = Question.query.filter_by(test_id=test_id).all()
        report_path = generate_report(user.username, test.name, questions, answers)
        response.report_path = report_path
        db.session.commit()

        flash('Response submitted successfully. Report generated.')
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login', role='student'))

@app.route('/download_report/<path:filename>')
def download_report(filename):
    return send_from_directory('reports', filename, as_attachment=True)

# Initialize the database and default users
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password='admin123', role='admin'))
    if not User.query.filter_by(username='student1').first():
        db.session.add(User(username='student1', password='student123', role='student'))
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
