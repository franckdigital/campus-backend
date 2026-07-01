"""
seed_elearning_complet.py — Seed complet et riche de tous les modules E-Learning.

Usage: python manage.py seed_elearning_complet
Pré-requis : avoir déjà exécuté `python manage.py seed_full`.

Couvre :
  - Cours autonomes MOOC (Course → Section → CourseChapter → CourseLesson)
  - Chapitres & Leçons de classe + blocs de contenu + progressions
  - Quiz (QCU / QCM / TRUEFALSE / TEXT / NUMERIC) + tentatives étudiants
  - Devoirs (DRAFT / PUBLISHED / CLOSED) + soumissions + corrections
  - Examens sécurisés (MID / FINAL / SUPP / TP) + sessions
  - Laboratoires virtuels + soumissions
  - Vidéothèque + progressions
  - Classes virtuelles (passées / en cours / à venir) + sondages + chat
  - Réunions Zoom
  - Bibliothèque numérique + favoris + progressions de lecture
  - Conversations IA (TUTOR / TEACHER / QUIZ_GEN / FLASHCARD / PLAN)
"""
import random
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

# ─── Données statiques ────────────────────────────────────────────────────────

COURSE_DATA = [
    {
        'title': 'Algorithmique et Programmation Python',
        'subtitle': 'Maîtrisez les fondamentaux de la programmation avec Python',
        'description': 'Un cours complet pour apprendre les algorithmes, les structures de données et la programmation orientée objet avec Python.',
        'level': 'beginner',
        'what_you_will_learn': ['Variables et types', 'Fonctions', 'Boucles et conditions', 'Listes et dictionnaires', 'POO'],
        'requirements': ['Aucun prérequis', 'Ordinateur avec Python installé'],
        'sections': [
            ('Introduction à Python', [
                ('Présentation du cours', 'video', 600),
                ('Installation de Python et VS Code', 'video', 900),
                ('Premier programme — Hello World', 'text', 300),
                ('Quiz d\'introduction', 'pdf', 0),
            ]),
            ('Variables et types de données', [
                ('Types primitifs : int, float, str, bool', 'video', 1200),
                ('Opérateurs arithmétiques', 'video', 800),
                ('Exercices pratiques', 'text', 600),
            ]),
            ('Structures de contrôle', [
                ('Conditions if/elif/else', 'video', 1100),
                ('Boucles for et while', 'video', 1300),
                ('Fonctions et portée des variables', 'video', 1500),
            ]),
        ],
    },
    {
        'title': 'Bases de Données — SQL et NoSQL',
        'subtitle': 'Concevez et interrogez des bases de données modernes',
        'description': 'Apprenez la modélisation relationnelle, le SQL avancé, et découvrez les bases NoSQL (MongoDB, Redis).',
        'level': 'intermediate',
        'what_you_will_learn': ['Modélisation E/R', 'SQL SELECT avancé', 'Jointures', 'Index et performances', 'Introduction MongoDB'],
        'requirements': ['Connaissances de base en informatique', 'Python recommandé'],
        'sections': [
            ('Introduction aux bases de données', [
                ('Pourquoi les bases de données ?', 'video', 700),
                ('Modèle relationnel', 'video', 1000),
                ('Installation de PostgreSQL', 'video', 800),
            ]),
            ('SQL fondamental', [
                ('CREATE TABLE et contraintes', 'video', 1200),
                ('SELECT, WHERE, ORDER BY', 'video', 1400),
                ('Jointures INNER / LEFT / RIGHT', 'video', 1600),
                ('Agrégats et GROUP BY', 'video', 1100),
            ]),
            ('SQL avancé et performances', [
                ('Sous-requêtes et CTEs', 'video', 1300),
                ('Index et EXPLAIN', 'video', 900),
                ('Transactions et ACID', 'video', 1000),
            ]),
        ],
    },
    {
        'title': 'Développement Web Full-Stack',
        'subtitle': 'HTML, CSS, JavaScript, React et Django',
        'description': 'Formation complète pour créer des applications web modernes, du frontend au backend.',
        'level': 'intermediate',
        'what_you_will_learn': ['HTML5 / CSS3', 'JavaScript ES6+', 'React', 'Django REST', 'Déploiement'],
        'requirements': ['Bases de programmation', 'Algorithmique recommandée'],
        'sections': [
            ('Frontend — HTML & CSS', [
                ('Structure d\'une page HTML5', 'video', 900),
                ('CSS Flexbox et Grid', 'video', 1200),
                ('Responsive Design', 'video', 1000),
            ]),
            ('JavaScript et React', [
                ('Variables, fonctions, closures', 'video', 1400),
                ('DOM et événements', 'video', 1100),
                ('React — Composants et état', 'video', 1800),
                ('React — Hooks et API', 'video', 2000),
            ]),
            ('Backend — Django', [
                ('Django — Modèles et ORM', 'video', 1600),
                ('Django REST Framework', 'video', 1500),
                ('Authentification JWT', 'video', 1200),
            ]),
        ],
    },
    {
        'title': 'Réseaux et Sécurité Informatique',
        'subtitle': 'Maîtrisez les protocoles réseaux et les bases de la cybersécurité',
        'description': 'Cours approfondi sur les modèles OSI/TCP-IP, les protocoles réseaux, et les bonnes pratiques de sécurité.',
        'level': 'advanced',
        'what_you_will_learn': ['Modèle OSI', 'TCP/IP', 'Routage', 'Pare-feu', 'Cryptographie'],
        'requirements': ['Bases en informatique', 'Systèmes d\'exploitation'],
        'sections': [
            ('Fondamentaux des réseaux', [
                ('Modèle OSI — 7 couches', 'video', 1400),
                ('Adressage IP et sous-réseaux', 'video', 1600),
                ('Protocoles TCP, UDP, ICMP', 'video', 1200),
            ]),
            ('Sécurité informatique', [
                ('Menaces et vulnérabilités', 'video', 1100),
                ('Chiffrement symétrique et asymétrique', 'video', 1300),
                ('PKI et certificats SSL/TLS', 'video', 1500),
                ('Pare-feu et VPN', 'video', 1400),
            ]),
        ],
    },
    {
        'title': 'Intelligence Artificielle et Machine Learning',
        'subtitle': 'Initiez-vous à l\'IA et aux algorithmes d\'apprentissage automatique',
        'description': 'Introduction pratique au Machine Learning avec scikit-learn, réseaux de neurones et deep learning.',
        'level': 'advanced',
        'what_you_will_learn': ['Régression et classification', 'Arbres de décision', 'Réseaux de neurones', 'TensorFlow', 'Évaluation des modèles'],
        'requirements': ['Python avancé', 'Mathématiques (algèbre linéaire, statistiques)'],
        'sections': [
            ('Introduction au ML', [
                ('Qu\'est-ce que le Machine Learning ?', 'video', 900),
                ('Types d\'apprentissage', 'video', 1100),
                ('Préparation des données', 'video', 1300),
            ]),
            ('Algorithmes classiques', [
                ('Régression linéaire et logistique', 'video', 1500),
                ('SVM et arbres de décision', 'video', 1400),
                ('Forêts aléatoires et Gradient Boosting', 'video', 1600),
            ]),
            ('Deep Learning', [
                ('Perceptron multicouche', 'video', 1800),
                ('Réseaux convolutifs (CNN)', 'video', 2000),
                ('Projet — Classification d\'images', 'video', 2200),
            ]),
        ],
    },
]

