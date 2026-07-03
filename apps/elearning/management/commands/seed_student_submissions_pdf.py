"""
seed_student_submissions_pdf.py — Crée des soumissions PDF d'étudiants pour devoirs,
examens et quiz, + corrections PDF du prof (corrected_file).

Usage :
    python manage.py seed_student_submissions_pdf
    python manage.py seed_student_submissions_pdf --clear
    python manage.py seed_student_submissions_pdf --type assignment
    python manage.py seed_student_submissions_pdf --type exam
    python manage.py seed_student_submissions_pdf --type quiz
"""
import io
import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone

# ─── Contenu fictif des copies étudiantes ─────────────────────────────────────

STUDENT_ANSWERS = [
    {
        'title': 'Analyse du marché et stratégie commerciale',
        'content': [
            ('Introduction', "Dans ce travail, j'analyserai le marché de la grande distribution en France en appliquant les outils vus en cours : SWOT, PESTEL et les 5 forces de Porter."),
            ('Analyse SWOT', "Forces : notoriété de la marque, réseau de distribution étendu.\nFaiblesses : marges faibles, dépendance aux fournisseurs.\nOpportunités : croissance du e-commerce, demande bio en hausse.\nMenaces : concurrence des hard-discounts, inflation des matières premières."),
            ('Analyse PESTEL', "Politique : réglementations sur les emballages plastiques (loi AGEC).\nÉconomique : pouvoir d'achat en baisse → report vers les MDD.\nSocial : consommateurs plus exigeants sur la traçabilité.\nTechnologique : digitalisation des points de vente, self-checkout.\nEnvironnemental : bilan carbone, déchets alimentaires.\nLégal : loi EGAlim, négociations commerciales annuelles."),
            ('Recommandations', "Je préconise une stratégie de différenciation par la qualité et le local, avec un renforcement de l\'offre en ligne (click-and-collect)."),
        ],
        'pages': 4,
    },
    {
        'title': 'Cas pratique RH — Gestion des conflits en entreprise',
        'content': [
            ('Présentation du cas', "L'entreprise TechPME (150 salariés, secteur informatique) fait face à un conflit entre l'équipe commerciale et l'équipe technique suite à des objectifs contradictoires."),
            ('Diagnostic du conflit', "Type de conflit : inter-groupes (commercial vs. technique).\nCauses profondes :\n1. Objectifs divergents (CA immédiat vs. qualité produit)\n2. Communication insuffisante entre les équipes\n3. Absence de référent transverse\nSignes : réunions tendues, délais non respectés, turnover en hausse."),
            ('Analyse selon la grille de Thomas-Kilmann', "Les commerciaux adoptent une posture de compétition (win-lose).\nLes techniciens sont dans l\'évitement.\nLe management opte pour le compromis, sans résoudre le fond."),
            ('Plan d\'action proposé', "1. Médiation externe (3 séances)\n2. Atelier co-construction des objectifs partagés\n3. Mise en place d\'un comité de pilotage mixte\n4. Révision du système d\'évaluation et de rémunération variable\n5. Formation communication non-violente pour les managers"),
            ('Conclusion', "Ce conflit révèle un problème structurel d'organisation. La résolution durable passe par une refonte partielle de la culture managériale."),
        ],
        'pages': 5,
    },
    {
        'title': 'Rapport — Leadership et styles de management',
        'content': [
            ('Introduction', "Ce rapport examine les quatre grands styles de leadership selon le modèle Hersey & Blanchard et analyse leur application dans le contexte de l'entreprise moderne."),
            ('Les 4 styles de management', "1. Directif (S1) : adapté aux collaborateurs débutants — le manager prescrit et contrôle.\n2. Persuasif (S2) : le manager explique et motive — collaborateurs en apprentissage.\n3. Participatif (S3) : le manager délègue la réflexion et conserve la décision.\n4. Délégatif (S4) : autonomie totale — collaborateurs experts et motivés."),
            ('Étude de cas : Amazon vs. Patagonia', "Amazon : management directif et par objectifs chiffrés (OKR). Forte pression de performance, turnover élevé.\nPatagonia : management délégatif, culture de confiance, faible turnover, forte adhésion aux valeurs.\nLeçon : le style doit s\'adapter à la maturité des équipes et aux valeurs de l\'organisation."),
            ('Le leadership situationnel appliqué', "Dans mon stage en entreprise, j'ai observé un manager utilisant S2 avec les nouveaux entrants et S4 avec les seniors. Cette flexibilité a réduit le temps d'onboarding de 30%."),
            ('Conclusion', "Il n'existe pas de style universellement supérieur. L'efficacité du leadership repose sur l'adéquation entre le style et la situation."),
        ],
        'pages': 5,
    },
    {
        'title': 'Analyse financière — Compte de résultat et rentabilité',
        'content': [
            ('Présentation de l\'entreprise', "Entreprise analysée : Carrefour SA. Données issues du rapport annuel 2023."),
            ('Analyse du compte de résultat', "Chiffre d'affaires : 88,2 Md€ (+4,2% vs. 2022)\nRBE (EBITDA) : 3,8 Md€ — marge EBITDA : 4,3%\nRésultat opérationnel : 1,4 Md€\nRésultat net part du groupe : 612 M€\nBPA : 0,82€"),
            ('Calcul des ratios', "Marge brute : 22,4%\nMarge opérationnelle : 1,6% (faible, secteur grande distribution)\nROE : 8,2%\nROCE : 6,7%\nEBITDA/CA : 4,3%\nDette nette/EBITDA : 2,3x (niveau acceptable)"),
            ('Analyse comparative sectorielle', "Versus Leclerc (non coté, CA estimé 46 Md€) : Carrefour plus diversifié géographiquement mais moins rentable sur le marché français.\nVersus Aldi : écart significatif de structure de coûts."),
            ('Conclusion et recommandations', "La rentabilité reste sous pression malgré la reprise post-Covid. La diversification vers les services (Carrefour Voyages, assurance) devrait améliorer les marges à terme."),
        ],
        'pages': 6,
    },
    {
        'title': 'Plan de recrutement et GPEC',
        'content': [
            ('Contexte', "La société LogiTrans (transport & logistique, 800 salariés) souhaite développer sa branche e-commerce. Elle doit recruter 45 personnes en 18 mois."),
            ('Analyse des besoins', "Postes prioritaires :\n- 12 gestionnaires de stock (BTS/Licence)\n- 8 développeurs full-stack (Bac+5)\n- 10 commerciaux terrain (BTS force de vente)\n- 8 chargés de clientèle e-commerce\n- 7 responsables logistique"),
            ('Processus de recrutement proposé', "Phase 1 : Sourcing (jobboards, LinkedIn, cooptation, écoles partenaires)\nPhase 2 : Pré-sélection (CV + questionnaire de présélection)\nPhase 3 : Entretiens (RH + opérationnel + test technique selon poste)\nPhase 4 : Onboarding 30 jours\nKPI : Time-to-hire < 35 jours, taux de rétention 1 an > 80%"),
            ('GPEC — Gestion prévisionnelle', "Cartographie des compétences actuelle : 3 domaines critiques en tension.\nPlan de formation associé : 120 000€ budget formation année N.\nMobilités internes identifiées : 8 collaborateurs pouvant évoluer vers les nouveaux postes."),
            ('Budget et ROI', "Coût total recrutement estimé : 285 000€\nROI attendu à 18 mois : chiffre d'affaires e-commerce supplémentaire de 4,2 M€"),
        ],
        'pages': 6,
    },
]

