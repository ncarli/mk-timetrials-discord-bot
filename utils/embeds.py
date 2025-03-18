"""
Utilitaires pour la création d'embeds Discord.
"""
import discord
from datetime import datetime
from typing import List, Dict, Any, Optional

from database.models import format_time
from config import COLORS, EMOJIS

def format_date(date: datetime) -> str:
    """
    Formate une date pour l'affichage.
    
    Args:
        date: Objet datetime
        
    Returns:
        Chaîne formatée (ex: "31 janvier 2023")
    """
    month_names = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    
    return f"{date.day} {month_names[date.month - 1]} {date.year}"

class EmbedBuilder:
    """
    Classe utilitaire pour créer des embeds Discord.
    """
    
    @staticmethod
    def tournament_announcement(tournament: Dict[str, Any]) -> discord.Embed:
        """
        Crée un embed pour l'annonce d'un nouveau tournoi.
        
        Args:
            tournament: Informations du tournoi
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"{EMOJIS['TROPHY']} Nouveau Tournoi Time Attack !",
            description=f"Une nouvelle compétition commence ! Montrez votre talent sur cette course.",
            color=COLORS['INFO']
        )
        
        embed.add_field(
            name="Course",
            value=f"**{tournament['course_name']}**",
            inline=True
        )
        
        embed.add_field(
            name="Coupe",
            value=f"{tournament['cup_name']}",
            inline=True
        )
        
        embed.add_field(
            name="Version d'origine",
            value=f"{tournament['course_origin']}",
            inline=True
        )
        
        embed.add_field(
            name="Classe de véhicule",
            value=f"**{tournament['vehicle_class']}**",
            inline=True
        )
        
        embed.add_field(
            name="Début",
            value=format_date(tournament['start_date']),
            inline=True
        )
        
        embed.add_field(
            name="Fin",
            value=format_date(tournament['end_date']),
            inline=True
        )
        
        embed.set_image(url=tournament['course_image'])
        
        embed.set_footer(text="Pour participer, utilisez /participer • Pour soumettre un temps, utilisez /score")
        
        return embed
    
    @staticmethod
    def tournament_leaderboard(tournament: Dict[str, Any], scores: List[Dict[str, Any]]) -> discord.Embed:
        """
        Crée un embed pour le classement d'un tournoi.
        
        Args:
            tournament: Informations du tournoi
            scores: Liste des meilleurs scores
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"{EMOJIS['TROPHY']} Classement: {tournament['course_name']} ({tournament['vehicle_class']})",
            description=f"Tournoi en cours: du {format_date(tournament['start_date'])} au {format_date(tournament['end_date'])}",
            color=COLORS['INFO']
        )
        
        if not scores:
            embed.add_field(
                name="Aucun score soumis",
                value="Soyez le premier à soumettre un temps !",
                inline=False
            )
        else:
            leaderboard_text = ""
            
            for i, score in enumerate(scores):
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"{i+1}."
                verification = " ✓" if score['verified'] else ""
                leaderboard_text += f"{medal} **{score['username']}**: {format_time(score['time_ms'])}{verification}\n"
            
            embed.add_field(
                name="Meilleurs temps",
                value=leaderboard_text,
                inline=False
            )
        
        embed.set_thumbnail(url=tournament['course_image'])
        embed.set_footer(text="✓ = Score vérifié • Mis à jour le " + datetime.now().strftime("%d/%m/%Y à %H:%M"))
        
        return embed
    
    @staticmethod
    def participation_confirmation(tournament: Dict[str, Any]) -> discord.Embed:
        """
        Crée un embed pour confirmer la participation à un tournoi.
        
        Args:
            tournament: Informations du tournoi
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"{EMOJIS['CHECK']} Participation confirmée !",
            description=f"Vous participez maintenant au tournoi sur **{tournament['course_name']}** ({tournament['vehicle_class']}).",
            color=COLORS['SUCCESS']
        )
        
        embed.add_field(
            name="Date de fin",
            value=format_date(tournament['end_date']),
            inline=False
        )
        
        embed.add_field(
            name="Comment soumettre un temps",
            value="Utilisez la commande `/score` suivie de votre temps au format mm:ss:ms (ex: 1:23:456).",
            inline=False
        )
        
        embed.set_thumbnail(url=tournament['course_image'])
        
        return embed
    
    @staticmethod
    def score_submission(tournament: Dict[str, Any], time_ms: int, screenshot_url: Optional[str] = None) -> discord.Embed:
        """
        Crée un embed pour confirmer la soumission d'un score.
        
        Args:
            tournament: Informations du tournoi
            time_ms: Temps soumis en millisecondes
            screenshot_url: URL de la capture d'écran (optionnelle)
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"{EMOJIS['TIMER']} Score soumis !",
            description=f"Votre temps de **{format_time(time_ms)}** a été enregistré pour **{tournament['course_name']}**.",
            color=COLORS['SUCCESS']
        )
        
        embed.add_field(
            name="Classe de véhicule",
            value=tournament['vehicle_class'],
            inline=True
        )
        
        if screenshot_url:
            embed.add_field(
                name="Capture d'écran",
                value="Votre capture d'écran a été enregistrée.",
                inline=True
            )
            embed.set_image(url=screenshot_url)
        
        embed.add_field(
            name="Validation",
            value="Votre score sera vérifié par un administrateur.",
            inline=False
        )
        
        embed.set_thumbnail(url=tournament['course_image'])
        
        return embed
    
    @staticmethod
    def tournament_reminder(tournament: Dict[str, Any], days_left: int) -> discord.Embed:
        """
        Crée un embed pour rappeler la fin prochaine d'un tournoi.
        
        Args:
            tournament: Informations du tournoi
            days_left: Nombre de jours restants
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"{EMOJIS['WARNING']} Rappel: Fin de tournoi dans {days_left} jours !",
            description=f"Le tournoi sur **{tournament['course_name']}** ({tournament['vehicle_class']}) se termine bientôt.",
            color=COLORS['WARNING']
        )
        
        embed.add_field(
            name="Date de fin",
            value=format_date(tournament['end_date']),
            inline=True
        )
        
        embed.add_field(
            name="Participants",
            value="Soumettez vos meilleurs temps avant la fin !",
            inline=True
        )
        
        embed.set_thumbnail(url=tournament['course_image'])
        
        return embed
    
    @staticmethod
    def tournament_ended(tournament: Dict[str, Any], scores: List[Dict[str, Any]]) -> discord.Embed:
        """
        Crée un embed pour annoncer la fin d'un tournoi.
        
        Args:
            tournament: Informations du tournoi
            scores: Liste des meilleurs scores
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"{EMOJIS['TROPHY']} Tournoi terminé: {tournament['course_name']}",
            description=f"Le tournoi sur **{tournament['course_name']}** ({tournament['vehicle_class']}) est maintenant terminé !",
            color=COLORS['INFO']
        )
        
        if not scores:
            embed.add_field(
                name="Aucun participant",
                value="Personne n'a soumis de temps pour ce tournoi.",
                inline=False
            )
        else:
            winners_text = ""
            
            for i, score in enumerate(scores[:3]):
                if i == 0:
                    winners_text += f"🥇 **{score['username']}**: {format_time(score['time_ms'])}\n"
                elif i == 1:
                    winners_text += f"🥈 **{score['username']}**: {format_time(score['time_ms'])}\n"
                elif i == 2:
                    winners_text += f"🥉 **{score['username']}**: {format_time(score['time_ms'])}\n"
            
            embed.add_field(
                name="Podium",
                value=winners_text if winners_text else "Pas assez de participants pour un podium complet.",
                inline=False
            )
        
        embed.add_field(
            name="Durée du tournoi",
            value=f"Du {format_date(tournament['start_date'])} au {format_date(tournament['end_date'])}",
            inline=False
        )
        
        embed.set_thumbnail(url=tournament['course_image'])
        
        return embed
    
    @staticmethod
    def error_message(title: str, description: str) -> discord.Embed:
        """
        Crée un embed pour afficher un message d'erreur.
        
        Args:
            title: Titre de l'erreur
            description: Description de l'erreur
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"{EMOJIS['CANCEL']} {title}",
            description=description,
            color=COLORS['ERROR']
        )
        
        return embed
    
    @staticmethod
    def confirmation_message(title: str, description: str) -> discord.Embed:
        """
        Crée un embed pour afficher un message de confirmation.
        
        Args:
            title: Titre du message
            description: Description du message
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"{EMOJIS['CHECK']} {title}",
            description=description,
            color=COLORS['SUCCESS']
        )
        
        return embed
    
    @staticmethod
    def admin_score_view(score_data: Dict[str, Any], user_data: Dict[str, Any], tournament: Dict[str, Any]) -> discord.Embed:
        """
        Crée un embed pour afficher un score à valider par un administrateur.
        
        Args:
            score_data: Informations du score
            user_data: Informations de l'utilisateur
            tournament: Informations du tournoi
            
        Returns:
            Embed Discord
        """
        embed = discord.Embed(
            title=f"Vérification de score: {user_data['username']}",
            description=f"Score soumis pour **{tournament['course_name']}** ({tournament['vehicle_class']})",
            color=COLORS['INFO']
        )
        
        embed.add_field(
            name="Temps",
            value=f"**{format_time(score_data['time_ms'])}**",
            inline=True
        )
        
        embed.add_field(
            name="Soumis le",
            value=score_data['submitted_at'].strftime("%d/%m/%Y à %H:%M"),
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="✅ Vérifié" if score_data['verified'] else "⏳ En attente de vérification",
            inline=True
        )
        
        if score_data['screenshot_url']:
            embed.add_field(
                name="Capture d'écran",
                value="Voir ci-dessous",
                inline=False
            )
            embed.set_image(url=score_data['screenshot_url'])
        else:
            embed.add_field(
                name="Capture d'écran",
                value="Aucune capture d'écran fournie",
                inline=False
            )
        
        embed.set_thumbnail(url=tournament['course_image'])
        embed.set_footer(text=f"ID du score: {score_data['id']}")
        
        return embed