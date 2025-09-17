import json
import os
import re
from datetime import datetime

import unicodedata

SETTINGS_FILE = "settings.json"


def format_date(ts):
    try:
        dt = datetime.fromtimestamp(int(ts))
        return dt.strftime("%d-%b-%Y %H:%M")  # Ej: 15-Sep-2025 10:30
    except Exception:
        return str(ts)  # fallback si no es un número

def strip_bbcode(text: str) -> str:
    """Elimina tags BBCode simples"""
    return re.sub(r"\[/?[^\]]+\]", "", text).strip()

def get_user_color(user):
    colors = {
        'pali': "#638db6",
        'riaj': "#638db6",
        'xavier': "#fb6160",
        'regol': "#fb6160",
        'säbel': "#ff5694",
        'zafiro bladen': "#ac97ff",
        'soria': "#65bdf3",
        'legend': "#85de85",
        'furanku': "#faa351",
        'vichoxd': "#62d4e3",
    }
    return colors.get(user.lower(), "#7f8c8d")

def save_setting(key, value):
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
    else:
        settings = {}
    settings[key] = value
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    defaults = {
        "theme": "dark",
        "json_file": "",
    }
    return defaults  # valor por defecto

def strip_accents(s: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )

ACCENT_GROUPS = {
    "a": "aáàäâ",
    "e": "eéèëê",
    "i": "iíìïî",
    "o": "oóòöô",
    "u": "uúùüû",
    "n": "nñ",
    "c": "cç",
}

def accent_insensitive_regex(text: str) -> str:
    pattern = ""
    for ch in text:
        low = ch.lower()
        if low in ACCENT_GROUPS:
            group = ACCENT_GROUPS[low]
            if ch.isupper():
                group = group.upper() + group
            pattern += f"[{group}]"
        else:
            pattern += re.escape(ch)
    return pattern

