"""
pdf_canvas_utils.py
────────────────────
Génération PDF via canvas.Canvas (API bas niveau ReportLab).
Aucun risque de conflit de style global — fonctionne sur tout serveur.
"""

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm


W, H = A4            # 595.27 x 841.89 pts
MARGIN_L = 2 * cm
MARGIN_R = W - 2 * cm
MARGIN_T = H - 1.5 * cm
MARGIN_B = 2 * cm


# ─── Couleurs (r, g, b) 0–1 ──────────────────────────────────────────────────

def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


DARK    = hex_rgb('#0f172a')
GRAY    = hex_rgb('#64748b')
LIGHT   = hex_rgb('#94a3b8')
WHITE   = (1, 1, 1)
PURPLE  = hex_rgb('#7c3aed')
PINK    = hex_rgb('#db2777')
GREEN   = hex_rgb('#059669')
RED     = hex_rgb('#dc2626')
GOLD    = hex_rgb('#d97706')
TEAL    = hex_rgb('#0f766e')
VIOLET_BG = hex_rgb('#f5f3ff')


# ─── Helpers bas niveau ───────────────────────────────────────────────────────

def draw_rect(c, x, y, w, h, fill_rgb, stroke_rgb=None, radius=0):
    c.setFillColorRGB(*fill_rgb)
    if stroke_rgb:
        c.setStrokeColorRGB(*stroke_rgb)
        c.setLineWidth(0.5)
    if radius:
        c.roundRect(x, y, w, h, radius, fill=1, stroke=1 if stroke_rgb else 0)
    else:
        c.rect(x, y, w, h, fill=1, stroke=1 if stroke_rgb else 0)


def draw_text(c, text, x, y, font='Helvetica', size=10, color=DARK, align='left', max_width=None):
    """Dessine une ligne de texte, en tronquant si nécessaire."""
    c.setFont(font, size)
    c.setFillColorRGB(*color)
    text = str(text)
    if max_width:
        while c.stringWidth(text, font, size) > max_width and len(text) > 3:
            text = text[:-4] + '...'
    if align == 'center':
        c.drawCentredString(x, y, text)
    elif align == 'right':
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)


def wrap_text(c, text, x, y, max_width, font='Helvetica', size=10, color=DARK, line_height=14):
    """Écrit un texte avec retour à la ligne automatique. Retourne le y final."""
    c.setFont(font, size)
    c.setFillColorRGB(*color)
    words = str(text).replace('\n', ' \n ').split(' ')
    line = ''
    for w in words:
        if w == '\n':
            c.drawString(x, y, line.strip())
            y -= line_height
            line = ''
            continue
        test = (line + ' ' + w).strip()
        if c.stringWidth(test, font, size) <= max_width:
            line = test
        else:
            if line:
                c.drawString(x, y, line)
                y -= line_height
            line = w
    if line:
        c.drawString(x, y, line)
        y -= line_height
    return y


def draw_line(c, x1, y1, x2, y2, color=LIGHT, width=0.5):
    c.setStrokeColorRGB(*color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)


# ─── Header bandeaux ─────────────────────────────────────────────────────────

def draw_header_banner(c, title1, title2, color1=DARK, color2=PINK):
    """Bandeau haut de page : nom étudiant + titre de l'évaluation."""
    # Bande supérieure
    draw_rect(c, MARGIN_L - 0.5*cm, H - 2.8*cm, W - 3*cm, 1.0*cm, fill_rgb=color1)
    draw_text(c, title1, W/2, H - 2.2*cm, 'Helvetica-Bold', 11, WHITE, 'center',
              max_width=W - 4*cm)

    # Bande inférieure (titre éval)
    draw_rect(c, MARGIN_L - 0.5*cm, H - 3.9*cm, W - 3*cm, 1.0*cm, fill_rgb=color2)
    draw_text(c, title2, W/2, H - 3.3*cm, 'Helvetica-Bold', 10, WHITE, 'center',
              max_width=W - 4*cm)


def draw_page_footer(c, page_num, total_pages):
    draw_line(c, MARGIN_L, MARGIN_B + 0.6*cm, MARGIN_R, MARGIN_B + 0.6*cm)
    draw_text(c, f'Page {page_num} / {total_pages}', W/2, MARGIN_B + 0.2*cm,
              size=8, color=LIGHT, align='center')
    draw_text(c, 'Campus LMS — Document généré automatiquement', MARGIN_L,
              MARGIN_B + 0.2*cm, size=7, color=LIGHT)


# ─── API publique ─────────────────────────────────────────────────────────────

