"""
Validateurs pour les entrées utilisateur.
"""
import re
from typing import Optional, Tuple

from database.models import parse_time
from config import VEHICLE_CLASSES

def validate_time_format(time_string: str) -> Tuple[bool, Optional[str]]:
    """
    Valide le format d'un temps soumis.
    
    Args:
        time_string: Chaîne de temps au format mm:ss:ms
        
    Returns:
        Tuple (validité, message d'erreur si invalide)
    """
    # Vérification du format général avec regex
    pattern = r"^\d{1,2}:\d{2}:\d{3}$"
    if not re.match(pattern, time_string):
        return False, "Format de temps invalide. Utilisez mm:ss:ms (ex: 1:23:456)"
    
    # Vérification des valeurs
    try:
        time_ms = parse_time(time_string)
        return True, None
    except ValueError as e:
        return False, str(e)

def validate_vehicle_class(vehicle_class: str) -> Tuple[bool, Optional[str]]:
    """
    Valide la classe de véhicule.
    
    Args:
        vehicle_class: Classe de véhicule
        
    Returns:
        Tuple (validité, message d'erreur si invalide)
    """
    if vehicle_class not in VEHICLE_CLASSES:
        return False, f"Classe de véhicule invalide. Options disponibles: {', '.join(VEHICLE_CLASSES)}"
    
    return True, None

def validate_duration(duration: int) -> Tuple[bool, Optional[str]]:
    """
    Valide la durée d'un tournoi.
    
    Args:
        duration: Durée en jours
        
    Returns:
        Tuple (validité, message d'erreur si invalide)
    """
    if duration < 1 or duration > 90:
        return False, "La durée doit être comprise entre 1 et 90 jours."
    
    return True, None

def validate_image_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Valide une URL d'image.
    
    Args:
        url: URL de l'image
        
    Returns:
        Tuple (validité, message d'erreur si invalide)
    """
    # Vérification basique d'URL
    pattern = r"^https?://.*\.(png|jpg|jpeg|gif|webp)$"
    if not re.match(pattern, url, re.IGNORECASE):
        return False, "URL d'image invalide. Formats acceptés: png, jpg, jpeg, gif, webp"
    
    return True, None