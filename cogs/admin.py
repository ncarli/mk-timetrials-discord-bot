"""
Cog pour les commandes d'administration du bot Mario Kart 8 Time Attack.
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from database.manager import DatabaseManager
from utils.embeds import EmbedBuilder
from utils.logger import log_command, log_error
from database.models import parse_time, format_time

class AdminCog(commands.Cog):
    """
    Commandes d'administration pour le bot Mario Kart 8 Time Attack.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def is_admin(self, interaction: discord.Interaction) -> bool:
        """
        Vérifie si l'utilisateur a les permissions d'administration.
        
        Args:
            interaction: Interaction Discord
            
        Returns:
            True si l'utilisateur est administrateur, False sinon
        """
        # Vérifier si l'utilisateur est administrateur du serveur
        if interaction.user.guild_permissions.administrator:
            return True
        
        # Vérifier si l'utilisateur a le rôle d'administration configuré
        admin_role_id = await DatabaseManager.get_admin_role(interaction.guild_id)
        if admin_role_id:
            role = interaction.guild.get_role(admin_role_id)
            if role and role in interaction.user.roles:
                return True
        
        return False
    
    @app_commands.command(
        name="config",
        description="Configure les paramètres du bot"
    )
    @app_commands.describe(
        prefix="Préfixe de commande (ex: !mk)",
        role_admin="Rôle pouvant administrer le bot"
    )
    async def configure_bot(
        self,
        interaction: discord.Interaction,
        prefix: Optional[str] = None,
        role_admin: Optional[discord.Role] = None
    ):
        """
        Configure les paramètres du bot pour le serveur.
        
        Args:
            interaction: Interaction Discord
            prefix: Nouveau préfixe de commande (optionnel)
            role_admin: Rôle d'administration (optionnel)
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "config")
        
        # Vérifier les permissions d'administration
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Permission refusée",
                    "Vous devez être administrateur pour configurer le bot."
                ),
                ephemeral=True
            )
            return
        
        # Enregistrer le serveur s'il n'existe pas déjà
        await DatabaseManager.register_server(interaction.guild_id, interaction.guild.name)
        
        changes = []
        
        # Mettre à jour le préfixe si fourni
        if prefix:
            if len(prefix) > 10:
                await interaction.response.send_message(
                    embed=EmbedBuilder.error_message(
                        "Préfixe trop long",
                        "Le préfixe doit comporter moins de 10 caractères."
                    ),
                    ephemeral=True
                )
                return
            
            await DatabaseManager.update_server_prefix(interaction.guild_id, prefix)
            changes.append(f"Préfixe défini sur `{prefix}`")
        
        # Mettre à jour le rôle d'administration si fourni
        if role_admin:
            await DatabaseManager.update_admin_role(interaction.guild_id, role_admin.id)
            changes.append(f"Rôle d'administration défini sur {role_admin.mention}")
        
        # Répondre avec les changements effectués
        if changes:
            await interaction.response.send_message(
                embed=EmbedBuilder.confirmation_message(
                    "Configuration mise à jour",
                    "\n".join(changes)
                )
            )
        else:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Aucun changement",
                    "Veuillez spécifier au moins un paramètre à modifier."
                ),
                ephemeral=True
            )
    
    @app_commands.command(
        name="verifier",
        description="Vérifie ou invalide un score soumis"
    )
    @app_commands.describe(
        utilisateur="Utilisateur dont le score doit être vérifié",
        action="Action à effectuer"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Vérifier le score", value="verify"),
        app_commands.Choice(name="Supprimer le score", value="delete")
    ])
    async def verify_score(
        self,
        interaction: discord.Interaction,
        utilisateur: discord.User,
        action: str
    ):
        """
        Vérifie ou invalide un score soumis.
        
        Args:
            interaction: Interaction Discord
            utilisateur: Utilisateur dont le score doit être vérifié
            action: Action à effectuer (vérifier ou supprimer)
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "verifier")
        
        # Vérifier les permissions d'administration
        if not await self.is_admin(interaction):
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Permission refusée",
                    "Vous devez être administrateur pour vérifier les scores."
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
                    "Il n'y a pas de tournoi en cours sur ce serveur."
                ),
                ephemeral=True
            )
            return
        
        # Récupérer l'ID utilisateur
        user_id = await DatabaseManager.register_user(str(utilisateur.id), utilisateur.display_name)
        
        # Vérifier si l'utilisateur participe au tournoi
        participation_id = await DatabaseManager.get_participation_id(tournament['id'], user_id)
        
        if not participation_id:
            await interaction.response.send_message(
                embed=EmbedBuilder.error_message(
                    "Pas de participation",
                    f"{utilisateur.mention} ne participe pas au tournoi en cours."
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
                    f"{utilisateur.mention} n'a pas encore soumis de temps pour ce tournoi."
                ),
                ephemeral=True
            )
            return
        
        # Trier par temps (du meilleur au pire)
        scores.sort(key=lambda x: x['time_ms'])
        best_score = scores[0]
        
        # Créer les informations utilisateur pour l'embed
        user_data = {
            "username": utilisateur.display_name,
            "discord_id": str(utilisateur.id)
        }
        
        # Créer l'embed avec les détails du score
        embed = EmbedBuilder.admin_score_view(best_score, user_data, tournament)

        if action == "verify":
            # Vérifier le score
            await DatabaseManager.verify_score(best_score['id'])
            
            # Mettre à jour le statut pour l'affichage
            best_score['verified'] = True
            
            # Créer et envoyer l'embed avec les détails du score vérifié
            embed = EmbedBuilder.admin_score_view(best_score, user_data, tournament)
            await interaction.response.send_message(embed=embed)
            
            # Confirmer la vérification
            follow_up_embed = EmbedBuilder.confirmation_message(
                "Score vérifié",
                f"Le score de {utilisateur.mention} ({format_time(best_score['time_ms'])}) a été marqué comme vérifié."
            )
            await interaction.followup.send(embed=follow_up_embed)
                
        elif action == "delete":
            # Répondre directement avec un message de confirmation
            embed = EmbedBuilder.confirmation_message(
                "Score supprimé",
                f"Le score de {utilisateur.mention} ({format_time(best_score['time_ms'])}) a été supprimé."
            )
            await interaction.response.send_message(embed=embed)
            
            # Supprimer le score
            await DatabaseManager.delete_score(best_score['id'])
        
        # Mettre à jour le classement
        tournament_cog = self.bot.get_cog('TournamentCog')
        if tournament_cog:
            await tournament_cog.update_leaderboard(interaction.guild_id, tournament['id'])
    
    @app_commands.command(
        name="historique",
        description="Affiche l'historique des tournois terminés"
    )
    async def tournament_history(self, interaction: discord.Interaction):
        """
        Affiche l'historique des tournois terminés sur le serveur.
        
        Args:
            interaction: Interaction Discord
        """
        # Journaliser la commande
        log_command(interaction.guild_id, interaction.user.id, "historique")
        
        # Récupérer l'historique des tournois (implémentation à faire)
        # Cette fonctionnalité nécessiterait une requête supplémentaire dans le DatabaseManager
        
        # Pour l'instant, renvoyer un message temporaire
        await interaction.response.send_message(
            embed=EmbedBuilder.confirmation_message(
                "Fonctionnalité à venir",
                "L'historique des tournois sera disponible dans une prochaine mise à jour."
            ),
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    """
    Ajoute le cog au bot.
    
    Args:
        bot: Instance du bot Discord
    """
    await bot.add_cog(AdminCog(bot))