"""
Cog pour la gestion des scores du bot Mario Kart 8 Time Attack.
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from database.manager import DatabaseManager
from database.models import parse_time, format_time
from utils.embeds import EmbedBuilder
from utils.validators import validate_time_format
from utils.logger import log_command, log_score_submission, log_error

class ScoresCog(commands.Cog):
    """
    Gestion des scores pour le bot Mario Kart 8 Time Attack.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(
        name="score",
        description="Soumet un temps pour le tournoi en cours"
    )
    @app_commands.describe(
        temps="Votre temps au format mm:ss:ms (ex: 1:23:456)",
        preuve="Capture d'écran de votre temps (optionnel)"
    )
    async def submit_score(
        self,
        interaction: discord.Interaction,
        temps: str,
        preuve: Optional[discord.Attachment] = None
    ):
        """
        Soumet un temps pour le tournoi en cours.
        
        Args:
            interaction: Interaction Discord
            temps: Temps au format mm:ss:ms
            preuve: Capture d'écran (optionnelle)
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "score")
        
        # Vérifier le format du temps
        valid_time, time_error = validate_time_format(temps)
        if not valid_time:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message("Format invalide", time_error),
                ephemeral=True
            )
            return
        
        # Convertir le temps en millisecondes
        time_ms = parse_time(temps)
        
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
        
        # Vérifier si l'utilisateur participe au tournoi
        user_id = await DatabaseManager.register_user(str(interaction.user.id), interaction.user.display_name)
        participation_id = await DatabaseManager.get_participation_id(tournament['id'], user_id)
        
        if not participation_id:
            # L'utilisateur ne participe pas encore, l'inscrire automatiquement
            participation_id = await DatabaseManager.register_participation(tournament['id'], user_id)
            
            # Annoncer le nouveau participant
            tournament_cog = self.bot.get_cog('TournamentCog')
            if tournament_cog:
                await tournament_cog.announce_new_participant(interaction, tournament)
            
        # Traiter la capture d'écran si elle est fournie
        screenshot_url = None
        if preuve:
            # Vérification simple du type de fichier
            valid_formats = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif']
            if preuve.content_type not in valid_formats:
                await interaction.response.send_message(
                    embed=EmbedBuilder.error_message(
                        "Format non supporté",
                        "Veuillez soumettre une image au format PNG, JPEG ou GIF."
                    ),
                    ephemeral=True
                )
                return
            
            # Utiliser l'URL de l'attachement directement
            screenshot_url = preuve.url
        
        # Enregistrer le score
        try:
            score_id = await DatabaseManager.submit_score(participation_id, time_ms, screenshot_url)
            
            # Confirmer la soumission
            embed = EmbedBuilder.score_submission(tournament, time_ms, screenshot_url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Journaliser la soumission
            log_score_submission(interaction.guild_id, interaction.user.id, tournament['id'], time_ms)
            
            # Mettre à jour le classement
            tournament_cog = self.bot.get_cog('TournamentCog')
            if tournament_cog:
                await tournament_cog.update_leaderboard(interaction.guild_id, tournament['id'])
        
        except Exception as e:
            log_error(f"Erreur lors de la soumission d'un score: {str(e)}")
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Erreur",
                    "Impossible d'enregistrer votre score. Veuillez réessayer."
                ),
                ephemeral=True
            )
    
    @app_commands.command(
        name="messcores",
        description="Affiche tous vos temps soumis pour le tournoi en cours"
    )
    async def view_scores(self, interaction: discord.Interaction):
        """
        Affiche tous les temps soumis par l'utilisateur pour le tournoi en cours.
        
        Args:
            interaction: Interaction Discord
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "messcores")
        
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
        
        # Récupérer l'ID utilisateur
        user_id = await DatabaseManager.register_user(str(interaction.user.id), interaction.user.display_name)
        
        # Vérifier si l'utilisateur participe au tournoi
        participation_id = await DatabaseManager.get_participation_id(tournament['id'], user_id)
        
        if not participation_id:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Pas de participation",
                    "Vous ne participez pas au tournoi en cours."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer tous les scores de l'utilisateur
        scores = await DatabaseManager.get_user_scores(participation_id)
        
        if not scores:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun score",
                    "Vous n'avez pas encore soumis de temps pour ce tournoi."
                ),
                ephemeral=True
            )
            return
        
        # Créer un embed pour afficher les scores
        embed = discord.Embed(
            title=f"Vos temps pour {tournament['course_name']} ({tournament['vehicle_class']})",
            description=f"Voici tous vos temps soumis pour le tournoi en cours.",
            color=0x3498DB  # Bleu
        )
        
        for i, score in enumerate(scores):
            embed.add_field(
                name=f"Temps #{i+1}",
                value=f"**{format_time(score['time_ms'])}** - Soumis le {score['submitted_at'].strftime('%d/%m/%Y à %H:%M')}",                inline=False
            )
        
        # Meilleur temps en évidence
        best_score = min(scores, key=lambda x: x['time_ms'])
        embed.add_field(
            name="Votre meilleur temps",
            value=f"**{format_time(best_score['time_ms'])}**",
            inline=False
        )
        
        embed.set_thumbnail(url=tournament['course_image'])
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """
    Ajoute le cog au bot.
    
    Args:
        bot: Instance du bot Discord
    """
    await bot.add_cog(ScoresCog(bot))