import os
from dotenv import load_dotenv

# Chargement des variables d'environnement depuis .env
load_dotenv()

# Token Discord (à stocker dans un fichier .env)
TOKEN = os.getenv('DISCORD_TOKEN')

# Configuration générale
DEFAULT_PREFIX = '!mk'
DEFAULT_TOURNAMENT_DURATION = 30  # en jours
REMINDER_DAYS_BEFORE_END = 3

# Classes de véhicules disponibles
VEHICLE_CLASSES = ['150cc', '200cc', 'Miroir']

# Chemin vers la base de données
DATABASE_PATH = 'data/tournaments.db'

# Chemin vers le fichier de données des courses
COURSES_FILE = 'data/courses.json'

# Configuration de journalisation
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/bot.log'

# Couleurs pour les embeds
COLORS = {
    'SUCCESS': 0x2ECC71,  # Vert
    'ERROR': 0xE74C3C,    # Rouge
    'INFO': 0x3498DB,     # Bleu
    'WARNING': 0xF1C40F,  # Jaune
}

# Emojis personnalisés
EMOJIS = {
    'TROPHY': '🏆',
    'TIMER': '⏱️',
    'CHECK': '✅',
    'CANCEL': '❌',
    'WARNING': '⚠️',
}