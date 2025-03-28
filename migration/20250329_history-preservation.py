import asyncio
import aiosqlite
from config import DATABASE_PATH

async def migrate_score_status():
    print("Début de la migration de la base de données...")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # 1. Créer la table score_status
        print("Création de la table score_status...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS score_status (
                status_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT
            )
        """)
        
        # 2. Insérer les valeurs de référence
        print("Insertion des statuts...")
        status_values = [
            (1, 'pending', 'Score en attente de vérification'),
            (2, 'verified', 'Score vérifié et retenu comme meilleur score'),
            (3, 'archived', 'Score vérifié mais non retenu (historique)'),
            (4, 'rejected', 'Score rejeté par un admin')
        ]
        
        for status in status_values:
            await db.execute(
                "INSERT OR IGNORE INTO score_status (status_id, name, description) VALUES (?, ?, ?)",
                status
            )
        
        # 3. Vérifier si la table score contient la colonne is_verified
        cursor = await db.execute("PRAGMA table_info(score)")
        columns = await cursor.fetchall()
        is_verified_exists = any(column[1] == 'is_verified' for column in columns)
        
        if is_verified_exists:
            print("Migration de la structure de la table score...")
            # 4. Créer une table temporaire
            await db.execute("""
                CREATE TABLE score_temp (
                    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participation_id INTEGER NOT NULL,
                    time_ms INTEGER NOT NULL,
                    screenshot_url TEXT,
                    submitted_at TIMESTAMP NOT NULL,
                    status_id INTEGER DEFAULT 1,
                    FOREIGN KEY (participation_id) REFERENCES participation (participation_id) ON DELETE CASCADE,
                    FOREIGN KEY (status_id) REFERENCES score_status (status_id)
                )
            """)
            
            # 5. Migrer les données
            print("Migration des données...")
            await db.execute("""
                INSERT INTO score_temp (score_id, participation_id, time_ms, screenshot_url, submitted_at, status_id)
                SELECT score_id, participation_id, time_ms, screenshot_url, submitted_at,
                    CASE WHEN is_verified = 1 THEN 2 ELSE 1 END as status_id
                FROM score
            """)
            
            # 6. Remplacer l'ancienne table
            print("Remplacement de la table score...")
            await db.execute("DROP TABLE score")
            await db.execute("ALTER TABLE score_temp RENAME TO score")
            
            print("Migration terminée avec succès!")
        else:
            print("La colonne is_verified n'existe pas, migration non nécessaire.")
        
        await db.commit()

if __name__ == "__main__":
    asyncio.run(migrate_score_status())