STUDENT_CORRECTIONS = [
    {
        'feedback': 'Excellent travail ! Analyse rigoureuse et bien structurée. Les recommandations sont pertinentes et argumentées. Quelques fautes de syntaxe mineures.',
        'note_comment': 'Très satisfaisant.',
        'corrections': [
            ('Q1', 'L\'analyse SWOT est complète et cohérente avec les données du secteur. +'),
            ('Q2', 'L\'analyse PESTEL intègre bien la dimension légale (loi AGEC). Bonne maîtrise.'),
            ('Q3', 'Les recommandations manquent de chiffrage. Prévoir des KPI mesurables.'),
        ],
    },
    {
        'feedback': 'Bonne compréhension du cas. La grille Thomas-Kilmann est bien appliquée. Le plan d\'action manque de réalisme budgétaire — chiffrez les actions.',
        'note_comment': 'Correct mais perfectible.',
        'corrections': [
            ('Q1', 'Diagnostic pertinent. Les causes profondes sont bien identifiées.'),
            ('Q2', 'Application correcte de Thomas-Kilmann, mais la nuance S3 aurait été appropriée.'),
            ('Q3', 'Plan d\'action trop général. Manque de planification (qui fait quoi, quand, avec quel budget).'),
        ],
    },
    {
        'feedback': 'Travail solide sur les styles de management. L\'étude de cas Amazon/Patagonia est pertinente. Développez davantage la partie leadership situationnel.',
        'note_comment': 'Satisfaisant.',
        'corrections': [
            ('Q1', 'Les 4 styles sont bien décrits. La référence à Hersey & Blanchard est correcte.'),
            ('Q2', 'Bonne analyse comparative mais manque de données chiffrées sur le turnover Patagonia.'),
            ('Q3', 'L\'exemple du stage est valorisé. Bien ancré dans la réalité professionnelle.'),
        ],
    },
    {
        'feedback': 'Analyse financière correcte. Les ratios sont bien calculés. Attention à l\'analyse sectorielle : les données Leclerc sont des estimations à nuancer.',
        'note_comment': 'Niveau satisfaisant.',
        'corrections': [
            ('Ratios', 'Calculs exacts. La marge opérationnelle est cohérente avec le secteur.'),
            ('Comparaison', 'Comparer avec Aldi (hard discount) n\'est pas pertinent structurellement. Préférer Ahold Delhaize.'),
            ('Conclusion', 'Recommandations réalistes. La diversification services est bien identifiée comme levier.'),
        ],
    },
    {
        'feedback': 'Très bon plan de recrutement. La GPEC est traitée avec sérieux. Le budget est réaliste. Dommage que le plan de formation ne détaille pas les modules.',
        'note_comment': 'Très bon travail.',
        'corrections': [
            ('Sourcing', 'Mix de canaux pertinent. La cooptation est souvent sous-utilisée — bon réflexe.'),
            ('KPI', 'Les KPI sont mesurables. Ajouter le coût par embauche (CPH) au tableau de bord.'),
            ('GPEC', 'Cartographie correcte. Manque la matrice compétences actuelles vs. compétences cibles.'),
        ],
    },
]


