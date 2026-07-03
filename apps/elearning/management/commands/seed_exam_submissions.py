"""
seed_exam_submissions.py
─────────────────────────
1. Upload des sujets PDF pour chaque examen sécurisé (côté prof/admin).
2. Création de sessions d'examen soumises par les étudiants avec upload
   de leur copie PDF.

Tout le contenu est en gestion commerciale / RH / management.
"""

import io
import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta


# ─── Contenus des sujets d'examen (prof uploade) ─────────────────────────────

EXAM_SUBJECTS = [
    {
        'title_hint': 'gestion',
        'subject_title': 'Examen Final — Gestion Commerciale & Stratégie',
        'questions': [
            ('1.', 'Définissez la segmentation de marché et présentez ses 4 critères principaux. (4 pts)'),
            ('2.', 'Analysez la matrice SWOT d\'une PME agroalimentaire de votre choix. (6 pts)'),
            ('3.', 'Expliquez le modèle des 5 forces de Porter et son utilité stratégique. (5 pts)'),
            ('4.', 'Calculez le taux de marge brute sachant : CA = 500 000 € · Achats = 280 000 €. (3 pts)'),
            ('5.', 'Quels KPI utiliseriez-vous pour piloter une force de vente de 12 commerciaux ? (2 pts)'),
        ],
    },
    {
        'title_hint': 'ressources',
        'subject_title': 'Examen — Gestion des Ressources Humaines',
        'questions': [
            ('1.', 'Décrivez le processus de recrutement en 6 étapes depuis la définition du besoin. (6 pts)'),
            ('2.', 'Qu\'est-ce que la GPEC ? Comment la mettre en place dans une entreprise de 200 salariés ? (6 pts)'),
            ('3.', 'Calculez le coût de recrutement d\'un cadre (annonce 1 200 €, cabinet 15 % du salaire annuel de 45 000 €, formation d\'intégration 800 €). (3 pts)'),
            ('4.', 'Distinguez contrat CDI et CDD : conditions, durée, renouvellement, rupture. (5 pts)'),
        ],
    },
    {
        'title_hint': 'management',
        'subject_title': 'Partiel — Théories et Pratiques du Management',
        'questions': [
            ('1.', 'Comparez les styles de management de McGregor (Théorie X vs Y) et leurs implications pratiques. (6 pts)'),
            ('2.', 'Présentez le modèle de leadership situationnel de Hersey & Blanchard avec un exemple concret. (6 pts)'),
            ('3.', 'Qu\'est-ce que le management par objectifs (MBO) de Drucker ? Avantages et limites. (4 pts)'),
            ('4.', 'Décrivez le modèle de conduite du changement de Kotter en 8 étapes. (4 pts)'),
        ],
    },
]

# ─── Copies étudiantes (réponses réalistes) ───────────────────────────────────

