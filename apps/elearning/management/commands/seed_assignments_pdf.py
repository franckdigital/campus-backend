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
        'title': 'Devoir 1 — Algorithmes et Structures de Données',
        'subject_keyword': 'algorithme',
        'max_score': 20,
        'days_offset': 10,
        'allow_late': False,
        'description': 'Ce devoir porte sur l\'analyse de complexité et l\'implémentation d\'algorithmes de tri et de recherche.',
        'instructions': 'Répondez à toutes les questions. Justifiez vos réponses. Le plagiat entraîne la note zéro.',
        'questions': [
            {
                'num': 1,
                'text': 'Analysez la complexité temporelle et spatiale de l\'algorithme de tri rapide (QuickSort) dans les cas suivants :',
                'sub': [
                    'a) Meilleur cas — donnez la complexité et justifiez',
                    'b) Cas moyen — donnez la complexité et justifiez',
                    'c) Pire cas — donnez la complexité, identifiez le cas déclencheur et proposez une solution',
                ],
                'points': 6,
            },
            {
                'num': 2,
                'text': 'Implémentez en Python les deux fonctions suivantes en utilisant une liste chaînée :',
                'sub': [
                    'a) insertion(valeur) — insère en tête de liste',
                    'b) recherche(valeur) — retourne True si la valeur existe, False sinon',
                    'c) Quelle est la complexité de chaque opération ? Justifiez.',
                ],
                'points': 7,
            },
            {
                'num': 3,
                'text': 'Comparez les structures de données suivantes en remplissant le tableau :',
                'sub': [
                    'Tableau, Liste chaînée, Pile, File, Arbre binaire de recherche',
                    'Pour chaque structure : accès (O(?)), insertion (O(?)), suppression (O(?)), recherche (O(?))',
                    'Donnez un exemple d\'utilisation réelle pour chacune.',
                ],
                'points': 7,
            },
        ],
        'scenario': 'mixed',
    },
    {
        'title': 'TP Noté — Bases de Données Relationnelles',
        'subject_keyword': 'base',
        'max_score': 20,
        'days_offset': -3,
        'allow_late': True,
        'description': 'Travail pratique sur la conception et l\'interrogation d\'une base de données.',
        'instructions': 'Vous devez rendre un fichier SQL complet exécutable sur MySQL 8. Nommez votre fichier : NOM_PRENOM_TP_BDD.sql',
        'questions': [
            {
                'num': 1,
                'text': 'MODÉLISATION (6 pts) — Concevez le schéma entité-relation d\'un système de gestion d\'une librairie en ligne :',
                'sub': [
                    'a) Identifiez les entités : Livre, Auteur, Client, Commande, LigneCommande, Catégorie',
                    'b) Définissez les associations avec leurs cardinalités',
                    'c) Identifiez les clés primaires et étrangères',
                    'd) Normalisez jusqu\'en 3NF — justifiez',
                ],
                'points': 6,
            },
            {
                'num': 2,
                'text': 'IMPLÉMENTATION SQL (6 pts) — Créez les tables correspondant à votre modèle avec les contraintes :',
                'sub': [
                    'NOT NULL, UNIQUE, CHECK, DEFAULT où pertinent',
                    'Clés étrangères avec ON DELETE approprié',
                    'Index sur les colonnes fréquemment cherchées',
                ],
                'points': 6,
            },
            {
                'num': 3,
                'text': 'REQUÊTES (8 pts) — Écrivez les requêtes SQL pour :',
                'sub': [
                    'a) Lister tous les livres d\'un auteur donné, triés par date de publication DESC (1 pt)',
                    'b) Calculer le chiffre d\'affaires total par mois pour l\'année 2024 (2 pts)',
                    'c) Trouver les 10 livres les plus vendus avec leur stock restant (2 pts)',
                    'd) Clients ayant commandé plus de 3 fois sans jamais annuler (3 pts)',
                ],
                'points': 8,
            },
        ],
        'scenario': 'graded',
    },
    {
        'title': 'Devoir Maison — Réseaux Informatiques',
        'subject_keyword': 'réseau',
        'max_score': 20,
        'days_offset': 14,
        'allow_late': False,
        'description': 'Devoir portant sur les protocoles réseau, le modèle OSI et la sécurité des communications.',
        'instructions': 'Réponses manuscrites ou numériques acceptées. Longueur recommandée : 4 à 6 pages.',
        'questions': [
            {
                'num': 1,
                'text': 'MODÈLE OSI (5 pts) :',
                'sub': [
                    'a) Citez et décrivez brièvement les 7 couches du modèle OSI',
                    'b) Donnez un protocole réel utilisé à chaque couche',
                    'c) Expliquez le rôle de l\'encapsulation lors de l\'envoi d\'un email',
                ],
                'points': 5,
            },
            {
                'num': 2,
                'text': 'PROTOCOLES TCP/IP (8 pts) :',
                'sub': [
                    'a) Expliquez la différence entre TCP et UDP avec des exemples d\'usage',
                    'b) Décrivez le handshake TCP en 3 étapes (SYN, SYN-ACK, ACK)',
                    'c) Qu\'est-ce que le NAT ? Pourquoi est-il utilisé ?',
                    'd) Expliquez comment fonctionne DNS avec un exemple de résolution',
                ],
                'points': 8,
            },
            {
                'num': 3,
                'text': 'SÉCURITÉ RÉSEAU (7 pts) :',
                'sub': [
                    'a) Qu\'est-ce qu\'une attaque Man-in-the-Middle ? Comment s\'en protéger ?',
                    'b) Expliquez le fonctionnement de TLS/SSL',
                    'c) Différence entre un pare-feu et un IDS/IPS',
                    'd) Qu\'est-ce qu\'un VPN ? Citez 2 protocoles VPN courants',
                ],
                'points': 7,
            },
        ],
        'scenario': 'pending',
    },
    {
        'title': 'Exercice — Programmation Orientée Objet (Python)',
        'subject_keyword': 'programm',
        'max_score': 20,
        'days_offset': 5,
        'allow_late': False,
        'description': 'Exercice pratique sur la POO : héritage, polymorphisme et interfaces.',
        'instructions': 'Répondez en Python 3.10+. Incluez les docstrings et des tests unitaires avec unittest.',
        'questions': [
            {
                'num': 1,
                'text': 'CLASSES DE BASE (6 pts) — Implémentez la hiérarchie suivante :',
                'sub': [
                    'Classe abstraite Vehicule : marque, modele, annee, vitesse_max',
                    'Méthode abstraite description() → str',
                    'Méthode demarrer() affichant "Démarrage de [marque] [modele]"',
                    'Sous-classes : Voiture (nb_portes), Moto (cylindree), Camion (charge_max_tonnes)',
                    'Chaque sous-classe implémente description() de manière polymorphe',
                ],
                'points': 6,
            },
            {
                'num': 2,
                'text': 'ENCAPSULATION & PROPRIÉTÉS (6 pts) :',
                'sub': [
                    'a) Ajoutez une propriété kilometrage avec getter et setter',
                    'b) Le setter doit refuser les valeurs négatives (lève ValueError)',
                    'c) Implémentez __str__ et __repr__ pour chaque classe',
                    'd) Ajoutez __eq__ pour comparer deux véhicules sur marque+modele+annee',
                ],
                'points': 6,
            },
            {
                'num': 3,
                'text': 'TESTS UNITAIRES (8 pts) :',
                'sub': [
                    'Écrivez des tests pour : création d\'instances, polymorphisme de description()',
                    'Test que le setter de kilometrage lève ValueError pour valeurs négatives',
                    'Test d\'égalité entre deux instances identiques et différentes',
                    'Taux de couverture attendu : ≥ 80% (vérifiable avec coverage.py)',
                ],
                'points': 8,
            },
        ],
        'scenario': 'submitted_text',
    },
    {
        'title': 'Projet Final — Intelligence Artificielle & Machine Learning',
        'subject_keyword': 'intelligence',
        'max_score': 50,
        'days_offset': 30,
        'allow_late': False,
        'description': 'Projet de fin de semestre à réaliser en binôme. Implémentation d\'un pipeline ML complet.',
        'instructions': 'Rendu : dossier ZIP contenant rapport PDF (max 15 pages) + code Python commenté + requirements.txt. Date limite stricte.',
        'questions': [
            {
                'num': 1,
                'text': 'PRÉPARATION DES DONNÉES (10 pts) :',
                'sub': [
                    'Choisissez un dataset public (Kaggle, UCI, sklearn) et justifiez ce choix',
                    'Analyse exploratoire : distribution, corrélations, valeurs manquantes',
                    'Nettoyage : imputation, encodage des catégorielles, normalisation',
                    'Visualisations : au moins 5 graphiques pertinents (matplotlib/seaborn)',
                ],
                'points': 10,
            },
            {
                'num': 2,
                'text': 'MODÉLISATION (20 pts) :',
                'sub': [
                    'Implémentez et comparez 3 algorithmes minimum (ex: Régression Logistique, Random Forest, SVM)',
                    'Validation croisée k-fold (k=5) pour chaque modèle',
                    'Métriques : accuracy, précision, rappel, F1-score, matrice de confusion',
                    'Hyperparameter tuning avec GridSearchCV ou RandomizedSearchCV',
                    'Sauvegarde du meilleur modèle avec joblib',
                ],
                'points': 20,
            },
            {
                'num': 3,
                'text': 'INTERPRÉTABILITÉ & RAPPORT (20 pts) :',
                'sub': [
                    'Importance des variables (feature importance ou SHAP)',
                    'Discussion des résultats : forces et limites du modèle retenu',
                    'Conclusion et perspectives d\'amélioration',
                    'Rapport structuré : Introduction, Méthodologie, Résultats, Conclusion',
                    'Présentation orale de 10 min (slides à inclure dans le rendu)',
                ],
                'points': 20,
            },
        ],
        'scenario': 'pending',
    },
    {
        'title': 'Devoir 4 — Bases de Données Relationnelles',
        'subject_keyword': 'base',
        'max_score': 20,
        'days_offset': 18,
        'allow_late': False,
        'description': 'Devoir portant sur les notions abordées en Bases de données relationnelles.',
        'instructions': 'Rendu sur papier ou fichier PDF. Répondez à toutes les questions.',
        'questions': [
            {
                'num': 1,
                'text': 'FORMES NORMALES (7 pts) :',
                'sub': [
                    'a) Qu\'est-ce que la première forme normale (1NF) ? Donnez un contre-exemple et corrigez-le',
                    'b) Expliquez la 2NF avec un exemple de dépendance partielle',
                    'c) Expliquez la 3NF avec un exemple de dépendance transitive',
                    'd) Normalisez la table suivante : Commande(NumCmd, DateCmd, CodeClient, NomClient, VilleClient, CodeProduit, NomProduit, Qté, PrixUnit)',
                ],
                'points': 7,
            },
            {
                'num': 2,
                'text': 'TRANSACTIONS ET CONCURRENCE (6 pts) :',
                'sub': [
                    'a) Définissez les propriétés ACID et illustrez chacune avec un exemple',
                    'b) Qu\'est-ce qu\'un deadlock ? Comment MySQL le détecte-t-il et le résout-il ?',
                    'c) Différence entre verrou partagé et verrou exclusif',
                ],
                'points': 6,
            },
            {
                'num': 3,
                'text': 'OPTIMISATION (7 pts) :',
                'sub': [
                    'a) Expliquez ce qu\'est un index et quand en créer un',
                    'b) Analysez la requête suivante avec EXPLAIN : SELECT * FROM commandes WHERE client_id = 42 AND statut = \'EN_COURS\'',
                    'c) Proposez une optimisation et justifiez',
                    'd) Différence entre INDEX simple, UNIQUE INDEX et INDEX composite',
                ],
                'points': 7,
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
