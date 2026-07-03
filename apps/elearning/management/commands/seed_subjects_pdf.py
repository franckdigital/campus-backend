"""
seed_subjects_pdf.py — Génère des PDFs de sujets pour quizzes et examens (et devoirs manquants).

Usage :
    python manage.py seed_subjects_pdf
    python manage.py seed_subjects_pdf --clear   # supprime les fichiers existants d'abord
    python manage.py seed_subjects_pdf --type quiz
    python manage.py seed_subjects_pdf --type exam
    python manage.py seed_subjects_pdf --type assignment
"""
import io
import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

# ─── PDF helpers ─────────────────────────────────────────────────────────────

def make_pdf(title, kind, subject_name, class_name, meta, description, instructions, questions, max_score):
    """Génère un PDF professionnel A4 avec ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    PINK   = HexColor('#db2777')
    PURPLE = HexColor('#7c3aed')
    AMBER  = HexColor('#d97706')
    DARK   = HexColor('#0f172a')
    GRAY   = HexColor('#64748b')
    LIGHT  = HexColor('#f8fafc')
    WHITE  = white

    ACCENT = PURPLE if kind == 'quiz' else AMBER if kind == 'exam' else PINK

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    s_inst   = sty('inst',   fontSize=9,  textColor=GRAY, alignment=TA_CENTER)
    s_desc   = sty('desc',   fontSize=10, textColor=DARK, leading=15, alignment=TA_JUSTIFY, spaceAfter=4)
    s_instr  = sty('instr',  fontSize=9,  textColor=GRAY, leading=13, alignment=TA_JUSTIFY)
    s_meta_l = sty('ml',     fontSize=8,  textColor=GRAY, fontName='Helvetica-Bold')
    s_meta_v = sty('mv',     fontSize=10, textColor=DARK, fontName='Helvetica-Bold')
    s_qtext  = sty('qt',     fontSize=10, textColor=DARK, leading=15, alignment=TA_JUSTIFY, spaceAfter=4)
    s_qsub   = sty('qs',     fontSize=10, textColor=HexColor('#374151'), leading=15, leftIndent=14, spaceAfter=2)
    s_footer = sty('foot',   fontSize=8,  textColor=GRAY, alignment=TA_CENTER)
    s_bttl   = sty('bttl',   fontSize=11, textColor=DARK, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=6)

    story = []

    # En-tête
    story.append(Paragraph('CAMPUS LMS — Établissement d\'Enseignement Supérieur', s_inst))
    story.append(Paragraph('Année Universitaire 2025-2026', s_inst))
    story.append(Spacer(1, 0.3*cm))

    # Bandeau titre
    kind_label = {'quiz': 'QUIZ / ÉVALUATION', 'exam': 'EXAMEN SÉCURISÉ', 'assignment': 'DEVOIR / EXERCICE'}.get(kind, kind.upper())
    banner = Table([[Paragraph(
        f'<b>{kind_label}</b><br/>{title}',
        sty('bt', fontSize=14, textColor=WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER)
    )]], colWidths=[17*cm])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), ACCENT),
        ('TOPPADDING', (0,0),(-1,-1), 12),
        ('BOTTOMPADDING', (0,0),(-1,-1), 12),
        ('LEFTPADDING', (0,0),(-1,-1), 14),
        ('RIGHTPADDING', (0,0),(-1,-1), 14),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.5*cm))

    # Métadonnées
    meta_cells = [[
        Table([[Paragraph(k, s_meta_l)], [Paragraph(v, s_meta_v)]], colWidths=[w*cm])
        for (k, v, w) in meta
    ]]
    widths = [w for (_, _, w) in meta]
    mt = Table(meta_cells, colWidths=[w*cm for w in widths])
    mt.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), LIGHT),
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('TOPPADDING', (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING', (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 6),
        ('BOX', (0,0),(-1,-1), 0.5, HexColor('#e2e8f0')),
        ('LINEAFTER', (0,0),(-2,0), 0.5, HexColor('#e2e8f0')),
    ]))
    story.append(mt)
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=6))
    story.append(Paragraph(description, s_desc))

    # Instructions
    instr_t = Table([[Paragraph(f'⚠ INSTRUCTIONS : {instructions}', s_instr)]], colWidths=[17*cm])
    instr_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), HexColor('#fffbeb')),
        ('BOX', (0,0),(-1,-1), 1, HexColor('#fde68a')),
        ('TOPPADDING', (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING', (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 10),
    ]))
    story.append(instr_t)
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=HexColor('#e2e8f0'), spaceAfter=8))

    # Questions
    for q in questions:
        blk = []
        qh = Table([[
            Paragraph(f'Question {q["num"]}', sty(f'qh{q["num"]}', fontSize=11, fontName='Helvetica-Bold', textColor=WHITE)),
            Paragraph(f'{q["points"]} pts', sty(f'qp{q["num"]}', fontSize=11, fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER)),
        ]], colWidths=[13.5*cm, 3.5*cm])
        qh.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), DARK),
            ('TOPPADDING', (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
            ('LEFTPADDING', (0,0),(-1,-1), 10),
            ('RIGHTPADDING', (0,0),(-1,-1), 10),
            ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ]))
        blk.append(qh)
        blk.append(Spacer(1, 0.2*cm))
        blk.append(Paragraph(q['text'], s_qtext))
        for sub in q.get('sub', []):
            blk.append(Paragraph(f'• {sub}', s_qsub))
        blk.append(Spacer(1, 0.25*cm))
        story.append(KeepTogether(blk))

    # Barème
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width='100%', thickness=1.5, color=ACCENT, spaceAfter=6))
    story.append(Paragraph('RÉCAPITULATIF DU BARÈME', s_bttl))
    bareme_data = [['N°', 'Intitulé', 'Points']] + [
        [str(q['num']), (q['text'][:58] + '…' if len(q['text']) > 58 else q['text']), f'{q["points"]} pts']
        for q in questions
    ] + [['', 'TOTAL', f'{max_score} pts']]
    bt = Table(bareme_data, colWidths=[1.8*cm, 12.2*cm, 3*cm])
    bt.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,0), DARK),
        ('TEXTCOLOR', (0,0),(-1,0), WHITE),
        ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0),(-1,-1), 9),
        ('ALIGN', (0,0),(0,-1), 'CENTER'),
        ('ALIGN', (2,0),(2,-1), 'CENTER'),
        ('TOPPADDING', (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
        ('LEFTPADDING', (0,0),(-1,-1), 8),
        ('RIGHTPADDING', (0,0),(-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1),(-1,-2), [WHITE, LIGHT]),
        ('BACKGROUND', (0,-1),(-1,-1), HexColor('#f5f3ff') if kind == 'quiz' else HexColor('#fef3c7') if kind == 'exam' else HexColor('#fce7f3')),
        ('FONTNAME', (0,-1),(-1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,-1),(-1,-1), ACCENT),
        ('BOX', (0,0),(-1,-1), 0.5, HexColor('#e2e8f0')),
        ('INNERGRID', (0,0),(-1,-1), 0.25, HexColor('#e2e8f0')),
    ]))
    story.append(bt)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('— Fin du sujet — Bonne chance ! —', s_footer))

    doc.build(story)
    return buf.getvalue()


# ─── Données quiz ─────────────────────────────────────────────────────────────

QUIZ_SUBJECTS = [
    {
        'title': 'Quiz — Fondamentaux du Marketing Commercial',
        'description': 'Évaluation des connaissances en marketing opérationnel et stratégique : mix marketing, segmentation, comportement du consommateur.',
        'instructions': 'Répondez à toutes les questions. QCM et questions ouvertes. Durée : 20 minutes. Documents non autorisés.',
        'max_score': 20,
        'questions': [
            {'num': 1, 'text': 'Qu\'est-ce que le mix marketing (4P) ? Citez et définissez chaque composante.',
             'sub': ['Produit, Prix, Place (Distribution), Promotion', 'Donnez un exemple concret pour chacun des 4P appliqué à une marque de votre choix.'], 'points': 4},
            {'num': 2, 'text': 'Différenciez segmentation, ciblage et positionnement (SCP).',
             'sub': ['A) La segmentation divise le marché en groupes homogènes — Vrai ou Faux ? Justifiez.',
                     'B) Donnez 4 critères de segmentation différents avec un exemple chacun.',
                     'C) Qu\'est-ce qu\'un positionnement distinctif ? Donnez un exemple.'], 'points': 6},
            {'num': 3, 'text': 'Analysez le comportement du consommateur selon le modèle AIDA.',
             'sub': ['Définissez chaque étape : Attention, Intérêt, Désir, Action.',
                     'Comment une campagne publicitaire peut-elle exploiter ce modèle ?'], 'points': 4},
            {'num': 4, 'text': 'Qu\'est-ce que la veille concurrentielle et comment la mettre en place ?',
             'sub': ['Citez 3 outils de veille concurrentielle.',
                     'Quelle est la différence entre veille stratégique et veille commerciale ?'], 'points': 4},
            {'num': 5, 'text': 'Définissez le concept de valeur client (Customer Lifetime Value — CLV).',
             'sub': ['Pourquoi est-ce un indicateur clé en gestion commerciale ?',
                     'Comment augmenter la CLV sans augmenter les coûts d\'acquisition ?'], 'points': 2},
        ],
    },
    {
        'title': 'Évaluation — Droit du Travail & Relations Sociales',
        'description': 'Quiz de contrôle sur le droit du travail, le contrat de travail et les relations collectives.',
        'instructions': 'Répondez à toutes les questions. Pas de documents autorisés. Les réponses doivent être rédigées.',
        'max_score': 20,
        'questions': [
            {'num': 1, 'text': 'Quelles sont les principales différences entre CDI, CDD et contrat d\'intérim ?',
             'sub': ['Conditions de recours, durée maximale, renouvellement, rupture — complétez le tableau comparatif.',
                     'Dans quel cas peut-on requalifier un CDD en CDI ?'], 'points': 5},
            {'num': 2, 'text': 'Expliquez la procédure de licenciement pour motif personnel.',
             'sub': ['Quelles sont les étapes obligatoires (convocation, entretien, notification) ?',
                     'Qu\'est-ce que le préavis et comment est-il calculé ?',
                     'Quelle est la différence entre licenciement pour cause réelle et sérieuse et faute grave ?'], 'points': 6},
            {'num': 3, 'text': 'Quel est le rôle du Comité Social et Économique (CSE) ?',
             'sub': ['Dans quelles entreprises est-il obligatoire ?',
                     'Quelles sont ses attributions économiques et sociales ?',
                     'Comment sont élus les représentants du personnel ?'], 'points': 5},
            {'num': 4, 'text': 'Qu\'est-ce qu\'une convention collective ? Quel est son champ d\'application ?',
             'sub': ['Quelle est la hiérarchie entre la loi, la convention collective et le contrat de travail ?',
                     'Donnez un exemple de domaine couvert par une convention collective.'], 'points': 4},
        ],
    },
    {
        'title': 'Quiz de Contrôle — Management et Leadership',
        'description': 'Évaluation des théories managériales, styles de leadership et outils de pilotage organisationnel.',
        'instructions': 'Questions à réponse courte et questions de réflexion. Durée : 25 minutes.',
        'max_score': 20,
        'questions': [
            {'num': 1, 'text': 'Présentez les 4 styles de management du modèle de Hersey & Blanchard.',
             'sub': ['Directif, Persuasif, Participatif, Délégatif — définissez chacun.',
                     'À quel type de collaborateur correspond chaque style ?'], 'points': 5},
            {'num': 2, 'text': 'Qu\'est-ce que le management par objectifs (MBO) ? Quelles en sont les limites ?',
             'sub': ['Définissez un objectif SMART avec un exemple RH.',
                     'Quels sont les 3 risques principaux de ce type de management ?'], 'points': 5},
            {'num': 3, 'text': 'Expliquez la différence entre manager et leader.',
             'sub': ['Un bon manager est-il nécessairement un bon leader ? Justifiez.',
                     'Citez 3 qualités d\'un leader transformationnel.'], 'points': 4},
            {'num': 4, 'text': 'Qu\'est-ce que l\'intelligence émotionnelle selon Goleman ?',
             'sub': ['Citez et définissez les 5 composantes.',
                     'Pourquoi est-elle considérée comme essentielle pour un manager ?'], 'points': 4},
            {'num': 5, 'text': 'Définissez le tableau de bord de gestion (BSC — Balanced Scorecard).',
             'sub': ['Quelles sont les 4 perspectives du BSC ?',
                     'Comment l\'utilise-t-on pour piloter une équipe commerciale ?'], 'points': 2},
        ],
    },
]

# ─── Données examens ──────────────────────────────────────────────────────────

EXAM_SUBJECTS = [
    {
        'title': 'Examen Final — Gestion Commerciale et Stratégie d\'Entreprise',
        'exam_type': 'FINAL',
        'duration': 120,
        'max_score': 20,
        'description': 'Examen final couvrant la gestion commerciale, la stratégie d\'entreprise et l\'analyse de marché.',
        'instructions': 'Calculatrice autorisée. Documents interdits. Répondez directement sur ce sujet. Justifiez toutes vos réponses.',
        'questions': [
            {'num': 1, 'text': 'ANALYSE STRATÉGIQUE (8 pts) — Cas : Entreprise DISTRIB+, grossiste en fournitures de bureau',
             'sub': [
                 'a) Réalisez une analyse SWOT complète de DISTRIB+ sur son marché actuel (4 pts)',
                 '   — Forces : réseau de 150 commerciaux, délais de livraison 24h, certifié ISO 9001',
                 '   — Menaces : e-commerce croissant, arrivée d\'Amazon Business, hausse des matières premières',
                 'b) Identifiez 2 opportunités de développement et proposez une stratégie pour chacune (2 pts)',
                 'c) Selon le modèle de Porter, quelles sont les 5 forces qui pèsent sur DISTRIB+ ? (2 pts)',
             ], 'points': 8},
            {'num': 2, 'text': 'GESTION COMMERCIALE (7 pts) — Politique tarifaire et négociation',
             'sub': [
                 'a) Définissez 3 méthodes de fixation du prix et précisez dans quel contexte les appliquer (3 pts)',
                 'b) Qu\'est-ce que la marge brute commerciale ? Calculez-la pour un article acheté à 45 € HT et vendu à 72 € HT (2 pts)',
                 'c) Quelles sont les 4 étapes clés d\'une négociation commerciale réussie ? (2 pts)',
             ], 'points': 7},
            {'num': 3, 'text': 'GESTION DE LA RELATION CLIENT (5 pts)',
             'sub': [
                 'a) Qu\'est-ce que le CRM ? Quels sont ses 3 piliers principaux ? (2 pts)',
                 'b) Expliquez la différence entre client actif, client dormant et prospect chaud. (1 pt)',
                 'c) Proposez un plan de fidélisation client pour DISTRIB+ sur 6 mois. (2 pts)',
             ], 'points': 5},
        ],
    },
    {
        'title': 'Partiel — Gestion des Ressources Humaines',
        'exam_type': 'MID',
        'duration': 90,
        'max_score': 20,
        'description': 'Contrôle de mi-semestre sur la GRH : recrutement, formation, gestion des compétences et droit social.',
        'instructions': 'Documents interdits. Répondez directement sur ce sujet. Soignez la présentation et structurez vos réponses.',
        'questions': [
            {'num': 1, 'text': 'RECRUTEMENT ET INTÉGRATION (7 pts)',
             'sub': [
                 'a) Décrivez les 6 étapes d\'un processus de recrutement efficace. (3 pts)',
                 'b) Qu\'est-ce qu\'un profil de poste ? Quelles informations doit-il contenir ? (2 pts)',
                 'c) Proposez un programme d\'intégration (onboarding) pour un nouveau commercial. Durée : 4 semaines. (2 pts)',
             ], 'points': 7},
            {'num': 2, 'text': 'FORMATION ET DÉVELOPPEMENT DES COMPÉTENCES (7 pts)',
             'sub': [
                 'a) Qu\'est-ce que le Plan de Développement des Compétences (PDC) ? Qui est concerné ? (2 pts)',
                 'b) Différenciez formation présentielle, e-learning et formation en situation de travail (FEST). (3 pts)',
                 'c) Expliquez la méthode d\'évaluation des formations de Kirkpatrick (4 niveaux). (2 pts)',
             ], 'points': 7},
            {'num': 3, 'text': 'GESTION DES PERFORMANCES ET ENTRETIENS (6 pts)',
             'sub': [
                 'a) Quel est l\'objectif d\'un entretien annuel d\'évaluation ? Quelles en sont les limites ? (2 pts)',
                 'b) Qu\'est-ce qu\'un entretien professionnel ? Le distinguez-vous de l\'entretien d\'évaluation. (2 pts)',
                 'c) Définissez les indicateurs RH clés : taux d\'absentéisme, turn-over, ratio formation/masse salariale. (2 pts)',
             ], 'points': 6},
        ],
    },
    {
        'title': 'Examen de Contrôle — Théories et Pratiques du Management',
        'exam_type': 'TP',
        'duration': 120,
        'max_score': 20,
        'description': 'Évaluation approfondie des théories managériales, de la conduite du changement et du pilotage d\'équipe.',
        'instructions': 'Cours autorisés, internet interdit. Toutes les réponses doivent être argumentées. Les exemples concrets sont valorisés.',
        'questions': [
            {'num': 1, 'text': 'THÉORIES DU MANAGEMENT (6 pts) — Analyse comparative',
             'sub': [
                 'a) Comparez le management taylorien (OST) et le management participatif. Points communs et divergences. (3 pts)',
                 'b) En quoi la théorie Y de McGregor s\'oppose-t-elle à la théorie X ? Donnez un exemple d\'application concrète en entreprise. (3 pts)',
             ], 'points': 6},
            {'num': 2, 'text': 'CONDUITE DU CHANGEMENT (8 pts) — Cas pratique',
             'sub': [
                 'Contexte : La société OPTIMA (250 salariés) décide de mettre en place un nouveau système ERP.',
                 'Les employés sont résistants. 30% envisagent de quitter l\'entreprise.',
                 'a) Identifiez les sources de résistance au changement selon le modèle de Kotter. (2 pts)',
                 'b) Proposez un plan de conduite du changement en 5 étapes. (3 pts)',
                 'c) Comment communiquer le changement efficacement à toutes les parties prenantes ? (3 pts)',
             ], 'points': 8},
            {'num': 3, 'text': 'PILOTAGE ET PERFORMANCE (6 pts)',
             'sub': [
                 'a) Définissez la notion de délégation. Quelles conditions doivent être réunies pour qu\'elle soit efficace ? (2 pts)',
                 'b) Qu\'est-ce que la cohésion d\'équipe ? Donnez 3 facteurs qui la renforcent et 2 qui la détruisent. (2 pts)',
                 'c) Rédigez les objectifs annuels SMART pour un responsable commercial d\'une PME de négoce. (2 pts)',
             ], 'points': 6},
        ],
    },
]

# ─── Commande ────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Génère des PDFs de sujets pour quizzes, examens et devoirs (côté prof)'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Efface les fichiers sujet existants avant de regénérer')
        parser.add_argument('--type', choices=['quiz', 'exam', 'assignment', 'all'], default='all',
                            help='Type de sujet à générer (défaut : all)')

    def handle(self, *args, **options):
        from apps.elearning.models import Quiz, SecureExam, Assignment
        from apps.academic.models import Class as ClassModel, Subject

        target = options.get('type', 'all')
        self.stdout.write(self.style.MIGRATE_HEADING(f'=== Seed Sujets PDF ({target}) ===\n'))

        if options.get('clear'):
            if target in ('quiz', 'all'):
                Quiz.objects.all().update(subject_file=None)
                self.stdout.write(self.style.WARNING('  🗑  Fichiers quiz effacés'))
            if target in ('exam', 'all'):
                SecureExam.objects.all().update(subject_file=None)
                self.stdout.write(self.style.WARNING('  🗑  Fichiers examen effacés'))
            if target in ('assignment', 'all'):
                Assignment.objects.all().update(attachment=None)
                self.stdout.write(self.style.WARNING('  🗑  Fichiers devoir effacés'))

        classes  = list(ClassModel.objects.filter(is_active=True)[:5])
        subjects = list(Subject.objects.filter(is_active=True))

        if not classes or not subjects:
            self.stdout.write(self.style.ERROR('❌ Aucune classe ou matière active. Lancez seed_academic d\'abord.'))
            return

        # ── Quiz
        if target in ('quiz', 'all'):
            self._seed_quiz_subjects(Quiz, classes, subjects)

        # ── Examens
        if target in ('exam', 'all'):
            self._seed_exam_subjects(SecureExam, classes, subjects)

        # ── Devoirs manquants
        if target in ('assignment', 'all'):
            self._seed_missing_assignment_pdfs(Assignment)

        self.stdout.write(self.style.SUCCESS('\n✅ Sujets PDF générés avec succès.'))

    # ── Quiz subjects ─────────────────────────────────────────────────────────

    def _seed_quiz_subjects(self, Quiz, classes, subjects):
        from apps.elearning.models import Question, Choice
        from datetime import timedelta
        from django.utils import timezone

        self.stdout.write(self.style.MIGRATE_HEADING('\n— Quiz sujets PDF —'))

        quizzes = list(Quiz.objects.filter(subject_file='').select_related('class_obj', 'subject')[:10])
        if not quizzes:
            quizzes = list(Quiz.objects.filter(subject_file__isnull=True).select_related('class_obj', 'subject')[:10])

        if not quizzes:
            # Crée de nouveaux quizzes avec PDF
            self.stdout.write('  Aucun quiz sans sujet — création de nouveaux quiz...')
            for i, qdata in enumerate(QUIZ_SUBJECTS):
                cls = classes[i % len(classes)]
                subj = subjects[i % len(subjects)]
                q = Quiz.objects.create(
                    title=qdata['title'],
                    description=qdata['description'],
                    class_obj=cls,
                    subject=subj,
                    time_limit_minutes=20,
                    pass_score_percent=50,
                    is_published=True,
                )
                for qi, qitem in enumerate(qdata['questions']):
                    question = Question.objects.create(
                        quiz=q,
                        question_type='TEXT',
                        text=qitem['text'],
                        points=qitem['points'],
                        order=qi,
                        explanation='; '.join(qitem.get('sub', [])),
                    )
                quizzes.append(q)
                self.stdout.write(f'  + Quiz créé : {q.title}')

        for i, quiz in enumerate(quizzes):
            if quiz.subject_file:
                continue
            qdata = QUIZ_SUBJECTS[i % len(QUIZ_SUBJECTS)]
            class_name = getattr(quiz.class_obj, 'name', str(quiz.class_obj))
            subject_name = getattr(quiz.subject, 'name', str(quiz.subject))

            meta = [
                ('MATIÈRE', subject_name, 4.5),
                ('CLASSE', class_name, 4.0),
                ('DURÉE', f'{quiz.time_limit_minutes or 20} min', 3.5),
                ('BARÈME', f'{qdata["max_score"]} pts', 3.0),
                ('SEUIL', f'{quiz.pass_score_percent}%', 2.0),
            ]
            try:
                pdf = make_pdf(
                    title=quiz.title, kind='quiz',
                    subject_name=subject_name, class_name=class_name,
                    meta=meta,
                    description=qdata['description'],
                    instructions=qdata['instructions'],
                    questions=qdata['questions'],
                    max_score=qdata['max_score'],
                )
                fname = f'quiz_sujet_{quiz.id}.pdf'
                quiz.subject_file.save(fname, ContentFile(pdf), save=True)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Quiz PDF : {quiz.title}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Erreur quiz {quiz.id} : {e}'))

    # ── Exam subjects ─────────────────────────────────────────────────────────

    def _seed_exam_subjects(self, SecureExam, classes, subjects):
        from datetime import timedelta
        from django.utils import timezone

        self.stdout.write(self.style.MIGRATE_HEADING('\n— Examen sujets PDF —'))

        exams = list(SecureExam.objects.filter(subject_file='').select_related('class_obj', 'subject')[:10])
        if not exams:
            exams = list(SecureExam.objects.filter(subject_file__isnull=True).select_related('class_obj', 'subject')[:10])

        if not exams:
            self.stdout.write('  Aucun examen sans sujet — création de nouveaux examens...')
            now = timezone.now()
            for i, edata in enumerate(EXAM_SUBJECTS):
                cls = classes[i % len(classes)]
                subj = subjects[i % len(subjects)]
                exam = SecureExam.objects.create(
                    title=edata['title'],
                    description=edata['description'],
                    class_obj=cls,
                    subject=subj,
                    exam_type=edata['exam_type'],
                    duration_minutes=edata['duration'],
                    max_score=edata['max_score'],
                    start_date=now - timedelta(days=3),
                    end_date=now - timedelta(days=1),
                    is_published=True,
                    pass_score_percent=50,
                    fullscreen_required=True,
                    block_copy_paste=True,
                )
                exams.append(exam)
                self.stdout.write(f'  + Examen créé : {exam.title}')

        for i, exam in enumerate(exams):
            if exam.subject_file:
                continue
            edata = EXAM_SUBJECTS[i % len(EXAM_SUBJECTS)]
            class_name  = getattr(exam.class_obj, 'name', str(exam.class_obj))
            subject_name = getattr(exam.subject, 'name', str(exam.subject))
            start_str = exam.start_date.strftime('%d/%m/%Y') if exam.start_date else '—'
            duration_str = f'{exam.duration_minutes} min'
            max_score = float(exam.max_score or edata['max_score'])

            meta = [
                ('MATIÈRE', subject_name, 4.5),
                ('CLASSE', class_name, 3.5),
                ('DATE', start_str, 3.5),
                ('DURÉE', duration_str, 2.5),
                ('BARÈME', f'{max_score:.0f} pts', 3.0),
            ]
            try:
                pdf = make_pdf(
                    title=exam.title, kind='exam',
                    subject_name=subject_name, class_name=class_name,
                    meta=meta,
                    description=edata['description'],
                    instructions=edata['instructions'],
                    questions=edata['questions'],
                    max_score=max_score,
                )
                fname = f'exam_sujet_{exam.id}.pdf'
                exam.subject_file.save(fname, ContentFile(pdf), save=True)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Exam PDF : {exam.title}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Erreur exam {exam.id} : {e}'))

    # ── Devoirs manquants ─────────────────────────────────────────────────────

    def _seed_missing_assignment_pdfs(self, Assignment):
        from apps.elearning.management.commands.seed_assignments_pdf import (
            SUBJECTS_DATA, generate_pdf,
        )
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Devoirs sans PDF —'))

        missing = Assignment.objects.filter(attachment='', status='PUBLISHED')
        if not missing.exists():
            missing = Assignment.objects.filter(attachment__isnull=True, status='PUBLISHED')
        if not missing.exists():
            self.stdout.write('  Tous les devoirs publiés ont déjà un PDF.')
            return

        for i, a in enumerate(missing[:10]):
            adata = SUBJECTS_DATA[i % len(SUBJECTS_DATA)]
            due = a.due_date
            class_name = getattr(a.class_obj, 'name', str(a.class_obj))
            subject_name = getattr(a.subject, 'name', str(a.subject))
            try:
                pdf = generate_pdf(
                    title=a.title,
                    subject_name=subject_name,
                    class_name=class_name,
                    due_date=due,
                    max_score=float(a.max_score),
                    description=a.description or adata['description'],
                    instructions=a.instructions or adata['instructions'],
                    questions=adata['questions'],
                )
                fname = f'devoir_sujet_{a.id}.pdf'
                a.attachment.save(fname, ContentFile(pdf), save=True)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Devoir PDF : {a.title}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ❌ Erreur devoir {a.id} : {e}'))