STUDENT_COPIES = [
    {
        'score_pct': 0.82,
        'answers': [
            ('Q1', 'La segmentation de marché consiste à diviser un marché en groupes homogènes. Les 4 critères : géographique (pays, région), démographique (âge, sexe), psychographique (style de vie) et comportemental (fréquence d\'achat, fidélité). Chaque segment doit être mesurable, accessible, substantiel et actionnable.'),
            ('Q2', 'Pour une PME agroalimentaire régionale : Forces : savoir-faire artisanal, circuits courts. Faiblesses : capacité de production limitée, faible notoriété nationale. Opportunités : tendance bio, e-commerce alimentaire. Menaces : grande distribution, coûts matières premières.'),
            ('Q3', 'Les 5 forces de Porter analysent l\'attractivité d\'un secteur : pouvoir de négociation des clients, pouvoir des fournisseurs, menace des substituts, menace des entrants, rivalité entre concurrents. Plus les forces sont intenses, moins le secteur est rentable. Outil utile pour choisir un positionnement stratégique.'),
            ('Q4', 'Taux de marge brute = (CA – Achats) / CA × 100 = (500 000 – 280 000) / 500 000 × 100 = 44 %. Ce taux mesure la rentabilité commerciale brute avant charges fixes.'),
            ('Q5', 'KPI force de vente : CA réalisé vs objectif, nombre de visites/semaine, taux de transformation devis/commande, panier moyen, taux de fidélisation clients, coût d\'acquisition client (CAC).'),
        ],
    },
    {
        'score_pct': 0.65,
        'answers': [
            ('Q1', 'Le recrutement suit 6 étapes : 1) Définition du poste et profil. 2) Choix des canaux (Pôle emploi, LinkedIn, cooptation). 3) Tri des candidatures. 4) Entretiens (téléphonique puis physique). 5) Vérification des références. 6) Intégration (onboarding). Un recrutement raté coûte en moyenne 15 000 €.'),
            ('Q2', 'La GPEC est une démarche qui anticipe les évolutions des emplois et compétences sur 3 à 5 ans. Mise en place : diagnostic des compétences actuelles, projection des besoins futurs, identification des écarts, plan d\'action (formation, mobilité, recrutement). Obligatoire pour les entreprises de +300 salariés.'),
            ('Q3', 'Coût total = 1 200 + (45 000 × 15%) + 800 = 1 200 + 6 750 + 800 = 8 750 €.'),
            ('Q4', 'CDI : contrat indéterminé, rupture par démission, licenciement ou rupture conventionnelle. CDD : limité à 18 mois, renouvelable 2 fois, prime de précarité de 10% à la fin. Le CDD ne peut pas être utilisé pour remplacer un poste permanent.'),
        ],
    },
    {
        'score_pct': 0.45,
        'answers': [
            ('Q1', 'McGregor décrit deux visions : Théorie X (l\'employé est passif, évite le travail, doit être contrôlé) → management directif. Théorie Y (l\'employé cherche la responsabilité, est créatif) → management participatif. La Théorie Y est plus adaptée aux environnements innovants.'),
            ('Q2', 'Hersey & Blanchard définissent 4 styles selon la maturité du collaborateur : Directif (dit quoi faire), Persuasif (explique pourquoi), Participatif (implique le collaborateur), Délégatif (laisse autonomie). Ex : un nouvel employé a besoin de directives claires.'),
            ('Q3', 'Le MBO fixe des objectifs mesurables entre manager et collaborateur. Avantages : motivation, clarté des attentes. Limites : peut devenir bureaucratique, risque de focalisation sur les objectifs au détriment de l\'esprit d\'équipe.'),
            ('Q4', 'Kotter : 1-Créer l\'urgence. 2-Former une coalition. 3-Vision. 4-Communiquer. 5-Lever les obstacles. 6-Victoires rapides. 7-Consolider. 8-Ancrer le changement dans la culture.'),
        ],
    },
    {
        'score_pct': 0.90,
        'answers': [
            ('Q1', 'La segmentation permet d\'adapter la stratégie marketing à des groupes distincts. Les 4 critères : 1) Géographique : découpage par zone (quartier, région, pays). 2) Démographique : âge, sexe, CSP, revenus. 3) Psychographique : valeurs, lifestyle, personnalité. 4) Comportemental : fidélité, taux d\'usage, occasions d\'achat. Un bon segment est mesurable, accessible, différenciable et profitable.'),
            ('Q2', 'SWOT pour une PME bio locale : F – Produits authentiques, lien producteur-consommateur, certification AB. F – Faible budget marketing, dépendance saisonnière. O – Boom du bio (+9% par an), développement des AMAP. M – Entrée des grandes surfaces sur le bio, aléas climatiques. Stratégie recommandée : différenciation par la traçabilité et le storytelling.'),
            ('Q3', 'Porter analyse 5 forces : (1) Rivalité intrasectorielle – intensité de la concurrence. (2) Pouvoir clients – leur capacité à négocier les prix. (3) Pouvoir fournisseurs. (4) Nouveaux entrants – barrières à l\'entrée. (5) Produits de substitution. Objectif : identifier les facteurs clés de succès et construire un avantage concurrentiel durable.'),
            ('Q4', '(500 000 – 280 000) / 500 000 = 220 000 / 500 000 = 44%. Ce taux permet de couvrir les charges fixes et de dégager du profit.'),
            ('Q5', 'Pour 12 commerciaux : CA par commercial, nombre de prospects contactés/semaine, taux de conversion, NPS client, délai moyen de closing, marge par vente. Je recommande un tableau de bord hebdomadaire et un coaching mensuel individuel.'),
        ],
    },
    {
        'score_pct': 0.30,
        'answers': [
            ('Q1', 'La segmentation, c\'est diviser les clients. On peut diviser par âge, par lieu, par habitude. C\'est important pour le marketing.'),
            ('Q2', 'SWOT = forces, faiblesses, opportunités, menaces. Pour une entreprise agroalimentaire : force = bons produits, faiblesse = pas assez de publicité.'),
            ('Q3', 'Porter a créé un modèle pour analyser la concurrence. Il y a 5 forces dont les concurrents, les clients et les fournisseurs.'),
            ('Q4', '500 000 – 280 000 = 220 000 €.'),
            ('Q5', 'Les KPI pour une force de vente sont le chiffre d\'affaires et le nombre de clients.'),
        ],
    },
]


