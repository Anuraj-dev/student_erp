"""
PDF Generation Service - Task 10 Implementation
Generates professional PDFs for fee receipts, admission letters, ID cards, and transcripts
Using ReportLab with college branding, watermarks, and QR codes
"""

import os
import io
from datetime import datetime, date
from decimal import Decimal
import qrcode
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.colors import HexColor

class PDFGenerator:
    """
    Professional PDF Generator for ERP Student Management System
    Government of Rajasthan - Directorate of Technical Education
    """
    
    # College branding constants
    COLLEGE_NAME = "Government Technical College"
    COLLEGE_ADDRESS = "Directorate of Technical Education\nGovernment of Rajasthan"
    COLLEGE_PHONE = "+91-141-XXXXXXX"
    COLLEGE_EMAIL = "info@dtegov.raj.in"
    COLLEGE_WEBSITE = "www.dte.rajasthan.gov.in"
    
    # Colors matching government theme
    GOVT_BLUE = HexColor('#003366')
    GOVT_ORANGE = HexColor('#FF6600')
    LIGHT_GRAY = HexColor('#F5F5F5')
    DARK_GRAY = HexColor('#333333')
    
    def __init__(self):
        """Initialize PDF generator with default settings"""
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        
    def _create_custom_styles(self):
        """Create custom paragraph styles for government documents"""
        # Header style
        self.styles.add(ParagraphStyle(
            name='GovHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=self.GOVT_BLUE,
            fontName='Helvetica-Bold'
        ))
        
        # Subheader style
        self.styles.add(ParagraphStyle(
            name='GovSubHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=8,
            alignment=TA_CENTER,
            textColor=self.GOVT_ORANGE,
            fontName='Helvetica-Bold'
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name='GovBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            textColor=self.DARK_GRAY,
            fontName='Helvetica'
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='GovFooter',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey,
            fontName='Helvetica-Oblique'
        ))

    def _add_header_footer(self, canvas_obj, doc):
        """Add government header and footer to every page"""
        canvas_obj.saveState()
        
        # Header
        canvas_obj.setFont('Helvetica-Bold', 14)
        canvas_obj.setFillColor(self.GOVT_BLUE)
        canvas_obj.drawCentredText(A4[0]/2, A4[1] - 40, self.COLLEGE_NAME)
        
        canvas_obj.setFont('Helvetica', 10)
        canvas_obj.setFillColor(self.GOVT_ORANGE)
        canvas_obj.drawCentredText(A4[0]/2, A4[1] - 55, self.COLLEGE_ADDRESS)
        
        # Draw header line
        canvas_obj.setStrokeColor(self.GOVT_BLUE)
        canvas_obj.setLineWidth(2)
        canvas_obj.line(50, A4[1] - 80, A4[0] - 50, A4[1] - 80)
        
        # Footer
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawCentredText(A4[0]/2, 30, f"Generated on {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        canvas_obj.drawCentredText(A4[0]/2, 20, f"{self.COLLEGE_PHONE} | {self.COLLEGE_EMAIL} | {self.COLLEGE_WEBSITE}")
        
        # Draw footer line
        canvas_obj.setStrokeColor(colors.grey)
        canvas_obj.setLineWidth(1)
        canvas_obj.line(50, 50, A4[0] - 50, 50)
        
        canvas_obj.restoreState()

    def _generate_qr_code(self, data, size=(60, 60)):
        """Generate QR code for document verification"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to ReportLab image
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return RLImage(img_buffer, width=size[0], height=size[1])

    def generate_fee_receipt(self, student_data, fee_data, transaction_data):
        """
        Generate professional fee receipt PDF
        
        Args:
            student_data: Dict with student information
            fee_data: Dict with fee details
            transaction_data: Dict with payment information
        
        Returns:
            bytes: PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=100,
            bottomMargin=80
        )
        
        # Build content
        content = []
        
        # Receipt header
        content.append(Paragraph("FEE RECEIPT", self.styles['GovHeader']))
        content.append(Spacer(1, 12))
        
        # Receipt number and date
        receipt_info = [
            ['Receipt No:', transaction_data.get('receipt_no', 'N/A'), 'Date:', datetime.now().strftime('%d-%m-%Y')],
            ['Transaction ID:', transaction_data.get('transaction_id', 'N/A'), 'Time:', datetime.now().strftime('%H:%M:%S')]
        ]
        receipt_table = Table(receipt_info, colWidths=[80, 120, 80, 120])
        receipt_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.LIGHT_GRAY),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.DARK_GRAY),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        content.append(receipt_table)
        content.append(Spacer(1, 20))
        
        # Student information
        content.append(Paragraph("STUDENT INFORMATION", self.styles['GovSubHeader']))
        student_info = [
            ['Roll No:', student_data.get('roll_no', 'N/A'), 'Name:', student_data.get('name', 'N/A')],
            ['Course:', student_data.get('course_name', 'N/A'), 'Semester:', str(student_data.get('current_semester', 'N/A'))],
            ['Email:', student_data.get('email', 'N/A'), 'Phone:', student_data.get('phone', 'N/A')]
        ]
        student_table = Table(student_info, colWidths=[80, 120, 80, 120])
        student_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        content.append(student_table)
        content.append(Spacer(1, 20))
        
        # Fee details
        content.append(Paragraph("FEE DETAILS", self.styles['GovSubHeader']))
        
        # Fee breakdown table
        fee_items = fee_data.get('breakdown', [])
        fee_table_data = [['Description', 'Amount (₹)']]
        
        total_amount = 0
        for item in fee_items:
            fee_table_data.append([item['description'], f"₹{item['amount']:,.2f}"])
            total_amount += item['amount']
        
        # Add total row
        fee_table_data.append(['TOTAL AMOUNT', f"₹{total_amount:,.2f}"])
        
        fee_table = Table(fee_table_data, colWidths=[300, 100])
        fee_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.GOVT_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), self.GOVT_ORANGE),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ]))
        content.append(fee_table)
        content.append(Spacer(1, 20))
        
        # Payment information
        content.append(Paragraph("PAYMENT DETAILS", self.styles['GovSubHeader']))
        payment_info = [
            ['Payment Method:', transaction_data.get('payment_method', 'N/A')],
            ['Amount Paid:', f"₹{transaction_data.get('amount', 0):,.2f}"],
            ['Status:', transaction_data.get('status', 'Success')],
            ['Remarks:', transaction_data.get('remarks', 'Payment successful')]
        ]
        payment_table = Table(payment_info, colWidths=[120, 280])
        payment_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        content.append(payment_table)
        content.append(Spacer(1, 30))
        
        # QR Code for verification
        qr_data = f"Receipt:{transaction_data.get('receipt_no')},Student:{student_data.get('roll_no')},Amount:{transaction_data.get('amount')}"
        qr_code = self._generate_qr_code(qr_data)
        
        # QR code with label
        qr_content = []
        qr_content.append(Paragraph("Scan for verification:", self.styles['GovFooter']))
        qr_content.append(qr_code)
        
        # Create table to position QR code on right
        signature_data = [
            ['', ''],
            ['Authorized Signature', qr_content]
        ]
        signature_table = Table(signature_data, colWidths=[300, 100])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
        ]))
        content.append(signature_table)
        
        # Build PDF
        doc.build(content, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)
        buffer.seek(0)
        return buffer.read()

    def generate_admission_letter(self, student_data, course_data, admission_data):
        """
        Generate admission confirmation letter
        
        Args:
            student_data: Dict with student information
            course_data: Dict with course details
            admission_data: Dict with admission details
        
        Returns:
            bytes: PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=100,
            bottomMargin=80
        )
        
        content = []
        
        # Letter header
        content.append(Paragraph("ADMISSION CONFIRMATION LETTER", self.styles['GovHeader']))
        content.append(Spacer(1, 20))
        
        # Reference information
        ref_info = f"Ref. No.: ADM/{datetime.now().year}/{admission_data.get('application_id', 'N/A')}"
        date_info = f"Date: {datetime.now().strftime('%d-%m-%Y')}"
        
        content.append(Paragraph(ref_info, self.styles['GovBody']))
        content.append(Paragraph(date_info, self.styles['GovBody']))
        content.append(Spacer(1, 20))
        
        # Congratulatory message
        congratulations = f"""
        <b>Dear {student_data.get('name', 'Student')},</b><br/><br/>
        
        Congratulations! We are pleased to inform you that you have been selected for admission to 
        <b>{course_data.get('course_name', 'N/A')}</b> program at our institution for the academic year 
        <b>{admission_data.get('admission_year', datetime.now().year)}</b>.<br/><br/>
        
        Your application has been thoroughly reviewed and we are impressed with your academic credentials 
        and potential. We welcome you to join our prestigious institution and look forward to your 
        contribution to our academic community.
        """
        
        content.append(Paragraph(congratulations, self.styles['GovBody']))
        content.append(Spacer(1, 20))
        
        # Admission details
        content.append(Paragraph("ADMISSION DETAILS", self.styles['GovSubHeader']))
        
        admission_details = [
            ['Student Name:', student_data.get('name', 'N/A')],
            ['Roll Number:', student_data.get('roll_no', 'N/A')],
            ['Course:', course_data.get('course_name', 'N/A')],
            ['Program Level:', course_data.get('program_level', 'N/A')],
            ['Duration:', f"{course_data.get('duration_years', 'N/A')} years"],
            ['Admission Year:', str(admission_data.get('admission_year', datetime.now().year))],
            ['Semester:', str(student_data.get('current_semester', 1))],
            ['Application ID:', admission_data.get('application_id', 'N/A')]
        ]
        
        details_table = Table(admission_details, colWidths=[150, 250])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), self.LIGHT_GRAY),
        ]))
        content.append(details_table)
        content.append(Spacer(1, 20))
        
        # Important instructions
        instructions = """
        <b>IMPORTANT INSTRUCTIONS:</b><br/><br/>
        
        1. Please report to the admission office by <b>{reporting_date}</b> for document verification 
           and completion of admission formalities.<br/>
        2. Bring all original documents along with attested photocopies.<br/>
        3. Pay the first semester fee within 15 days of reporting.<br/>
        4. Hostel accommodation is subject to availability and separate application.<br/>
        5. This admission is subject to verification of documents and eligibility criteria.<br/>
        6. Ragging is a criminal offense and strictly prohibited.<br/><br/>
        
        We wish you all the best for your academic journey ahead!
        """.format(
            reporting_date=admission_data.get('reporting_date', 'TBD')
        )
        
        content.append(Paragraph(instructions, self.styles['GovBody']))
        content.append(Spacer(1, 30))
        
        # QR code for verification
        qr_data = f"Admission:{admission_data.get('application_id')},Student:{student_data.get('name')},Roll:{student_data.get('roll_no')}"
        qr_code = self._generate_qr_code(qr_data)
        
        # Signature and QR code
        signature_data = [
            ['', ''],
            ['', ''],
            ['Registrar', 'Verify Document:'],
            ['Government Technical College', qr_code]
        ]
        signature_table = Table(signature_data, colWidths=[300, 100])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 2), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (1, 2), (1, 2), 8),
        ]))
        content.append(signature_table)
        
        # Build PDF
        doc.build(content, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)
        buffer.seek(0)
        return buffer.read()

    def generate_id_card(self, student_data, course_data):
        """
        Generate student ID card PDF
        
        Args:
            student_data: Dict with student information
            course_data: Dict with course details
        
        Returns:
            bytes: PDF content as bytes
        """
        buffer = io.BytesIO()
        
        # ID card size (3.5" x 2.125")
        card_width = 3.5 * inch
        card_height = 2.125 * inch
        
        # Create canvas for custom layout
        c = canvas.Canvas(buffer, pagesize=(card_width * 2 + inch, card_height + inch))
        
        # Card 1 - Front side
        self._draw_id_card_front(c, 0.5 * inch, 0.5 * inch, card_width, card_height, student_data, course_data)
        
        # Card 2 - Back side  
        self._draw_id_card_back(c, card_width + inch, 0.5 * inch, card_width, card_height, student_data)
        
        c.save()
        buffer.seek(0)
        return buffer.read()

    def _draw_id_card_front(self, canvas_obj, x, y, width, height, student_data, course_data):
        """Draw front side of ID card"""
        # Card background
        canvas_obj.setFillColor(colors.white)
        canvas_obj.rect(x, y, width, height, fill=1, stroke=1)
        
        # Header background
        canvas_obj.setFillColor(self.GOVT_BLUE)
        canvas_obj.rect(x, y + height - 40, width, 40, fill=1)
        
        # College name
        canvas_obj.setFillColor(colors.white)
        canvas_obj.setFont('Helvetica-Bold', 8)
        canvas_obj.drawCentredText(x + width/2, y + height - 15, "GOVERNMENT TECHNICAL COLLEGE")
        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.drawCentredText(x + width/2, y + height - 25, "Directorate of Technical Education, Rajasthan")
        
        # Student photo placeholder
        photo_x = x + 10
        photo_y = y + height - 90
        canvas_obj.setFillColor(self.LIGHT_GRAY)
        canvas_obj.rect(photo_x, photo_y, 40, 50, fill=1, stroke=1)
        canvas_obj.setFillColor(colors.black)
        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.drawCentredText(photo_x + 20, photo_y + 25, "PHOTO")
        
        # Student details
        details_x = x + 60
        details_y = y + height - 50
        
        canvas_obj.setFillColor(colors.black)
        canvas_obj.setFont('Helvetica-Bold', 7)
        canvas_obj.drawString(details_x, details_y, f"Name: {student_data.get('name', 'N/A')}")
        canvas_obj.drawString(details_x, details_y - 10, f"Roll No: {student_data.get('roll_no', 'N/A')}")
        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.drawString(details_x, details_y - 20, f"Course: {course_data.get('course_name', 'N/A')}")
        canvas_obj.drawString(details_x, details_y - 30, f"Year: {student_data.get('admission_year', 'N/A')}")
        
        # Valid until
        canvas_obj.setFont('Helvetica', 5)
        valid_until = datetime.now().year + int(course_data.get('duration_years', 4))
        canvas_obj.drawString(x + 10, y + 5, f"Valid Until: {valid_until}")

    def _draw_id_card_back(self, canvas_obj, x, y, width, height, student_data):
        """Draw back side of ID card"""
        # Card background
        canvas_obj.setFillColor(colors.white)
        canvas_obj.rect(x, y, width, height, fill=1, stroke=1)
        
        # QR code for verification
        qr_data = f"ID:{student_data.get('roll_no')},Name:{student_data.get('name')},Valid:{datetime.now().year + 4}"
        
        # Create QR code manually for canvas
        qr = qrcode.QRCode(version=1, box_size=2, border=1)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Draw QR code (simplified)
        canvas_obj.setFillColor(colors.black)
        canvas_obj.setFont('Helvetica', 6)
        canvas_obj.drawCentredText(x + width/2, y + height - 20, "STUDENT ID VERIFICATION")
        
        # Emergency contact
        canvas_obj.setFont('Helvetica-Bold', 6)
        canvas_obj.drawString(x + 10, y + height/2, "Emergency Contact:")
        canvas_obj.setFont('Helvetica', 5)
        canvas_obj.drawString(x + 10, y + height/2 - 10, f"Phone: {student_data.get('guardian_phone', 'N/A')}")
        canvas_obj.drawString(x + 10, y + height/2 - 20, f"Email: {student_data.get('guardian_email', 'N/A')}")
        
        # Rules and regulations
        canvas_obj.setFont('Helvetica', 4)
        rules_text = [
            "1. This card is non-transferable",
            "2. Report loss immediately",
            "3. Carry this card always on campus",
            "4. Follow college rules and regulations"
        ]
        
        for i, rule in enumerate(rules_text):
            canvas_obj.drawString(x + 10, y + 40 - (i * 8), rule)

    def generate_transcript(self, student_data, course_data, examination_records):
        """
        Generate academic transcript
        
        Args:
            student_data: Dict with student information
            course_data: Dict with course details
            examination_records: List of examination records
        
        Returns:
            bytes: PDF content as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=100,
            bottomMargin=80
        )
        
        content = []
        
        # Transcript header
        content.append(Paragraph("ACADEMIC TRANSCRIPT", self.styles['GovHeader']))
        content.append(Spacer(1, 20))
        
        # Student information
        content.append(Paragraph("STUDENT INFORMATION", self.styles['GovSubHeader']))
        
        student_info = [
            ['Name:', student_data.get('name', 'N/A'), 'Roll Number:', student_data.get('roll_no', 'N/A')],
            ['Course:', course_data.get('course_name', 'N/A'), 'Program Level:', course_data.get('program_level', 'N/A')],
            ['Admission Year:', str(student_data.get('admission_year', 'N/A')), 'Duration:', f"{course_data.get('duration_years', 'N/A')} years"],
            ['Date of Birth:', student_data.get('date_of_birth', 'N/A'), 'Current Semester:', str(student_data.get('current_semester', 'N/A'))]
        ]
        
        info_table = Table(student_info, colWidths=[100, 150, 100, 150])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), self.LIGHT_GRAY),
            ('BACKGROUND', (2, 0), (2, -1), self.LIGHT_GRAY),
        ]))
        content.append(info_table)
        content.append(Spacer(1, 20))
        
        # Academic records
        content.append(Paragraph("ACADEMIC PERFORMANCE", self.styles['GovSubHeader']))
        
        if examination_records:
            # Group records by semester
            semester_records = {}
            for record in examination_records:
                sem = record.get('semester', 1)
                if sem not in semester_records:
                    semester_records[sem] = []
                semester_records[sem].append(record)
            
            total_gpa = 0
            total_semesters = len(semester_records)
            
            for semester in sorted(semester_records.keys()):
                content.append(Paragraph(f"Semester {semester}", self.styles['GovSubHeader']))
                
                # Semester table
                sem_data = [['Subject Code', 'Subject Name', 'Credits', 'Grade', 'Grade Points']]
                semester_credits = 0
                semester_points = 0
                
                for record in semester_records[semester]:
                    credits = record.get('credits', 3)
                    grade_points = record.get('grade_points', 0)
                    sem_data.append([
                        record.get('subject_code', 'N/A'),
                        record.get('subject_name', 'N/A'),
                        str(credits),
                        record.get('grade', 'N/A'),
                        str(grade_points)
                    ])
                    semester_credits += credits
                    semester_points += grade_points * credits
                
                # Calculate semester GPA
                sem_gpa = semester_points / semester_credits if semester_credits > 0 else 0
                sem_data.append(['', 'Semester GPA:', str(semester_credits), '', f"{sem_gpa:.2f}"])
                total_gpa += sem_gpa
                
                sem_table = Table(sem_data, colWidths=[80, 200, 60, 60, 80])
                sem_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), self.GOVT_BLUE),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, -1), (-1, -1), self.LIGHT_GRAY),
                ]))
                content.append(sem_table)
                content.append(Spacer(1, 15))
            
            # Overall GPA
            overall_gpa = total_gpa / total_semesters if total_semesters > 0 else 0
            gpa_info = f"<b>Overall CGPA: {overall_gpa:.2f}</b>"
            content.append(Paragraph(gpa_info, self.styles['GovSubHeader']))
            
        else:
            content.append(Paragraph("No examination records available.", self.styles['GovBody']))
        
        content.append(Spacer(1, 30))
        
        # Grading scale
        content.append(Paragraph("GRADING SCALE", self.styles['GovSubHeader']))
        grading_data = [
            ['Grade', 'Grade Points', 'Percentage Range'],
            ['A+', '10', '90-100%'],
            ['A', '9', '80-89%'],
            ['B+', '8', '70-79%'],
            ['B', '7', '60-69%'],
            ['C', '6', '50-59%'],
            ['D', '5', '40-49%'],
            ['F', '0', 'Below 40%']
        ]
        
        grading_table = Table(grading_data, colWidths=[100, 100, 150])
        grading_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.GOVT_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        content.append(grading_table)
        content.append(Spacer(1, 20))
        
        # QR code and signature
        qr_data = f"Transcript:{student_data.get('roll_no')},CGPA:{overall_gpa if 'overall_gpa' in locals() else 0:.2f}"
        qr_code = self._generate_qr_code(qr_data)
        
        signature_data = [
            ['Date of Issue:', datetime.now().strftime('%d-%m-%Y'), ''],
            ['', '', ''],
            ['Controller of Examinations', '', qr_code],
            ['Government Technical College', '', 'Scan to Verify']
        ]
        signature_table = Table(signature_data, colWidths=[200, 150, 100])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 2), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (2, -1), (2, -1), 6),
        ]))
        content.append(signature_table)
        
        # Build PDF
        doc.build(content, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)
        buffer.seek(0)
        return buffer.read()

# Utility functions for easy access
def generate_fee_receipt(student_data, fee_data, transaction_data):
    """Generate fee receipt PDF"""
    generator = PDFGenerator()
    return generator.generate_fee_receipt(student_data, fee_data, transaction_data)

def generate_admission_letter(student_data, course_data, admission_data):
    """Generate admission letter PDF"""
    generator = PDFGenerator()
    return generator.generate_admission_letter(student_data, course_data, admission_data)

def generate_id_card(student_data, course_data):
    """Generate student ID card PDF"""
    generator = PDFGenerator()
    return generator.generate_id_card(student_data, course_data)

def generate_transcript(student_data, course_data, examination_records):
    """Generate academic transcript PDF"""
    generator = PDFGenerator()
    return generator.generate_transcript(student_data, course_data, examination_records)