def generate_student_pdf(student_name, assignment_title, answers):
    """Génère un PDF de copie étudiant avec ReportLab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    PINK = HexColor('#db2777')
    DARK = HexColor('#0f172a')
    GRAY = HexColor('#64748b')
    LIGHT = HexColor('#f8fafc')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    story = []

    # En-tête
    story.append(Paragraph('CAMPUS LMS — Travail Étudiant', sty('inst', fontSize=9, textColor=GRAY, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.2*cm))

    # Bandeau
    banner = Table([[Paragraph(
        f'COPIE DE : {student_name.upper()}',
        sty('bn', fontSize=13, textColor=white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    )]], colWidths=[17*cm])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), DARK),
        ('TOPPADDING', (0,0),(-1,-1), 10),
        ('BOTTOMPADDING', (0,0),(-1,-1), 10),
    ]))
    story.append(banner)

    sub_banner = Table([[Paragraph(
        assignment_title,
        sty('sb', fontSize=11, textColor=white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    )]], colWidths=[17*cm])
    sub_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), PINK),
        ('TOPPADDING', (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(sub_banner)
    story.append(Spacer(1, 0.6*cm))

    # Réponses
    for section_title, section_body in answers:
        story.append(Paragraph(
            section_title,
            sty(f's_{section_title[:8]}', fontSize=12, fontName='Helvetica-Bold', textColor=DARK,
                spaceBefore=10, spaceAfter=4, borderPad=4)
        ))
        story.append(HRFlowable(width='100%', thickness=0.5, color=PINK, spaceAfter=4))
        # Paragraphes du corps (split sur les sauts de ligne)
        for line in section_body.split('\n'):
            if line.strip():
                story.append(Paragraph(
                    line,
                    sty(f'b_{hash(line)%9999}', fontSize=10, textColor=DARK, leading=15,
                        alignment=TA_JUSTIFY, spaceAfter=2)
                ))
        story.append(Spacer(1, 0.3*cm))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f'— Copie de {student_name} — Document généré automatiquement —',
                            sty('foot', fontSize=8, textColor=GRAY, alignment=TA_CENTER)))

    doc.build(story)
    return buf.getvalue()


def generate_correction_pdf(student_name, assignment_title, score, max_score, feedback, corrections):
    """Génère un PDF de correction du professeur."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

    GREEN = HexColor('#059669')
    DARK  = HexColor('#0f172a')
    GRAY  = HexColor('#64748b')
    LIGHT = HexColor('#f0fdf4')
    PINK  = HexColor('#db2777')
    RED   = HexColor('#dc2626')

    pct = score / max_score * 100 if max_score > 0 else 0
    color = GREEN if pct >= 50 else RED

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    story = []

    # En-tête
    story.append(Paragraph('CAMPUS LMS — Correction du Professeur', sty('inst', fontSize=9, textColor=GRAY, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.2*cm))

    # Bandeau
    banner = Table([[Paragraph(
        f'CORRECTION — {student_name.upper()}',
        sty('bn', fontSize=13, textColor=white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    )]], colWidths=[17*cm])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), color),
        ('TOPPADDING', (0,0),(-1,-1), 10),
        ('BOTTOMPADDING', (0,0),(-1,-1), 10),
    ]))
    story.append(banner)

    sub_banner = Table([[Paragraph(
        assignment_title,
        sty('sb', fontSize=11, textColor=white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    )]], colWidths=[17*cm])
    sub_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), DARK),
        ('TOPPADDING', (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(sub_banner)
    story.append(Spacer(1, 0.5*cm))

    # Note
    note_tbl = Table([[
        Paragraph('NOTE OBTENUE', sty('nl', fontSize=9, textColor=GRAY, fontName='Helvetica-Bold')),
        Paragraph(f'{score} / {max_score}', sty('nv', fontSize=28, textColor=color, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph(f'{pct:.1f}%', sty('np', fontSize=18, textColor=color, fontName='Helvetica-Bold', alignment=TA_CENTER)),
        Paragraph('MENTION', sty('ml', fontSize=9, textColor=GRAY, fontName='Helvetica-Bold')),
        Paragraph('Bien' if pct >= 70 else 'Assez bien' if pct >= 60 else 'Passable' if pct >= 50 else 'Insuffisant',
                  sty('mv', fontSize=14, textColor=color, fontName='Helvetica-Bold')),
    ]], colWidths=[3.5*cm, 4*cm, 3*cm, 2.5*cm, 4*cm])
    note_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), LIGHT if pct >= 50 else HexColor('#fef2f2')),
        ('BOX', (0,0),(-1,-1), 1, color),
        ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0),(-1,-1), 12),
        ('BOTTOMPADDING', (0,0),(-1,-1), 12),
        ('LEFTPADDING', (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 10),
        ('LINEAFTER', (0,0),(3,0), 0.5, HexColor('#e2e8f0')),
    ]))
    story.append(note_tbl)
    story.append(Spacer(1, 0.5*cm))

    # Appréciation générale
    story.append(Paragraph('APPRÉCIATION GÉNÉRALE', sty('ap_h', fontSize=11, fontName='Helvetica-Bold', textColor=DARK, spaceAfter=4)))
    story.append(HRFlowable(width='100%', thickness=1, color=GREEN, spaceAfter=4))
    feedback_tbl = Table([[Paragraph(feedback, sty('fb', fontSize=10, textColor=DARK, leading=15, alignment=TA_JUSTIFY))]], colWidths=[17*cm])
    feedback_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), LIGHT if pct >= 50 else HexColor('#fef2f2')),
        ('BOX', (0,0),(-1,-1), 0.5, HexColor('#d1fae5') if pct >= 50 else HexColor('#fecaca')),
        ('TOPPADDING', (0,0),(-1,-1), 10),
        ('BOTTOMPADDING', (0,0),(-1,-1), 10),
        ('LEFTPADDING', (0,0),(-1,-1), 12),
        ('RIGHTPADDING', (0,0),(-1,-1), 12),
    ]))
    story.append(feedback_tbl)
    story.append(Spacer(1, 0.5*cm))

    # Commentaires par question
    if corrections:
        story.append(Paragraph('COMMENTAIRES DÉTAILLÉS', sty('cmt_h', fontSize=11, fontName='Helvetica-Bold', textColor=DARK, spaceAfter=4)))
        story.append(HRFlowable(width='100%', thickness=1, color=GRAY, spaceAfter=4))
        for q_label, comment in corrections:
            cmt = Table([[
                Paragraph(q_label, sty(f'ql_{q_label}', fontSize=10, fontName='Helvetica-Bold', textColor=DARK)),
                Paragraph(comment, sty(f'qc_{q_label}', fontSize=10, textColor=HexColor('#374151'), leading=14)),
            ]], colWidths=[2.5*cm, 14.5*cm])
            cmt.setStyle(TableStyle([
                ('VALIGN', (0,0),(-1,-1), 'TOP'),
                ('TOPPADDING', (0,0),(-1,-1), 5),
                ('BOTTOMPADDING', (0,0),(-1,-1), 5),
                ('LEFTPADDING', (0,0),(-1,-1), 6),
                ('RIGHTPADDING', (0,0),(-1,-1), 6),
                ('LINEBELOW', (0,0),(-1,-1), 0.25, HexColor('#f1f5f9')),
            ]))
            story.append(cmt)
        story.append(Spacer(1, 0.3*cm))

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('— Document confidentiel — Correction établie par le corps enseignant de Campus LMS —',
                            sty('foot', fontSize=8, textColor=GRAY, alignment=TA_CENTER)))
    doc.build(story)
    return buf.getvalue()