LESSON_CONTENTS = [
    "Ce cours aborde les concepts fondamentaux et les méthodes appliquées dans ce domaine. Les étudiants découvriront les bases théoriques avant de passer à la pratique.",
    "La séance commence par un rappel des notions vues précédemment. Nous approfondissons ensuite les mécanismes clés à travers des exemples concrets et des exercices.",
    "Ce chapitre introduit les outils et frameworks utilisés par les professionnels. Une attention particulière est portée aux bonnes pratiques et aux standards du secteur.",
    "Les étudiants apprendront à analyser des problèmes complexes et à proposer des solutions structurées. Les cas pratiques permettent de consolider les acquis.",
    "Révision approfondie des concepts abordés dans les séances précédentes. Exercices de renforcement et préparation à l'évaluation.",
]

QUIZ_BANKS = {
    'info': [
        {
            'text': "Qu'est-ce qu'un algorithme ?",
            'type': 'QCU',
            'choices': [
                ('Une suite finie d\'instructions pour résoudre un problème', True),
                ('Un langage de programmation', False),
                ('Un logiciel de traitement de texte', False),
                ('Un composant matériel', False),
            ],
            'explanation': 'Un algorithme est une séquence finie et non ambiguë d\'instructions permettant de résoudre un problème.',
        },
        {
            'text': 'Lesquels de ces langages sont des langages de programmation orientée objet ?',
            'type': 'QCM',
            'choices': [
                ('Java', True),
                ('Python', True),
                ('HTML', False),
                ('C++', True),
            ],
            'explanation': 'HTML est un langage de balisage, pas un langage de programmation orientée objet.',
        },
        {
            'text': 'La compilation transforme le code source en code machine.',
            'type': 'TRUEFALSE',
            'choices': [
                ('Vrai', True),
                ('Faux', False),
            ],
            'explanation': 'La compilation traduit le code source (lisible par l\'humain) en code machine (exécutable par le processeur).',
        },
        {
            'text': 'Qu\'est-ce que la récursivité en programmation ?',
            'type': 'TEXT',
            'text_answer': 'une fonction qui s\'appelle elle-même',
            'explanation': 'La récursivité est le mécanisme par lequel une fonction s\'appelle elle-même pour résoudre un problème.',
        },
        {
            'text': 'Quelle est la complexité temporelle d\'un tri à bulles dans le pire des cas (en notation O) ? Entrez le nombre pour O(n^x) :',
            'type': 'NUMERIC',
            'numeric_answer': 2,
            'numeric_tolerance': 0,
            'explanation': 'La complexité du tri à bulles dans le pire des cas est O(n²).',
        },
        {
            'text': 'Lesquelles de ces structures de données permettent un accès en O(1) ?',
            'type': 'QCM',
            'choices': [
                ('Tableau (accès par index)', True),
                ('Table de hachage (cas moyen)', True),
                ('Liste chaînée', False),
                ('Arbre binaire de recherche équilibré', False),
            ],
            'explanation': 'Les tableaux et tables de hachage offrent un accès en O(1) en moyenne.',
        },
        {
            'text': 'Le modèle OSI comporte 7 couches.',
            'type': 'TRUEFALSE',
            'choices': [
                ('Vrai', True),
                ('Faux', False),
            ],
            'explanation': 'Le modèle OSI (Open Systems Interconnection) est composé de 7 couches : physique, liaison, réseau, transport, session, présentation, application.',
        },
        {
            'text': 'Quelle couche OSI est responsable du routage des paquets ?',
            'type': 'QCU',
            'choices': [
                ('Couche Réseau (Layer 3)', True),
                ('Couche Transport (Layer 4)', False),
                ('Couche Liaison (Layer 2)', False),
                ('Couche Application (Layer 7)', False),
            ],
            'explanation': 'La couche Réseau (Layer 3) est responsable du routage des paquets entre les réseaux.',
        },
        {
            'text': 'Lesquelles de ces caractéristiques définissent une transaction ACID ?',
            'type': 'QCM',
            'choices': [
                ('Atomicité', True),
                ('Cohérence', True),
                ('Isolation', True),
                ('Durabilité', True),
            ],
            'explanation': 'ACID signifie Atomicité, Cohérence, Isolation, Durabilité.',
        },
        {
            'text': 'Quel protocole est utilisé pour le transfert de pages web sécurisé ?',
            'type': 'QCU',
            'choices': [
                ('HTTPS', True),
                ('HTTP', False),
                ('FTP', False),
                ('SMTP', False),
            ],
            'explanation': 'HTTPS (HTTP Secure) utilise TLS pour chiffrer les communications.',
        },
    ],
    'math': [
        {
            'text': 'Quelle est la dérivée de f(x) = x² ?',
            'type': 'QCU',
            'choices': [
                ('f\'(x) = 2x', True),
                ('f\'(x) = x', False),
                ('f\'(x) = 2', False),
                ('f\'(x) = x²/2', False),
            ],
            'explanation': 'La dérivée de xⁿ est n·xⁿ⁻¹. Donc la dérivée de x² est 2x.',
        },
        {
            'text': 'Le théorème de Pythagore s\'applique uniquement aux triangles rectangles.',
            'type': 'TRUEFALSE',
            'choices': [
                ('Vrai', True),
                ('Faux', False),
            ],
            'explanation': 'Le théorème de Pythagore stipule que dans un triangle rectangle, a² + b² = c² où c est l\'hypoténuse.',
        },
        {
            'text': 'Lesquelles de ces propriétés caractérisent une matrice identité ?',
            'type': 'QCM',
            'choices': [
                ('Diagonale principale = 1', True),
                ('Tous les autres éléments = 0', True),
                ('Matrice carrée', True),
                ('Déterminant = 0', False),
            ],
            'explanation': 'La matrice identité est carrée, avec des 1 sur la diagonale et des 0 ailleurs. Son déterminant est 1.',
        },
        {
            'text': 'Quel est le résultat de log₁₀(100) ?',
            'type': 'NUMERIC',
            'numeric_answer': 2,
            'numeric_tolerance': 0,
            'explanation': 'log₁₀(100) = log₁₀(10²) = 2',
        },
        {
            'text': 'Définissez brièvement la notion de limite en analyse mathématique.',
            'type': 'TEXT',
            'text_answer': '',
            'explanation': 'La limite d\'une fonction en un point est la valeur vers laquelle la fonction tend lorsque la variable s\'approche de ce point.',
        },
    ],
    'general': [
        {
            'text': 'Qu\'est-ce que la méthode scientifique ?',
            'type': 'TEXT',
            'text_answer': '',
            'explanation': 'La méthode scientifique est un processus d\'acquisition des connaissances basé sur l\'observation, la formulation d\'hypothèses, l\'expérimentation et l\'analyse des résultats.',
        },
        {
            'text': 'L\'apprentissage actif est plus efficace que l\'apprentissage passif.',
            'type': 'TRUEFALSE',
            'choices': [
                ('Vrai', True),
                ('Faux', False),
            ],
            'explanation': 'Les recherches en sciences de l\'éducation montrent que l\'apprentissage actif (participation, résolution de problèmes) est généralement plus efficace.',
        },
        {
            'text': 'Lesquels de ces éléments favorisent une bonne gestion du temps ?',
            'type': 'QCM',
            'choices': [
                ('Priorisation des tâches', True),
                ('Planification', True),
                ('Multitâche permanent', False),
                ('Révisions régulières', True),
            ],
            'explanation': 'Le multitâche permanent réduit la productivité. La priorisation, planification et révisions régulières sont des stratégies efficaces.',
        },
    ],
}

