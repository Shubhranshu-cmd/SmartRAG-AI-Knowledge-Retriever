from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph
)

def export_pdf(text, filename):
    doc = SimpleDocTemplate(
        filename
    )
    doc.build(
        [Paragraph(text)]
    )