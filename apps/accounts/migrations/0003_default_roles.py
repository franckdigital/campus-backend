from django.db import migrations


DEFAULT_ROLES = [
    {
        'name': 'Administrateur',
        'code': 'ADMIN',
        'description': 'Accès total à toutes les fonctionnalités du système',
        'is_system': True,
    },
    {
        'name': 'Direction',
        'code': 'DIRECTION',
        'description': 'Accès étendu à la gestion académique et administrative',
        'is_system': True,
    },
    {
        'name': 'Scolarité',
        'code': 'SCOLARITE',
        'description': 'Gestion des inscriptions, présences et dossiers étudiants',
        'is_system': True,
    },
    {
        'name': 'Comptabilité',
        'code': 'COMPTABILITE',
        'description': 'Gestion financière, paiements et comptabilité',
        'is_system': True,
    },
    {
        'name': 'Enseignant',
        'code': 'ENSEIGNANT',
        'description': 'Saisie des notes, présences et contenu e-learning',
        'is_system': True,
    },
    {
        'name': 'Étudiant',
        'code': 'ETUDIANT',
        'description': 'Accès en lecture au dossier personnel et à l\'e-learning',
        'is_system': True,
    },
    {
        'name': 'Parent',
        'code': 'PARENT',
        'description': 'Consultation du dossier des enfants et des paiements',
        'is_system': True,
    },
]


def create_default_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    for role_data in DEFAULT_ROLES:
        Role.objects.get_or_create(
            code=role_data['code'],
            defaults=role_data,
        )


def reverse_default_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    codes = [r['code'] for r in DEFAULT_ROLES]
    Role.objects.filter(code__in=codes, is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_roles, reverse_default_roles),
    ]
