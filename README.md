# Campus Management System - Backend

Système de gestion universitaire complet développé avec Django REST Framework.

## Fonctionnalités

### Modules principaux
- **Multi-site** : Support de plusieurs campus
- **Scolarité** : Gestion des étudiants, inscriptions, dossiers
- **Enseignants** : Profils, planning, multi-site
- **Parents** : Liaison étudiants-parents, notifications
- **Présence QR** : Scan QR code anti-fraude
- **Absences** : Demandes et justifications
- **Factures & Paiements** : Espèces et Mobile Money (CinetPay)
- **Trésorerie** : Sessions de caisse, rapports
- **Comptabilité** : Plan comptable, écritures, exports
- **GED** : Documents, validation, archivage
- **E-learning** : Zoom, leçons, devoirs, corrections
- **Chat** : Par classe, WebSocket temps réel
- **Notifications** : Multi-canal, WebSocket

## Prérequis

- Python 3.10+
- MySQL 8.0+
- Redis 6.0+

## Installation

### 1. Cloner le projet
```bash
cd C:\Users\HP\Desktop\projets
git clone <repo-url> campus-backend
cd campus-backend
```

### 2. Créer l'environnement virtuel
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer la base de données MySQL
```sql
CREATE DATABASE campus_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'campus_user'@'localhost' IDENTIFIED BY 'votre_mot_de_passe';
GRANT ALL PRIVILEGES ON campus_db.* TO 'campus_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Configurer les variables d'environnement
```bash
copy .env.example .env
# Éditer .env avec vos paramètres
```

### 6. Appliquer les migrations
```bash
python manage.py migrate
```

### 7. Créer un superutilisateur
```bash
python manage.py createsuperuser
```

### 8. Lancer le serveur de développement
```bash
# HTTP classique
python manage.py runserver

# Avec WebSocket (recommandé)
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

## Structure du projet

```
campus-backend/
├── config/                 # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── core/              # Sites, années académiques, audit
│   ├── accounts/          # Utilisateurs, rôles, permissions
│   ├── students/          # Étudiants, parents, dossiers
│   ├── academic/          # Filières, classes, enseignants
│   ├── attendance/        # Présence QR, absences
│   ├── finance/           # Factures, paiements, caisse
│   ├── payments/          # Intégration CinetPay
│   ├── accounting/        # Comptabilité
│   ├── documents/         # GED, archives
│   ├── elearning/         # Zoom, leçons, devoirs
│   ├── chat/              # Chat temps réel
│   ├── notifications/     # Notifications
│   └── reports/           # Tableaux de bord, rapports
├── media/                 # Fichiers uploadés
├── static/                # Fichiers statiques
├── logs/                  # Logs applicatifs
└── requirements.txt
```

## API Endpoints

Base URL: `/api/v1/`

### Authentification
- `POST /auth/login/` - Connexion
- `POST /auth/refresh/` - Rafraîchir le token
- `GET /auth/me/` - Profil utilisateur

### Sites & Configuration
- `GET/POST /sites/` - Gestion des campus
- `GET/POST /academic-years/` - Années académiques

### Étudiants & Parents
- `GET/POST /students/` - Gestion des étudiants
- `GET /students/{id}/dossier/` - Dossier complet
- `POST /students/{id}/link-parent/` - Lier un parent
- `GET/POST /parents/` - Gestion des parents

### Enseignants & Classes
- `GET/POST /teachers/` - Gestion des enseignants
- `POST /teachers/{id}/assign-sites/` - Affectation multi-site
- `GET/POST /classes/` - Gestion des classes
- `GET/POST /sessions/` - Emploi du temps

### Présence
- `POST /attendance/open/` - Ouvrir une session
- `GET /attendance-sessions/{id}/qr/` - Générer QR code
- `POST /attendance/scan/` - Scanner (étudiant)
- `POST /absence-requests/` - Demande d'absence

### Finances
- `GET/POST /invoices/` - Factures
- `POST /invoices/{id}/add-item/` - Ajouter une ligne
- `POST /payments/cash/` - Paiement espèces
- `POST /payments/cinetpay/initiate/` - Initier Mobile Money
- `POST /payments/cinetpay/callback/` - Callback CinetPay

### Trésorerie & Comptabilité
- `POST /cash/sessions/open/` - Ouvrir une caisse
- `POST /cash-sessions/{id}/close/` - Clôturer
- `GET /cash/reports/daily/` - Rapport journalier
- `GET /accounting/journal-entries/` - Écritures
- `GET /accounting/exports/excel/` - Export Excel

### E-learning
- `POST /zoom/create-meeting/` - Créer réunion Zoom
- `GET/POST /lessons/` - Leçons
- `GET/POST /assignments/` - Devoirs
- `POST /assignments/{id}/submit/` - Soumettre
- `POST /submissions/{id}/correct/` - Corriger

### Chat & Notifications
- `GET /chats/class/{class_id}/` - Chat de classe
- `POST /chats/{id}/send-message/` - Envoyer message
- `GET /notifications/` - Notifications
- `POST /notifications/{id}/read/` - Marquer lu

### WebSocket
- `WS /ws/chat/{chat_id}/` - Chat temps réel
- `WS /ws/notifications/` - Notifications temps réel

## Celery (Tâches asynchrones)

```bash
# Worker
celery -A config worker -l info

# Beat (tâches planifiées)
celery -A config beat -l info
```

## Déploiement Production

### Docker (recommandé)
```bash
docker-compose up -d
```

### Manuel
1. Configurer Nginx comme reverse proxy
2. Utiliser Gunicorn pour HTTP
3. Utiliser Daphne pour WebSocket
4. Configurer SSL avec Let's Encrypt
5. Configurer les services systemd

## Tests

```bash
pytest
```

## Documentation API

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- Schema: `/api/schema/`

## Licence

Propriétaire - Tous droits réservés
