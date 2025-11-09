import spacy
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from typing import Dict, List
import re

# modèle fr
try:
    nlp = spacy.load("fr_core_news_sm")
except OSError:
    print("Modèle spaCy non trouvé. Exécutez: python -m spacy download fr_core_news_sm")
    nlp = None


# Extraction des entités
def extract_entities(text: str) -> Dict[str, List[str]]:
    if not nlp:
        return {"personnes": [], "lieux": [], "dates": [], "organisations": []}
    
    doc = nlp(text)
    
    personnes = []
    lieux = []
    dates = []
    organisations = []
    
    for ent in doc.ents:
        if ent.label_ == "PER":
            personnes.append(ent.text)
        elif ent.label_ == "LOC":
            lieux.append(ent.text)
        elif ent.label_ == "DATE":
            dates.append(ent.text)
        elif ent.label_ == "ORG":
            organisations.append(ent.text)
    
    # Enlever les doublons
    return {
        "personnes": list(set(personnes)),
        "lieux": list(set(lieux)),
        "dates": list(set(dates)),
        "organisations": list(set(organisations))
    }


# Parse les dates en français
# TODO: gérer plus de cas (hier, semaines, etc)
def parse_french_date(date_str: str) -> datetime:
    
    date_str = date_str.lower().strip()
    now = datetime.now()
    
    # Cas "demain"
    if "demain" in date_str:
        dt = now + timedelta(days=1)
        
        # Extraire l'heure si présente
        hour_match = re.search(r"(\d{1,2})h?(?::(\d{2}))?\s*(am|pm|A|M)?", date_str)
        if hour_match:
            hour = int(hour_match.group(1))
            minute = int(hour_match.group(2) or 0)
            dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)  # 9h par défaut
        
        return dt
    
    # jours de la semaine
    jours_fr = {
        "lundi": 0, "l": 0,
        "mardi": 1, "ma": 1,
        "mercredi": 2, "me": 2,
        "jeudi": 3, "j": 3,
        "vendredi": 4, "v": 4,
        "samedi": 5, "s": 5,
        "dimanche": 6, "d": 6
    }
    
    for nom_jour, num_jour in jours_fr.items():
        if nom_jour in date_str:
            current_weekday = now.weekday()
            days_ahead = num_jour - current_weekday
            
            if days_ahead <= 0:
                days_ahead += 7
            
            dt = now + timedelta(days=days_ahead)
            
            # Extraire l'heure si présente
            hour_match = re.search(r"(\d{1,2})h?(?::(\d{2}))?\s*(am|pm|A|M)?", date_str)
            if hour_match:
                hour = int(hour_match.group(1))
                minute = int(hour_match.group(2) or 0)
                dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # Cas "samedi matin" = 9h, "samedi après-midi" = 14h, etc.
                if "matin" in date_str:
                    dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
                elif "midi" in date_str or "noon" in date_str:
                    dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
                elif "après-midi" in date_str or "am" in date_str:
                    dt = dt.replace(hour=14, minute=0, second=0, microsecond=0)
                elif "soir" in date_str:
                    dt = dt.replace(hour=18, minute=0, second=0, microsecond=0)
                else:
                    dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
            
            return dt
    
    # Cas des dates relatives simples (aujourd'hui, etc.)
    if "aujourd'hui" in date_str or "today" in date_str:
        dt = now.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        # Essayer de parser avec dateutil pour les formats standards
        try:
            dt = parse_date(date_str, dayfirst=True)
        except:
            dt = now  # Par défaut, retourner maintenant
    
    return dt


# Extraire les dates du texte
def extract_dates(text: str) -> List[Dict]:
    if not nlp:
        return []
    
    doc = nlp(text)
    dates = []
    
    for ent in doc.ents:
        if ent.label_ == "DATE":
            try:
                parsed_date = parse_french_date(ent.text)
                dates.append({
                    "text": ent.text,
                    "datetime": parsed_date.isoformat(),
                    "timestamp": parsed_date.timestamp()
                })
            except:
                # Si parse échoue, garder le texte original
                dates.append({
                    "text": ent.text,
                    "datetime": None,
                    "timestamp": None
                })
    
    return dates


# Suggère une tâche à partir du texte
def suggest_task(text: str) -> Dict:
    if not nlp:
        return {"titre": "", "description": "", "date_echéance": None, "priorité": 1}
    
    doc = nlp(text)
    entities = extract_entities(text)
    dates_found = extract_dates(text)
    
    # Le texte devient le titre (limité à 100 chars)
    titre = text[:100] if len(text) <= 100 else text[:97] + "..."
    
    # Description avec les entités
    description_parts = []
    if entities["personnes"]:
        description_parts.append(f"Personnes: {', '.join(entities['personnes'])}")
    if entities["lieux"]:
        description_parts.append(f"Lieux: {', '.join(entities['lieux'])}")
    if entities["organisations"]:
        description_parts.append(f"Organisations: {', '.join(entities['organisations'])}")
    
    description = " | ".join(description_parts) if description_parts else text
    
    # Date d'échéance
    date_echéance = dates_found[0]["datetime"] if dates_found else None
    
    # Priorité selon les mots-clés
    text_lower = text.lower()
    priorité = 2  # normal par défaut
    if any(w in text_lower for w in ["urgent", "asap", "immédiat", "important"]):
        priorité = 3
    elif any(w in text_lower for w in ["quand tu peux", "pas urgent", "optionnel"]):
        priorité = 1
    
    return {
        "titre": titre,
        "description": description,
        "date_echéance": date_echéance,
        "priorité": priorité
    }
