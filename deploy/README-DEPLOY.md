# Guide de Déploiement Production - Campus Backend

## Prérequis serveur (Ubuntu 22.04+)

```bash
# Mise à jour système
sudo apt update && sudo apt upgrade -y

# Installer les dépendances
sudo apt install -y python3.11 python3.11-venv python3-pip \
    mysql-server redis-server nginx certbot python3-certbot-nginx \
    supervisor git
```

## 1. Préparation du projet

```bash
# Créer le répertoire
sudo mkdir -p /var/www/campus-backend
sudo chown $USER:$USER /var/www/campus-backend

# Cloner ou copier le projet
cd /var/www/campus-backend
git clone <repo> .  # ou copier les fichiers

# Environnement virtuel
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configuration
cp .env.example .env
nano .env  # Configurer MySQL, Redis, etc.
```

## 2. Base de données MySQL

```bash
sudo mysql
```

```sql
CREATE DATABASE campus_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'campus_user'@'localhost' IDENTIFIED BY 'MotDePasseSecurise123!';
GRANT ALL PRIVILEGES ON campus_db.* TO 'campus_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 3. Migrations et statiques

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

## 4. Services Systemd

```bash
# Copier les fichiers de service
sudo cp deploy/campus-*.service /etc/systemd/system/

# Créer les répertoires de logs
sudo mkdir -p /var/log/campus /var/run/campus
sudo chown www-data:www-data /var/log/campus /var/run/campus

# Activer les services
sudo systemctl daemon-reload
sudo systemctl enable campus-gunicorn campus-daphne campus-celery campus-celery-beat
sudo systemctl start campus-gunicorn campus-daphne campus-celery campus-celery-beat
```

## 5. Nginx

```bash
# Copier la configuration
sudo cp deploy/nginx-campus.conf /etc/nginx/sites-available/campus
sudo ln -s /etc/nginx/sites-available/campus /etc/nginx/sites-enabled/

# Éditer le domaine
sudo nano /etc/nginx/sites-available/campus

# Tester et recharger
sudo nginx -t
sudo systemctl reload nginx
```

## 6. SSL avec Let's Encrypt

```bash
sudo certbot --nginx -d api-campus.numerix.digital
```

## 7. Vérification

```bash
# Statut des services
sudo systemctl status campus-gunicorn
sudo systemctl status campus-daphne
sudo systemctl status campus-celery

# Logs
sudo journalctl -u campus-gunicorn -f
sudo journalctl -u campus-daphne -f
```

## Commandes utiles

```bash
# Redémarrer tous les services
sudo systemctl restart campus-gunicorn campus-daphne campus-celery campus-celery-beat

# Mettre à jour l'application
cd /var/www/campus-backend
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart campus-gunicorn campus-daphne
```

## Architecture

```
Internet
    │
    ▼
[Nginx :443/:80]
    │
    ├── /static/ → Fichiers statiques
    ├── /media/ → Fichiers uploadés
    ├── /ws/* → Daphne :8002 (WebSocket)
    └── /* → Gunicorn :8001 (HTTP)
                │
                ├── MySQL :3306
                └── Redis :6379
                        │
                        └── Celery Workers
```

## Ports utilisés

| Service | Port | Description |
|---------|------|-------------|
| Nginx | 80, 443 | Reverse proxy |
| Gunicorn | 8001 | HTTP API |
| Daphne | 8002 | WebSocket |
| MySQL | 3306 | Base de données |
| Redis | 6379 | Cache / Celery |