def generate_student_submission_pdf(student_name, assignment_title, sections):
    """
    Génère la copie d'un étudiant.
    sections: list of (title: str, body: str)
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    text_w = MARGIN_R - MARGIN_L

    def new_page(page_num):
        draw_text(c, 'CAMPUS LMS — Copie étudiant', W/2, H - 1.0*cm,
                  size=8, color=LIGHT, align='center')
        draw_header_banner(c, f'COPIE DE : {student_name.upper()}', assignment_title,
                           color1=DARK, color2=PINK)
        return H - 4.4*cm  # y de départ après le bandeau

    y = new_page(1)
    page = 1

    for title, body in sections:
        if y < MARGIN_B + 4*cm:
            draw_page_footer(c, page, '?')
            c.showPage()
            page += 1
            y = new_page(page)

        # Titre de section
        y -= 0.3*cm
        draw_rect(c, MARGIN_L, y - 0.5*cm, text_w, 0.7*cm, fill_rgb=hex_rgb('#f8fafc'),
                  stroke_rgb=hex_rgb('#e2e8f0'))
        draw_text(c, title, MARGIN_L + 0.3*cm, y - 0.1*cm,
                  'Helvetica-Bold', 11, DARK)
        draw_line(c, MARGIN_L, y - 0.6*cm, MARGIN_L + 0.08*cm * len(title) * 3, y - 0.6*cm,
                  color=PINK, width=1.5)
        y -= 1.0*cm

        # Corps du texte
        for para in body.split('\n'):
            para = para.strip()
            if not para:
                y -= 0.2*cm
                continue
            if y < MARGIN_B + 3*cm:
                draw_page_footer(c, page, '?')
                c.showPage()
                page += 1
                y = new_page(page)
            y = wrap_text(c, para, MARGIN_L, y, text_w, size=10, color=DARK, line_height=14)
            y -= 0.15*cm

        y -= 0.5*cm

    # Pied de page final
    y -= 0.5*cm
    draw_line(c, MARGIN_L, y, MARGIN_R, y, color=PINK, width=0.5)
    y -= 0.35*cm
    draw_text(c, f'Copie de {student_name} — Campus LMS', W/2, y,
              size=8, color=GRAY, align='center')

    draw_page_footer(c, page, page)
    c.save()
    return buf.getvalue()


def generate_correction_pdf(student_name, assignment_title, score, max_score, feedback, corrections):
    """
    Génère la correction du professeur.
    corrections: list of (label: str, comment: str)
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    text_w = MARGIN_R - MARGIN_L
    pct = score / max_score * 100 if max_score > 0 else 0
    grade_color = GREEN if pct >= 50 else RED

    # ── Page 1 ──
    draw_text(c, 'CAMPUS LMS — Correction professeur', W/2, H - 1.0*cm,
              size=8, color=LIGHT, align='center')

    draw_header_banner(c, f'CORRECTION — {student_name.upper()}', assignment_title,
                       color1=DARK, color2=GREEN if pct >= 50 else RED)

    y = H - 4.8*cm

    # ── Note ──
    draw_rect(c, MARGIN_L, y - 1.8*cm, text_w, 1.8*cm, fill_rgb=hex_rgb('#f0fdf4') if pct >= 50 else hex_rgb('#fef2f2'),
              stroke_rgb=hex_rgb('#bbf7d0') if pct >= 50 else hex_rgb('#fecaca'))
    draw_text(c, f'{score} / {max_score} pts', MARGIN_L + 0.5*cm, y - 0.6*cm,
              'Helvetica-Bold', 18, grade_color)
    draw_text(c, f'{pct:.0f}%  —  {"Validé" if pct >= 50 else "Insuffisant"}',
              MARGIN_L + 5*cm, y - 0.6*cm, 'Helvetica-Bold', 12, grade_color)
    draw_text(c, 'Seuil de validation : 50%', MARGIN_R - 0.3*cm, y - 1.3*cm,
              size=8, color=GRAY, align='right')
    y -= 2.3*cm

    # ── Appréciation générale ──
    y -= 0.3*cm
    draw_text(c, 'APPRÉCIATION GÉNÉRALE', MARGIN_L, y, 'Helvetica-Bold', 10, PURPLE)
    draw_line(c, MARGIN_L, y - 0.2*cm, MARGIN_R, y - 0.2*cm, PURPLE, 1)
    y -= 0.5*cm

    y = wrap_text(c, feedback, MARGIN_L, y, text_w, size=10, color=DARK, line_height=15)
    y -= 0.6*cm

    # ── Corrections point par point ──
    if corrections:
        draw_text(c, 'CORRECTIONS PAR POINT', MARGIN_L, y, 'Helvetica-Bold', 10, PURPLE)
        draw_line(c, MARGIN_L, y - 0.2*cm, MARGIN_R, y - 0.2*cm, PURPLE, 1)
        y -= 0.6*cm

        for label, comment in corrections:
            if y < MARGIN_B + 4*cm:
                draw_page_footer(c, 1, 1)
                c.showPage()
                draw_text(c, 'CAMPUS LMS — Correction professeur (suite)', W/2, H - 1.0*cm,
                          size=8, color=LIGHT, align='center')
                y = H - 2.0*cm

            # Badge label
            lbl_w = min(c.stringWidth(label, 'Helvetica-Bold', 9) + 10, 5*cm)
            draw_rect(c, MARGIN_L, y - 0.45*cm, lbl_w, 0.55*cm,
                      fill_rgb=VIOLET_BG, stroke_rgb=hex_rgb('#ddd6fe'))
            draw_text(c, label, MARGIN_L + 0.2*cm, y - 0.25*cm,
                      'Helvetica-Bold', 9, PURPLE)

            # Commentaire
            y -= 0.65*cm
            y = wrap_text(c, comment, MARGIN_L + 0.3*cm, y,
                          text_w - 0.3*cm, size=10, color=DARK, line_height=14)
            draw_line(c, MARGIN_L, y - 0.1*cm, MARGIN_R, y - 0.1*cm,
                      color=hex_rgb('#f1f5f9'), width=0.3)
            y -= 0.4*cm

    # Signature
    y -= 0.5*cm
    draw_line(c, MARGIN_L, y, MARGIN_R, y, PINK, 0.5)
    y -= 0.3*cm
    draw_text(c, f'Correction validée par le professeur — Campus LMS', W/2, y,
              size=8, color=GRAY, align='center')

    draw_page_footer(c, 1, 1)
    c.save()
    return buf.getvalue()


