"""
Cog pour la gestion des tournois Mario Kart 8 Time Attack.
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks

import random
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from database.manager import DatabaseManager
from database.models import initialize_database, format_time
from utils.embeds import EmbedBuilder, format_date
from utils.validators import validate_vehicle_class, validate_duration
from utils.logger import logger, log_command, log_tournament_creation, log_tournament_end, log_error
from config import VEHICLE_CLASSES, DEFAULT_TOURNAMENT_DURATION, REMINDER_DAYS_BEFORE_END

class TournamentCog(commands.Cog):
    """
    Gestion des tournois Mario Kart 8 Time Attack.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # C'est la bonne façon de démarrer des tâches dans les versions récentes de discord.py
        # Bot.add_listener exécutera la méthode une fois que l'événement on_ready sera déclenché
        bot.add_listener(self.start_tasks, 'on_ready')  

    async def start_tasks(self):
        """Initialise la base de données et démarre les tâches périodiques."""
        await self.bot.wait_until_ready()   
        await initialize_database()
        
        # Démarrer les tâches périodiques si elles ne sont pas déjà en cours
        if not self.check_ended_tournaments.is_running():
            self.check_ended_tournaments.start()
            logger.info("Tâche de vérification des tournois terminés démarrée")

    @tasks.loop(hours=1)
    async def check_ended_tournaments(self):
        """
        Vérifie et traite les tournois qui sont terminés.
        Cette tâche s'exécute toutes les heures.
        """
        logger.info("Vérification des tournois terminés en cours...")
        
        try:
            # Récupérer les tournois terminés mais encore actifs
            ended_tournaments = await self._get_ended_tournaments()
            
            for tournament in ended_tournaments:
                logger.info(f"Traitement du tournoi terminé {tournament['id']} sur {tournament['guild_id']}")
                
                # Récupérer les meilleurs scores
                scores = await DatabaseManager.get_best_scores(tournament['id'])
                
                # Récupérer le serveur Discord
                guild = self.bot.get_guild(tournament['guild_id'])
                if not guild:
                    logger.warning(f"Impossible de trouver le serveur {tournament['guild_id']} pour le tournoi {tournament['id']}")
                    continue
                
                # Récupérer les participants pour les mentionner
                participants = await self._get_tournament_participants(tournament['id'])
                
                # Création de l'embed pour l'annonce de fin
                end_embed = EmbedBuilder.tournament_ended(tournament, scores)
                
                # Chercher le canal où se trouve le message d'origine
                original_channel = None
                original_message = None
                
                if tournament['message_id']:
                    for channel in guild.text_channels:
                        try:
                            original_message = await channel.fetch_message(int(tournament['message_id']))
                            original_channel = channel
                            break
                        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                            continue
                
                # Envoyer l'annonce de fin dans le canal d'origine si disponible
                if original_channel and original_message:
                    try:
                        await original_channel.send(embed=end_embed)
                        await original_message.unpin()
                    except discord.HTTPException as e:
                        logger.error(f"Erreur lors de l'envoi du message de fin pour le tournoi {tournament['id']} : {str(e)}")
                
                # Gérer le thread si disponible
                if tournament['thread_id']:
                    try:
                        thread = guild.get_thread(int(tournament['thread_id']))
                        if thread:
                            # Envoyer un message de fin dans le thread avec mention de tous les participants
                            end_thread_embed = discord.Embed(
                                title="🏁 Tournoi terminé !",
                                description=f"Le tournoi sur **{tournament['course_name']}** est maintenant terminé.",
                                color=0xF1C40F  # Jaune/Or
                            )
                            
                            # Ajouter les résultats
                            if scores:
                                winners_text = ""
                                for i, score in enumerate(scores[:3]):
                                    if i == 0:
                                        winners_text += f"🥇 **{score['username']}**: {format_time(score['time_ms'])}\n"
                                    elif i == 1:
                                        winners_text += f"🥈 **{score['username']}**: {format_time(score['time_ms'])}\n"
                                    elif i == 2:
                                        winners_text += f"🥉 **{score['username']}**: {format_time(score['time_ms'])}\n"
                                
                                end_thread_embed.add_field(
                                    name="Podium",
                                    value=winners_text if winners_text else "Pas assez de participants pour un podium complet.",
                                    inline=False
                                )
                            else:
                                end_thread_embed.add_field(
                                    name="Résultats",
                                    value="Aucun temps n'a été soumis pour ce tournoi.",
                                    inline=False
                                )
                            
                            # Ajouter la durée du tournoi
                            end_thread_embed.add_field(
                                name="Durée du tournoi",
                                value=f"Du {format_date(tournament['start_date'])} au {format_date(tournament['end_date'])}",
                                inline=False
                            )
                            
                            end_thread_embed.set_thumbnail(url=tournament['course_image'])
                            
                            # Envoyer l'embed dans le thread
                            await thread.send(embed=end_thread_embed)
                            
                            # Notification aux participants
                            if participants:
                                participants_mentions = [f"<@{participant_id}>" for participant_id in participants]
                                notification_message = "Le tournoi est terminé ! Merci à tous les participants."
                                
                                # Si nous avons un podium, féliciter les gagnants
                                if scores and len(scores) >= 1:
                                    notification_message += f"\n\nFélicitations à <@{scores[0]['discord_id']}> pour sa victoire avec un temps de {format_time(scores[0]['time_ms'])} ! 🏆"
                                
                                # Envoyer la notification et les mentions
                                await thread.send(notification_message)
                                if len(participants) > 0:
                                    participants_text = " ".join(participants_mentions)
                                    await thread.send(f"Information pour : {participants_text}")
                            
                            # Archiver le thread
                            await thread.edit(archived=True, locked=False)  # Archivé mais pas verrouillé
                            logger.info(f"Thread {thread.id} pour le tournoi {tournament['id']} archivé suite à la fin du tournoi")
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la gestion du thread pour le tournoi terminé {tournament['id']} : {str(e)}")
                
                # Marquer le tournoi comme inactif dans la base de données
                await DatabaseManager.cancel_tournament(tournament['id'])
                log_tournament_end(tournament['guild_id'], tournament['id'], len(participants))
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des tournois terminés : {str(e)}")

    @check_ended_tournaments.before_loop
    async def before_check_ended_tournaments(self):
        """S'assure que le bot est prêt avant de commencer la tâche."""
        await self.bot.wait_until_ready()

    async def _get_ended_tournaments(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des tournois qui sont terminés mais encore marqués comme actifs.
        
        Returns:
            Liste des tournois terminés
        """
        conn    = await DatabaseManager.get_connection()
        now     = datetime.now()
        
        cursor  = await conn.execute(
            """
            SELECT t.tournament_id, t.server_id, t.course_id, t.vehicle_class, t.start_date, t.end_date, t.message_id, t.thread_id, c.name, c.cup, c.origin, c.image_url
            FROM tournament t
            JOIN course c ON t.course_id = c.course_id
            WHERE t.is_active = 1 AND t.end_date < ?
            """,
            (now.isoformat(),)
        )
        rows = await cursor.fetchall()
        
        tournaments = []
        for row in rows:
            tournaments.append({
                "id": row[0],
                "guild_id": row[1],
                "course_id": row[2],
                "vehicle_class": row[3],
                "start_date": datetime.fromisoformat(row[4]),
                "end_date": datetime.fromisoformat(row[5]),
                "message_id": row[6],
                "thread_id": row[7],
                "course_name": row[8],
                "cup_name": row[9],
                "course_origin": row[10],
                "course_image": row[11]
            })
        
        return tournaments

    async def update_leaderboard(self, guild_id: int, tournament_id: int):
        """
        Met à jour le message de classement du tournoi dans le canal principal et dans le thread.
        
        Args:
            guild_id: ID du serveur Discord
            tournament_id: ID du tournoi
        """
        try:
            # Récupérer les informations du tournoi
            tournament = await DatabaseManager.get_active_tournament(guild_id)
            if not tournament or tournament['id'] != tournament_id:
                return
            
            # Récupérer les meilleurs scores
            scores = await DatabaseManager.get_best_scores(tournament_id)
            
            # Mettre à jour le message de classement
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            # Créer l'embed de classement
            leaderboard_embed = EmbedBuilder.tournament_leaderboard(tournament, scores)
            
            # 1. Mettre à jour le message original dans le canal principal
            updated_main_channel = False
            for channel in guild.text_channels:
                try:
                    if tournament['message_id']:
                        message = await channel.fetch_message(int(tournament['message_id']))
                        await message.edit(embed=leaderboard_embed)
                        updated_main_channel = True
                        break
                except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError) as e:
                    logger.error(f"Erreur lors de la mise à jour du classement dans le canal principal: {str(e)}")
                    continue
            
            # 2. Mettre à jour le thread si disponible
            if tournament['thread_id']:
                try:
                    thread = self.bot.get_channel(int(tournament['thread_id']))
                    if thread:
                        # Rechercher un message existant avec le classement dans le thread
                        # ou envoyer un nouveau message s'il n'y en a pas
                        async for message in thread.history(limit=50):
                            if message.author == self.bot.user and message.embeds:
                                for embed in message.embeds:
                                    if embed.title and "Classement:" in embed.title:
                                        try:
                                            await message.edit(embed=leaderboard_embed)
                                            return  # Classement mis à jour avec succès dans le thread
                                        except discord.HTTPException as e:
                                            logger.error(f"Erreur lors de la mise à jour du classement dans le thread: {str(e)}")
                        
                        # Si aucun message de classement n'a été trouvé, envoyer un nouveau
                        await thread.send(embed=leaderboard_embed)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError) as e:
                    logger.error(f"Erreur lors de la mise à jour du classement dans le thread: {str(e)}")
            
            # Si le classement n'a pas pu être mis à jour dans le canal principal ou le thread
            if not updated_main_channel and not tournament['thread_id']:
                logger.warning(f"Impossible de mettre à jour le classement pour le tournoi {tournament_id}")
        
        except Exception as e:
            log_error(f"Erreur lors de la mise à jour du classement: {str(e)}")
    
    @app_commands.command(
        name="tournoi",
        description="Crée un nouveau tournoi Time Attack"
    )
    @app_commands.describe(
        classe="Classe de véhicule (150cc, 200cc, Miroir)",
        duree="Durée du tournoi en jours (1-90)",
        course="Nom de la course (optionnel, aléatoire si non spécifié)"
    )
    @app_commands.choices(classe=[
        app_commands.Choice(name="150cc", value="150cc"),
        app_commands.Choice(name="200cc", value="200cc"),
        app_commands.Choice(name="Miroir", value="Miroir")
    ])
    async def create_tournament(
        self,
        interaction: discord.Interaction,
        classe: str = "150cc",
        duree: int = DEFAULT_TOURNAMENT_DURATION,
        course: Optional[str] = None
    ):
        """
        Crée un nouveau tournoi Time Attack avec une course aléatoire.
        
        Args:
            interaction: Interaction Discord
            classe: Classe de véhicule (150cc, 200cc, Miroir)
            duree: Durée du tournoi en jours (1-90)
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "tournoi")
        
        # Vérifier les permissions (administrateur ou rôle spécifique)
        if not interaction.user.guild_permissions.administrator:
            admin_role_id = await DatabaseManager.get_admin_role(interaction.guild_id)
            if admin_role_id:
                role = interaction.guild.get_role(admin_role_id)
                if not role or role not in interaction.user.roles:
                    await interaction.response.send_message(
                        embed=EmbedBuilder.error_message(
                            "Permission refusée",
                            "Vous devez être administrateur ou avoir le rôle approprié pour créer un tournoi."
                        ),
                        ephemeral=True
                    )
                    return
            else:
                await interaction.response.send_message(
                    embed=EmbedBuilder.error_message(
                        "Permission refusée",
                        "Vous devez être administrateur pour créer un tournoi."
                    ),
                    ephemeral=True
                )
                return
        
        # Vérification des paramètres
        valid_vehicle, vehicle_error = validate_vehicle_class(classe)
        if not valid_vehicle:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message("Paramètre invalide", vehicle_error),
                ephemeral=True
            )
            return
        
        valid_duration, duration_error = validate_duration(duree)
        if not valid_duration:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message("Paramètre invalide", duration_error),
                ephemeral=True
            )
            return
        
        # Vérifier s'il y a déjà un tournoi actif
        active_tournament = await DatabaseManager.get_active_tournament(interaction.guild_id)
        if active_tournament:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Tournoi déjà en cours",
                    f"Un tournoi est déjà actif sur **{active_tournament['course_name']}** jusqu'au {active_tournament['end_date'].strftime('%d/%m/%Y')}."
                ),
                ephemeral=True
            )
            return
        
        # Enregistrer le serveur s'il n'existe pas déjà
        await DatabaseManager.register_server(interaction.guild_id, interaction.guild.name)
        
        # Sélectionner une course (aléatoire ou spécifique)
        if course:
            course_data = await DatabaseManager.get_course_by_name(course)
            if not course_data:
                await interaction.response.send_message(
                    embed=EmbedBuilder.error_message(
                        "Course introuvable",
                        f"La course '{course}' n'a pas été trouvée. Vérifiez l'orthographe ou laissez vide pour une sélection aléatoire."
                    ),
                    ephemeral=True
                )
                return
        else:
            course_data = await DatabaseManager.get_random_course()
        
        # Créer le tournoi dans la base de données
        tournament_id = await DatabaseManager.create_tournament(
            interaction.guild_id,
            course_data['id'],
            classe,
            duree
        )
        
        if not tournament_id:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Erreur",
                    "Impossible de créer le tournoi. Veuillez réessayer."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer les informations complètes du tournoi
        tournament = await DatabaseManager.get_active_tournament(interaction.guild_id)
        
        # Créer l'embed d'annonce
        embed = EmbedBuilder.tournament_announcement(tournament)
        
        # Envoyer le message d'annonce
        await interaction.response.send_message(embed=embed)
        
        # Récupérer le message envoyé pour l'épingler et stocker son ID
        original_message = await interaction.original_response()
        
        # Épingler le message
        try:
            await original_message.pin()
        except discord.Forbidden:
            # Le bot n'a pas la permission d'épingler, continuer sans épingler
            pass
        
        # Créer un thread pour le tournoi
        try:
            # Création du thread à partir du message d'annonce
            thread_name = f"🏁 Tournoi {tournament['course_name']} ({tournament['vehicle_class']})"
            thread = await original_message.create_thread(
                name=thread_name,
                auto_archive_duration=10080  # 7 jours (maximum)
            )
            
            # Envoi d'un message d'accueil dans le thread
            welcome_embed = discord.Embed(
                title=f"Bienvenue dans le tournoi {tournament['course_name']} !",
                description=(
                    "Ce thread est dédié au tournoi en cours. Vous y trouverez toutes les informations "
                    "et mises à jour concernant ce tournoi.\n\n"
                    "Utilisez les commandes suivantes ici même :"
                ),
                color=0x3498DB  # Bleu
            )
            
            welcome_embed.add_field(
                name="Commandes principales",
                value=(
                    "`/participer` - S'inscrire au tournoi\n"
                    "`/score <temps> [preuve]` - Soumettre un temps\n"
                    "`/messcores` - Voir vos temps soumis\n"
                    "`/info` - Afficher le classement actuel"
                ),
                inline=False
            )
            
            welcome_embed.set_thumbnail(url=tournament['course_image'])
            
            await thread.send(embed=welcome_embed)
            
            # Enregistrer l'ID du thread dans la base de données
            await DatabaseManager.update_tournament_thread(tournament_id, str(thread.id))
            
            logger.info(f"Thread créé pour le tournoi {tournament_id} : {thread.id}")
        except discord.Forbidden:
            logger.error(f"Impossible de créer un thread pour le tournoi {tournament_id} : permission insuffisante")
        except Exception as e:
            logger.error(f"Erreur lors de la création du thread pour le tournoi {tournament_id} : {str(e)}")
        
        # Mettre à jour l'ID du message dans la base de données
        await DatabaseManager.update_tournament_message(tournament_id, str(original_message.id))
        
        # Logger la création du tournoi
        log_tournament_creation(interaction.guild_id, tournament_id, course_data['name'])
        
    @create_tournament.autocomplete('course')
    async def course_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        if not current:
            return []
        
        courses = await DatabaseManager.search_courses(current)
        return [
            app_commands.Choice(name=course['name'], value=course['name'])
            for course in courses[:10]
        ]
    
    @app_commands.command(
        name="participer",
        description="Participe au tournoi Time Attack en cours"
    )
    async def join_tournament(self, interaction: discord.Interaction):
        """
        Inscrit l'utilisateur au tournoi en cours.
        
        Args:
            interaction: Interaction Discord
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "participer")
        
        # Vérifier s'il y a un tournoi actif
        tournament = await DatabaseManager.get_active_tournament(interaction.guild_id)
        if not tournament:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun tournoi actif",
                    "Il n'y a pas de tournoi en cours sur ce serveur."
                ),
                ephemeral=True
            )
            return
        
        # Enregistrer l'utilisateur
        user_id = await DatabaseManager.register_user(str(interaction.user.id), interaction.user.display_name)
        
        # Vérifier si l'utilisateur participe déjà au tournoi
        participation_id        = await DatabaseManager.get_participation_id(tournament['id'], user_id)
        already_participating   = participation_id is not None
        
        if not already_participating:
            # Enregistrer la participation seulement s'il ne participe pas déjà
            participation_id = await DatabaseManager.register_participation(tournament['id'], user_id)
            
            # Confirmer l'inscription à l'utilisateur (message privé)
            embed = EmbedBuilder.participation_confirmation(tournament)
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
            
            # Déterminer si nous sommes déjà dans le thread du tournoi
            in_tournament_thread = (
                interaction.channel and 
                isinstance(interaction.channel, discord.Thread) and 
                str(interaction.channel.id) == tournament['thread_id']
            )
            
            # Annoncer le nouveau participant dans le thread ou le canal approprié
            if not in_tournament_thread:
                # Informer l'utilisateur que la confirmation a été envoyée dans le thread
                thread_link = f"<#{tournament['thread_id']}>" if tournament['thread_id'] else "le thread du tournoi"
                await interaction.followup.send(
                    f"Votre participation a été annoncée dans {thread_link}. Retrouvez-y toutes les informations sur le tournoi !",
                    ephemeral=True
                )
            
            # Annoncer le nouveau participant dans le thread ou le canal approprié
            await self.announce_new_participant(interaction, tournament)
        else:
            # Si l'utilisateur participe déjà, lui envoyer un message privé
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Déjà inscrit",
                    f"Vous participez déjà au tournoi sur **{tournament['course_name']}**."
                ),
                ephemeral=True
            )
            
            # Suggérer à l'utilisateur de rejoindre le thread s'il n'y est pas déjà
            if tournament['thread_id'] and not isinstance(interaction.channel, discord.Thread):
                await interaction.followup.send(
                    f"Pour suivre le tournoi, rejoignez le thread dédié : <#{tournament['thread_id']}>",
                    ephemeral=True
                )

    @app_commands.command(
        name="annuler",
        description="Annule le tournoi Time Attack en cours"
    )
    async def cancel_tournament(self, interaction: discord.Interaction):
        """
        Annule le tournoi en cours.
        
        Args:
            interaction: Interaction Discord
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "annuler")
        
        # Vérifier les permissions (administrateur ou rôle spécifique)
        if not interaction.user.guild_permissions.administrator:
            admin_role_id = await DatabaseManager.get_admin_role(interaction.guild_id)
            if admin_role_id:
                role = interaction.guild.get_role(admin_role_id)
                if not role or role not in interaction.user.roles:
                    await interaction.response.send_message(
                        embed=EmbedBuilder.error_message(
                            "Permission refusée",
                            "Vous devez être administrateur ou avoir le rôle approprié pour annuler un tournoi."
                        ),
                        ephemeral=True
                    )
                    return
            else:
                await interaction.response.send_message(
                    embed=EmbedBuilder.error_message(
                        "Permission refusée",
                        "Vous devez être administrateur pour annuler un tournoi."
                    ),
                    ephemeral=True
                )
                return
        
        # Vérifier s'il y a un tournoi actif
        tournament = await DatabaseManager.get_active_tournament(interaction.guild_id)
        if not tournament:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun tournoi actif",
                    "Il n'y a pas de tournoi en cours à annuler."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer les participants pour les mentionner
        participants = await self._get_tournament_participants(tournament['id'])
        
        # Créer un embed pour l'annulation
        cancel_embed = EmbedBuilder.confirmation_message(
            "Tournoi annulé",
            f"Le tournoi sur **{tournament['course_name']}** a été annulé par {interaction.user.mention}."
        )
        
        # Répondre à l'interaction initiale
        await interaction.response.send_message(embed=cancel_embed)
        
        # Gérer le thread du tournoi si disponible
        if tournament['thread_id']:
            try:
                thread = interaction.guild.get_thread(int(tournament['thread_id']))
                if thread:
                    # Envoyer un message d'annulation dans le thread avec mention de tous les participants
                    cancel_thread_embed = discord.Embed(
                        title="🚫 Tournoi annulé",
                        description=f"Le tournoi sur **{tournament['course_name']}** a été annulé par {interaction.user.mention}.",
                        color=0xE74C3C  # Rouge
                    )
                    
                    # Ajouter la liste des participants
                    if participants:
                        participants_mentions = [f"<@{participant_id}>" for participant_id in participants]
                        cancel_thread_embed.add_field(
                            name=f"Notification aux {len(participants)} participants",
                            value="Ce tournoi a été annulé. Merci de votre participation !",
                            inline=False
                        )
                        
                        # Envoyer le message avec les mentions
                        await thread.send(embed=cancel_thread_embed)
                        
                        # Envoyer les mentions dans un message séparé pour notifier les participants
                        if len(participants) > 0:
                            participants_text = " ".join(participants_mentions)
                            await thread.send(f"Information importante pour : {participants_text}")
                    else:
                        # S'il n'y a pas de participants, envoyer juste l'embed
                        await thread.send(embed=cancel_thread_embed)
                    
                    # Archiver le thread
                    await thread.edit(archived=True, locked=True)
                    logger.info(f"Thread {thread.id} pour le tournoi {tournament['id']} archivé suite à l'annulation")
            except Exception as e:
                logger.error(f"Erreur lors de la gestion du thread pour le tournoi annulé {tournament['id']} : {str(e)}")
        
        # Annuler le tournoi dans la base de données
        success = await DatabaseManager.cancel_tournament(tournament['id'])
        
        if success:
            # Trouver et dépingler le message du tournoi
            try:
                message = await interaction.channel.fetch_message(tournament['message_id'])
                await message.unpin()
            except (discord.NotFound, discord.Forbidden):
                # Le message n'existe plus ou le bot n'a pas la permission, ignorer
                pass
        else:
            # Notification en cas d'erreur avec la base de données
            await interaction.followup.send(
                embed=EmbedBuilder.error_message(
                    "Erreur",
                    "Le tournoi a été annulé, mais une erreur s'est produite lors de la mise à jour de la base de données."
                ),
                ephemeral=True
            )
            
    async def _get_tournament_participants(self, tournament_id: int) -> List[str]:
        """
        Récupère la liste des IDs Discord des participants à un tournoi.
        
        Args:
            tournament_id: ID du tournoi
            
        Returns:
            Liste des IDs Discord des participants
        """
        conn = await DatabaseManager.get_connection()
        cursor = await conn.execute(
            """
            SELECT u.discord_id
            FROM user u
            JOIN participation p ON u.user_id = p.user_id
            WHERE p.tournament_id = ?
            """,
            (tournament_id,)
        )
        rows = await cursor.fetchall()
        
        return [row[0] for row in rows]
    
    @app_commands.command(
        name="info",
        description="Affiche les informations sur le tournoi en cours"
    )
    async def tournament_info(self, interaction: discord.Interaction):
        """
        Affiche les informations sur le tournoi en cours.
        
        Args:
            interaction: Interaction Discord
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "info")
        
        # Vérifier s'il y a un tournoi actif
        tournament = await DatabaseManager.get_active_tournament(interaction.guild_id)
        if not tournament:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun tournoi actif",
                    "Il n'y a pas de tournoi en cours sur ce serveur."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer les meilleurs scores
        scores = await DatabaseManager.get_best_scores(tournament['id'])
        
        # Créer l'embed d'information
        embed = EmbedBuilder.tournament_leaderboard(tournament, scores)
        
        # Déterminer si nous sommes dans le thread du tournoi
        in_tournament_thread = (
            interaction.channel and 
            isinstance(interaction.channel, discord.Thread) and 
            str(interaction.channel.id) == tournament['thread_id']
        )
        
        # Si nous sommes dans le thread du tournoi, on peut envoyer le message publiquement
        # Sinon, on suggère à l'utilisateur de rejoindre le thread
        if in_tournament_thread:
            # Envoyer les informations publiquement dans le thread
            await interaction.response.send_message(embed=embed)
        else:
            # Envoyer les informations en privé
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Si un thread existe, suggérer à l'utilisateur de le rejoindre
            if tournament['thread_id']:
                await interaction.followup.send(
                    f"Pour suivre le tournoi et interagir avec les autres participants, rejoignez le thread dédié : <#{tournament['thread_id']}>",
                    ephemeral=True
                )
        
    async def announce_new_participant(self, interaction, tournament, user=None):
        """
        Annonce publiquement qu'un nouvel utilisateur participe au tournoi.
        
        Args:
            interaction: Interaction Discord
            tournament: Informations du tournoi
            user: Utilisateur qui participe (optionnel, par défaut utilise interaction.user)
        """
        if user is None:
            user = interaction.user
            
        # Créer un embed pour l'annonce publique avec une phrase aléatoire
        phrases = [
            f"Les moteurs rugissent, {user.mention} entre en piste !",
            f"Un nouveau challenger apparaît ! {user.mention} prend le volant !",
            f"Attention {user.mention} a des étoiles dans les yeux et la main sur l'accélérateur !",
            f"La rumeur dit que {user.mention} a battu Army lui-même... Mais chut, c'est un secret !",
            f"{user.mention} arrive avec une carapace bleue et beaucoup d'ambition !",
            f"Les Lakitus sont formels : {user.mention} pourrait bien créer la surprise !",
            f"Un Boo a murmuré que {user.mention} connaît tous les raccourcis..."
        ]
        
        public_embed = discord.Embed(
            title=f"🏎️ Nouveau participant !",
            description=random.choice(phrases),
            color=0x2ECC71  # Vert
        )
        
        # Ajouter un compte à rebours
        time_left = tournament['end_date'] - datetime.now()
        days_left = time_left.days
        hours_left = time_left.seconds // 3600
        
        public_embed.add_field(
            name="⏱️ Temps restant",
            value=f"{days_left} jours et {hours_left} heures",
            inline=True
        )
        
        # Ajouter le nombre de participants
        participants_count = await DatabaseManager.get_tournament_participants_count(tournament['id'])
        public_embed.add_field(
            name="👥 Participants",
            value=f"{participants_count} pilotes en course",
            inline=True
        )
        
        public_embed.set_thumbnail(url=tournament['course_image'])
        
        # Envoyer l'annonce dans le thread si disponible, sinon dans le canal d'origine
        if tournament['thread_id']:
            try:
                thread = interaction.guild.get_thread(int(tournament['thread_id']))
                if thread:
                    await thread.send(embed=public_embed)
                    return
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, ValueError) as e:
                logger.error(f"Erreur lors de l'envoi de l'annonce dans le thread: {str(e)}")
        
        # Si le thread n'existe pas ou n'est pas accessible, envoyer dans le canal d'origine
        channel = interaction.channel
        await channel.send(embed=public_embed)

    @app_commands.command(
        name="tournois",
        description="Liste tous les tournois actifs sur le serveur"
    )
    async def list_tournaments(self, interaction: discord.Interaction):
        """
        Liste tous les tournois actifs sur le serveur.
        
        Args:
            interaction: Interaction Discord
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "tournois")
        
        # Vérifier s'il y a un tournoi actif
        tournament = await DatabaseManager.get_active_tournament(interaction.guild_id)
        
        if not tournament:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun tournoi actif",
                    "Il n'y a pas de tournoi en cours sur ce serveur."
                ),
                ephemeral=True
            )
            return
        
        # Créer un embed pour afficher les informations sur le tournoi actif
        embed = discord.Embed(
            title="🏁 Tournoi actif",
            description=f"Un tournoi est en cours sur ce serveur :",
            color=0x3498DB  # Bleu
        )
        
        # Ajouter les informations du tournoi
        embed.add_field(
            name="Course",
            value=f"**{tournament['course_name']}** ({tournament['vehicle_class']})",
            inline=True
        )
        
        # Calculer le temps restant
        time_left = tournament['end_date'] - datetime.now()
        days_left = time_left.days
        hours_left = time_left.seconds // 3600
        
        embed.add_field(
            name="Temps restant",
            value=f"{days_left} jours et {hours_left} heures",
            inline=True
        )
        
        # Lien vers le thread
        if tournament['thread_id']:
            embed.add_field(
                name="Thread dédié",
                value=f"[Cliquez ici](https://discord.com/channels/{interaction.guild_id}/{tournament['thread_id']}) pour rejoindre le thread du tournoi.",
                inline=False
            )
        
        # Nombre de participants
        participants_count = await DatabaseManager.get_tournament_participants_count(tournament['id'])
        
        embed.add_field(
            name="Participants",
            value=f"{participants_count} pilote{'s' if participants_count != 1 else ''}",
            inline=True
        )
        
        # Dates du tournoi
        embed.add_field(
            name="Période",
            value=f"Du {format_date(tournament['start_date'])} au {format_date(tournament['end_date'])}",
            inline=True
        )
        
        embed.set_thumbnail(url=tournament['course_image'])
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    """
    Ajoute le cog au bot.
    
    Args:
        bot: Instance du bot Discord
    """
    await bot.add_cog(TournamentCog(bot))