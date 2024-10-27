# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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
