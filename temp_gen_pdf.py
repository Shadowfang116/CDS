from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
c = canvas.Canvas('test_plot_12.pdf', pagesize=letter)
c.drawString(100, 700, 'Plot No 12')
c.save()