def generate_exam_subject_pdf(title, questions_list, meta_info=None, intro=''):
    """
    Génère un sujet d'examen.
    questions_list: list of (q_label: str, q_text: str)
    meta_info: dict {label: value}
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    text_w = MARGIN_R - MARGIN_L

    def new_page(is_first=False):
        draw_text(c, 'CAMPUS LMS — Sujet d\'examen', W/2, H - 1.0*cm,
                  size=8, color=LIGHT, align='center')
        draw_rect(c, MARGIN_L - 0.5*cm, H - 3.0*cm, W - 3*cm, 1.8*cm, TEAL)
        draw_text(c, title, W/2, H - 1.9*cm, 'Helvetica-Bold', 13, WHITE, 'center',
                  max_width=W - 4*cm)
        draw_line(c, MARGIN_L, H - 3.1*cm, MARGIN_R, H - 3.1*cm, color=TEAL, width=2)
        return H - 3.8*cm

    y = new_page(True)

    # Meta infos
    if meta_info:
        parts = [f'{k} : {v}' for k, v in meta_info.items()]
        info_line = '   |   '.join(parts)
        draw_text(c, info_line, W/2, y, size=9, color=GRAY, align='center',
                  max_width=text_w)
        y -= 0.6*cm
        draw_line(c, MARGIN_L, y, MARGIN_R, y, color=hex_rgb('#e2e8f0'))
        y -= 0.5*cm

    # Consignes
    if intro:
        draw_text(c, 'CONSIGNES', MARGIN_L, y, 'Helvetica-Bold', 10, TEAL)
        y -= 0.4*cm
        for line in intro.replace('\\n', '\n').split('\n'):
            line = line.strip()
            if not line:
                continue
            if y < MARGIN_B + 4*cm:
                c.showPage()
                y = new_page()
            y = wrap_text(c, f'• {line}', MARGIN_L + 0.3*cm, y,
                          text_w - 0.3*cm, size=10, color=DARK, line_height=14)
            y -= 0.1*cm
        draw_line(c, MARGIN_L, y - 0.2*cm, MARGIN_R, y - 0.2*cm, hex_rgb('#e2e8f0'))
        y -= 0.7*cm

    # Questions
    draw_text(c, 'QUESTIONS', MARGIN_L, y, 'Helvetica-Bold', 10, TEAL)
    y -= 0.5*cm

    page = 1
    for q_label, q_text in questions_list:
        if y < MARGIN_B + 6*cm:
            draw_page_footer(c, page, '?')
            c.showPage()
            page += 1
            y = new_page()
            y -= 0.3*cm

        # Header question
        draw_rect(c, MARGIN_L, y - 0.55*cm, text_w, 0.65*cm,
                  fill_rgb=hex_rgb('#f0fdfa'), stroke_rgb=hex_rgb('#99f6e4'))
        draw_text(c, q_label, MARGIN_L + 0.3*cm, y - 0.25*cm,
                  'Helvetica-Bold', 10, TEAL)
        y -= 0.9*cm

        # Texte de la question
        y = wrap_text(c, q_text, MARGIN_L, y, text_w, size=10.5, color=DARK, line_height=15)
        y -= 0.4*cm

        # Lignes de réponse
        for _ in range(4):
            draw_line(c, MARGIN_L, y, MARGIN_R, y, hex_rgb('#cbd5e1'), 0.3)
            y -= 0.55*cm
        y -= 0.4*cm

    draw_page_footer(c, page, page)
    c.save()
    return buf.getvalue()