LIBRARY_DOCS_RICH = [
    ('Algorithmique avancée — Graphes et optimisation', 'BOOK', 'Pr. Martin Dupont', 2023, 350,
     'Approche rigoureuse des algorithmes de graphes : BFS, DFS, Dijkstra, Bellman-Ford, algorithmes de flot.'),
    ('Introduction à la Programmation Python — 3e édition', 'COURSE', 'Équipe pédagogique', 2024, 280,
     'Support de cours complet pour apprendre Python de zéro, avec exercices corrigés.'),
    ('Bases de Données Relationnelles — Théorie et Pratique', 'BOOK', 'Pr. Sophie Leclerc', 2022, 420,
     'Manuel complet sur la modélisation E/R, le SQL, les SGBD et l\'optimisation des requêtes.'),
    ('Cybersécurité — Fondamentaux et Bonnes Pratiques', 'REPORT', 'ANSSI / Équipe sécurité', 2023, 180,
     'Guide pratique sur la sécurisation des systèmes, la gestion des vulnérabilités et la réponse aux incidents.'),
    ('Mémoire — Développement d\'une plateforme e-learning', 'MEMOIR', 'Aminata Diallo', 2023, 120,
     'Mémoire de fin de cycle portant sur la conception et le développement d\'une plateforme LMS open source.'),
    ('Réseaux Informatiques — Protocoles et Architecture', 'BOOK', 'Pr. Jean-Baptiste Morin', 2022, 380,
     'Étude approfondie des protocoles réseaux, du modèle OSI au routage BGP en passant par la sécurité réseau.'),
    ('Machine Learning avec Python — Scikit-Learn et TensorFlow', 'COURSE', 'Équipe IA', 2024, 310,
     'Formation pratique au machine learning et au deep learning avec les bibliothèques Python les plus utilisées.'),
    ('Mathématiques pour l\'Informatique', 'BOOK', 'Pr. Claire Fontaine', 2021, 450,
     'Algèbre linéaire, probabilités, statistiques et logique mathématique appliquées à l\'informatique.'),
    ('Architecture des Systèmes d\'Information', 'ARTICLE', 'Dr. Pierre Renaud', 2023, 45,
     'Article scientifique sur les tendances en architecture SI : microservices, cloud natif, API-first.'),
    ('Gestion de Projet Agile — Scrum et Kanban', 'COURSE', 'Équipe formation', 2024, 160,
     'Guide pratique des méthodologies agiles pour la gestion de projets informatiques.'),
    ('Thèse — Optimisation des algorithmes de tri sur GPU', 'THESIS', 'Kofi Mensah', 2022, 240,
     'Thèse de doctorat sur l\'accélération GPU des algorithmes de tri pour le big data.'),
    ('Revue — Tendances du développement web en 2024', 'JOURNAL', 'Collectif dev', 2024, 80,
     'Panorama des frameworks, outils et pratiques dominant le développement web frontend et backend.'),
]

VIDEO_DATA = [
    ('Introduction à l\'architecture MVC', 'YOUTUBE', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 1800, 'mvc,architecture,patterns'),
    ('Tutoriel Git et GitHub — Les bases', 'YOUTUBE', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 2400, 'git,github,versionning'),
    ('Docker en 30 minutes', 'YOUTUBE', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 1800, 'docker,conteneurisation,devops'),
    ('REST API avec Django REST Framework', 'YOUTUBE', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 3600, 'django,api,rest,python'),
    ('React Hooks — useState et useEffect', 'YOUTUBE', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 2700, 'react,hooks,javascript'),
    ('Sécurité Web — OWASP Top 10', 'YOUTUBE', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 3000, 'securite,owasp,web'),
    ('Machine Learning — Régression logistique', 'YOUTUBE', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 2100, 'ml,ia,python,sklearn'),
    ('Cours magistral — Algorithmique avancée', 'EXTERNAL', 'https://example.com/video/algo', 5400, 'algorithmique,cours'),
    ('TP Noté — Implémentation d\'un serveur HTTP', 'EXTERNAL', 'https://example.com/video/tp', 4500, 'reseau,http,tp'),
    ('Conférence — Intelligence Artificielle et Éducation', 'EXTERNAL', 'https://example.com/video/ia-edu', 3600, 'ia,education,conference'),
]

LAB_DATA = [
    ('TP — Implémentation d\'un tri rapide', 'PROGRAMMING',
     'Implémenter l\'algorithme QuickSort en Python et analyser sa complexité.',
     'Comprendre le paradigme diviser pour régner. Maîtriser l\'analyse de complexité.'),
    ('TP — Serveur TCP/IP basique', 'NETWORK',
     'Créer un serveur et un client TCP en Python avec le module socket.',
     'Appliquer les concepts des sockets réseau. Comprendre le modèle client-serveur.'),
    ('TP — Conteneurisation avec Docker', 'DOCKER',
     'Créer un Dockerfile pour une application web Django et l\'orchestrer avec docker-compose.',
     'Maîtriser la conteneurisation Docker. Déployer une application multi-services.'),
    ('TP — Requêtes SQL avancées', 'INFO',
     'Sur une base de données fournie, écrire des requêtes SQL complexes avec jointures, sous-requêtes et fonctions d\'agrégat.',
     'Maîtriser le SQL avancé. Optimiser les performances de requêtes.'),
    ('TP — Réseau de neurones avec TensorFlow', 'AI',
     'Construire un réseau de neurones pour classer des images MNIST avec TensorFlow/Keras.',
     'Implémenter un réseau de neurones basique. Évaluer et améliorer un modèle de deep learning.'),
    ('TP — Sécurité — Analyse de vulnérabilités', 'LINUX',
     'Sur un environnement de lab isolé, identifier et corriger des vulnérabilités web (XSS, SQLi).',
     'Comprendre les attaques web courantes. Appliquer les mesures de correction.'),
    ('TP — Administration Linux', 'LINUX',
     'Configurer un serveur Ubuntu : utilisateurs, permissions, services, pare-feu iptables.',
     'Maîtriser l\'administration système Linux. Sécuriser un serveur de production.'),
    ('Simulation — Physique des semi-conducteurs', 'PHYSICS',
     'Utiliser le simulateur TCAD pour modéliser le comportement électronique d\'une jonction PN.',
     'Comprendre le comportement des jonctions PN. Analyser les caractéristiques I/V.'),
]

