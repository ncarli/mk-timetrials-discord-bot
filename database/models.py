"""
Définition du schéma de la base de données pour le bot Mario Kart 8 Time Attack.
"""
import os
import json
import aiosqlite
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from config import DATABASE_PATH, COURSES_FILE, DEFAULT_TOURNAMENT_DURATION

# Assurez-vous que le répertoire de la base de données existe
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# SQL pour la création des tables
CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS server (
        server_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        prefix TEXT DEFAULT '!mk',
        admin_role_id INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS course (
        course_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        cup TEXT NOT NULL,
        origin TEXT NOT NULL,
        image_url TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id TEXT UNIQUE NOT NULL,
        username TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tournament (
        tournament_id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        vehicle_class TEXT NOT NULL,
        start_date TIMESTAMP NOT NULL,
        end_date TIMESTAMP NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        message_id TEXT,
        FOREIGN KEY (server_id) REFERENCES server (server_id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES course (course_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS participation (
        participation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        join_date TIMESTAMP NOT NULL,
        FOREIGN KEY (tournament_id) REFERENCES tournament (tournament_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES user (user_id),
        UNIQUE (tournament_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS score (
        score_id INTEGER PRIMARY KEY AUTOINCREMENT,
        participation_id INTEGER NOT NULL,
        time_ms INTEGER NOT NULL,
        screenshot_url TEXT,
        submitted_at TIMESTAMP NOT NULL,
        is_verified BOOLEAN DEFAULT 0,
        FOREIGN KEY (participation_id) REFERENCES participation (participation_id) ON DELETE CASCADE
    )
    """
]

async def initialize_database() -> None:
    """
    Initialise la base de données et importe les données des courses.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Création des tables
        for table_sql in CREATE_TABLES:
            await db.execute(table_sql)
        
        # Vérifier si les courses sont déjà importées
        cursor = await db.execute("SELECT COUNT(*) FROM course")
        count = await cursor.fetchone()
        
        # Importer les courses si nécessaire
        if count[0] == 0:
            # Charger les données des courses depuis le fichier JSON
            try:
                with open(COURSES_FILE, 'r', encoding='utf-8') as f:
                    courses_data = json.load(f)
                
                # Insertion des courses dans la base de données
                for course in courses_data['courses']:
                    await db.execute(
                        "INSERT INTO course (course_id, name, cup, origin, image_url) VALUES (?, ?, ?, ?, ?)",
                        (course['id'], course['name'], course['cup'], course['origin'], course['image_url'])
                    )
                
                await db.commit()
                print(f"Importation réussie de {len(courses_data['courses'])} courses.")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Erreur lors de l'importation des courses: {e}")
                # Créer un fichier vide pour éviter de futures erreurs
                if not os.path.exists(COURSES_FILE):
                    os.makedirs(os.path.dirname(COURSES_FILE), exist_ok=True)
                    with open(COURSES_FILE, 'w', encoding='utf-8') as f:
                        json.dump({"courses": []}, f)
        
        await db.commit()
        print("Initialisation de la base de données terminée.")


def parse_time(time_str: str) -> int:
    """
    Convertit une chaîne de temps au format mm:ss:ms en millisecondes.
    
    Args:
        time_str: Chaîne au format "1:23:456" (minutes:secondes:millisecondes)
    
    Returns:
        Temps total en millisecondes
    
    Raises:
        ValueError: Si le format est invalide
    """
    parts = time_str.split(':')
    if len(parts) != 3:
        raise ValueError("Format de temps invalide. Utilisez mm:ss:ms (ex: 1:23:456)")
    
    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
        milliseconds = int(parts[2])
        
        if seconds >= 60 or milliseconds >= 1000:
            raise ValueError("Format de temps invalide: secondes < 60, millisecondes < 1000")
        
        total_ms = (minutes * 60 * 1000) + (seconds * 1000) + milliseconds
        return total_ms
    except ValueError:
        raise ValueError("Format de temps invalide. Utilisez mm:ss:ms (ex: 1:23:456)")


def format_time(time_ms: int) -> str:
    """
    Convertit un temps en millisecondes en chaîne formatée mm:ss:ms.
    
    Args:
        time_ms: Temps en millisecondes
    
    Returns:
        Chaîne formatée "1:23:456"
    """
    minutes = time_ms // (60 * 1000)
    seconds = (time_ms % (60 * 1000)) // 1000
    milliseconds = time_ms % 1000
    
    return f"{minutes}:{seconds:02d}:{milliseconds:03d}"