# ─── Command ──────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Crée des copies PDF d\'étudiants + corrections PDF du prof pour devoirs, examens et quiz'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Supprime les soumissions/corrections existantes avant de recréer')
        parser.add_argument('--type', choices=['assignment', 'exam', 'quiz', 'all'], default='all',
                            help='Type de travaux à créer (défaut: all)')
        parser.add_argument('--max-students', type=int, default=8,
                            help='Nombre max d\'étudiants par devoir/exam (défaut: 8)')

    def handle(self, *args, **options):
        from apps.elearning.models import (
            Assignment, AssignmentSubmission, AssignmentCorrection,
            Quiz, QuizAttempt, AttemptAnswer, Question, Choice,
            SecureExam, ExamSession,
        )
        from apps.students.models import Student

        target = options.get('type', 'all')
        max_stu = options.get('max_students', 8)

        self.stdout.write(self.style.MIGRATE_HEADING(f'=== Seed Soumissions Étudiants ({target}) ===\n'))

        students = list(Student.objects.select_related('user').all()[:30])
        if not students:
            self.stdout.write(self.style.ERROR('❌ Aucun étudiant trouvé. Lancez seed_students d\'abord.'))
            return

        if options.get('clear'):
            if target in ('assignment', 'all'):
                n = AssignmentSubmission.objects.count()
                AssignmentSubmission.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'  🗑  {n} soumissions supprimées'))
            if target in ('exam', 'all'):
                n = ExamSession.objects.count()
                ExamSession.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'  🗑  {n} sessions examen supprimées'))
            if target in ('quiz', 'all'):
                n = QuizAttempt.objects.count()
                QuizAttempt.objects.all().delete()
                self.stdout.write(self.style.WARNING(f'  🗑  {n} tentatives quiz supprimées'))

        # ── Devoirs ───────────────────────────────────────────────────────────
        if target in ('assignment', 'all'):
            self._seed_assignment_submissions(Assignment, AssignmentSubmission, AssignmentCorrection, students, max_stu)

        # ── Examens ───────────────────────────────────────────────────────────
        if target in ('exam', 'all'):
            self._seed_exam_sessions(SecureExam, ExamSession, students, max_stu)

        # ── Quiz ──────────────────────────────────────────────────────────────
        if target in ('quiz', 'all'):
            self._seed_quiz_attempts(Quiz, QuizAttempt, AttemptAnswer, Question, Choice, students, max_stu)

        self.stdout.write(self.style.SUCCESS('\n✅ Soumissions créées avec succès.'))

    # ── Devoirs ───────────────────────────────────────────────────────────────

    def _seed_assignment_submissions(self, Assignment, AssignmentSubmission, AssignmentCorrection, students, max_stu):
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Soumissions Devoirs —'))

        assignments = list(Assignment.objects.filter(status='PUBLISHED').select_related('class_obj', 'subject')[:10])
        if not assignments:
            self.stdout.write(self.style.WARNING('  Aucun devoir publié trouvé.'))
            return

        teacher_user = Assignment.objects.filter(teacher__isnull=False).values_list('teacher__user', flat=True).first()

        for assignment in assignments:
            sample = random.sample(students, min(max_stu, len(students)))
            n_sub = 0
            n_cor = 0

            for student in sample:
                if AssignmentSubmission.objects.filter(assignment=assignment, student=student).exists():
                    continue

                ans_data = random.choice(STUDENT_ANSWERS)
                sub_pdf = None
                try:
                    student_name = f"{student.user.first_name} {student.user.last_name}".strip() or f"Étudiant {student.matricule}"
                    sub_pdf_bytes = generate_student_pdf(
                        student_name=student_name,
                        assignment_title=assignment.title,
                        answers=ans_data['content'],
                    )
                    sub_pdf = ContentFile(sub_pdf_bytes)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    ⚠ PDF copie impossible : {e}'))

                sub = AssignmentSubmission(
                    assignment=assignment,
                    student=student,
                    content='\n\n'.join(f'{t}\n{b}' for t, b in ans_data['content'][:2]),
                    status='SUBMITTED',
                )
                if sub_pdf:
                    fname = f'copie_{student.matricule}_{assignment.id}.pdf'
                    sub.file.save(fname, sub_pdf, save=False)
                sub.save()
                n_sub += 1

                # Correction : 60% de chance pour les devoirs passés
                do_correction = assignment.due_date < timezone.now() and random.random() < 0.65
                if not do_correction and random.random() < 0.2:
                    do_correction = True  # quelques corrections anticipées

                if do_correction:
                    max_s = float(assignment.max_score)
                    score = round(random.uniform(max_s * 0.35, max_s), 1)
                    cor_data = random.choice(STUDENT_CORRECTIONS)
                    cor_pdf_bytes = None
                    try:
                        student_name = f"{student.user.first_name} {student.user.last_name}".strip() or f"Étudiant {student.matricule}"
                        cor_pdf_bytes = generate_correction_pdf(
                            student_name=student_name,
                            assignment_title=assignment.title,
                            score=score,
                            max_score=max_s,
                            feedback=cor_data['feedback'],
                            corrections=cor_data['corrections'],
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'    ⚠ PDF correction impossible : {e}'))

                    cor = AssignmentCorrection(
                        submission=sub,
                        score=score,
                        feedback=cor_data['feedback'],
                        corrected_by_id=teacher_user,
                    )
                    if cor_pdf_bytes:
                        fname = f'correction_{student.matricule}_{assignment.id}.pdf'
                        cor.corrected_file.save(fname, ContentFile(cor_pdf_bytes), save=False)
                    cor.save()
                    n_cor += 1

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {assignment.title[:50]} → {n_sub} copies, {n_cor} corrections PDF'
            ))

    # ── Examens ───────────────────────────────────────────────────────────────

    def _seed_exam_sessions(self, SecureExam, ExamSession, students, max_stu):
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Sessions Examens —'))

        exams = list(SecureExam.objects.filter(is_published=True).select_related('class_obj', 'subject')[:8])
        if not exams:
            self.stdout.write(self.style.WARNING('  Aucun examen publié trouvé.'))
            return

        teacher_user_id = None
        try:
            from apps.teachers.models import TeacherProfile
            t = TeacherProfile.objects.first()
            teacher_user_id = t.user_id if t else None
        except Exception:
            pass

        for exam in exams:
            past_exam = exam.end_date and exam.end_date < timezone.now()
            sample = random.sample(students, min(max_stu, len(students)))
            n_ses = 0
            n_cor = 0

            for student in sample:
                if ExamSession.objects.filter(exam=exam, student=student).exists():
                    continue

                score_val = None
                feedback_val = ''
                cor_pdf = None

                # Pour les examens passés, on génère des scores + corrections
                if past_exam and random.random() < 0.75:
                    max_s = float(exam.max_score or 20)
                    score_val = round(random.uniform(max_s * 0.30, max_s), 1)
                    cor_data = random.choice(STUDENT_CORRECTIONS)
                    feedback_val = cor_data['feedback']
                    try:
                        student_name = f"{student.user.first_name} {student.user.last_name}".strip() or f"Étudiant {student.matricule}"
                        cor_pdf_bytes = generate_correction_pdf(
                            student_name=student_name,
                            assignment_title=exam.title,
                            score=score_val,
                            max_score=max_s,
                            feedback=feedback_val,
                            corrections=cor_data['corrections'],
                        )
                        cor_pdf = ContentFile(cor_pdf_bytes)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'    ⚠ PDF correction exam impossible : {e}'))

                ses = ExamSession(
                    exam=exam,
                    student=student,
                    status='SUBMITTED' if past_exam else 'STARTED',
                    submitted_at=exam.end_date if past_exam else None,
                    score=score_val,
                    feedback=feedback_val,
                    corrected_by_id=teacher_user_id if score_val is not None else None,
                    corrected_at=timezone.now() if score_val is not None else None,
                )
                if cor_pdf and score_val is not None:
                    fname = f'exam_correction_{student.matricule}_{exam.id}.pdf'
                    ses.corrected_file.save(fname, cor_pdf, save=False)
                ses.save()
                n_ses += 1
                if score_val is not None:
                    n_cor += 1

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {exam.title[:50]} → {n_ses} sessions, {n_cor} corrigées'
            ))

    # ── Quiz ──────────────────────────────────────────────────────────────────

    def _seed_quiz_attempts(self, Quiz, QuizAttempt, AttemptAnswer, Question, Choice, students, max_stu):
        from decimal import Decimal
        self.stdout.write(self.style.MIGRATE_HEADING('\n— Tentatives Quiz —'))

        quizzes = list(Quiz.objects.filter(is_published=True).prefetch_related('questions__choices')[:8])
        if not quizzes:
            self.stdout.write(self.style.WARNING('  Aucun quiz publié trouvé.'))
            return

        for quiz in quizzes:
            questions = list(quiz.questions.filter(is_active=True).prefetch_related('choices'))
            if not questions:
                continue

            sample = random.sample(students, min(max_stu, len(students)))
            n_att = 0

            for student in sample:
                if QuizAttempt.objects.filter(quiz=quiz, student=student).exists():
                    continue

                attempt = QuizAttempt.objects.create(
                    quiz=quiz,
                    student=student,
                    submitted_at=timezone.now(),
                )

                total_score = Decimal('0')
                max_total = Decimal('0')

                for q in questions:
                    choices = list(q.choices.all())
                    answer = AttemptAnswer(attempt=attempt, question=q)
                    pts = Decimal('0')
                    max_q = q.points or Decimal('1')

                    if q.question_type in ('QCU', 'QCM', 'TRUEFALSE'):
                        correct = [c for c in choices if c.is_correct]
                        wrong   = [c for c in choices if not c.is_correct]
                        # 70% chance de bonne réponse
                        if random.random() < 0.70 and correct:
                            selected = correct[:1] if q.question_type == 'QCU' else correct
                            pts = max_q
                        else:
                            selected = wrong[:1] if wrong else []
                            pts = Decimal('0')
                        answer.is_correct = pts > 0
                        answer.points_earned = pts
                        answer.save()
                        if selected:
                            answer.selected_choices.set(selected)

                    elif q.question_type == 'NUMERIC':
                        expected = float(q.numeric_answer or 0)
                        tolerance = float(q.numeric_tolerance or 0)
                        # 60% chance de réponse correcte
                        if random.random() < 0.60:
                            val = expected + random.uniform(-tolerance, tolerance)
                            pts = max_q
                            answer.is_correct = True
                        else:
                            val = expected * random.uniform(0.5, 1.8)
                            pts = Decimal('0')
                            answer.is_correct = False
                        answer.numeric_response = round(val, 2)
                        answer.points_earned = pts
                        answer.save()

                    elif q.question_type == 'TEXT':
                        text_answers = [
                            "La gestion prévisionnelle permet d'anticiper les besoins en compétences et d'adapter la politique RH.",
                            "Le management par objectifs (MBO) responsabilise les collaborateurs et aligne leurs efforts sur la stratégie de l'entreprise.",
                            "Une stratégie de différenciation consiste à proposer une offre perçue comme unique par les clients, justifiant un prix premium.",
                            "La segmentation marketing divise le marché en groupes homogènes de consommateurs ayant des besoins similaires.",
                            "Le coaching managérial accompagne un collaborateur dans le développement de ses compétences par un suivi individualisé.",
                        ]
                        answer.text_response = random.choice(text_answers)
                        answer.is_correct = None  # à corriger manuellement
                        answer.points_earned = Decimal('0')
                        answer.save()

                    elif q.question_type == 'MATCHING' and choices:
                        matching = {str(c.id): c.match_text for c in choices}
                        if random.random() < 0.65:
                            answer.matching_response = matching
                            pts = max_q
                            answer.is_correct = True
                        else:
                            vals = list(matching.values())
                            random.shuffle(vals)
                            answer.matching_response = {k: v for k, v in zip(matching.keys(), vals)}
                            pts = Decimal('0')
                            answer.is_correct = False
                        answer.points_earned = pts
                        answer.save()

                    elif q.question_type == 'ORDERING' and choices:
                        ids = [c.id for c in choices]
                        if random.random() < 0.65:
                            answer.ordering_response = ids
                            pts = max_q
                            answer.is_correct = True
                        else:
                            shuffled = ids.copy()
                            random.shuffle(shuffled)
                            answer.ordering_response = shuffled
                            pts = Decimal('0')
                            answer.is_correct = False
                        answer.points_earned = pts
                        answer.save()

                    total_score += pts
                    max_total += max_q

                # Finaliser la tentative
                attempt.score = total_score
                attempt.max_score = max_total
                attempt.percent = (total_score / max_total * 100) if max_total > 0 else Decimal('0')
                has_pending_text = AttemptAnswer.objects.filter(attempt=attempt, is_correct__isnull=True).exists()
                attempt.is_graded = not has_pending_text
                attempt.is_passed = attempt.is_graded and attempt.percent >= quiz.pass_score_percent
                attempt.save()
                n_att += 1

            self.stdout.write(self.style.SUCCESS(f'  ✓ {quiz.title[:50]} → {n_att} tentatives créées'))
