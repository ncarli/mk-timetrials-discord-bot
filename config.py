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

TRASH_TALK_MESSAGES = [
    "🔥 MASSACRE TEMPOREL ! L'ancien record vient d'être tellement humilié qu'il demande à être effacé des mémoires !",
    "⚡ BRUTALITÉ CHRONOMÉTRIQUE ! Tu n'as pas battu le record, tu l'as ANÉANTI ! Army est attentif ...",
    "🚀 PULVÉRISATION COSMIQUE ! L'ancien record pleure dans un coin pendant que ton temps se pavane sur le podium !",
    "🏆 EXÉCUTION SANS PITIÉ ! Ce n'est plus un record, c'est une insulte aux lois de la physique de Mario Kart !",
    "💯 CARNAGE TEMPOREL ! Le chronomètre vient de démissionner après avoir vu ce temps SCANDALEUX !",
    "⭐ DESTRUCTION MASSIVE ! L'ancien record a été tellement battu qu'il devrait être considéré comme un temps de débutant !",
    "🎯 ASSASSINAT DU CHRONO ! Tu viens de commettre un meurtre en direct sur le tableau des scores !",
    "🔄 RÉVOLUTION BRUTALE ! Les lois du temps viennent d'être réécrites avec une violence inouïe !",
    "💪 DÉMOLITION CHRONOMÉTRIQUE ! Ce n'est plus une course, c'est une exécution publique de l'ancien record !",
    "⚡ POW POW POW ! Tu viens de tous les écraser comme un Thwomp en colère !",
    "🏆 TRIPLE CHAMPIGNON DE VITESSE ! Tu as laissé les autres manger ta poussière d'étoile !",
    "💯 BAM ! Plus destructeur qu'une Bill Balle ! Les autres concurrents viennent d'être relégués au rang d'amateur !",
    "🔄 CHANGEMENT DE PROGRAMME ! Les autres peuvent maintenant apprendre à aimer la vue depuis la dernière place !",
    "👑 DOMINATION ABSOLUE ! Tu les as tous envoyés dans le ravin comme un vulgaire Goomba ! Qu'ils aillent réviser leurs trajectoires !"
]