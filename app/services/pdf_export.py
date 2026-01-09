"""
PDF Export Service for Iraq Education AI Assistant.
Exports lesson plans and quizzes to print-ready PDF format.
Uses ReportLab for Arabic RTL support.
"""
import io
from typing import Dict, List, Optional
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def is_pdf_available() -> bool:
    """Check if PDF export is available."""
    return PDF_AVAILABLE


def _get_arabic_styles() -> Dict:
    """Get Arabic-friendly paragraph styles."""
    styles = getSampleStyleSheet()
    
    # Arabic styles (right-aligned)
    styles.add(ParagraphStyle(
        name='ArabicTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        alignment=TA_RIGHT,
        spaceAfter=12,
        textColor=colors.HexColor('#0d6efd')
    ))
    
    styles.add(ParagraphStyle(
        name='ArabicHeading',
        fontName='Helvetica-Bold',
        fontSize=14,
        alignment=TA_RIGHT,
        spaceAfter=8,
        spaceBefore=12,
        textColor=colors.HexColor('#1c2430')
    ))
    
    styles.add(ParagraphStyle(
        name='ArabicBody',
        fontName='Helvetica',
        fontSize=11,
        alignment=TA_RIGHT,
        spaceAfter=6,
        leading=16
    ))
    
    styles.add(ParagraphStyle(
        name='ArabicBullet',
        fontName='Helvetica',
        fontSize=11,
        alignment=TA_RIGHT,
        leftIndent=20,
        spaceAfter=4
    ))
    
    return styles


def export_lesson_plan_pdf(plan: Dict) -> bytes:
    """
    Export lesson plan to PDF.
    
    Args:
        plan: Lesson plan dictionary from build_lesson_plan()
    
    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise RuntimeError("PDF export not available - install reportlab")
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = _get_arabic_styles()
    story = []
    
    meta = plan.get("meta", {})
    
    # Title
    title = f"خطة درس: {meta.get('lesson_title', '—')}"
    story.append(Paragraph(title, styles['ArabicTitle']))
    
    # Meta info table
    meta_data = [
        [f"المادة: {meta.get('subject', '—')}", f"الصف: {meta.get('grade', '—')}"],
        [f"نوع الدرس: {meta.get('lesson_type', '—')}", f"المدة: {meta.get('duration_minutes', 45)} دقيقة"]
    ]
    meta_table = Table(meta_data, colWidths=[8*cm, 8*cm])
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e6ecf7'))
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Objectives
    story.append(Paragraph("الأهداف:", styles['ArabicHeading']))
    for obj in plan.get("objectives", []):
        story.append(Paragraph(f"• {obj}", styles['ArabicBullet']))
    
    # Phases
    story.append(Paragraph("مراحل الدرس:", styles['ArabicHeading']))
    phases_data = [["المرحلة", "الوقت", "النشاط"]]
    for phase in plan.get("phases", []):
        phases_data.append([
            phase.get("name", ""),
            f"{phase.get('minutes', 0)} دقيقة",
            phase.get("desc", "")
        ])
    
    phases_table = Table(phases_data, colWidths=[4*cm, 3*cm, 9*cm])
    phases_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e6ecf7')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(phases_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Assessment
    story.append(Paragraph("التقويم:", styles['ArabicHeading']))
    for item in plan.get("assessment", []):
        story.append(Paragraph(f"• {item}", styles['ArabicBullet']))
    
    # Differentiation
    story.append(Paragraph("مراعاة الفروقات:", styles['ArabicHeading']))
    for item in plan.get("differentiation", []):
        story.append(Paragraph(f"• {item}", styles['ArabicBullet']))
    
    # Homework
    story.append(Paragraph("الواجب المنزلي:", styles['ArabicHeading']))
    for item in plan.get("homework", []):
        story.append(Paragraph(f"• {item}", styles['ArabicBullet']))
    
    # Footer
    story.append(Spacer(1, 1*cm))
    footer_text = f"تم إنشاء هذه الخطة بواسطة مساعد التعليم الذكي — {datetime.now().strftime('%Y-%m-%d')}"
    story.append(Paragraph(footer_text, ParagraphStyle(
        name='Footer',
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.gray
    )))
    
    doc.build(story)
    return buffer.getvalue()


def export_quiz_pdf(quiz: Dict, include_answers: bool = True) -> bytes:
    """
    Export quiz to PDF.
    
    Args:
        quiz: Quiz dictionary from generate_quiz_smart()
        include_answers: Whether to include answer key
    
    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise RuntimeError("PDF export not available - install reportlab")
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = _get_arabic_styles()
    story = []
    
    meta = quiz.get("meta", {})
    
    # Title
    title = f"اختبار {meta.get('subject', '')} - {meta.get('grade', '')}"
    story.append(Paragraph(title, styles['ArabicTitle']))
    
    # Info
    info = f"عدد الأسئلة: {meta.get('question_count', 0)} | المستوى: {meta.get('difficulty', 'متوسط')}"
    story.append(Paragraph(info, styles['ArabicBody']))
    story.append(Spacer(1, 0.5*cm))
    
    # Student info box
    story.append(Paragraph("الاسم: ________________    الصف: ________________    التاريخ: ________________", styles['ArabicBody']))
    story.append(Spacer(1, 0.5*cm))
    
    # Questions
    questions = quiz.get("questions", [])
    answer_key = []
    
    for i, q in enumerate(questions, 1):
        q_type = q.get("type", "سؤال")
        question_text = q.get("question", "")
        
        story.append(Paragraph(f"<b>س{i}:</b> {question_text}", styles['ArabicBody']))
        
        if q_type == "اختيار من متعدد":
            choices = q.get("choices", [])
            for j, choice in enumerate(choices):
                letters = ["أ", "ب", "ج", "د"]
                letter = letters[j] if j < len(letters) else str(j+1)
                story.append(Paragraph(f"    {letter}) {choice}", styles['ArabicBullet']))
            answer_key.append(f"س{i}: {letters[q.get('answer_index', 0)]}")
        
        elif q_type == "صح/خطأ":
            story.append(Paragraph("    (    ) صح     (    ) خطأ", styles['ArabicBullet']))
            answer_key.append(f"س{i}: {q.get('answer', 'صح')}")
        
        elif q_type == "أكمل الفراغ":
            answer_key.append(f"س{i}: {q.get('answer', '')}")
        
        elif q_type == "سؤال قصير":
            story.append(Paragraph("الجواب: _________________________________________________", styles['ArabicBullet']))
            answer_key.append(f"س{i}: {q.get('answer_hint', '')[:50]}...")
        
        story.append(Spacer(1, 0.3*cm))
    
    # Answer key (if requested)
    if include_answers and answer_key:
        story.append(PageBreak())
        story.append(Paragraph("مفتاح الإجابات", styles['ArabicTitle']))
        story.append(Spacer(1, 0.5*cm))
        
        for ans in answer_key:
            story.append(Paragraph(ans, styles['ArabicBody']))
    
    # Footer
    story.append(Spacer(1, 1*cm))
    footer_text = f"تم إنشاء هذا الاختبار بواسطة مساعد التعليم الذكي — {datetime.now().strftime('%Y-%m-%d')}"
    story.append(Paragraph(footer_text, ParagraphStyle(
        name='Footer',
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.gray
    )))
    
    doc.build(story)
    return buffer.getvalue()
