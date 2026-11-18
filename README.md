# DocHub
 
Plateforme web de gestion des documents, actualités, événements et demandes de support d'un groupe ou d'une organisation, avec tableau de bord statistique, rapports et fonctionnalités d'assistance par IA.
 
Projet académique réalisé en équipe, selon la méthodologie Scrum (3 sprints d'une semaine).
 
## Équipe
 
| Rôle | Membre |
|---|---|
| Product Owner / Scrum Master | Mme Hajer Ghodhbani |
| Module Utilisateurs | Amine Challouf |
| Module Documents | Yassine Babay |
| Module Actualités | Mouadh Jebabli |
| Module Événements | Amal Hlaili |
| Module Support | Iyed Aloui |
| Module Statistiques | Meriem Dhrif |
 
## Stack technique
 
- **Backend** : Python, Django
- **Base de données** : Oracle (image Docker `gvenzl/oracle-free`)
- **Conteneurisation** : Docker, Docker Compose
- **Versionnement** : Git
## Prérequis
 
- [Docker](https://docs.docker.com/get-docker/) et Docker Compose
- [Git](https://git-scm.com/)
## Installation
 
1. **Cloner le dépôt**
```bash
git clone https://github.com/Lisette8/Dochub
cd DocHub
```
 
2. **Créer le fichier d'environnement**
```bash
cp .env.example .env (macos)
copy .env.example .env (windows)
```
 
   Puis renseigner les valeurs dans `.env`. Les variables utilisées pour la base de données sont :
 
   | Variable | Description | Valeur par défaut |
   |---|---|---|
   | `DB_HOST` | Hôte Oracle | `localhost` |
   | `DB_PORT` | Port Oracle | `1521` |
   | `DB_NAME` | Nom du service Oracle | `FREEPDB1` |
   | `DB_USER` | Utilisateur de la base | (obligatoire) |
   | `DB_PASSWORD` | Mot de passe | (obligatoire) |
 
   > Le fichier `.env` ne doit **jamais** être commité.
 
3. **Lancer la stack**
```bash
docker compose up --build
```
 
   Deux services démarrent : `db` (Oracle) et `web` (Django, port 8000). Attendre que `db` soit `healthy` avant de continuer.
 
4. **Appliquer les migrations**
```bash
docker compose exec web python manage.py migrate
```
 
5. **Créer un compte administrateur**
```bash
docker compose exec web python manage.py createsuperuser
```

## Commandes utiles
 
```bash
# Voir l'état des conteneurs
docker compose ps
 
# Voir les logs de l'application
docker compose logs -f web
 
# Créer les migrations d'une app
docker compose exec web python manage.py makemigrations <app>
 
# Arrêter la stack
docker compose down
```

## Documentation du projet

https://trello.com/invite/b/6ac541effe3cc229de368ad4/ATTI38fcd34140db4ac2f1df675412193c6b20E240CD/softwarebig6
 
