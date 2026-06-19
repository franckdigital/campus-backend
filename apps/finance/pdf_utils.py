from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.http import HttpResponse
from io import BytesIO
import datetime


def _n(val):
    """Safe float conversion."""
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def _s(val, fallback='—'):
    """Safe string conversion."""
    v = str(val).strip() if val is not None else ''
    return v if v else fallback


def generate_invoice_pdf(invoice):
    """Génère un PDF pour une facture étudiant."""
    buffer = BytesIO()

    # ── TEST MINIMAL ── à retirer après validation ─────────────────────
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f'FACTURE TEST', styles['Heading1']),
        Spacer(1, 0.5*cm),
        Paragraph(f'Numero : {invoice.invoice_number}', styles['Normal']),
        Paragraph(f'Total  : {invoice.total} FCFA', styles['Normal']),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer
    # ── FIN TEST ────────────────────────────────────────────────────────

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    styles = getSampleStyleSheet()

    # ── Styles ─────────────────────────────────────────────────────────
    inv_school_style = ParagraphStyle(
        'InvSchool', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=2
    )
    inv_title_style = ParagraphStyle(
        'InvTitle', parent=styles['Heading1'],
        fontSize=20, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=4,
        spaceBefore=8,
        textColor=colors.HexColor('#1e40af')
    )
    inv_number_style = ParagraphStyle(
        'InvNumber', parent=styles['Normal'],
        fontSize=11, alignment=TA_CENTER, spaceAfter=4,
        textColor=colors.HexColor('#374151')
    )
    inv_label_style = ParagraphStyle(
        'InvLabel', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold'
    )
    inv_value_style = ParagraphStyle(
        'InvValue', parent=styles['Normal'],
        fontSize=10
    )
    inv_right_style = ParagraphStyle(
        'InvRight', parent=styles['Normal'],
        fontSize=10, alignment=TA_RIGHT
    )
    inv_right_bold_style = ParagraphStyle(
        'InvRightBold', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold', alignment=TA_RIGHT
    )
    inv_footer_style = ParagraphStyle(
        'InvFooter', parent=styles['Normal'],
        fontSize=8, alignment=TA_CENTER,
        textColor=colors.HexColor('#6b7280')
    )

    story = []

    # ── En-tête ────────────────────────────────────────────────────────
    site_name = invoice.site.name if invoice.site else 'Campus'
    story.append(Paragraph(site_name.upper(), inv_school_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph('FACTURE', inv_title_style))
    story.append(Paragraph(
        f'N&#176; {_s(invoice.invoice_number)}', inv_number_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # ── Infos facture / étudiant ───────────────────────────────────────
    student = invoice.student
    if student and student.user:
        student_name = f"{_s(student.user.first_name, '')} {_s(student.user.last_name, '')}".strip() or '—'
    else:
        student_name = '—'
    matricule = _s(getattr(student, 'matricule', None))
    academic_year = _s(invoice.academic_year.name if invoice.academic_year else None)

    info_data = [
        [Paragraph('Etudiant', inv_label_style), Paragraph(student_name, inv_value_style)],
        [Paragraph('Matricule', inv_label_style), Paragraph(matricule, inv_value_style)],
        [Paragraph('Annee academique', inv_label_style), Paragraph(academic_year, inv_value_style)],
        [Paragraph("Date d'emission", inv_label_style),
         Paragraph(_s(invoice.issue_date.strftime('%d/%m/%Y') if invoice.issue_date else None), inv_value_style)],
        [Paragraph("Date d'echeance", inv_label_style),
         Paragraph(_s(invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else None), inv_value_style)],
        [Paragraph('Statut', inv_label_style),
         Paragraph(_s(invoice.get_status_display() if hasattr(invoice, 'get_status_display') else invoice.status), inv_value_style)],
    ]
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EFF6FF')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e40af')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DBEAFE')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.6*cm))

    # ── Tableau des lignes ────────────────────────────────────────────
    items_list = list(invoice.items.all())
    table_data = [[
        Paragraph('Description', ParagraphStyle('InvThDesc', parent=styles['Normal'],
                  fontSize=9, fontName='Helvetica-Bold', textColor=colors.white)),
        Paragraph('Qte', ParagraphStyle('InvThQte', parent=styles['Normal'],
                  fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph('Prix unit.', ParagraphStyle('InvThPU', parent=styles['Normal'],
                  fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph('Total', ParagraphStyle('InvThTot', parent=styles['Normal'],
                  fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, alignment=TA_RIGHT)),
    ]]

    if items_list:
        for item in items_list:
            table_data.append([
                Paragraph(_s(item.description, 'Frais'), inv_value_style),
                Paragraph(str(item.quantity or 1), inv_right_style),
                Paragraph(f'{_n(item.unit_price):,.0f} F', inv_right_style),
                Paragraph(f'{_n(item.total):,.0f} F', inv_right_style),
            ])
    else:
        table_data.append([
            Paragraph('Frais de scolarite', inv_value_style),
            Paragraph('1', inv_right_style),
            Paragraph(f'{_n(invoice.total):,.0f} F', inv_right_style),
            Paragraph(f'{_n(invoice.total):,.0f} F', inv_right_style),
        ])

    items_table = Table(table_data, colWidths=[8*cm, 2*cm, 4*cm, 4*cm])
    ts = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(table_data)):
        bg = colors.white if i % 2 == 1 else colors.HexColor('#F8FAFF')
        ts.append(('BACKGROUND', (0, i), (-1, i), bg))
    items_table.setStyle(TableStyle(ts))
    story.append(items_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Totaux ────────────────────────────────────────────────────────
    balance = _n(invoice.balance)
    totals_data = [
        [Paragraph('Sous-total', inv_right_style),
         Paragraph(f'{_n(invoice.subtotal):,.0f} F', inv_right_style)],
        [Paragraph('Remise', inv_right_style),
         Paragraph(f'{_n(invoice.discount):,.0f} F', inv_right_style)],
        [Paragraph('Taxe', inv_right_style),
         Paragraph(f'{_n(invoice.tax):,.0f} F', inv_right_style)],
        [Paragraph('<b>Total</b>', inv_right_bold_style),
         Paragraph(f'<b>{_n(invoice.total):,.0f} F</b>', inv_right_bold_style)],
        [Paragraph('Deja paye', inv_right_style),
         Paragraph(f'{_n(invoice.amount_paid):,.0f} F', inv_right_style)],
        [Paragraph('<b>Reste a payer</b>',
                   ParagraphStyle('InvBalLabel', parent=styles['Normal'],
                                  fontSize=11, fontName='Helvetica-Bold', alignment=TA_RIGHT,
                                  textColor=colors.HexColor('#DC2626') if balance > 0 else colors.HexColor('#16A34A'))),
         Paragraph(f'<b>{balance:,.0f} F</b>',
                   ParagraphStyle('InvBalVal', parent=styles['Normal'],
                                  fontSize=11, fontName='Helvetica-Bold', alignment=TA_RIGHT,
                                  textColor=colors.HexColor('#DC2626') if balance > 0 else colors.HexColor('#16A34A')))],
    ]
    totals_table = Table(totals_data, colWidths=[13*cm, 5*cm])
    totals_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 3), (-1, 3), 1, colors.HexColor('#1e40af')),
        ('LINEABOVE', (0, 5), (-1, 5), 1, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 1*cm))

    # ── Pied de page ─────────────────────────────────────────────────
    today = datetime.date.today().strftime('%d/%m/%Y')
    story.append(Paragraph(
        f'Document genere le {today}', inv_footer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_receipt_pdf(payment):
    """Génère un PDF reçu pour un paiement."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    styles = getSampleStyleSheet()

    # ── Styles ─────────────────────────────────────────────────────────
    rec_school_style = ParagraphStyle(
        'RecSchool', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=2
    )
    rec_title_style = ParagraphStyle(
        'RecTitle', parent=styles['Heading1'],
        fontSize=20, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=4,
        spaceBefore=8,
        textColor=colors.HexColor('#059669')
    )
    rec_number_style = ParagraphStyle(
        'RecNumber', parent=styles['Normal'],
        fontSize=11, alignment=TA_CENTER, spaceAfter=4,
        textColor=colors.HexColor('#374151')
    )
    rec_label_style = ParagraphStyle(
        'RecLabel', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold'
    )
    rec_value_style = ParagraphStyle(
        'RecValue', parent=styles['Normal'],
        fontSize=10
    )
    rec_right_style = ParagraphStyle(
        'RecRight', parent=styles['Normal'],
        fontSize=10, alignment=TA_RIGHT
    )
    rec_footer_style = ParagraphStyle(
        'RecFooter', parent=styles['Normal'],
        fontSize=8, alignment=TA_CENTER,
        textColor=colors.HexColor('#6b7280')
    )

    story = []
    invoice = payment.invoice
    student = invoice.student if invoice else None

    # ── En-tête ────────────────────────────────────────────────────────
    site_name = invoice.site.name if invoice and invoice.site else 'Campus'
    story.append(Paragraph(site_name.upper(), rec_school_style))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph('RECU DE PAIEMENT', rec_title_style))
    story.append(Paragraph(
        f'N&#176; {_s(payment.payment_number)}', rec_number_style
    ))
    story.append(Spacer(1, 0.5*cm))

    # ── Infos paiement ────────────────────────────────────────────────
    if student and student.user:
        student_name = f"{_s(student.user.first_name, '')} {_s(student.user.last_name, '')}".strip() or '—'
    else:
        student_name = '—'
    matricule = _s(getattr(student, 'matricule', None))
    pay_date = payment.payment_date.strftime('%d/%m/%Y a %H:%M') if payment.payment_date else '—'
    pay_method = _s(payment.payment_method.name if payment.payment_method else None)
    received_by = '—'
    if payment.received_by:
        received_by = f"{_s(payment.received_by.first_name, '')} {_s(payment.received_by.last_name, '')}".strip() or '—'

    info_data = [
        [Paragraph('Etudiant', rec_label_style), Paragraph(student_name, rec_value_style)],
        [Paragraph('Matricule', rec_label_style), Paragraph(matricule, rec_value_style)],
        [Paragraph('Facture N&#176;', rec_label_style),
         Paragraph(_s(invoice.invoice_number if invoice else None), rec_value_style)],
        [Paragraph('Date de paiement', rec_label_style), Paragraph(pay_date, rec_value_style)],
        [Paragraph('Mode de paiement', rec_label_style), Paragraph(pay_method, rec_value_style)],
        [Paragraph('Recu par', rec_label_style), Paragraph(received_by, rec_value_style)],
    ]
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECFDF5')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#059669')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A7F3D0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Montant ────────────────────────────────────────────────────────
    balance = _n(invoice.balance) if invoice else 0
    amount_data = [
        [Paragraph('<b>Montant paye</b>',
                   ParagraphStyle('RecAmtLabel', parent=styles['Normal'],
                                  fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER)),
         Paragraph(f'<b>{_n(payment.amount):,.0f} FCFA</b>',
                   ParagraphStyle('RecAmtVal', parent=styles['Normal'],
                                  fontSize=14, fontName='Helvetica-Bold', alignment=TA_CENTER,
                                  textColor=colors.HexColor('#059669')))],
        [Paragraph('Reste a payer sur la facture',
                   ParagraphStyle('RecRemLabel', parent=styles['Normal'],
                                  fontSize=10, alignment=TA_CENTER,
                                  textColor=colors.HexColor('#6b7280'))),
         Paragraph(f'{balance:,.0f} FCFA',
                   ParagraphStyle('RecRemVal', parent=styles['Normal'],
                                  fontSize=10, alignment=TA_CENTER,
                                  textColor=colors.HexColor('#DC2626') if balance > 0 else colors.HexColor('#059669')))],
    ]
    amount_table = Table(amount_data, colWidths=[9*cm, 9*cm])
    amount_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECFDF5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#059669')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(amount_table)
    story.append(Spacer(1, 1*cm))

    # ── Notes ──────────────────────────────────────────────────────────
    if payment.notes:
        note_style = ParagraphStyle('RecNote', parent=styles['Normal'],
                                    fontSize=9, textColor=colors.HexColor('#6b7280'))
        story.append(Paragraph(f'Note : {payment.notes}', note_style))
        story.append(Spacer(1, 0.5*cm))

    # ── Signature ─────────────────────────────────────────────────────
    sig_data = [
        [Paragraph('Signature du beneficiaire', rec_label_style),
         Paragraph('Signature du caissier', rec_label_style)],
        ['', ''],
    ]
    sig_table = Table(sig_data, colWidths=[9*cm, 9*cm], rowHeights=[1*cm, 3*cm])
    sig_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#D1D5DB')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Pied de page ─────────────────────────────────────────────────
    today = datetime.date.today().strftime('%d/%m/%Y')
    story.append(Paragraph(f'Document genere le {today}', rec_footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer


def create_pdf_response(buffer, filename, inline=True):
    """Crée une réponse HTTP avec le PDF."""
    pdf_bytes = buffer.getvalue()
    print(f'[PDF] {filename}: {len(pdf_bytes)} bytes')
    disposition = 'inline' if inline else 'attachment'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    response['Content-Length'] = str(len(pdf_bytes))
    return response


def generate_invoice_html(invoice):
    """Génère une page HTML imprimable pour une facture."""
    def n(val):
        try:
            return float(val or 0)
        except (TypeError, ValueError):
            return 0.0

    student = invoice.student
    if student and student.user:
        student_name = f"{student.user.first_name} {student.user.last_name}".strip() or 'N/A'
    else:
        student_name = 'N/A'
    matricule = getattr(student, 'matricule', 'N/A') or 'N/A'
    site_name = invoice.site.name if invoice.site else 'Campus'
    academic_year = invoice.academic_year.name if invoice.academic_year else 'N/A'
    issue_date = invoice.issue_date.strftime('%d/%m/%Y') if invoice.issue_date else 'N/A'
    due_date = invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else 'N/A'
    status_display = invoice.get_status_display() if hasattr(invoice, 'get_status_display') else invoice.status
    balance = n(invoice.balance)
    balance_color = '#DC2626' if balance > 0 else '#16A34A'

    items_rows = ''
    for item in invoice.items.all():
        items_rows += f'''
        <tr>
            <td>{item.description or ""}</td>
            <td style="text-align:center">{item.quantity or 1}</td>
            <td style="text-align:right">{n(item.unit_price):,.0f} F</td>
            <td style="text-align:right">{n(item.total):,.0f} F</td>
        </tr>'''
    if not items_rows:
        items_rows = f'<tr><td>Frais de scolarite</td><td style="text-align:center">1</td><td style="text-align:right">{n(invoice.total):,.0f} F</td><td style="text-align:right">{n(invoice.total):,.0f} F</td></tr>'

    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Facture {invoice.invoice_number}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; color: #1e293b; background: #f8fafc; }}
  .page {{ max-width: 800px; margin: 20px auto; background: white; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; border-bottom: 3px solid #1e40af; padding-bottom: 20px; }}
  .school-name {{ font-size: 20px; font-weight: bold; color: #1e40af; }}
  .invoice-title {{ text-align: right; }}
  .invoice-title h1 {{ font-size: 32px; color: #1e40af; font-weight: 900; letter-spacing: 2px; }}
  .invoice-title .num {{ font-size: 14px; color: #64748b; margin-top: 4px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 28px; }}
  .info-box {{ background: #f1f5f9; border-radius: 8px; padding: 16px; }}
  .info-box h3 {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 10px; }}
  .info-box p {{ font-size: 14px; margin-bottom: 4px; }}
  .info-box p strong {{ color: #1e293b; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
  thead tr {{ background: #1e40af; color: white; }}
  thead th {{ padding: 10px 12px; text-align: left; font-size: 13px; }}
  tbody tr:nth-child(even) {{ background: #f8fafc; }}
  tbody td {{ padding: 10px 12px; font-size: 13px; border-bottom: 1px solid #e2e8f0; }}
  .totals {{ margin-left: auto; width: 280px; }}
  .totals table {{ margin: 0; }}
  .totals td {{ padding: 6px 8px; font-size: 13px; }}
  .totals .total-row td {{ font-weight: bold; font-size: 15px; border-top: 2px solid #1e40af; padding-top: 10px; }}
  .balance-row td {{ font-weight: bold; font-size: 15px; color: {balance_color}; }}
  .footer {{ margin-top: 40px; text-align: center; color: #94a3b8; font-size: 11px; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
  .print-btn {{ position: fixed; top: 16px; right: 16px; background: #1e40af; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; cursor: pointer; z-index: 999; }}
  @media print {{
    body {{ background: white; }}
    .page {{ box-shadow: none; margin: 0; padding: 20px; }}
    .print-btn {{ display: none; }}
  }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">&#128438; Imprimer / PDF</button>
<div class="page">
  <div class="header">
    <div>
      <div class="school-name">{site_name}</div>
      <div style="color:#64748b;font-size:13px;margin-top:4px">{academic_year}</div>
    </div>
    <div class="invoice-title">
      <h1>FACTURE</h1>
      <div class="num">N&deg; {invoice.invoice_number}</div>
      <div style="margin-top:8px;font-size:12px;background:#EFF6FF;color:#1e40af;padding:4px 10px;border-radius:4px;display:inline-block">{status_display}</div>
    </div>
  </div>

  <div class="info-grid">
    <div class="info-box">
      <h3>Etudiant</h3>
      <p><strong>{student_name}</strong></p>
      <p style="color:#64748b">Matricule : {matricule}</p>
    </div>
    <div class="info-box">
      <h3>Details de la facture</h3>
      <p>Date d&apos;emission : <strong>{issue_date}</strong></p>
      <p>Date d&apos;echeance : <strong>{due_date}</strong></p>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Description</th>
        <th style="text-align:center">Qte</th>
        <th style="text-align:right">Prix unitaire</th>
        <th style="text-align:right">Total</th>
      </tr>
    </thead>
    <tbody>{items_rows}</tbody>
  </table>

  <div class="totals">
    <table>
      <tr><td>Sous-total</td><td style="text-align:right">{n(invoice.subtotal):,.0f} F</td></tr>
      <tr><td>Remise</td><td style="text-align:right">{n(invoice.discount):,.0f} F</td></tr>
      <tr><td>Taxe</td><td style="text-align:right">{n(invoice.tax):,.0f} F</td></tr>
      <tr class="total-row"><td>Total</td><td style="text-align:right">{n(invoice.total):,.0f} F</td></tr>
      <tr><td>Deja paye</td><td style="text-align:right">{n(invoice.amount_paid):,.0f} F</td></tr>
      <tr class="balance-row"><td>Reste a payer</td><td style="text-align:right">{balance:,.0f} F</td></tr>
    </table>
  </div>

  <div class="footer">Document genere le {datetime.date.today().strftime('%d/%m/%Y')}</div>
</div>
</body></html>'''
    return html


def generate_receipt_html(payment):
    """Génère une page HTML imprimable pour un reçu de paiement."""
    def n(val):
        try:
            return float(val or 0)
        except (TypeError, ValueError):
            return 0.0

    invoice = payment.invoice
    student = invoice.student if invoice else None
    if student and student.user:
        student_name = f"{student.user.first_name} {student.user.last_name}".strip() or 'N/A'
    else:
        student_name = 'N/A'
    matricule = getattr(student, 'matricule', 'N/A') or 'N/A'
    site_name = invoice.site.name if invoice and invoice.site else 'Campus'
    pay_date = payment.payment_date.strftime('%d/%m/%Y a %H:%M') if payment.payment_date else 'N/A'
    pay_method = payment.payment_method.name if payment.payment_method else 'N/A'
    received_by = 'N/A'
    if payment.received_by:
        received_by = f"{payment.received_by.first_name} {payment.received_by.last_name}".strip() or 'N/A'
    balance = n(invoice.balance) if invoice else 0
    balance_color = '#DC2626' if balance > 0 else '#16A34A'

    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Recu {payment.payment_number}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; color: #1e293b; background: #f8fafc; }}
  .page {{ max-width: 600px; margin: 20px auto; background: white; padding: 40px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
  .header {{ text-align: center; border-bottom: 3px solid #059669; padding-bottom: 20px; margin-bottom: 28px; }}
  .header h1 {{ font-size: 28px; color: #059669; font-weight: 900; letter-spacing: 2px; }}
  .header .num {{ font-size: 14px; color: #64748b; margin-top: 4px; }}
  .amount-box {{ background: #ECFDF5; border: 2px solid #059669; border-radius: 12px; padding: 24px; text-align: center; margin: 24px 0; }}
  .amount-box .label {{ font-size: 13px; color: #064e3b; text-transform: uppercase; letter-spacing: 1px; }}
  .amount-box .amount {{ font-size: 36px; font-weight: 900; color: #059669; margin-top: 8px; }}
  .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
  .info-table td {{ padding: 10px 8px; font-size: 13px; border-bottom: 1px solid #e2e8f0; }}
  .info-table td:first-child {{ font-weight: bold; color: #64748b; width: 45%; }}
  .balance {{ text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; font-size: 14px; color: {balance_color}; background: {'#FEF2F2' if balance > 0 else '#F0FDF4'}; }}
  .sigs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 40px; }}
  .sig-box {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; height: 80px; }}
  .sig-box .sig-label {{ font-size: 11px; color: #64748b; text-align: center; }}
  .footer {{ margin-top: 24px; text-align: center; color: #94a3b8; font-size: 11px; }}
  .print-btn {{ position: fixed; top: 16px; right: 16px; background: #059669; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-size: 14px; cursor: pointer; }}
  @media print {{
    body {{ background: white; }}
    .page {{ box-shadow: none; margin: 0; }}
    .print-btn {{ display: none; }}
  }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">&#128438; Imprimer / PDF</button>
<div class="page">
  <div class="header">
    <div style="font-size:16px;font-weight:bold;color:#064e3b;margin-bottom:8px">{site_name}</div>
    <h1>RECU DE PAIEMENT</h1>
    <div class="num">N&deg; {payment.payment_number}</div>
  </div>

  <div class="amount-box">
    <div class="label">Montant paye</div>
    <div class="amount">{n(payment.amount):,.0f} FCFA</div>
  </div>

  <table class="info-table">
    <tr><td>Etudiant</td><td><strong>{student_name}</strong></td></tr>
    <tr><td>Matricule</td><td>{matricule}</td></tr>
    <tr><td>Facture N&deg;</td><td>{invoice.invoice_number if invoice else 'N/A'}</td></tr>
    <tr><td>Date de paiement</td><td>{pay_date}</td></tr>
    <tr><td>Mode de paiement</td><td>{pay_method}</td></tr>
    <tr><td>Reference</td><td>{payment.reference or 'N/A'}</td></tr>
    <tr><td>Recu par</td><td>{received_by}</td></tr>
  </table>

  <div class="balance">Reste a payer sur la facture : {balance:,.0f} FCFA</div>

  <div class="sigs">
    <div class="sig-box"><div class="sig-label">Signature du beneficiaire</div></div>
    <div class="sig-box"><div class="sig-label">Signature du caissier</div></div>
  </div>

  <div class="footer">Document genere le {datetime.date.today().strftime('%d/%m/%Y')}</div>
</div>
</body></html>'''
    return html