AI_CONVERSATIONS = {
    'TUTOR': [
        ("Peux-tu m'expliquer la différence entre une pile et une file d'attente ?",
         "Bien sûr ! Une **pile (stack)** suit le principe LIFO (Last In, First Out) : le dernier élément ajouté est le premier sorti. Comme une pile d'assiettes.\n\nUne **file d'attente (queue)** suit le principe FIFO (First In, First Out) : le premier élément ajouté est le premier sorti. Comme une file à la caisse.\n\nExemple d'usage :\n- Pile : gestion de l'historique de navigation, appels de fonctions (call stack)\n- File : traitement de tâches par ordre d'arrivée, BFS (parcours en largeur)"),
        ("Je ne comprends pas les closures en JavaScript",
         "Les **closures** (fermetures) sont une notion fondamentale en JavaScript.\n\nUne closure est créée quand une fonction interne *capture* des variables de sa fonction parente, même après que la fonction parente ait terminé son exécution.\n\n```javascript\nfunction compteur() {\n  let n = 0;\n  return function() {\n    n++;\n    return n;\n  };\n}\nconst c = compteur();\nc(); // 1\nc(); // 2\nc(); // 3\n```\n\nIci, la fonction retournée *se souvient* de `n` même après la fin de `compteur()`. C'est une closure !"),
        ("Comment fonctionne l'algorithme de Dijkstra ?",
         "L'algorithme de **Dijkstra** trouve le chemin le plus court dans un graphe pondéré (poids positifs).\n\n**Principe :**\n1. Initialiser toutes les distances à ∞, sauf le nœud source (distance = 0)\n2. Sélectionner le nœud non visité avec la plus petite distance\n3. Mettre à jour les distances de ses voisins\n4. Marquer ce nœud comme visité\n5. Répéter jusqu'à avoir visité tous les nœuds\n\n**Complexité :** O((V + E) log V) avec une file de priorité."),
    ],
    'TEACHER': [
        ("Génère un plan de cours sur les algorithmes de tri pour une classe de licence 2",
         "Voici un plan de cours structuré sur les **Algorithmes de Tri** pour L2 :\n\n**Séance 1 — Introduction et tris naïfs (2h)**\n- Définition et critères de comparaison\n- Tri par sélection — O(n²)\n- Tri par insertion — O(n²) / O(n) meilleur cas\n\n**Séance 2 — Tris efficaces (2h)**\n- Tri rapide (QuickSort) — O(n log n) moyen\n- Tri fusion (MergeSort) — O(n log n) garanti\n\n**Séance 3 — Tris spécialisés (2h)**\n- Tri par tas (HeapSort)\n- Tri par comptage, tri radix (cas particuliers)\n\n**TP — Implémentation et benchmarking (3h)**\n\n**Évaluation — QCM + exercice de codage**"),
        ("Aide-moi à créer des questions d'examen sur les réseaux",
         "Voici une sélection de questions pour un examen sur les réseaux :\n\n**QCU :**\n- Quelle couche du modèle OSI est responsable du routage ?\n- Quel protocole est utilisé pour la résolution d'adresses IP en adresses MAC ?\n\n**Questions ouvertes :**\n- Expliquez la différence entre TCP et UDP avec un exemple d'application pour chacun.\n- Décrivez le processus de connexion TCP (three-way handshake).\n\n**Exercice pratique :**\n- Calculez le masque de sous-réseau pour diviser 192.168.1.0/24 en 4 sous-réseaux égaux."),
    ],
    'QUIZ_GEN': [
        ("Génère 5 questions QCM sur Python pour des débutants",
         "Voici 5 questions QCM sur Python niveau débutant :\n\n**Q1.** Quelle instruction affiche du texte en Python ?\na) echo  b) printf  c) print  ✓  d) display\n\n**Q2.** Comment déclarer une liste en Python ?\na) list = (1,2,3)  b) list = [1,2,3]  ✓  c) list = {1,2,3}  d) list = <1,2,3>\n\n**Q3.** Quel symbole est utilisé pour les commentaires en Python ?\na) //  b) /* */  c) #  ✓  d) --\n\n**Q4.** Quelle est la sortie de `len([1,2,3])` ?\na) 0  b) 2  c) 3  ✓  d) 4\n\n**Q5.** Comment importer le module math ?\na) include math  b) require math  c) import math  ✓  d) use math"),
    ],
    'FLASHCARD': [
        ("Crée des flashcards sur les structures de données",
         "**Flashcards — Structures de données**\n\n🃏 **Carte 1**\nQ: Qu'est-ce qu'une pile (stack) ?\nR: Structure LIFO. Opérations : push (empiler), pop (dépiler), peek (sommet).\n\n🃏 **Carte 2**\nQ: Différence entre liste chaînée et tableau ?\nR: Tableau = accès O(1), insertion O(n). Liste = accès O(n), insertion en tête O(1).\n\n🃏 **Carte 3**\nQ: Complexité de recherche dans une table de hachage ?\nR: O(1) en moyenne, O(n) dans le pire cas (collisions).\n\n🃏 **Carte 4**\nQ: Qu'est-ce qu'un arbre AVL ?\nR: Arbre binaire de recherche auto-équilibré. Hauteur O(log n), toutes opérations O(log n)."),
    ],
    'PLAN': [
        ("Crée-moi un plan de révision pour mon examen de BD dans 2 semaines",
         "**Plan de révision — Bases de Données (14 jours)**\n\n📅 **Semaine 1 — Révision des bases**\n- J1-J2 : Modèle E/R → diagrammes et contraintes\n- J3-J4 : SQL fondamental (SELECT, JOIN, GROUP BY)\n- J5 : SQL avancé (sous-requêtes, CTEs, fonctions)\n- J6 : Normalisation (1NF, 2NF, 3NF, BCNF)\n- J7 : Révision générale + quiz blanc\n\n📅 **Semaine 2 — Approfondissement et entraînement**\n- J8-J9 : Index, transactions ACID\n- J10 : NoSQL (MongoDB basics)\n- J11-J12 : Exercices types annales\n- J13 : Simulation d'examen (temps limité)\n- J14 : Révision légère + repos\n\n💡 **Conseil :** Pratiquer SQL sur db-fiddle.com ou PostgreSQL local."),
    ],
}


