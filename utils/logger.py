"""
Système de journalisation pour le bot Mario Kart 8 Time Attack.
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

from config import LOG_LEVEL, LOG_FILE

# Créer le répertoire des logs s'il n'existe pas
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configuration du logger
logger = logging.getLogger('mk8_bot')
logger.setLevel(getattr(logging, LOG_LEVEL))

# Format du message de log
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Handler pour la console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Handler pour le fichier de log avec rotation (5 fichiers de 5 Mo max)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_command(guild_id: int, user_id: int, command_name: str, status: str = "SUCCESS") -> None:
    """
    Enregistre l'exécution d'une commande dans les logs.
    
    Args:
        guild_id: ID du serveur Discord
        user_id: ID de l'utilisateur
        command_name: Nom de la commande
        status: Statut de l'exécution (SUCCESS ou ERROR)
    """
    logger.info(f"Command: {command_name} | Server: {guild_id} | User: {user_id} | Status: {status}")

def log_tournament_creation(guild_id: int, tournament_id: int, course_name: str) -> None:
    """
    Enregistre la création d'un tournoi dans les logs.
    
    Args:
        guild_id: ID du serveur Discord
        tournament_id: ID du tournoi
        course_name: Nom de la course
    """
    logger.info(f"Tournament created: {tournament_id} | Server: {guild_id} | Course: {course_name}")

def log_tournament_end(guild_id: int, tournament_id: int, participants_count: int) -> None:
    """
    Enregistre la fin d'un tournoi dans les logs.
    
    Args:
        guild_id: ID du serveur Discord
        tournament_id: ID du tournoi
        participants_count: Nombre de participants
    """
    logger.info(f"Tournament ended: {tournament_id} | Server: {guild_id} | Participants: {participants_count}")

def log_score_submission(guild_id: int, user_id: int, tournament_id: int, time_ms: int) -> None:
    """
    Enregistre la soumission d'un score dans les logs.
    
    Args:
        guild_id: ID du serveur Discord
        user_id: ID de l'utilisateur
        tournament_id: ID du tournoi
        time_ms: Temps en millisecondes
    """
    logger.info(f"Score submitted: {time_ms}ms | Server: {guild_id} | User: {user_id} | Tournament: {tournament_id}")

def log_error(error_message: str, details: str = "") -> None:
    """
    Enregistre une erreur dans les logs.
    
    Args:
        error_message: Message d'erreur
        details: Détails supplémentaires
    """
    logger.error(f"{error_message} | Details: {details}")