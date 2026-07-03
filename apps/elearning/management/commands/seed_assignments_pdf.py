"""
seed_assignments_pdf.py — Crée de vrais sujets de devoirs en PDF avec reportlab.

Usage:
    python manage.py seed_assignments_pdf
    python manage.py seed_assignments_pdf --clear   # supprime d'abord les anciens

Génère des sujets PDF réalistes avec :
  - En-tête institutionnel
  - Questions numérotées
  - Barème détaillé
  - Instructions de rendu
"""
import io
import os
import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone

# ─── Données des sujets ──────────────────────────────────────────────────────

SUBJECTS_DATA = [
    {
        'title': 'Devoir 1 — Analyse de Marché et Plan Commercial',
        'subject_keyword': 'commercial',
        'max_score': 20,
        'days_offset': 10,
        'allow_late': False,
        'description': 'Ce devoir porte sur la réalisation d\'une étude de marché et l\'élaboration d\'un plan d\'action commercial.',
        'instructions': 'Répondez à toutes les questions. Appuyez-vous sur des exemples concrets d\'entreprises réelles. Le plagiat entraîne la note zéro.',
        'questions': [
            {
                'num': 1,
                'text': 'ÉTUDE DE MARCHÉ (7 pts) — Vous travaillez pour une PME souhaitant lancer une gamme de cosmétiques bio sur le marché national :',
                'sub': [
                    'a) Définissez les objectifs de l\'étude de marché et choisissez la méthode adaptée (qualitative ou quantitative). Justifiez. (2 pts)',
                    'b) Réalisez une analyse PESTEL en identifiant au moins 2 facteurs par dimension. (3 pts)',
                    'c) Analysez la concurrence à l\'aide du modèle des 5 forces de Porter. Identifiez les forces les plus déterminantes. (2 pts)',
                ],
                'points': 7,
            },
            {
                'num': 2,
                'text': 'SEGMENTATION ET CIBLAGE (6 pts) :',
                'sub': [
                    'a) Proposez une segmentation du marché des cosmétiques bio selon 3 critères différents (socio-démographique, comportemental, psychographique). (3 pts)',
                    'b) Choisissez un segment cible et justifiez votre choix à l\'aide des critères d\'un bon segment (mesurable, accessible, rentable, actionnable). (2 pts)',
                    'c) Définissez le positionnement de la marque sur ce segment. Rédigez une phrase de positionnement. (1 pt)',
                ],
                'points': 6,
            },
            {
                'num': 3,
                'text': 'PLAN D\'ACTION COMMERCIAL (7 pts) :',
                'sub': [
                    'a) Définissez les objectifs commerciaux SMART pour les 12 premiers mois. (2 pts)',
                    'b) Proposez un mix marketing (4P) cohérent avec le positionnement défini. (3 pts)',
                    'c) Construisez un tableau de bord avec 4 indicateurs de performance (KPI) commerciaux pertinents. (2 pts)',
                ],
                'points': 7,
            },
        ],
        'scenario': 'mixed',
    },
    {
        'title': 'TP Noté — Gestion et Résolution de Conflits RH',
        'subject_keyword': 'ressources',
        'max_score': 20,
        'days_offset': -3,
        'allow_late': True,
        'description': 'Travail pratique sur la gestion des conflits en entreprise, la médiation et le droit social.',
        'instructions': 'Rendu en format PDF. Répondez en vous basant sur des cas concrets. Longueur recommandée : 4 à 6 pages.',
        'questions': [
            {
                'num': 1,
                'text': 'ANALYSE D\'UN CAS DE CONFLIT (8 pts) — Lisez la situation suivante et répondez :',
                'sub': [
                    'Contexte : Un responsable commercial reproche à deux membres de son équipe de ne pas atteindre leurs objectifs. Il leur attribue les clients les moins intéressants en représailles. Les salariés menacent de saisir les prud\'hommes.',
                    'a) Identifiez les types de conflits présents (conflit de rôle, conflit interpersonnel, conflit hiérarchique). (2 pts)',
                    'b) Analysez les causes profondes du conflit (outil : iceberg du conflit ou modèle de Thomas-Kilmann). (3 pts)',
                    'c) En tant que DRH, proposez une démarche structurée de résolution du conflit en 5 étapes. (3 pts)',
                ],
                'points': 8,
            },
            {
                'num': 2,
                'text': 'OUTILS DE PRÉVENTION ET MÉDIATION (6 pts) :',
                'sub': [
                    'a) Définissez la médiation et distinguez-la de la conciliation et de l\'arbitrage. (2 pts)',
                    'b) Quels dispositifs préventifs pouvez-vous mettre en place pour éviter ce type de conflit ? Citez et expliquez 3 mesures concrètes. (2 pts)',
                    'c) Quelle est la responsabilité de l\'employeur en matière de harcèlement moral ? Citez les articles du Code du Travail applicables. (2 pts)',
                ],
                'points': 6,
            },
            {
                'num': 3,
                'text': 'PROCÉDURE DISCIPLINAIRE (6 pts) :',
                'sub': [
                    'a) Dans quel cas peut-on initier une procédure disciplinaire ? Définissez la notion de faute (simple, grave, lourde). (2 pts)',
                    'b) Décrivez les étapes obligatoires de la procédure disciplinaire selon le Code du Travail. (2 pts)',
                    'c) Quelles sanctions sont possibles hors le licenciement ? Dans quel ordre doivent-elles être appliquées ? (2 pts)',
                ],
                'points': 6,
            },
        ],
        'scenario': 'graded',
    },
    {
        'title': 'Devoir Maison — Stratégie d\'Entreprise et Diagnostic Stratégique',
        'subject_keyword': 'management',
        'max_score': 20,
        'days_offset': 14,
        'allow_late': False,
        'description': 'Devoir portant sur le diagnostic stratégique, les modèles d\'analyse et la formulation de stratégies d\'entreprise.',
        'instructions': 'Réponses rédigées. Toute affirmation doit être illustrée par un exemple d\'entreprise réelle. Longueur : 5 à 8 pages.',
        'questions': [
            {
                'num': 1,
                'text': 'DIAGNOSTIC INTERNE (7 pts) :',
                'sub': [
                    'a) Expliquez la chaîne de valeur de Porter. Identifiez les activités principales et de soutien. (3 pts)',
                    'b) Qu\'est-ce qu\'une ressource stratégique selon le modèle VRIO ? Appliquez ce modèle à une entreprise de votre choix. (2 pts)',
                    'c) Construisez une matrice BCG pour une entreprise multisectorielle avec 4 DAS fictifs. Interprétez les résultats. (2 pts)',
                ],
                'points': 7,
            },
            {
                'num': 2,
                'text': 'FORMULATION STRATÉGIQUE (7 pts) :',
                'sub': [
                    'a) Présentez les 3 stratégies génériques de Porter (domination par les coûts, différenciation, concentration). Donnez un exemple pour chacune. (3 pts)',
                    'b) Qu\'est-ce que la matrice Ansoff ? Appliquez-la à une PME souhaitant se développer. (2 pts)',
                    'c) Comparez stratégie de croissance interne et externe (fusion-acquisition). Avantages et inconvénients. (2 pts)',
                ],
                'points': 7,
            },
            {
                'num': 3,
                'text': 'MISE EN OEUVRE ET CONTRÔLE (6 pts) :',
                'sub': [
                    'a) Quels sont les facteurs clés de succès (FCS) dans la mise en oeuvre d\'une stratégie de différenciation ? (2 pts)',
                    'b) Expliquez le concept de Balanced Scorecard (BSC) et ses 4 perspectives. (2 pts)',
                    'c) Pourquoi 70% des stratégies échouent lors de la mise en oeuvre ? Proposez 3 leviers pour éviter cet écueil. (2 pts)',
                ],
                'points': 6,
            },
        ],
        'scenario': 'pending',
    },
    {
        'title': 'Exercice — Gestion Prévisionnelle des Emplois et des Compétences (GPEC)',
        'subject_keyword': 'ressources',
        'max_score': 20,
        'days_offset': 5,
        'allow_late': False,
        'description': 'Exercice pratique sur la GPEC : diagnostic des compétences, plan de formation et gestion des carrières.',
        'instructions': 'Répondez en vous appuyant sur des outils RH concrets. Rendu PDF, 4 à 6 pages recommandées.',
        'questions': [
            {
                'num': 1,
                'text': 'DIAGNOSTIC DES COMPÉTENCES (6 pts) — Vous êtes DRH d\'une entreprise de distribution (300 salariés) :',
                'sub': [
                    'a) Définissez la GPEC et distinguez-la de la gestion administrative des RH. (2 pts)',
                    'b) Construisez un référentiel de compétences pour le poste de "Responsable Secteur Commercial". (2 pts)',
                    '   Incluez : compétences techniques (savoir), comportementales (savoir-être), managériales (savoir-faire)',
                    'c) Proposez un outil de cartographie des compétences pour votre équipe de 12 commerciaux. (2 pts)',
                ],
                'points': 6,
            },
            {
                'num': 2,
                'text': 'PLAN DE DÉVELOPPEMENT DES COMPÉTENCES (8 pts) :',
                'sub': [
                    'a) Suite au diagnostic, 40% des commerciaux maîtrisent mal les techniques de vente digitale.',
                    '   Rédigez un plan de formation sur 12 mois. Précisez : objectifs, modalités (présentiel/distanciel/FEST), budget prévisionnel, indicateurs d\'évaluation. (4 pts)',
                    'b) Quelle est la différence entre CPF, Plan de développement des compétences et Pro-A ? (2 pts)',
                    'c) Comment mesurer le retour sur investissement (ROI) d\'une action de formation ? (2 pts)',
                ],
                'points': 8,
            },
            {
                'num': 3,
                'text': 'GESTION DES CARRIÈRES (6 pts) :',
                'sub': [
                    'a) Définissez la mobilité interne et ses 3 formes (horizontale, verticale, géographique). Donnez un exemple. (2 pts)',
                    'b) Qu\'est-ce qu\'un entretien de carrière ? En quoi diffère-t-il de l\'entretien professionnel ? (2 pts)',
                    'c) Comment construire un plan de succession pour un poste clé comme Directeur Commercial ? (2 pts)',
                ],
                'points': 6,
            },
        ],
        'scenario': 'submitted_text',
    },
    {
        'title': 'Projet Final — Business Plan d\'une Entreprise Commerciale',
        'subject_keyword': 'commercial',
        'max_score': 50,
        'days_offset': 30,
        'allow_late': False,
        'description': 'Projet de fin de semestre à réaliser en binôme. Élaboration d\'un business plan complet pour une nouvelle activité commerciale.',
        'instructions': 'Rendu : dossier PDF (max 20 pages) + présentation Powerpoint (15 slides max). Date limite stricte. Soutenance orale de 15 minutes.',
        'questions': [
            {
                'num': 1,
                'text': 'ÉTUDE DE FAISABILITÉ ET ANALYSE DE MARCHÉ (15 pts) :',
                'sub': [
                    'a) Présentez le concept commercial, le problème client résolu et la proposition de valeur unique (UVP). (3 pts)',
                    'b) Réalisez une analyse PESTEL complète et une étude de la concurrence (matrice concurrentielle + positionnement). (5 pts)',
                    'c) Définissez la cible (personas détaillés, taille du marché accessible — TAM/SAM/SOM). (4 pts)',
                    'd) Synthèse SWOT — matrice des forces/faiblesses/opportunités/menaces. (3 pts)',
                ],
                'points': 15,
            },
            {
                'num': 2,
                'text': 'STRATÉGIE COMMERCIALE ET MARKETING (20 pts) :',
                'sub': [
                    'a) Mix marketing complet (7P pour le service ou 4P pour le produit) avec justification de chaque choix. (6 pts)',
                    'b) Plan de prospection et d\'acquisition client : canaux, budget, calendrier sur 12 mois. (5 pts)',
                    'c) Politique de fidélisation : programme, CRM, indicateurs de suivi (NPS, taux de réachat, CLV). (5 pts)',
                    'd) Objectifs commerciaux SMART sur 3 ans avec jalons trimestriels. (4 pts)',
                ],
                'points': 20,
            },
            {
                'num': 3,
                'text': 'PLAN FINANCIER ET ORGANISATION RH (15 pts) :',
                'sub': [
                    'a) Compte de résultat prévisionnel sur 3 ans (CA, charges, résultat net). (5 pts)',
                    'b) Calcul du seuil de rentabilité (point mort) et délai de retour sur investissement. (4 pts)',
                    'c) Plan RH : organigramme, fiches de poste clés, politique de rémunération et plan de recrutement. (4 pts)',
                    'd) Risques identifiés et plan de mitigation (tableau des risques avec probabilité et impact). (2 pts)',
                ],
                'points': 15,
            },
        ],
        'scenario': 'pending',
    },
    {
        'title': 'Devoir 4 — Techniques de Vente et Négociation Commerciale',
        'subject_keyword': 'commercial',
        'max_score': 20,
        'days_offset': 18,
        'allow_late': False,
        'description': 'Devoir portant sur les techniques de vente, la conduite d\'un entretien commercial et la négociation.',
        'instructions': 'Rendu sur papier ou fichier PDF. Répondez à toutes les questions. Les jeux de rôles sont décrits à l\'écrit.',
        'questions': [
            {
                'num': 1,
                'text': 'TECHNIQUES D\'ENTRETIEN DE VENTE (7 pts) :',
                'sub': [
                    'a) Décrivez les 5 étapes de la méthode AIDA appliquées à un entretien de vente BtoB. (3 pts)',
                    'b) Qu\'est-ce que la méthode SPIN Selling ? Donnez 2 exemples de questions pour chaque type (Situation, Problème, Implication, Need-Payoff). (2 pts)',
                    'c) Comment gérer un client qui dit "c\'est trop cher" ? Proposez une réponse structurée avec reformulation et argumentation. (2 pts)',
                ],
                'points': 7,
            },
            {
                'num': 2,
                'text': 'NÉGOCIATION COMMERCIALE (7 pts) :',
                'sub': [
                    'a) Différenciez la négociation distributive (gagnant-perdant) de la négociation intégrative (gagnant-gagnant). Donnez un exemple concret de chaque. (3 pts)',
                    'b) Qu\'est-ce que la BATNA (Best Alternative To a Negotiated Agreement) ? Comment l\'identifier et l\'utiliser en négociation ? (2 pts)',
                    'c) Citez et expliquez 4 tactiques de négociation courantes (ex : la porte dans la face, le pied dans la porte, etc.). (2 pts)',
                ],
                'points': 7,
            },
            {
                'num': 3,
                'text': 'GESTION DU PORTEFEUILLE CLIENT (6 pts) :',
                'sub': [
                    'a) Qu\'est-ce que la méthode ABC (loi de Pareto) appliquée aux clients ? Comment la mettre en oeuvre ? (2 pts)',
                    'b) Construisez un plan d\'action pour réactiver 20 clients dormants d\'une société de conseil. (2 pts)',
                    'c) Définissez les indicateurs de pilotage d\'un commercial : taux de transformation, panier moyen, CA par client, durée du cycle de vente. (2 pts)',
                ],
                'points': 6,
            },
        ],
        'scenario': 'pending',
    },
]

