#!/bin/bash
# Script de déploiement Campus Backend
# Usage: sudo bash deploy.sh

set -e

PROJECT_DIR="/var/www/campus-backend"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="/var/log/campus"
RUN_DIR="/var/run/campus"

echo "=== Déploiement Campus Backend ==="

# 1. Créer les répertoires nécessaires
echo "Création des répertoires..."
mkdir -p $LOG_DIR $RUN_DIR
chown -R www-data:www-data $LOG_DIR $RUN_DIR

# 2. Aller dans le répertoire du projet
cd $PROJECT_DIR

# 3. Activer l'environnement virtuel
source $VENV_DIR/bin/activate

# 4. Installer/Mettre à jour les dépendances
echo "Installation des dépendances..."
pip install -r requirements.txt

# 5. Collecter les fichiers statiques
echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# 6. Appliquer les migrations
echo "Application des migrations..."
python manage.py migrate --noinput

# 7. Copier les fichiers de service systemd
echo "Configuration des services systemd..."
cp deploy/campus-gunicorn.service /etc/systemd/system/
cp deploy/campus-daphne.service /etc/systemd/system/
cp deploy/campus-celery.service /etc/systemd/system/
cp deploy/campus-celery-beat.service /etc/systemd/system/

# 8. Recharger systemd
systemctl daemon-reload

# 9. Activer et démarrer les services
echo "Démarrage des services..."
systemctl enable campus-gunicorn campus-daphne campus-celery campus-celery-beat
systemctl restart campus-gunicorn campus-daphne campus-celery campus-celery-beat

# 10. Configurer Nginx
echo "Configuration Nginx..."
cp deploy/nginx-campus.conf /etc/nginx/sites-available/campus
ln -sf /etc/nginx/sites-available/campus /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "=== Déploiement terminé ==="
echo ""
echo "Vérification des services:"
systemctl status campus-gunicorn --no-pager
systemctl status campus-daphne --no-pager
systemctl status campus-celery --no-pager

echo ""
echo "Commandes utiles:"
echo "  - Logs Gunicorn: journalctl -u campus-gunicorn -f"
echo "  - Logs Daphne: journalctl -u campus-daphne -f"
echo "  - Redémarrer: sudo systemctl restart campus-gunicorn campus-daphne"
