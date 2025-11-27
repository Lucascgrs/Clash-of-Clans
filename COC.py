# -*- coding: utf-8 -*-
import unicodedata
import requests
import random
import string
import sys
import pandas as pd
import os
import time
import pyautogui
import pyperclip
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import pytesseract
from pathlib import Path
import logging
from typing import List, Dict

# --- CONFIG ---

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

API_URL = "https://api.clashofclans.com/v1"
API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjcwMzc0ZTMxLTFkMTEtNDk2Mi1hNmEwLTMwODEyOThhMzRiMCIsImlhdCI6MTc2MzM3NDg1Nywic3ViIjoiZGV2ZWxvcGVyLzUwNzVhOTk1LTI5NWUtNTZiMS0yZTQ2LWY0YmMyNTgxN2QwMyIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjk1LjE3OC45MS4xOTgiXSwidHlwZSI6ImNsaWVudCJ9XX0.iQjs1tOCHhitaMEWyvsKW3B9lEM7MFpxBuxemCDQlYyQnBMwjacazl41ivm-uygZnEbpX78z-eWg8gjL8PE8uw"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}

LOCATION_FRANCE = 32000087
DEFAULT_MAX_WORKERS = 50


# --- HELPERS ---

def clean_string(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").strip()


def safe_get(url: str, headers: dict, params=None, retries=3, delay=2):
    """GET avec retry + backoff exponentiel."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=6)
            r.raise_for_status()
            return r
        except Exception as e:
            logging.warning(f"Tentative {attempt+1}/{retries} échouée: {e}")
            time.sleep(delay * (attempt + 1))
    logging.error("Abandon après plusieurs erreurs.")
    return None


# --- CLASH OF CLANS API ---

def search_clans(name: str, limit: int, locationId: bool = True) -> list[str]:
    params = {"name": name, "limit": limit}
    if locationId:
        params["locationId"] = LOCATION_FRANCE

    r = safe_get(f"{API_URL}/clans", HEADERS, params)
    if not r:
        return []
    return [c["tag"] for c in r.json().get("items", [])]


def random_clan_search(limit: int) -> list[str]:
    prefix = "".join(random.choices(string.ascii_uppercase, k=3))
    logging.info(f"Recherche clans prefix: {prefix}")
    return search_clans(prefix, limit)


# --- PLAYER FILTERS & EXTRACTION ---

def extract_player_info(m: dict) -> dict:
    return {
        "name": m.get("name"),
        "role": m.get("role"),
        "expLevel": m.get("expLevel"),
        "townHallLevel": m.get("townHallLevel"),
        "trophies": m.get("trophies"),
        "donations": m.get("donations"),
        "donationsReceived": m.get("donationsReceived")
    }


def filter_player(m: dict) -> bool:
    if m.get("trophies", 0) < 0 or m["trophies"] > 1000:
        return False
    if m.get("townHallLevel", 0) < 13:
        return False
    if m.get("league", {}).get("name") == "Unranked":
        return False
    if m["donations"] == 0 and m["donationsReceived"] == 0:
        return False
    return True


def get_clan_members(clan_tag: str, token: str, condition=True) -> dict:
    tag_encoded = clan_tag.replace("#", "%23")
    url = f"{API_URL}/clans/{tag_encoded}/members"

    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        raise Exception(f"Erreur API clan {clan_tag}: {r.status_code}")

    members = r.json().get("items", [])
    result = {}

    for m in members:
        tag = m["tag"]
        if not condition or filter_player(m):
            result[tag] = extract_player_info(m)

    return result


# --- MULTITHREADING ---

def get_all_clan_members_threadpool(clan_tags: list[str], token: str, max_workers=50, condition=True) -> list[dict]:
    results = []
    errors = 0

    logging.info(f"Collecte joueurs sur {len(clan_tags)} clans...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_clan_members, tag, token, condition): tag for tag in clan_tags}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Clans scannés"):
            tag = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                errors += 1
                logging.error(f"Erreur clan {tag}: {e}")

    logging.info(f"Terminé. Erreurs: {errors}")
    return results


# --- EXCEL SAVE ---

def flatten_player_data(list_of_clan_dicts: list[dict]) -> list[dict]:
    rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for clan in list_of_clan_dicts:
        for tag, info in clan.items():
            rows.append({"timestamp": timestamp, "player_tag": tag, **info})

    return rows


def save_to_excel(list_of_clan_dicts: list[dict], file_name="player_data.xlsx"):
    new = pd.DataFrame(flatten_player_data(list_of_clan_dicts))

    if os.path.exists(file_name):
        old = pd.read_excel(file_name)
        df = pd.concat([old, new], ignore_index=True)
    else:
        df = new

    df.to_excel(file_name, index=False)
    logging.info(f"Sauvegardé: {file_name} (+{len(new)} lignes)")


# --- TEXT FILE TAGS ---

def read_tags_from_txt(path="player_tags.txt") -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def save_tags_to_txt(tags: list[str], path="player_tags.txt"):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(tags))


# --- AUTO INPUT CLASH OF CLANS (pyautogui) ---

def automate_coc_input(text: str):
    def wait(): time.sleep(random.uniform(0.5, 1))

    coords = {
        "chat": (75, 62),#J22YGJ98

        "search_btn": (1438, 91),
        "input_zone": (1450, 200),
        "send_btn": (1100, 570),
        "escape": (5, 5),
        "fill": (1100, 300),
        "invite": (600, 570)
    }

    pyautogui.click(*coords["chat"]); wait()
    pyautogui.click(*coords["search_btn"]); wait()
    pyautogui.click(*coords["input_zone"]); wait()
    pyautogui.click(*coords["fill"]);wait()

    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v"); wait()
    pyautogui.press("enter"); wait()

    pyautogui.click(*coords["invite"]); wait()
    pyautogui.click(*coords["escape"])


# --- VISU TROPHIES ---

def plot_trophies_evolution(file_name="player_data.xlsx", players_to_plot=None):
    if not os.path.exists(file_name):
        logging.error(f"Fichier introuvable: {file_name}")
        return

    df = pd.read_excel(file_name)
    if "name" not in df or "trophies" not in df:
        logging.error("Colonnes nécessaires manquantes.")
        return

    if "timestamp" in df:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        df["timestamp"] = pd.date_range(start="2024", periods=len(df), freq="H")

    df = df.dropna(subset=["timestamp"])

    if players_to_plot:
        df = df[df["name"].isin(players_to_plot)]

    plt.figure(figsize=(10, 5))
    for name, g in df.groupby("name"):
        g = g.sort_values("timestamp")
        plt.plot(g["timestamp"], g["trophies"], label=name)

    plt.title("Évolution des trophées")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# --- WAR INFO ---

def get_last_clan_war_info(clan_tag: str, token: str) -> dict:
    tag_enc = clan_tag.replace("#", "%23")
    r = requests.get(f"{API_URL}/clans/{tag_enc}/currentwar",
                     headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return r.json()
    logging.error(f"Erreur GDC {r.status_code}: {r.text}")
    return {}


def save_clan_war_to_excel(data: dict, filename: str, clan_tag: str):
    if not data or data.get("state") != "warEnded":
        logging.warning("Pas de guerre terminée.")
        return

    clan = data["clan"] if data["clan"].get("tag") == clan_tag else data["opponent"]
    rows = []

    for m in clan.get("members", []):
        attacks = m.get("attacks", [])
        rows.append({
            "Name": m.get("name"),
            "Tag": m.get("tag"),
            "Map Position": m.get("mapPosition"),
            "Townhall Level": m.get("townhallLevel"),
            "Attacks Done": len(attacks),
            "Stars": sum(a.get("stars", 0) for a in attacks),
            "Destruction %": sum(a.get("destructionPercentage", 0) for a in attacks) / max(len(attacks), 1),
            "War End Time": data.get("endTime")
        })

    new = pd.DataFrame(rows)

    if os.path.exists(filename):
        old = pd.read_excel(filename)
        df = pd.concat([old, new], ignore_index=True)
    else:
        df = new

    df.to_excel(filename, index=False)
    logging.info(f"GDC enregistrée dans {filename}")


# --- MAIN FEATURES ---

def invite(different_name=10, nb_of_clan_with_the_same_name=10,
           inviting=True, condition=True, searching_players=True):

    if searching_players:
        clan_tags = []
        for _ in tqdm(range(different_name), desc="Recherche clans"):
            clan_tags.extend(random_clan_search(nb_of_clan_with_the_same_name))

        players = get_all_clan_members_threadpool(
            clan_tags, API_TOKEN, max_workers=DEFAULT_MAX_WORKERS, condition=condition
        )

        tags = list({tag for clan in players for tag in clan})
        save_to_excel(players, file_name="All_Players.xlsx")
        save_tags_to_txt(tags)
        print("ecrit sur txt")

    if inviting:
        tags = read_tags_from_txt()
        logging.info(f"{len(tags)} joueurs à inviter...")

        for tag in tqdm(tags.copy(), desc="Invitations"):
            automate_coc_input(tag)
            tags.remove(tag)
            save_tags_to_txt(tags)


def spy_my_clan(clan_tag="#2R2YVCLJQ"):
    data = get_all_clan_members_threadpool([clan_tag], API_TOKEN, condition=False)
    save_to_excel(data, "EPF_Players.xlsx")

    war = get_last_clan_war_info(clan_tag, API_TOKEN)
    save_clan_war_to_excel(war, "gdc.xlsx", clan_tag)

    plot_trophies_evolution("EPF_Players.xlsx",
                            players_to_plot=["P’tit Lulu", "FrysT"])


# --- EXECUTION ---

if __name__ == "__main__":
    import PlayActions
    PlayActions.attaque_with_all_accounts(0, 10, 0, False, True, False, False)
    invite(1000, 50, inviting=True, condition=True, searching_players=False)