# ─── Génération PDF sujet d'examen ────────────────────────────────────────────

def generate_exam_subject_pdf(exam_title, subject_data, class_name='', subject_name='', duration=120, max_score=20):
    """PDF du sujet d'examen uploadé par le prof."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    GOLD = HexColor('#d97706')
    DARK = HexColor('#1e293b')
    GRAY = HexColor('#64748b')
    WHITE = HexColor('#ffffff')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2.5*cm, rightMargin=2.5*cm)
    styles = getSampleStyleSheet()

    def sty(name='N', **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    story = []

    # En-tête institution
    story.append(Paragraph('CAMPUS LMS — Examen Sécurisé', sty('inst', fontSize=9, textColor=GRAY, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*cm))

    # Titre
    title_tbl = Table([[Paragraph(
        subject_data['subject_title'],
        sty('T', fontSize=14, textColor=WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER)
    )]], colWidths=[16*cm])
    title_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), DARK),
        ('TOPPADDING', (0,0),(-1,-1), 12),
        ('BOTTOMPADDING', (0,0),(-1,-1), 12),
        ('ROUNDEDCORNERS', [4,4,4,4]),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Infos examen
    infos = []
    if class_name:
        infos.append(f'Classe : {class_name}')
    if subject_name:
        infos.append(f'Matière : {subject_name}')
    infos.append(f'Durée : {duration} minutes')
    infos.append(f'Barème : {max_score} points')
    story.append(Paragraph(' · '.join(infos), sty('I', fontSize=10, textColor=GRAY, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD))
    story.append(Spacer(1, 0.6*cm))

    # Consignes
    story.append(Paragraph('CONSIGNES', sty('CTitle', fontSize=11, textColor=GOLD, fontName='Helvetica-Bold')))
    story.append(Spacer(1, 0.2*cm))
    consignes = [
        '• Répondez à toutes les questions dans les espaces prévus.',
        '• Justifiez vos réponses avec des exemples concrets lorsque c\'est demandé.',
        '• Tout document non autorisé est interdit.',
        '• Lisez attentivement chaque question avant de répondre.',
    ]
    for c in consignes:
        story.append(Paragraph(c, sty('Cg', fontSize=10, textColor=DARK, leftIndent=10, spaceAfter=3)))
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(Spacer(1, 0.6*cm))

    # Questions
    story.append(Paragraph('QUESTIONS', sty('QTitle', fontSize=11, textColor=GOLD, fontName='Helvetica-Bold')))
    story.append(Spacer(1, 0.4*cm))

    for num, text in subject_data['questions']:
        story.append(Paragraph(
            f'<b>{num}</b> {text}',
            sty('Q', fontSize=11, textColor=DARK, spaceAfter=4, leftIndent=0)
        ))
        # Espace pour réponse
        story.append(Spacer(1, 0.3*cm))
        for _ in range(4):
            story.append(HRFlowable(width="100%", thickness=0.3, color=HexColor('#e2e8f0'), spaceAfter=0.5*cm))
        story.append(Spacer(1, 0.5*cm))

    doc.build(story)
    return buf.getvalue()


# ─── Génération PDF copie étudiant ────────────────────────────────────────────

def generate_student_copy_pdf(student_name, matricule, exam_title, copy_data):
    """PDF de la copie d'examen rendue par l'étudiant."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    VIOLET = HexColor('#7c3aed')
    DARK = HexColor('#1e293b')
    GRAY = HexColor('#64748b')
    WHITE = HexColor('#ffffff')
    LIGHT_BG = HexColor('#f8fafc')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=1.5*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = getSampleStyleSheet()

    def sty(name='N', **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    story = []

    # En-tête
    story.append(Paragraph('CAMPUS LMS — Copie d\'Examen Étudiant', sty('H', fontSize=9, textColor=GRAY, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.2*cm))

    # Bandeau étudiant
    hdr_tbl = Table([[
        Paragraph(f'COPIE DE : {student_name.upper()}', sty('N', fontSize=12, textColor=WHITE, fontName='Helvetica-Bold')),
        Paragraph(f'Matricule : {matricule}', sty('M', fontSize=10, textColor=WHITE, alignment=TA_LEFT)),
    ]], colWidths=[11*cm, 6*cm])
    hdr_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), DARK),
        ('TOPPADDING', (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING', (0,0),(-1,-1), 12),
    ]))
    story.append(hdr_tbl)

    # Titre de l'examen
    exam_tbl = Table([[
        Paragraph(exam_title, sty('E', fontSize=11, textColor=WHITE, fontName='Helvetica-Bold', alignment=TA_CENTER))
    ]], colWidths=[17*cm])
    exam_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), VIOLET),
        ('TOPPADDING', (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
    ]))
    story.append(exam_tbl)
    story.append(Spacer(1, 0.8*cm))

    # Réponses
    for num, answer_text in copy_data['answers']:
        # Numéro de question
        q_row = Table([[
            Paragraph(f'Question {num}', sty('QN', fontSize=10, textColor=VIOLET, fontName='Helvetica-Bold'))
        ]], colWidths=[17*cm])
        q_row.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), HexColor('#f5f3ff')),
            ('TOPPADDING', (0,0),(-1,-1), 4),
            ('BOTTOMPADDING', (0,0),(-1,-1), 4),
            ('LEFTPADDING', (0,0),(-1,-1), 8),
        ]))
        story.append(q_row)
        story.append(Spacer(1, 0.15*cm))

        # Réponse
        story.append(Paragraph(
            answer_text,
            sty('A', fontSize=10, textColor=DARK, leftIndent=8, rightIndent=8,
                spaceAfter=4, leading=14)
        ))
        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#e2e8f0')))
        story.append(Spacer(1, 0.4*cm))

    # Signature
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        f'Copie soumise électroniquement · {timezone.now().strftime("%d/%m/%Y à %H:%M")}',
        sty('F', fontSize=8, textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Upload sujets PDF pour les examens + création de copies étudiantes soumises"

    def add_arguments(self, parser):
        parser.add_argument('--students', type=int, default=6,
                            help='Nombre max d\'étudiants par examen (défaut: 6)')
        parser.add_argument('--subjects-only', action='store_true',
                            help='Uploader seulement les sujets, sans créer de copies étudiantes')

    def handle(self, *args, **options):
        from apps.elearning.models import SecureExam, ExamSession

        max_stu = options['students']
        subjects_only = options['subjects_only']

        try:
            from apps.students.models import Student
            students = list(Student.objects.select_related('user').all())
        except Exception:
            students = []

        try:
            from apps.teachers.models import TeacherProfile
            teacher = TeacherProfile.objects.first()
            teacher_user = teacher.user if teacher else None
        except Exception:
            teacher_user = None

        exams = list(SecureExam.objects.filter(is_published=True).select_related('class_obj', 'subject')[:8])
        if not exams:
            self.stdout.write(self.style.WARNING('Aucun examen publié trouvé.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n=== Seed Exam Submissions — {len(exams)} examens ==='
        ))

        for exam in exams:
            # ── Upload sujet PDF (prof) ────────────────────────────────────────
            subject_data = random.choice(EXAM_SUBJECTS)
            n_sub = 0
            n_cop = 0

            if not exam.subject_file:
                try:
                    pdf_bytes = generate_exam_subject_pdf(
                        exam_title=exam.title,
                        subject_data=subject_data,
                        class_name=getattr(exam.class_obj, 'name', ''),
                        subject_name=getattr(exam.subject, 'name', ''),
                        duration=exam.duration_minutes,
                        max_score=float(exam.max_score or 20),
                    )
                    fname = f'sujet_{exam.id}.pdf'
                    exam.subject_file.save(fname, ContentFile(pdf_bytes), save=True)
                    n_sub = 1
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Sujet PDF uploadé : {exam.title[:50]}'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Sujet PDF impossible : {e}'))
            else:
                self.stdout.write(f'  → Sujet déjà présent : {exam.title[:50]}')

            if subjects_only or not students:
                continue

            # ── Copies étudiantes ──────────────────────────────────────────────
            sample = random.sample(students, min(max_stu, len(students)))

            for student in sample:
                if ExamSession.objects.filter(exam=exam, student=student).exists():
                    continue

                past = exam.end_date and exam.end_date < timezone.now()
                copy_data = random.choice(STUDENT_COPIES)
                score_pct = copy_data['score_pct']

                student_name = f"{student.user.first_name} {student.user.last_name}".strip() or f"Étudiant {student.matricule}"

                # PDF de la copie étudiant
                sub_pdf = None
                try:
                    pdf_bytes = generate_student_copy_pdf(
                        student_name=student_name,
                        matricule=student.matricule,
                        exam_title=exam.title,
                        copy_data=copy_data,
                    )
                    sub_pdf = ContentFile(pdf_bytes)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'    ⚠ PDF copie impossible : {e}'))

                score_val = None
                feedback_val = ''
                cor_pdf = None

                if past:
                    max_s = float(exam.max_score or 20)
                    score_val = round(score_pct * max_s, 1)
                    feedback_val = random.choice([
                        'Bonne maîtrise des concepts fondamentaux. Approfondissez les applications pratiques.',
                        'Analyse pertinente. Manque de précision sur les calculs.',
                        'Réponses trop courtes sur certaines questions théoriques.',
                        'Excellent travail. Exemples bien choisis et raisonnement structuré.',
                        'Effort visible mais les définitions manquent de rigueur académique.',
                    ])
                    # PDF correction prof
                    try:
                        from apps.elearning.management.commands.seed_student_submissions_pdf import generate_correction_pdf
                        cor_pdf_bytes = generate_correction_pdf(
                            student_name=student_name,
                            assignment_title=exam.title,
                            score=score_val,
                            max_score=max_s,
                            feedback=feedback_val,
                            corrections=[('Appréciation globale', feedback_val)],
                        )
                        cor_pdf = ContentFile(cor_pdf_bytes)
                    except Exception:
                        pass

                ses = ExamSession(
                    exam=exam,
                    student=student,
                    status='SUBMITTED' if past else 'SUBMITTED',
                    submitted_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                    score=score_val,
                    feedback=feedback_val,
                    corrected_by=teacher_user if score_val is not None else None,
                    corrected_at=timezone.now() - timedelta(days=random.randint(0, 5)) if score_val is not None else None,
                )
                ses.save()

                if sub_pdf:
                    fname = f'copie_{student.matricule}_{exam.id}.pdf'
                    ses.submission_file.save(fname, sub_pdf, save=False)
                if cor_pdf:
                    fname = f'correction_{student.matricule}_{exam.id}.pdf'
                    ses.corrected_file.save(fname, cor_pdf, save=False)
                ses.save()
                n_cop += 1

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ {exam.title[:55]} → sujet: {"✓" if n_sub else "→"} · {n_cop} copies étudiantes'
            ))

        self.stdout.write(self.style.SUCCESS('\n✅ Seed exam submissions terminé.'))
