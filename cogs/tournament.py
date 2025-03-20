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
from database.models import initialize_database
from utils.embeds import EmbedBuilder
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
        bot.add_listener(self.start_tasks, 'on_ready')  

    async def start_tasks(self):
        """Initialise la base de données et démarre les tâches périodiques."""
        await self.bot.wait_until_ready()   
        await initialize_database()

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
            
            # Annoncer le nouveau participant
            await self.announce_new_participant(interaction, tournament)
        
        # Confirmer l'inscription à l'utilisateur (message privé)
        embed = EmbedBuilder.participation_confirmation(tournament)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
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
        
        # Annuler le tournoi
        success = await DatabaseManager.cancel_tournament(tournament['id'])
        
        if success:
            # Confirmer l'annulation
            embed = EmbedBuilder.confirmation_message(
                "Tournoi annulé",
                f"Le tournoi sur **{tournament['course_name']}** a été annulé."
            )
            await interaction.response.send_message(embed=embed)
            
            # Trouver et dépingler le message du tournoi
            try:
                message = await interaction.channel.fetch_message(tournament['message_id'])
                await message.unpin()
            except (discord.NotFound, discord.Forbidden):
                # Le message n'existe plus ou le bot n'a pas la permission, ignorer
                pass
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Erreur",
                    "Impossible d'annuler le tournoi. Veuillez réessayer."
                ),
                ephemeral=True
            )
    
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
        
        # Envoyer les informations
        await interaction.response.send_message(embed=embed)
        
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

async def setup(bot: commands.Bot):
    """
    Ajoute le cog au bot.
    
    Args:
        bot: Instance du bot Discord
    """
    await bot.add_cog(TournamentCog(bot))