# ─── Générateur de PDF ────────────────────────────────────────────────────────

def generate_pdf(title, subject_name, class_name, due_date, max_score, description, instructions, questions):
    """Génère un PDF professionnel de sujet de devoir avec reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    # ── Couleurs
    PINK = HexColor('#db2777')
    PINK_LIGHT = HexColor('#fce7f3')
    DARK = HexColor('#0f172a')
    GRAY = HexColor('#64748b')
    LIGHT_GRAY = HexColor('#f8fafc')

    # ── Styles
    styles = getSampleStyleSheet()

    h_institution = ParagraphStyle(
        'Institution', parent=styles['Normal'],
        fontSize=9, textColor=GRAY, alignment=TA_CENTER, spaceAfter=2,
    )
    h_title = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontSize=18, textColor=DARK, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=4,
    )
    h_subtitle = ParagraphStyle(
        'DocSub', parent=styles['Normal'],
        fontSize=11, textColor=PINK, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=10,
    )
    meta_label = ParagraphStyle(
        'MetaLabel', parent=styles['Normal'],
        fontSize=8, textColor=GRAY, fontName='Helvetica-Bold',
        spaceAfter=1,
    )
    meta_value = ParagraphStyle(
        'MetaValue', parent=styles['Normal'],
        fontSize=10, textColor=DARK, fontName='Helvetica-Bold',
        spaceAfter=0,
    )
    p_desc = ParagraphStyle(
        'Desc', parent=styles['Normal'],
        fontSize=10, textColor=DARK, leading=15,
        alignment=TA_JUSTIFY, spaceAfter=4,
    )
    p_instr = ParagraphStyle(
        'Instr', parent=styles['Normal'],
        fontSize=9, textColor=GRAY, leading=13,
        alignment=TA_JUSTIFY,
    )
    q_header = ParagraphStyle(
        'QHeader', parent=styles['Normal'],
        fontSize=12, textColor=DARK, fontName='Helvetica-Bold',
        spaceBefore=14, spaceAfter=4,
    )
    q_text = ParagraphStyle(
        'QText', parent=styles['Normal'],
        fontSize=10, textColor=DARK, leading=15,
        alignment=TA_JUSTIFY, spaceAfter=4,
    )
    q_sub = ParagraphStyle(
        'QSub', parent=styles['Normal'],
        fontSize=10, textColor=HexColor('#374151'), leading=15,
        leftIndent=14, spaceAfter=2,
    )
    pts_style = ParagraphStyle(
        'Points', parent=styles['Normal'],
        fontSize=9, textColor=PINK, fontName='Helvetica-Bold',
        alignment=TA_LEFT, spaceAfter=8,
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=GRAY, alignment=TA_CENTER,
    )

    story = []

    # ── En-tête institutionnel
    story.append(Paragraph('CAMPUS LMS — Établissement d\'Enseignement Supérieur', h_institution))
    story.append(Paragraph(f'Année Universitaire 2025-2026', h_institution))
    story.append(Spacer(1, 0.3 * cm))

    # ── Bandeau coloré titre
    banner_data = [[Paragraph(title, ParagraphStyle(
        'BTitle', parent=styles['Normal'],
        fontSize=15, textColor=white, fontName='Helvetica-Bold', alignment=TA_CENTER,
    ))]]
    banner = Table(banner_data, colWidths=[17 * cm])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PINK),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [8]),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.5 * cm))

    # ── Métadonnées
    due_str = due_date.strftime('%d %B %Y à %H:%M') if due_date else '—'
    meta_rows = [
        [
            [Paragraph('MATIÈRE', meta_label), Paragraph(subject_name, meta_value)],
            [Paragraph('CLASSE', meta_label), Paragraph(class_name, meta_value)],
            [Paragraph('DATE LIMITE', meta_label), Paragraph(due_str, meta_value)],
            [Paragraph('BARÈME TOTAL', meta_label), Paragraph(f'{max_score} points', meta_value)],
        ]
    ]
    meta_table_data = [[
        Table([[Paragraph('MATIÈRE', meta_label)], [Paragraph(subject_name, meta_value)]], colWidths=[3.8 * cm]),
        Table([[Paragraph('CLASSE', meta_label)], [Paragraph(class_name, meta_value)]], colWidths=[3.8 * cm]),
        Table([[Paragraph('DATE LIMITE', meta_label)], [Paragraph(due_str, meta_value)]], colWidths=[5.5 * cm]),
        Table([[Paragraph('BARÈME', meta_label)], [Paragraph(f'{max_score} pts', meta_value)]], colWidths=[2.5 * cm]),
    ]]
    meta_table = Table(meta_table_data, colWidths=[4 * cm, 4 * cm, 5.5 * cm, 3.5 * cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('LINEAFTER', (0, 0), (2, 0), 0.5, HexColor('#e2e8f0')),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Description
    story.append(HRFlowable(width='100%', thickness=1.5, color=PINK, spaceAfter=6))
    story.append(Paragraph(description, p_desc))

    # ── Instructions
    instr_data = [[
        Paragraph(f'⚠ INSTRUCTIONS : {instructions}', p_instr)
    ]]
    instr_table = Table(instr_data, colWidths=[17 * cm])
    instr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#fffbeb')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#fde68a')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(instr_table)
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=HexColor('#e2e8f0'), spaceAfter=8))

    # ── Questions
    for q in questions:
        block = []

        # Numéro et libellé de la question
        q_header_data = [[
            Paragraph(f'Question {q["num"]}', ParagraphStyle(
                f'QN{q["num"]}', parent=styles['Normal'],
                fontSize=11, fontName='Helvetica-Bold', textColor=white,
            )),
            Paragraph(f'{q["points"]} pts', ParagraphStyle(
                f'QP{q["num"]}', parent=styles['Normal'],
                fontSize=11, fontName='Helvetica-Bold', textColor=white,
                alignment=TA_CENTER,
            )),
        ]]
        q_head_table = Table(q_header_data, colWidths=[13.5 * cm, 3.5 * cm])
        q_head_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#1e293b')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        block.append(q_head_table)
        block.append(Spacer(1, 0.25 * cm))
        block.append(Paragraph(q['text'], q_text))

        for sub in q.get('sub', []):
            block.append(Paragraph(f'• {sub}', q_sub))

        block.append(Spacer(1, 0.3 * cm))
        story.append(KeepTogether(block))

    # ── Barème récapitulatif
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width='100%', thickness=1.5, color=PINK, spaceAfter=8))
    story.append(Paragraph('RÉCAPITULATIF DU BARÈME', ParagraphStyle(
        'BaremeTitle', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold', textColor=DARK,
        alignment=TA_CENTER, spaceAfter=6,
    )))

    bareme_data = [['Question', 'Intitulé', 'Points']] + [
        [f'Question {q["num"]}', q['text'][:60] + '…' if len(q['text']) > 60 else q['text'], f'{q["points"]} pts']
        for q in questions
    ] + [['', 'TOTAL', f'{max_score} pts']]

    bareme_table = Table(bareme_data, colWidths=[2.5 * cm, 11 * cm, 3.5 * cm])
    bareme_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, LIGHT_GRAY]),
        ('BACKGROUND', (0, -1), (-1, -1), PINK_LIGHT),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), PINK),
        ('BOX', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, HexColor('#e2e8f0')),
    ])
    bareme_table.setStyle(bareme_style)
    story.append(bareme_table)

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph('— Fin du sujet — Bonne chance ! —', footer_style))

    doc.build(story)
    return buf.getvalue()


# ─── Commande ────────────────────────────────────────────────────────────────

TEXT_RESPONSES = [
    "J'ai analysé le problème et ma solution se base sur une approche itérative. La complexité obtenue est O(n log n) dans le meilleur cas.\n\nVoici mon implémentation :\n\n```python\ndef solution(lst):\n    if not lst:\n        return []\n    pivot = lst[len(lst) // 2]\n    left = [x for x in lst if x < pivot]\n    mid = [x for x in lst if x == pivot]\n    right = [x for x in lst if x > pivot]\n    return solution(left) + mid + solution(right)\n```\n\nLa complexité temporelle est O(n log n) en moyenne.",

    "Pour la question 1 :\n\nLa première forme normale (1NF) impose que chaque colonne d'une table contienne des valeurs atomiques.\nExemple non-normalisé : Client(id, nom, telephones) où telephones = '0102030405, 0607080910'\nCorrection : créer une table séparée Telephone(client_id, numero)\n\nPour la 2NF, toute dépendance non-clé doit dépendre de la totalité de la clé primaire...",

    "Réponse Question 2 :\n\nLes classes ont été implémentées avec les méthodes requises :\n\n```python\nfrom abc import ABC, abstractmethod\n\nclass Vehicule(ABC):\n    def __init__(self, marque, modele, annee, vitesse_max):\n        self._marque = marque\n        self._modele = modele\n        self.annee = annee\n        self.vitesse_max = vitesse_max\n        self._kilometrage = 0\n    \n    @abstractmethod\n    def description(self) -> str:\n        pass\n```\n\nLes tests unitaires ont tous été passés avec succès.",

    "Réponse aux questions du TP :\n\n1. Les protocoles TCP et UDP diffèrent principalement par leur mode de connexion. TCP établit une connexion fiable via le handshake 3-way, garantit l'ordre des paquets et la livraison. UDP est sans connexion, plus rapide mais sans garantie de livraison.\n\n2. Le handshake TCP :\n- SYN : le client envoie un segment avec le flag SYN\n- SYN-ACK : le serveur répond avec SYN+ACK\n- ACK : le client confirme\n\n3. NAT (Network Address Translation) permet de mapper plusieurs adresses privées vers une seule adresse publique.",
]

CORRECTION_FEEDBACKS = [
    'Très bon travail ! La solution est correcte et bien documentée. Quelques optimisations mineures possibles.',
    'Bonne approche mais des erreurs dans la complexité calculée. Relire la notation Big O.',
    'Solution fonctionnelle mais incomplète — les cas limites ne sont pas traités. Note plafonnée.',
    'Excellent ! Solution originale et optimisée. La documentation est exemplaire. Félicitations.',
    'Travail insuffisant. Les bases ne sont pas maîtrisées. Revoir les chapitres 1 à 3.',
    'Correct mais les tests unitaires sont absents. -3 points selon le barème.',
    'Bonne compréhension générale. Les requêtes SQL sont correctes mais pourraient être optimisées.',
]


class Command(BaseCommand):
    help = 'Crée des sujets de devoirs PDF réalistes et les associe à des devoirs'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Supprime les devoirs existants avant de créer')

    def handle(self, *args, **options):
        from apps.elearning.models import (
            Assignment, AssignmentSubmission, AssignmentCorrection
        )
        from apps.students.models import Student
        from apps.academic.models import Class as ClassModel, Subject

        self.stdout.write(self.style.MIGRATE_HEADING('=== Seed Devoirs avec PDF ===\n'))

        if options.get('clear'):
            count = Assignment.objects.count()
            Assignment.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'  🗑  {count} devoirs supprimés\n'))

        # ── Données académiques
        classes = list(ClassModel.objects.filter(is_active=True)[:5])
        if not classes:
            self.stdout.write(self.style.ERROR('❌ Aucune classe active trouvée. Lancez seed_academic d\'abord.'))
            return

        all_subjects = list(Subject.objects.filter(is_active=True))
        all_students = list(Student.objects.select_related('user').all()[:30])

        if not all_subjects:
            self.stdout.write(self.style.ERROR('❌ Aucune matière trouvée.'))
            return

        if not all_students:
            self.stdout.write(self.style.WARNING('⚠  Aucun étudiant — les soumissions ne seront pas créées.'))

        # ── Créer les devoirs
        created_assignments = []

        for i, adata in enumerate(SUBJECTS_DATA):
            cls = classes[i % len(classes)]
            class_name = getattr(cls, 'name', str(cls))

            # Cherche une matière qui correspond au mot-clé (ou la première dispo)
            kw = adata['subject_keyword'].lower()
            subject = next(
                (s for s in all_subjects if kw in (s.name or '').lower()),
                all_subjects[i % len(all_subjects)]
            )
            subject_name = getattr(subject, 'name', str(subject))

            due_date = timezone.now() + timedelta(days=adata['days_offset'])

            # ── Générer le PDF
            self.stdout.write(f'📄 Génération du PDF : {adata["title"]}')
            try:
                pdf_bytes = generate_pdf(
                    title=adata['title'],
                    subject_name=subject_name,
                    class_name=class_name,
                    due_date=due_date,
                    max_score=adata['max_score'],
                    description=adata['description'],
                    instructions=adata['instructions'],
                    questions=adata['questions'],
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'   ❌ Erreur PDF : {exc}'))
                pdf_bytes = None

            # ── Créer le devoir
            assignment = Assignment(
                title=adata['title'],
                description=adata['description'],
                instructions=adata['instructions'],
                class_obj=cls,
                subject=subject,
                max_score=adata['max_score'],
                due_date=due_date,
                status='PUBLISHED',
                allow_late_submission=adata['allow_late'],
                is_active=True,
            )

            if pdf_bytes:
                safe_title = adata['title'][:40].replace(' ', '_').replace('—', '-').replace('/', '-')
                filename = f'sujet_{safe_title}_{i+1}.pdf'
                assignment.attachment.save(filename, ContentFile(pdf_bytes), save=False)

            assignment.save()
            created_assignments.append((assignment, adata))
            self.stdout.write(self.style.SUCCESS(f'   ✓ Devoir créé : {assignment.title}'))

        # ── Créer les soumissions
        if all_students:
            self.stdout.write(self.style.MIGRATE_HEADING('\nCréation des soumissions...\n'))

            for assignment, adata in created_assignments:
                scenario = adata['scenario']
                n_students = min(15, len(all_students))
                sample = random.sample(all_students, n_students)

                for student in sample:
                    # Décide si l'étudiant a rendu
                    if scenario == 'pending' and random.random() < 0.7:
                        continue
                    if scenario == 'mixed' and random.random() < 0.3:
                        continue

                    # Évite les doublons
                    if AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists():
                        continue

                    use_text = random.random() > 0.35
                    sub = AssignmentSubmission(
                        assignment=assignment,
                        student=student,
                        content=random.choice(TEXT_RESPONSES) if use_text else '',
                        status='SUBMITTED',
                    )
                    sub.save()

                    # Correction selon le scénario
                    if scenario == 'graded' or (scenario == 'mixed' and random.random() > 0.4):
                        score = round(random.uniform(8, float(adata['max_score'])), 1)
                        AssignmentCorrection.objects.create(
                            submission=sub,
                            score=score,
                            feedback=random.choice(CORRECTION_FEEDBACKS),
                        )
                        sub.status = 'GRADED'
                        sub.save()

                self.stdout.write(f'  📝 Soumissions créées pour : {assignment.title}')

        total = len(created_assignments)
        pdfs = sum(1 for a, _ in created_assignments if a.attachment)
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ {total} devoirs créés dont {pdfs} avec PDF attaché.'
        ))
