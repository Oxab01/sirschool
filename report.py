# report.py
import os
from fpdf import FPDF

def generate_report(username, test_name, questions, answers):
    """Generate a PDF report for the student's test submission."""
    report_folder = "reports"
    os.makedirs(report_folder, exist_ok=True)
    report_filename = f"report_{username}_{test_name}.pdf"
    report_path = os.path.join(report_folder, report_filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Report for {username}", 0, 1, "C")
    pdf.cell(0, 10, f"Test: {test_name}", 0, 1, "C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    for question in questions:
        pdf.cell(0, 10, f"Q: {question.text}", 0, 1)
        user_answer = answers.get(f"question_{question.id}", "Not Answered")
        pdf.cell(0, 10, f"Your Answer: {user_answer}", 0, 1)
        pdf.ln(5)

    pdf.output(report_path)
    return report_filename
