"""
Gestionnaire des opérations de base de données pour le bot Mario Kart 8 Time Attack.
"""
import aiosqlite
import random
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union

from config import DATABASE_PATH, DEFAULT_TOURNAMENT_DURATION

class DatabaseManager:
    """
    Gestionnaire des opérations de base de données pour le bot Mario Kart 8 Time Attack.
    """
    
    # Variable de classe pour stocker une seule connexion
    _connection = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_connection(cls):
        """Retourne une connexion à la base de données."""
        async with cls._lock:
            if cls._connection is None:
                cls._connection = await aiosqlite.connect(DATABASE_PATH)
                cls._connection.row_factory = aiosqlite.Row
            return cls._connection
    
    @classmethod
    async def close_connection(cls):
        """Ferme la connexion à la base de données si elle existe."""
        if cls._connection is not None:
            await cls._connection.close()
            cls._connection = None
    
    @classmethod
    async def register_server(cls, server_id: int, server_name: str) -> None:
        """
        Enregistre un serveur dans la base de données s'il n'existe pas déjà.
        
        Args:
            server_id: ID du serveur Discord
            server_name: Nom du serveur Discord
        """
        conn = await cls.get_connection()
        
        # Vérifier si le serveur existe déjà
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM server WHERE server_id = ?", 
            (server_id,)
        )
        result = await cursor.fetchone()
        
        if result and result[0] == 0:
            # Le serveur n'existe pas, l'ajouter
            await conn.execute(
                "INSERT INTO server (server_id, name) VALUES (?, ?)",
                (server_id, server_name)
            )
            await conn.commit()
    
    @classmethod
    async def update_server_prefix(cls, server_id: int, prefix: str) -> bool:
        """
        Met à jour le préfixe de commande pour un serveur.
        
        Args:
            server_id: ID du serveur Discord
            prefix: Nouveau préfixe de commande
            
        Returns:
            True si la mise à jour est réussie, False sinon
        """
        conn = await cls.get_connection()
        try:
            await conn.execute(
                "UPDATE server SET prefix = ? WHERE server_id = ?",
                (prefix, server_id)
            )
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False
    
    @classmethod
    async def get_server_prefix(cls, server_id: int) -> str:
        """
        Récupère le préfixe de commande d'un serveur.
        
        Args:
            server_id: ID du serveur Discord
            
        Returns:
            Préfixe de commande du serveur ou le préfixe par défaut '!mk'
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            "SELECT prefix FROM server WHERE server_id = ?",
            (server_id,)
        )
        result = await cursor.fetchone()
        
        return result[0] if result else '!mk'
    
    @classmethod
    async def update_admin_role(cls, server_id: int, role_id: int) -> bool:
        """
        Met à jour le rôle administrateur pour un serveur.
        
        Args:
            server_id: ID du serveur Discord
            role_id: ID du rôle administrateur
            
        Returns:
            True si la mise à jour est réussie, False sinon
        """
        conn = await cls.get_connection()
        try:
            await conn.execute(
                "UPDATE server SET admin_role_id = ? WHERE server_id = ?",
                (role_id, server_id)
            )
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False
    
    @classmethod
    async def get_admin_role(cls, server_id: int) -> Optional[int]:
        """
        Récupère l'ID du rôle administrateur d'un serveur.
        
        Args:
            server_id: ID du serveur Discord
            
        Returns:
            ID du rôle administrateur ou None si non défini
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            "SELECT admin_role_id FROM server WHERE server_id = ?",
            (server_id,)
        )
        result = await cursor.fetchone()
        
        return result[0] if result else None
    
    @classmethod
    async def get_random_course(cls) -> Dict[str, Any]:
        """
        Sélectionne une course aléatoire parmi toutes les courses disponibles.
        
        Returns:
            Dictionnaire contenant les informations de la course
        """
        conn = await cls.get_connection()
        cursor = await conn.execute("SELECT course_id, name, cup, origin, image_url FROM course ORDER BY RANDOM() LIMIT 1")
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "cup": row[2],
                "origin": row[3],
                "image_url": row[4]
            }
        return None
    
    @classmethod
    async def get_course_by_id(cls, course_id: int) -> Dict[str, Any]:
        """
        Récupère les informations d'une course par son ID.
        
        Args:
            course_id: ID de la course
            
        Returns:
            Dictionnaire contenant les informations de la course ou None si non trouvée
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            "SELECT course_id, name, cup, origin, image_url FROM course WHERE course_id = ?",
            (course_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "cup": row[2],
                "origin": row[3],
                "image_url": row[4]
            }
        return None
    
    @classmethod
    async def create_tournament(
        cls, 
        server_id: int, 
        course_id: int, 
        vehicle_class: str, 
        duration: int = DEFAULT_TOURNAMENT_DURATION
    ) -> Optional[int]:
        """
        Crée un nouveau tournoi dans la base de données.
        
        Args:
            server_id: ID du serveur Discord
            course_id: ID de la course sélectionnée
            vehicle_class: Classe de véhicule (150cc, 200cc, Miroir)
            duration: Durée du tournoi en jours
            
        Returns:
            ID du tournoi créé ou None en cas d'erreur
        """
        conn = await cls.get_connection()
        
        # Vérifier s'il existe déjà un tournoi actif pour ce serveur
        cursor = await conn.execute(
            "SELECT tournament_id FROM tournament WHERE server_id = ? AND is_active = 1",
            (server_id,)
        )
        result = await cursor.fetchone()
        
        if result:
            # Il y a déjà un tournoi actif
            return None
        
        # Créer un nouveau tournoi
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration)
        
        cursor = await conn.execute(
            """
            INSERT INTO tournament 
            (server_id, course_id, vehicle_class, start_date, end_date, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (server_id, course_id, vehicle_class, start_date, end_date)
        )
        await conn.commit()
        
        return cursor.lastrowid
    
    @classmethod
    async def update_tournament_message(cls, tournament_id: int, message_id: str) -> bool:
        """
        Met à jour l'ID du message associé à un tournoi.
        
        Args:
            tournament_id: ID du tournoi
            message_id: ID du message Discord
            
        Returns:
            True si la mise à jour est réussie, False sinon
        """
        conn = await cls.get_connection()
        try:
            await conn.execute(
                "UPDATE tournament SET message_id = ? WHERE tournament_id = ?",
                (message_id, tournament_id)
            )
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False
    
    @classmethod
    async def get_active_tournament(cls, server_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère le tournoi actif pour un serveur.
        
        Args:
            server_id: ID du serveur Discord
            
        Returns:
            Dictionnaire contenant les informations du tournoi actif ou None si aucun
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            """
            SELECT t.tournament_id, t.course_id, t.vehicle_class, t.start_date, t.end_date, t.message_id, t.thread_id, c.name, c.cup, c.origin, c.image_url
            FROM tournament t
            JOIN course c ON t.course_id = c.course_id
            WHERE t.server_id = ? AND t.is_active = 1
            """,
            (server_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "course_id": row[1],
                "vehicle_class": row[2],
                "start_date": datetime.fromisoformat(row[3]),
                "end_date": datetime.fromisoformat(row[4]),
                "message_id": row[5],
                "thread_id": row[6],
                "course_name": row[7],
                "cup_name": row[8],
                "course_origin": row[9],
                "course_image": row[10]
            }
        return None
    
    @classmethod
    async def cancel_tournament(cls, tournament_id: int) -> bool:
        """
        Annule un tournoi actif.
        
        Args:
            tournament_id: ID du tournoi
            
        Returns:
            True si l'annulation est réussie, False sinon
        """
        conn = await cls.get_connection()
        try:
            await conn.execute(
                "UPDATE tournament SET is_active = 0 WHERE tournament_id = ?",
                (tournament_id,)
            )
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False
    
    @classmethod
    async def register_user(cls, discord_id: str, username: str) -> int:
        """
        Enregistre un utilisateur dans la base de données s'il n'existe pas déjà.
        
        Args:
            discord_id: ID Discord de l'utilisateur
            username: Nom d'utilisateur Discord
            
        Returns:
            ID de l'utilisateur dans la base de données
        """
        conn = await cls.get_connection()
        
        # Vérifier si l'utilisateur existe déjà
        cursor = await conn.execute(
            "SELECT user_id FROM user WHERE discord_id = ?",
            (discord_id,)
        )
        result = await cursor.fetchone()
        
        if result:
            # Mettre à jour le nom d'utilisateur au cas où il aurait changé
            await conn.execute(
                "UPDATE user SET username = ? WHERE discord_id = ?",
                (username, discord_id)
            )
            await conn.commit()
            return result[0]
        
        # Créer un nouvel utilisateur
        cursor = await conn.execute(
            "INSERT INTO user (discord_id, username) VALUES (?, ?)",
            (discord_id, username)
        )
        await conn.commit()
        
        return cursor.lastrowid
    
    @classmethod
    async def register_participation(cls, tournament_id: int, user_id: int) -> Optional[int]:
        """
        Enregistre la participation d'un utilisateur à un tournoi.
        
        Args:
            tournament_id: ID du tournoi
            user_id: ID de l'utilisateur
            
        Returns:
            ID de la participation ou None si l'utilisateur participe déjà
        """
        conn = await cls.get_connection()
        
        # Vérifier si l'utilisateur participe déjà
        cursor = await conn.execute(
            "SELECT participation_id FROM participation WHERE tournament_id = ? AND user_id = ?",
            (tournament_id, user_id)
        )
        result = await cursor.fetchone()
        
        if result:
            # L'utilisateur participe déjà
            return result[0]
        
        # Enregistrer la participation
        join_date = datetime.now()
        cursor = await conn.execute(
            "INSERT INTO participation (tournament_id, user_id, join_date) VALUES (?, ?, ?)",
            (tournament_id, user_id, join_date)
        )
        await conn.commit()
        
        return cursor.lastrowid
    
    @classmethod
    async def submit_score(cls, participation_id: int, time_ms: int, screenshot_url: Optional[str] = None) -> int:
        """
        Enregistre un score pour un participant.
        
        Args:
            participation_id: ID de la participation
            time_ms: Temps en millisecondes
            screenshot_url: URL de la capture d'écran (optionnelle)
            
        Returns:
            ID du score enregistré
        """
        conn = await cls.get_connection()
        submitted_at = datetime.now()
        cursor = await conn.execute(
            """
            INSERT INTO score (participation_id, time_ms, screenshot_url, submitted_at)
            VALUES (?, ?, ?, ?)
            """,
            (participation_id, time_ms, screenshot_url, submitted_at)
        )
        await conn.commit()
        
        return cursor.lastrowid
    
    @classmethod
    async def get_best_scores(cls, tournament_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Récupère les meilleurs scores d'un tournoi.
        
        Args:
            tournament_id: ID du tournoi
            limit: Nombre maximum de scores à récupérer
            
        Returns:
            Liste des meilleurs scores
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            """
            SELECT u.username, u.discord_id, s.time_ms, s.screenshot_url, s.status_id, ss.name as status_name
            FROM score s
            JOIN participation p ON s.participation_id = p.participation_id
            JOIN user u ON p.user_id = u.user_id
            JOIN score_status ss ON s.status_id = ss.status_id
            WHERE p.tournament_id = ?
            AND (
                -- Priorité aux scores vérifiés (si disponible pour l'utilisateur)
                s.status_id = 2 
                OR 
                -- Sinon, on prend le meilleur score en attente
                (s.status_id = 1 AND NOT EXISTS (
                    SELECT 1 FROM score s2 
                    JOIN participation p2 ON s2.participation_id = p2.participation_id 
                    WHERE p2.user_id = p.user_id AND p2.tournament_id = p.tournament_id AND s2.status_id = 2
                ))
            )
            ORDER BY s.time_ms ASC
            LIMIT ?
            """,
            (tournament_id, limit)
        )
        rows = await cursor.fetchall()
        
        scores = []
        for row in rows:
            scores.append({
                "username": row[0],
                "discord_id": row[1],
                "time_ms": row[2],
                "screenshot_url": row[3],
                "status_id": row[4],
                "status": row[5],
                "verified": row[4] == 2  # Pour compatibilité avec le code existant (2 = verified)
            })
        
        return scores
    
    @classmethod
    async def get_participation_id(cls, tournament_id: int, user_id: int) -> Optional[int]:
        """
        Récupère l'ID de participation d'un utilisateur à un tournoi.
        
        Args:
            tournament_id: ID du tournoi
            user_id: ID de l'utilisateur
            
        Returns:
            ID de la participation ou None si l'utilisateur ne participe pas
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            "SELECT participation_id FROM participation WHERE tournament_id = ? AND user_id = ?",
            (tournament_id, user_id)
        )
        result = await cursor.fetchone()
        
        return result[0] if result else None
    
    @classmethod
    async def get_user_scores(cls, participation_id: int) -> List[Dict[str, Any]]:
        """
        Récupère tous les scores d'un participant.
        
        Args:
            participation_id: ID de la participation
            
        Returns:
            Liste des scores soumis par le participant
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            """
            SELECT s.score_id, s.time_ms, s.screenshot_url, s.submitted_at, s.status_id, ss.name as status_name
            FROM score s
            JOIN score_status ss ON s.status_id = ss.status_id
            WHERE s.participation_id = ?
            ORDER BY s.time_ms ASC
            """,
            (participation_id,)
        )
        rows = await cursor.fetchall()
        
        scores = []
        for row in rows:
            scores.append({
                "id": row[0],
                "time_ms": row[1],
                "screenshot_url": row[2],
                "submitted_at": datetime.fromisoformat(row[3]),
                "status_id": row[4],
                "status": row[5],
                "verified": row[4] == 2  # Pour compatibilité (status_id=2 correspond à "verified")
            })
        
        return scores
    
    @classmethod
    async def verify_score(cls, score_id: int) -> bool:
        """
        Marque un score comme vérifié sans modifier les autres scores.
        
        Args:
            score_id: ID du score
            
        Returns:
            True si la mise à jour est réussie, False sinon
        """
        conn = await cls.get_connection()
        try:
            # Marquer ce score comme vérifié (status_id=2)
            await conn.execute(
                "UPDATE score SET status_id = 2 WHERE score_id = ?",
                (score_id,)
            )
            
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False
    
    @classmethod
    async def delete_score(cls, score_id: int) -> bool:
        """
        Supprime un score.
        
        Args:
            score_id: ID du score
            
        Returns:
            True si la suppression est réussie, False sinon
        """
        conn = await cls.get_connection()
        try:
            await conn.execute(
                "DELETE FROM score WHERE score_id = ?",
                (score_id,)
            )
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False
    
    @classmethod
    async def get_tournament_participants_count(cls, tournament_id: int) -> int:
        """
        Récupère le nombre de participants à un tournoi.
        
        Args:
            tournament_id: ID du tournoi
            
        Returns:
            Nombre de participants
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM participation WHERE tournament_id = ?",
            (tournament_id,)
        )
        result = await cursor.fetchone()
        
        return result[0] if result else 0
    
    @classmethod
    async def get_course_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une course par son nom (recherche partielle insensible à la casse).
        
        Args:
            name: Nom complet ou partiel de la course
            
        Returns:
            Dictionnaire contenant les informations de la course ou None si non trouvée
        """
        
        conn = await cls.get_connection()
        
        # LIKE pour une recherche partielle et LOWER pour ignorer la casse
        cursor = await conn.execute(
            "SELECT course_id, name, cup, origin, image_url FROM course WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{name}%",)
        )
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "cup": row[2],
                "origin": row[3],
                "image_url": row[4]
            }
        return None
    
    @classmethod
    async def search_courses(cls, search_term: str) -> List[Dict[str, Any]]:
        """
        Recherche des courses par nom.
        
        Args:
            search_term: Terme de recherche
            
        Returns:
            Liste des courses correspondantes
        """
        
        conn    = await cls.get_connection()
        cursor  = await conn.execute(
            "SELECT course_id, name FROM course WHERE LOWER(name) LIKE LOWER(?) ORDER BY name LIMIT 10",
            (f"%{search_term}%",)
        )
        rows = await cursor.fetchall()
        
        return [{"id": row[0], "name": row[1]} for row in rows]
    
    @classmethod
    async def update_tournament_thread(cls, tournament_id: int, thread_id: str) -> bool:
        """
        Met à jour l'ID du thread associé à un tournoi.
        
        Args:
            tournament_id: ID du tournoi
            thread_id: ID du thread Discord
            
        Returns:
            True si la mise à jour est réussie, False sinon
        """
        conn = await cls.get_connection()
        try:
            await conn.execute(
                "UPDATE tournament SET thread_id = ? WHERE tournament_id = ?",
                (thread_id, tournament_id)
            )
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False

    @classmethod
    async def get_tournament_thread(cls, tournament_id: int) -> Optional[str]:
        """
        Récupère l'ID du thread associé à un tournoi.
        
        Args:
            tournament_id: ID du tournoi
            
        Returns:
            ID du thread ou None si non défini
        """
        conn = await cls.get_connection()
        cursor = await conn.execute(
            "SELECT thread_id FROM tournament WHERE tournament_id = ?",
            (tournament_id,)
        )
        result = await cursor.fetchone()
        
        return result[0] if result and result[0] else None

    @classmethod
    async def update_score_status(cls, score_id: int, status_id: int) -> bool:
        """
        Met à jour le statut d'un score.
        
        Args:
            score_id: ID du score
            status_id: Nouvel ID de statut
            
        Returns:
            True si la mise à jour est réussie, False sinon
        """
        conn = await cls.get_connection()
        try:
            await conn.execute(
                "UPDATE score SET status_id = ? WHERE score_id = ?",
                (status_id, score_id)
            )
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False

    @classmethod
    async def archive_other_scores(cls, score_id: int) -> bool:
        """
        Marque tous les autres scores de la même participation comme archivés.
        """
        conn = await cls.get_connection()
        try:
            # Récupérer la participation_id du score
            cursor = await conn.execute(
                "SELECT participation_id FROM score WHERE score_id = ?",
                (score_id,)
            )
            result = await cursor.fetchone()
            if not result:
                return False
                
            participation_id = result[0]
            
            # Marquer tous les autres scores de la même participation comme archivés
            await conn.execute(
                "UPDATE score SET status_id = 3 WHERE participation_id = ? AND score_id != ?",
                (participation_id, score_id)
            )
            
            await conn.commit()
            return True
        except aiosqlite.Error:
            return False