class Command(BaseCommand):
    help = (
        'Seed complet de tous les modules E-Learning : cours MOOC, leçons, quiz, '
        'devoirs, examens, labs, vidéos, classes virtuelles, bibliothèque, IA.'
    )

    def handle(self, *args, **options):
        from apps.academic.models import Class as ClassModel
        from apps.students.models import Student

        if not ClassModel.objects.exists():
            raise CommandError(
                "Aucune classe trouvée. Exécutez d'abord `python manage.py seed_full`."
            )

        self.stdout.write('\n=== NETTOYAGE E-LEARNING ===')
        self._clean()

        stats = defaultdict(int)
        now = timezone.now()

        classes = list(ClassModel.objects.select_related('site').prefetch_related(
            'subject_teachers__subject', 'subject_teachers__teacher__user'
        ))
        all_students = list(Student.objects.select_related('user').all())

        self.stdout.write('\n=== COURS AUTONOMES (MOOC) ===')
        self._seed_courses(stats, now)

        self.stdout.write('\n=== CONTENU PAR CLASSE ===')
        for cls in classes:
            cst = list(cls.subject_teachers.select_related('subject', 'teacher__user').all())
            if not cst:
                continue
            students = list(Student.objects.filter(enrollments__class_obj=cls).distinct().select_related('user'))
            if not students:
                continue
            self.stdout.write(f'  → {cls.code} ({cls.site.name if cls.site else "?"}) '
                              f'| {len(cst)} matières | {len(students)} étudiants')
            self._seed_class_content(cls, cst, students, stats, now)

        self.stdout.write('\n=== BIBLIOTHÈQUE NUMÉRIQUE ===')
        self._seed_library(all_students, stats, now)

        self.stdout.write('\n=== CONVERSATIONS IA GLOBALES ===')
        self._seed_ai_global(all_students, classes, stats, now)

        self._summary(stats)

    # =========================================================================
    # NETTOYAGE
    # =========================================================================

    def _clean(self):
        from apps.elearning.models import (
            HandRaise, ClassroomChatMessage, PollResponse, ClassroomPoll, VirtualClassroom,
            VideoDownloadToken, VideoProgress, VideoSubtitle, VideoLibrary,
            AIMessage, AIConversation,
            LabSubmission, VirtualLab,
            ExamSnapshot, ExamSession, SecureExam,
            ReadingProgress, DocumentFavorite, LibraryDocument,
            AssignmentCorrection, AssignmentSubmission, Assignment,
            AttemptAnswer, QuizAttempt, Choice, Question, Quiz,
            LessonProgress, LessonAttachment, Lesson, Chapter,
            ZoomMeeting,
            CourseLesson, CourseChapter, CourseSection, Course,
        )
        order = [
            HandRaise, ClassroomChatMessage, PollResponse, ClassroomPoll, VirtualClassroom,
            VideoDownloadToken, VideoProgress, VideoSubtitle, VideoLibrary,
            AIMessage, AIConversation,
            LabSubmission, VirtualLab,
            ExamSnapshot, ExamSession, SecureExam,
            ReadingProgress, DocumentFavorite, LibraryDocument,
            AssignmentCorrection, AssignmentSubmission, Assignment,
            AttemptAnswer, QuizAttempt, Choice, Question, Quiz,
            LessonProgress, LessonAttachment, Lesson, Chapter,
            ZoomMeeting,
            CourseLesson, CourseChapter, CourseSection, Course,
        ]
        for model in order:
            try:
                n = model.objects.count()
                model.objects.all().delete()
                if n:
                    self.stdout.write(f'  Supprimé {n:>4}  {model.__name__}')
            except Exception as e:
                self.stdout.write(f'  WARN {model.__name__}: {e}')

    # =========================================================================
    # COURS AUTONOMES (MOOC)
    # =========================================================================

    def _seed_courses(self, stats, now):
        from apps.elearning.models import Course, CourseSection, CourseChapter, CourseLesson
        from apps.accounts.models import User
        from apps.core.models import Site

        instructors = list(User.objects.filter(user_type='TEACHER')[:5])
        if not instructors:
            instructors = list(User.objects.filter(is_superuser=True)[:1])
        sites = list(Site.objects.all())

        for i, cdata in enumerate(COURSE_DATA):
            instructor = instructors[i % len(instructors)] if instructors else None
            site = sites[i % len(sites)] if sites else None

            course = Course.objects.create(
                title=cdata['title'],
                subtitle=cdata['subtitle'],
                description=cdata['description'],
                level=cdata['level'],
                language='Français',
                status='published',
                is_free=(i % 3 != 2),
                price=0 if (i % 3 != 2) else 15000,
                certificate_enabled=(i % 2 == 0),
                target_audience='Étudiants en informatique et passionnés de technologie',
                requirements=cdata['requirements'],
                what_you_will_learn=cdata['what_you_will_learn'],
                total_students=random.randint(20, 200),
                average_rating=round(random.uniform(3.5, 5.0), 2),
                instructor=instructor,
                site=site,
            )
            stats['courses'] += 1

            for s_idx, (s_title, chapters) in enumerate(cdata['sections']):
                section = CourseSection.objects.create(
                    course=course, title=s_title, order=s_idx + 1
                )
                stats['course_sections'] += 1

                chapter = CourseChapter.objects.create(
                    section=section,
                    title=f'Contenu — {s_title}',
                    description=f'Chapitres et leçons de la section {s_title}.',
                    order=1,
                )
                stats['course_chapters'] += 1

                for l_idx, (l_title, content_type, duration) in enumerate(chapters):
                    CourseLesson.objects.create(
                        chapter=chapter,
                        title=l_title,
                        content_type=content_type,
                        duration_seconds=duration,
                        is_preview_free=(l_idx == 0),
                        download_allowed=(content_type == 'pdf'),
                        text_content=f'Contenu textuel de la leçon : {l_title}.' if content_type == 'text' else '',
                        external_embed_url='https://www.youtube.com/embed/dQw4w9WgXcQ' if content_type == 'video' else '',
                        order=l_idx + 1,
                    )
                    stats['course_lessons'] += 1

        self.stdout.write(f'  {stats["courses"]} cours, {stats["course_sections"]} sections, '
                          f'{stats["course_chapters"]} chapitres, {stats["course_lessons"]} leçons')

    # =========================================================================
    # CONTENU PAR CLASSE
    # =========================================================================

    def _seed_class_content(self, cls, cst, students, stats, now):
        from apps.academic.models import Session as AcaSession

        sessions = list(AcaSession.objects.filter(class_obj=cls).select_related('subject', 'teacher__user'))

        for idx, link in enumerate(cst):
            subject = link.subject
            teacher = link.teacher
            bank_key = 'info' if idx % 3 != 2 else ('math' if idx % 3 == 1 else 'general')
            bank = QUIZ_BANKS.get(bank_key, QUIZ_BANKS['info'])

            # ── Chapitres & Leçons ─────────────────────────────────────────
            chapters = self._seed_chapters_lessons(cls, subject, teacher, idx, now, stats)

            # ── Quiz avec variété de types ─────────────────────────────────
            quiz_regular = self._seed_quiz(
                cls, subject, chapters[0]['lesson'] if chapters else None,
                f'Quiz — {subject.name}', bank, students, now, stats,
                time_limit=20, max_attempts=3, is_exam_quiz=False,
            )

            # ── Devoir ────────────────────────────────────────────────────
            self._seed_assignment(cls, subject, teacher,
                                  chapters[0]['lesson'] if chapters else None,
                                  students, now, stats, idx)

            # ── Examen sécurisé ───────────────────────────────────────────
            if idx % 2 == 0:
                self._seed_secure_exam(
                    cls, subject, teacher, bank, students, now, stats, idx,
                    exam_type='FINAL' if idx % 4 == 0 else 'MID',
                )
            else:
                self._seed_secure_exam(
                    cls, subject, teacher, bank, students, now, stats, idx,
                    exam_type='TP' if idx % 4 == 1 else 'SUPP',
                )

            # ── Laboratoire virtuel ───────────────────────────────────────
            lab_info = LAB_DATA[idx % len(LAB_DATA)]
            self._seed_lab(cls, subject, teacher,
                           chapters[0]['lesson'] if chapters else None,
                           students, now, stats, lab_info)

            # ── Vidéo ─────────────────────────────────────────────────────
            self._seed_video(cls, subject,
                             chapters[0]['lesson'] if chapters else None,
                             students, now, stats, idx)

            # ── Classe virtuelle ──────────────────────────────────────────
            self._seed_virtual_classroom(cls, subject, teacher,
                                         chapters[0]['lesson'] if chapters else None,
                                         students, now, stats, idx)

        # ── Réunions Zoom (sur les premières sessions) ─────────────────────
        if sessions and cst:
            teacher_user = cst[0].teacher.user
            for sess in sessions[:min(3, len(sessions))]:
                self._seed_zoom(sess, teacher_user, cls, now, stats)

    # ─── Chapitres & Leçons ───────────────────────────────────────────────────

    def _seed_chapters_lessons(self, cls, subject, teacher, idx, now, stats):
        from apps.elearning.models import Chapter, Lesson, LessonAttachment, LessonProgress

        result = []
        for ch_num in range(1, 3):
            chapter = Chapter.objects.create(
                title=f'Chapitre {ch_num} — {subject.name}',
                description=f'{"Introduction" if ch_num == 1 else "Approfondissement"} de {subject.name}.',
                class_obj=cls, subject=subject, order=(idx * 2) + ch_num, is_published=True,
            )
            stats['chapters'] += 1

            ch_lessons = []
            for li in range(1, 4):
                lesson = Lesson.objects.create(
                    title=f'Leçon {li} — {subject.name} (Chap. {ch_num})',
                    description=f'Contenu pédagogique — {subject.name}, chapitre {ch_num}, séance {li}.',
                    content=LESSON_CONTENTS[li % len(LESSON_CONTENTS)],
                    class_obj=cls, subject=subject, teacher=teacher, chapter=chapter,
                    order=li, is_published=True, published_at=now - timedelta(days=30 - li * 5),
                    min_watch_percent=80 if li < 3 else 60,
                )
                stats['lessons'] += 1

                # Blocs de contenu
                LessonAttachment.objects.create(
                    lesson=lesson,
                    title=f'Support de cours — {subject.name} L{li}',
                    block_type='TEXT',
                    order=1,
                    content=LESSON_CONTENTS[(li + idx) % len(LESSON_CONTENTS)],
                )
                LessonAttachment.objects.create(
                    lesson=lesson,
                    title=f'Vidéo complémentaire — L{li}',
                    block_type='YOUTUBE',
                    order=2,
                    url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                )
                stats['lesson_attachments'] = stats.get('lesson_attachments', 0) + 2

                ch_lessons.append(lesson)

            first_lesson = ch_lessons[0] if ch_lessons else None
            if first_lesson:
                from apps.students.models import Student as StudentModel
                for si, student in enumerate(
                    StudentModel.objects.filter(enrollments__class_obj=cls).distinct()[:6]
                ):
                    watch = [100, 100, 80, 60, 30, 0][si % 6]
                    lp = LessonProgress.objects.create(
                        student=student, lesson=first_lesson,
                        started_at=now - timedelta(days=14),
                        watch_percent=watch,
                        time_spent_seconds=watch * 12,
                    )
                    lp.evaluate_completion()
                    stats['lesson_progress'] += 1

            result.append({'chapter': chapter, 'lessons': ch_lessons, 'lesson': first_lesson})

        return result

    # ─── Quiz ─────────────────────────────────────────────────────────────────

    def _seed_quiz(self, cls, subject, lesson, title, bank, students, now, stats,
                   time_limit=20, max_attempts=2, is_exam_quiz=False):
        from apps.elearning.models import Quiz, Question, Choice, QuizAttempt, AttemptAnswer

        quiz = Quiz.objects.create(
            title=title,
            description=f'Évaluation — {subject.name}.',
            class_obj=cls, subject=subject, lesson=lesson,
            time_limit_minutes=time_limit,
            max_attempts=max_attempts,
            pass_score_percent=50,
            shuffle_questions=True,
            is_published=True,
        )
        stats['quizzes'] += 1

        # Sélectionner 5 questions variées depuis la banque
        selected = random.sample(bank, min(5, len(bank)))
        for q_idx, qdata in enumerate(selected, start=1):
            q_kwargs = {
                'quiz': quiz,
                'question_type': qdata['type'],
                'text': qdata['text'],
                'order': q_idx,
                'points': 2 if qdata['type'] in ('QCU', 'TRUEFALSE') else 3,
                'explanation': qdata.get('explanation', ''),
            }
            if qdata['type'] == 'TEXT':
                q_kwargs['text_answer'] = qdata.get('text_answer', '')
            if qdata['type'] == 'NUMERIC':
                q_kwargs['numeric_answer'] = qdata.get('numeric_answer', 0)
                q_kwargs['numeric_tolerance'] = qdata.get('numeric_tolerance', 0)

            question = Question.objects.create(**q_kwargs)
            stats['questions'] += 1

            if qdata['type'] in ('QCU', 'QCM', 'TRUEFALSE'):
                for c_order, (c_text, c_correct) in enumerate(qdata['choices'], start=1):
                    Choice.objects.create(
                        question=question, text=c_text,
                        is_correct=c_correct, order=c_order,
                    )

        # Tentatives étudiants
        for si, student in enumerate(students[:4]):
            attempt = QuizAttempt.objects.create(quiz=quiz, student=student)
            for q in quiz.questions.all():
                ans = AttemptAnswer.objects.create(attempt=attempt, question=q)
                if q.question_type in ('QCU', 'QCM', 'TRUEFALSE'):
                    correct_choices = q.choices.filter(is_correct=True)
                    wrong_choices = q.choices.filter(is_correct=False)
                    if si == 0:  # Excellent
                        ans.selected_choices.set(correct_choices)
                    elif si == 1:  # Bien
                        if random.random() > 0.3:
                            ans.selected_choices.set(correct_choices)
                        else:
                            ans.selected_choices.set(wrong_choices[:1] if wrong_choices else correct_choices)
                    elif si == 2:  # Moyen
                        if random.random() > 0.5:
                            ans.selected_choices.set(correct_choices)
                        else:
                            ans.selected_choices.set(wrong_choices[:1] if wrong_choices else correct_choices)
                    else:  # Faible
                        ans.selected_choices.set(wrong_choices[:1] if wrong_choices else correct_choices)
                elif q.question_type == 'TEXT':
                    ans.text_response = q.text_answer if (si < 2 and q.text_answer) else 'Je ne sais pas.'
                elif q.question_type == 'NUMERIC':
                    if q.numeric_answer is not None:
                        ans.numeric_response = q.numeric_answer if si < 3 else q.numeric_answer + 5
                    ans.save()
                ans.grade()
            attempt.finalize()
            stats['quiz_attempts'] += 1

        return quiz

    # ─── Devoir ───────────────────────────────────────────────────────────────

    def _seed_assignment(self, cls, subject, teacher, lesson, students, now, stats, idx):
        from apps.elearning.models import Assignment, AssignmentSubmission, AssignmentCorrection

        statuses = ['PUBLISHED', 'PUBLISHED', 'CLOSED', 'DRAFT']
        status = statuses[idx % len(statuses)]
        due_offset = [-5, 7, -15, 20][idx % 4]  # négatif = passé (retard possible)

        assignment = Assignment.objects.create(
            title=f'Devoir {idx + 1} — {subject.name}',
            description=f'Devoir portant sur les notions abordées en {subject.name}.',
            instructions='Lire attentivement les consignes. Rendre avant la date limite. Plagiat interdit.',
            class_obj=cls, subject=subject, teacher=teacher, lesson=lesson,
            due_date=now + timedelta(days=due_offset),
            max_score=20,
            status=status,
            published_at=now - timedelta(days=5) if status != 'DRAFT' else None,
            allow_late_submission=(idx % 3 == 0),
            late_penalty_percent=10 if (idx % 3 == 0) else 0,
        )
        stats['assignments'] += 1

        if status in ('PUBLISHED', 'CLOSED'):
            for si, student in enumerate(students):
                if si % 4 == 3:  # 25% n'ont pas rendu
                    continue
                sub = AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=student,
                    content=f'Rapport rédigé par {student.user.full_name or student.matricule}. '
                            f'Ce devoir porte sur {subject.name} et présente une analyse approfondie du sujet.',
                )
                stats['submissions'] += 1

                if status == 'CLOSED' or si % 2 == 0:
                    score = round(random.uniform(8, 19), 2)
                    feedbacks = [
                        'Excellent travail, synthèse bien structurée.',
                        'Bon travail dans l\'ensemble, quelques points à approfondir.',
                        'Travail satisfaisant, manque d\'exemples concrets.',
                        'Efforts visibles mais analyse insuffisante.',
                    ]
                    AssignmentCorrection.objects.create(
                        submission=sub,
                        score=score,
                        feedback=feedbacks[si % len(feedbacks)],
                        corrected_by=teacher.user,
                    )
                    stats['corrections'] += 1

    # ─── Examen sécurisé ──────────────────────────────────────────────────────

    def _seed_secure_exam(self, cls, subject, teacher, bank, students, now, stats, idx, exam_type='FINAL'):
        from apps.elearning.models import (
            Quiz, Question, Choice, SecureExam,
            ExamSession, QuizAttempt, AttemptAnswer,
        )

        durations = {'FINAL': 120, 'MID': 90, 'TP': 180, 'SUPP': 120, 'CONCOURS': 240}
        duration = durations.get(exam_type, 120)

        # Décalage dans le temps selon le type
        if exam_type in ('SUPP',):
            start = now + timedelta(days=30)
        elif exam_type == 'MID':
            start = now + timedelta(days=10)
        elif exam_type == 'TP':
            start = now - timedelta(days=3)  # TP récent passé
        else:
            start = now + timedelta(days=45)

        exam_quiz = Quiz.objects.create(
            title=f'Quiz Examen — {subject.name}',
            class_obj=cls, subject=subject,
            time_limit_minutes=duration,
            max_attempts=1, pass_score_percent=50, is_published=True,
        )

        selected = random.sample(bank, min(8, len(bank)))
        for q_idx, qdata in enumerate(selected, start=1):
            q_kwargs = {
                'quiz': exam_quiz,
                'question_type': qdata['type'],
                'text': qdata['text'],
                'order': q_idx,
                'points': 5 if qdata['type'] in ('QCU', 'TRUEFALSE') else 8,
                'explanation': qdata.get('explanation', ''),
            }
            if qdata['type'] == 'TEXT':
                q_kwargs['text_answer'] = qdata.get('text_answer', '')
            if qdata['type'] == 'NUMERIC':
                q_kwargs['numeric_answer'] = qdata.get('numeric_answer', 0)
                q_kwargs['numeric_tolerance'] = qdata.get('numeric_tolerance', 0)

            question = Question.objects.create(**q_kwargs)
            stats['questions'] += 1

            if qdata['type'] in ('QCU', 'QCM', 'TRUEFALSE'):
                for c_order, (c_text, c_correct) in enumerate(qdata['choices'], start=1):
                    Choice.objects.create(
                        question=question, text=c_text,
                        is_correct=c_correct, order=c_order,
                    )

        exam = SecureExam.objects.create(
            title=f'{"Examen Final" if exam_type == "FINAL" else exam_type} — {subject.name}',
            description=f'Examen {exam_type} de {subject.name}. Durée : {duration} minutes.',
            class_obj=cls, subject=subject, quiz=exam_quiz,
            exam_type=exam_type, duration_minutes=duration,
            start_date=start, end_date=start + timedelta(hours=duration // 60 + 1),
            max_attempts=1,
            fullscreen_required=True,
            webcam_required=(idx % 3 == 0),
            block_copy_paste=True,
            max_tab_switches=3,
            is_published=True,
            pass_score_percent=50,
            coefficient=2 if exam_type == 'FINAL' else 1,
        )
        stats['exams'] += 1
        stats['quizzes'] += 1

        # Sessions pour examens passés (TP)
        if exam_type == 'TP':
            for si, student in enumerate(students[:3]):
                attempt = QuizAttempt.objects.create(quiz=exam_quiz, student=student)
                for q in exam_quiz.questions.all():
                    ans = AttemptAnswer.objects.create(attempt=attempt, question=q)
                    if q.question_type in ('QCU', 'QCM', 'TRUEFALSE'):
                        correct = q.choices.filter(is_correct=True)
                        wrong = q.choices.filter(is_correct=False)
                        if si == 0:
                            ans.selected_choices.set(correct)
                        elif si == 1:
                            if random.random() > 0.3:
                                ans.selected_choices.set(correct)
                            else:
                                ans.selected_choices.set(wrong[:1])
                        else:
                            ans.selected_choices.set(wrong[:1] if wrong else correct)
                    ans.grade()
                attempt.finalize()

                session_status = ['SUBMITTED', 'SUBMITTED', 'FLAGGED'][si]
                ExamSession.objects.create(
                    exam=exam, student=student,
                    quiz_attempt=attempt,
                    submitted_at=now - timedelta(days=2),
                    status=session_status,
                    tab_switch_count=si,
                    is_flagged=(si == 2),
                    flag_reason='Changements d\'onglet excessifs.' if si == 2 else '',
                )
                stats['exam_sessions'] = stats.get('exam_sessions', 0) + 1
                stats['quiz_attempts'] += 1

    # ─── Laboratoire virtuel ──────────────────────────────────────────────────

    def _seed_lab(self, cls, subject, teacher, lesson, students, now, stats, lab_info):
        from apps.elearning.models import VirtualLab, LabSubmission

        lab_title, lab_type, instructions, objectives = lab_info

        lab = VirtualLab.objects.create(
            title=f'{lab_title} [{subject.code}]',
            description=f'Laboratoire virtuel de {subject.name}.',
            instructions=instructions,
            objectives=objectives,
            lab_type=lab_type,
            class_obj=cls, subject=subject, lesson=lesson,
            access_url='https://lab.example.com/session',
            embed_url='https://lab.example.com/embed',
            duration_minutes=random.choice([90, 120, 180]),
            due_date=now + timedelta(days=random.choice([7, 14, 21])),
            max_attempts=3,
            max_score=20,
            is_published=True,
            order=1,
        )
        stats['labs'] += 1

        statuses_lab = ['SUBMITTED', 'SUBMITTED', 'GRADED', 'STARTED']
        for si, student in enumerate(students[:4]):
            sub_status = statuses_lab[si % len(statuses_lab)]
            sub = LabSubmission.objects.create(
                lab=lab, student=student,
                status=sub_status,
                report_text=f'Compte-rendu du laboratoire par {student.user.full_name or student.matricule}. '
                            f'Protocole suivi étape par étape. Résultats conformes aux attentes.',
                submitted_at=now - timedelta(days=si + 1) if sub_status in ('SUBMITTED', 'GRADED') else None,
            )
            if sub_status == 'GRADED':
                sub.score = round(random.uniform(12, 19), 2)
                sub.feedback = 'Très bon rapport, résultats bien présentés.'
                sub.graded_by = teacher
                sub.graded_at = now - timedelta(hours=12)
                sub.save()
            stats['lab_submissions'] += 1

    # ─── Vidéo ────────────────────────────────────────────────────────────────

    def _seed_video(self, cls, subject, lesson, students, now, stats, idx):
        from apps.elearning.models import VideoLibrary, VideoProgress

        vdata = VIDEO_DATA[idx % len(VIDEO_DATA)]
        v_title, v_source, v_url, v_duration, v_tags = vdata

        video = VideoLibrary.objects.create(
            title=f'{v_title} — {subject.name}',
            description=f'Ressource vidéo pour le cours de {subject.name}.',
            source_type=v_source,
            source_url=v_url,
            duration_seconds=v_duration,
            tags=v_tags,
            class_obj=cls, subject=subject, lesson=lesson,
            is_downloadable=False,
            watermark_enabled=True,
            disable_right_click=True,
            is_published=True,
            order=idx + 1,
            view_count=random.randint(5, 80),
        )
        stats['videos'] += 1

        for si, student in enumerate(students[:3]):
            watched = [v_duration, int(v_duration * 0.7), int(v_duration * 0.3)][si]
            VideoProgress.objects.create(
                student=student, video=video,
                position_seconds=watched,
                total_watched_seconds=watched,
                is_completed=(watched >= v_duration * 0.9),
            )
            stats['video_progress'] += 1

    # ─── Classe virtuelle ─────────────────────────────────────────────────────

    def _seed_virtual_classroom(self, cls, subject, teacher, lesson, students, now, stats, idx):
        from apps.elearning.models import VirtualClassroom, ClassroomPoll, PollResponse, ClassroomChatMessage

        providers = ['JITSI', 'ZOOM', 'MEET', 'BBB', 'TEAMS']
        # Passé, en cours, futur
        offsets = [(-3, True), (0, False), (7, False)]
        offset_days, is_ended = offsets[idx % len(offsets)]

        start = now + timedelta(days=offset_days, hours=9)

        vc = VirtualClassroom.objects.create(
            title=f'Séance en ligne — {subject.name} (S{idx + 1})',
            provider=providers[idx % len(providers)],
            class_obj=cls, subject=subject, lesson=lesson,
            start_time=start,
            duration_minutes=random.choice([60, 90, 120]),
            join_url='https://meet.jit.si/campus-demo',
            jitsi_room_name=f'campus-{cls.code}-{subject.code}-{idx}',
            enable_recording=True,
            enable_whiteboard=True,
            enable_polls=(idx % 2 == 0),
            enable_chat=True,
            enable_hand_raise=True,
            breakout_rooms=2 if idx % 3 == 0 else 0,
            is_ended=is_ended,
            ended_at=start + timedelta(minutes=90) if is_ended else None,
            recording_url='https://example.com/recording/demo' if is_ended else '',
            ai_summary='Résumé IA de la séance : concepts clés abordés, questions posées, exercices réalisés.' if is_ended else '',
            created_by=teacher.user,
        )
        stats['classrooms'] += 1

        # Sondage dans une séance sur deux
        if idx % 2 == 0:
            poll = ClassroomPoll.objects.create(
                classroom=vc,
                question='Avez-vous bien compris les notions abordées aujourd\'hui ?',
                options=['Très bien', 'Assez bien', 'Pas vraiment', 'Pas du tout'],
                is_active=not is_ended,
                show_results=is_ended,
            )
            for si, student in enumerate(students[:4]):
                PollResponse.objects.create(
                    poll=poll, student=student,
                    selected_option=random.randint(0, 3),
                )

        # Messages de chat pour les séances passées
        if is_ended and students:
            messages = [
                (teacher.user, 'Bonjour à tous ! Nous allons commencer par un rappel du cours précédent.'),
                (students[0].user if students else teacher.user, 'Bonjour professeur !'),
                (teacher.user, 'Qui peut me résumer les points clés de la dernière leçon ?'),
                (students[1].user if len(students) > 1 else teacher.user, 'On avait vu les structures de données et leur complexité.'),
                (teacher.user, 'Très bien ! Aujourd\'hui on passe à la pratique.'),
            ]
            for msg_user, msg_text in messages:
                ClassroomChatMessage.objects.create(
                    classroom=vc, user=msg_user, message=msg_text,
                )

    # ─── Zoom ─────────────────────────────────────────────────────────────────

    def _seed_zoom(self, session, teacher_user, cls, now, stats):
        from apps.elearning.models import ZoomMeeting

        ZoomMeeting.objects.create(
            session=session,
            meeting_id=f'{random.randint(100,999)} {random.randint(1000,9999)} {random.randint(1000,9999)}',
            topic=f'{session.subject.name} — {cls.code}',
            start_time=now + timedelta(days=random.randint(1, 30), hours=9),
            duration=90,
            join_url='https://zoom.us/j/0000000000',
            host=teacher_user,
            created_by=teacher_user,
        )
        stats['zoom_meetings'] += 1

    # =========================================================================
    # BIBLIOTHÈQUE
    # =========================================================================

    def _seed_library(self, all_students, stats, now):
        from apps.elearning.models import LibraryDocument, ReadingProgress, DocumentFavorite
        from apps.accounts.models import User
        from apps.core.models import Site
        from apps.academic.models import Subject

        uploader = User.objects.filter(is_superuser=True).first()
        subjects = list(Subject.objects.all()[:15])
        sites = list(Site.objects.all())

        created_docs = []
        for i, (title, dtype, authors, year, pages, abstract) in enumerate(LIBRARY_DOCS_RICH):
            site = sites[i % len(sites)] if (i < len(LIBRARY_DOCS_RICH) // 2 and sites) else None
            doc = LibraryDocument.objects.create(
                title=title,
                authors=authors,
                doc_type=dtype,
                year=year,
                pages=pages,
                abstract=abstract,
                publisher='Campus Éditions',
                language='fr',
                keywords=', '.join(title.lower().split()[:5]),
                is_downloadable=True,
                is_online_readable=True,
                is_published=True,
                download_count=random.randint(5, 150),
                view_count=random.randint(20, 500),
                site=site,
                uploaded_by=uploader,
            )
            if subjects:
                doc.subjects.set(random.sample(subjects, min(3, len(subjects))))
            created_docs.append(doc)
            stats['library_documents'] += 1

        # Progressions et favoris
        for student in all_students[:8]:
            for doc in random.sample(created_docs, min(3, len(created_docs))):
                ReadingProgress.objects.create(
                    student=student, document=doc,
                    current_page=random.randint(1, doc.pages or 100),
                )
                stats['reading_progress'] = stats.get('reading_progress', 0) + 1

            for doc in random.sample(created_docs, min(2, len(created_docs))):
                DocumentFavorite.objects.get_or_create(student=student, document=doc)
                stats['doc_favorites'] = stats.get('doc_favorites', 0) + 1

        self.stdout.write(f'  {stats["library_documents"]} documents créés')

    # =========================================================================
    # CONVERSATIONS IA
    # =========================================================================

    def _seed_ai_global(self, all_students, classes, stats, now):
        from apps.elearning.models import AIConversation, AIMessage
        from apps.accounts.models import User

        teachers = list(User.objects.filter(user_type='TEACHER')[:5])

        # Conversations étudiants
        for student in all_students[:6]:
            for conv_type, convs in AI_CONVERSATIONS.items():
                if conv_type not in ('TUTOR', 'FLASHCARD', 'PLAN'):
                    continue
                qa_pair = convs[0]
                conv = AIConversation.objects.create(
                    user=student.user,
                    conv_type=conv_type,
                    title=f'{conv_type} — {student.user.full_name or student.matricule}',
                )
                user_msg, asst_msg = qa_pair
                AIMessage.objects.create(conversation=conv, role='user', content=user_msg)
                AIMessage.objects.create(conversation=conv, role='assistant', content=asst_msg)
                stats['ai_conversations'] += 1

        # Conversations enseignants
        for teacher in teachers:
            for conv_type in ('TEACHER', 'QUIZ_GEN', 'CONTENT'):
                if conv_type not in AI_CONVERSATIONS:
                    continue
                qa_pair = AI_CONVERSATIONS[conv_type][0]
                conv = AIConversation.objects.create(
                    user=teacher,
                    conv_type=conv_type,
                    title=f'Assistant {conv_type} — {teacher.full_name or teacher.email}',
                )
                user_msg, asst_msg = qa_pair
                AIMessage.objects.create(conversation=conv, role='user', content=user_msg)
                AIMessage.objects.create(conversation=conv, role='assistant', content=asst_msg, tokens_used=320)
                stats['ai_conversations'] += 1

        self.stdout.write(f'  {stats["ai_conversations"]} conversations IA créées')

    # =========================================================================
    # RÉSUMÉ
    # =========================================================================

    def _summary(self, stats):
        sep = '=' * 72
        labels = [
            ('courses', 'Cours autonomes (MOOC)'),
            ('course_sections', 'Sections de cours'),
            ('course_chapters', 'Chapitres de cours'),
            ('course_lessons', 'Leçons de cours'),
            ('chapters', 'Chapitres de classe'),
            ('lessons', 'Leçons de classe'),
            ('lesson_attachments', 'Blocs de contenu'),
            ('lesson_progress', 'Progressions de leçon'),
            ('quizzes', 'Quiz'),
            ('questions', 'Questions'),
            ('quiz_attempts', 'Tentatives de quiz'),
            ('assignments', 'Devoirs'),
            ('submissions', 'Soumissions de devoirs'),
            ('corrections', 'Corrections'),
            ('exams', 'Examens sécurisés'),
            ('exam_sessions', 'Sessions d\'examen'),
            ('labs', 'Laboratoires virtuels'),
            ('lab_submissions', 'Soumissions de labo'),
            ('videos', 'Vidéos'),
            ('video_progress', 'Progressions vidéo'),
            ('classrooms', 'Classes virtuelles'),
            ('zoom_meetings', 'Réunions Zoom'),
            ('library_documents', 'Documents bibliothèque'),
            ('reading_progress', 'Progressions de lecture'),
            ('doc_favorites', 'Favoris documents'),
            ('ai_conversations', 'Conversations IA'),
        ]
        self.stdout.write('\n' + sep)
        self.stdout.write('SEED E-LEARNING COMPLET — TERMINÉ')
        self.stdout.write(sep)
        total = 0
        for key, label in labels:
            n = stats.get(key, 0)
            total += n
            if n:
                self.stdout.write(f'  {label:<35}: {n:>5}')
        self.stdout.write(f'  {"TOTAL":<35}: {total:>5}')
        self.stdout.write(sep + '\n')
