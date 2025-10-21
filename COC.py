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
import PlayActions



pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
sys.stdout.reconfigure(encoding='utf-8')

API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjlkYjU5YWJhLWUzZDctNGUxMS04MWQ3LWYwMGUwODA0NWNlNiIsImlhdCI6MTc1Nzc4NzAyMiwic3ViIjoiZGV2ZWxvcGVyLzUwNzVhOTk1LTI5NWUtNTZiMS0yZTQ2LWY0YmMyNTgxN2QwMyIsInNjb3BlcyI6WyJjbGFzaCJdLCJsaW1pdHMiOlt7InRpZXIiOiJkZXZlbG9wZXIvc2lsdmVyIiwidHlwZSI6InRocm90dGxpbmcifSx7ImNpZHJzIjpbIjkyLjE2Ny45MC4yOSJdLCJ0eXBlIjoiY2xpZW50In1dfQ.oSUcPmTHo5zNmldSvXg3prDANLa_tZfQkHpmtlpKfE3Jnj1sp_cQ86nnJWeTDqgO7R8nByPBy0XolP7GyfuYng"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json"
}

ZONE_PSEUDO = (91, 21, 350, 36)
ZONE_CLAN = (91, 57, 250, 36)


def clean_string(s):
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    return s.strip()


def safe_get(url, headers, params=None):
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Erreur réseau/API : {e}\n")
        time.sleep(2)
        return None


def search_clans(name: str, limit: int, locationId: bool = True) -> list:
    url = "https://api.clashofclans.com/v1/clans"
    params = {"name": name, "limit": limit}

    if locationId:
        params["locationId"] = 32000087  # France
    response = safe_get(url, HEADERS, params)

    return [clan['tag'] for clan in response.json().get("items", [])] if response else []


def random_clan_search(limit: int) -> list:
    prefix = ''.join(random.choices(string.ascii_uppercase, k=3))
    print(f"Recherche avec prefix aléatoire : {prefix}")
    return search_clans(prefix, limit)


def get_clan_members(clan_tag, token, condition=True):

    CLAN_TAG = clan_tag.replace('#', '%23')
    url = f"https://api.clashofclans.com/v1/clans/{CLAN_TAG}/members"

    headers = {
        "Authorization": f"Bearer {token}"
    }

    player_info_dict = {}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        members = data.get("items", [])

        for member in members:
            tag = member['tag']

            rank = member.get('league', {}).get('name', 'Unranked')
            trophies = member.get('trophies', 0)
            player_info = {}

            if 2000 <= trophies <= 4300 and rank != 'Unranked' and int(member.get('townHallLevel', 'N/A')) >= 12 and (member['donations'] > 0 or member['donationsReceived'] > 0) and condition:
                player_info = {
                    "name": member['name'],
                    "role": member['role'],
                    "expLevel": member['expLevel'],
                    "townHallLevel": member.get('townHallLevel', 'N/A'),
                    "trophies": trophies,
                    "donations": member['donations'],
                    "donationsReceived": member['donationsReceived']
                }
                player_info_dict[tag] = player_info
            if not condition:
                player_info = {
                    "name": member['name'],
                    "role": member['role'],
                    "expLevel": member['expLevel'],
                    "townHallLevel": member.get('townHallLevel', 'N/A'),
                    "trophies": trophies,
                    "donations": member['donations'],
                    "donationsReceived": member['donationsReceived']
                }
                player_info_dict[tag] = player_info
    else:
        raise Exception("")
        #print(f"Erreur ici {response.status_code}: {response.text}")

    return player_info_dict


def get_all_clan_members_threadpool(clan_tags, token, max_workers=50, condition=True):
    results = []
    total_clans = len(clan_tags)
    successful_clans = 0
    failed_clans = 0

    print(f"Début de la collecte des membres pour {total_clans} clans...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_clan_members, tag, token, condition): tag for tag in clan_tags}

        for future in as_completed(futures):
            clan_tag = futures[future]
            try:
                result = future.result()
                results.append(result)

                # Update success counter
                successful_clans += 1
                # Print progress on the same line
                print(f"Progression: {successful_clans + failed_clans}/{total_clans} clans traités | Réussis: {successful_clans} | Échoués: {failed_clans}", end="\r", flush=True)

            except Exception as e:
                # Update failed counter
                failed_clans += 1
                print(f"\nErreur avec le clan {clan_tag}: {e}")
                print(f"Progression: {successful_clans + failed_clans}/{total_clans} clans traités | Réussis: {successful_clans} | Échoués: {failed_clans}", end="\r", flush=True)

    # Final summary with newline
    print(f"\nCollecte terminée! Clans réussis: {successful_clans} | Clans échoués: {failed_clans}")
    return results


def plot_trophies_evolution(file_name="player_data.xlsx", players_to_plot=None):

    if not os.path.exists(file_name):
        print(f"⛔ Fichier '{file_name}' introuvable.")
        return

    df = pd.read_excel(file_name)

    if "name" not in df.columns or "trophies" not in df.columns:
        print("⛔ Le fichier doit contenir les colonnes 'name' et 'trophies'.")
        return

    # Convertir timestamp si présent, sinon créer une colonne avec des valeurs séquentielles
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        df["timestamp"] = pd.date_range(start="2024-01-01", periods=len(df), freq="H")

    df = df.dropna(subset=["timestamp"])

    # Filtrage optionnel
    if players_to_plot is not None:
        df = df[df["name"].isin(players_to_plot)]

    # Tracer
    plt.figure(figsize=(10, 5))
    for name, group in df.groupby("name"):
        group = group.sort_values("timestamp")
        plt.plot(group["timestamp"], group["trophies"], marker="o", label=name)

    plt.title("Évolution des trophées")
    plt.xlabel("Temps")
    plt.ylabel("Trophées")
    plt.legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
    plt.tight_layout()
    plt.grid(True)
    plt.show()


def get_last_clan_war_info(clan_tag: str, api_token: str) -> dict:

    encoded_tag = clan_tag.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur {response.status_code} : {response.text}")
        return {}


def save_clan_war_to_excel(data: dict, filename: str, clan_tag: str):

    if not data or data.get('state') != 'warEnded':
        print("⛔ Aucune guerre terminée à enregistrer.")
        return

    clan = data.get("clan", {})
    if clan.get("tag") != clan_tag:
        # Cela arrive si le clan est en défense dans la guerre
        clan = data.get("opponent", {})

    members = clan.get("members", [])
    rows = []
    for m in members:
        row = {
            "Name": m.get("name"),
            "Tag": m.get("tag"),
            "Map Position": m.get("mapPosition"),
            "Townhall Level": m.get("townhallLevel"),
            "Attacks Done": len(m.get("attacks", [])),
            "Stars": sum(a.get("stars", 0) for a in m.get("attacks", [])),
            "Destruction %": sum(a.get("destructionPercentage", 0) for a in m.get("attacks", [])) / max(len(m.get("attacks", [])), 1),
            "War End Time": data.get("endTime")
        }
        rows.append(row)

    new_df = pd.DataFrame(rows)

    if os.path.exists(filename):
        try:
            old_df = pd.read_excel(filename)
            combined_df = pd.concat([old_df, new_df], ignore_index=True)
        except Exception as e:
            print(f"Erreur lors de la lecture de l'ancien fichier : {e}")
            combined_df = new_df
    else:
        combined_df = new_df

    combined_df.to_excel(filename, index=False)
    print(f"✅ Données mises à jour dans '{filename}'")


def flatten_player_data(dict_list: list[dict]) -> list[dict]:
    rows = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for clan in dict_list:
        for tag, info in clan.items():
            row = {"timestamp": timestamp, "player_tag": tag, **info}
            rows.append(row)
    return rows


def save_to_excel(dict_list: list[dict], file_name="player_data.xlsx"):
    new_data = flatten_player_data(dict_list)
    new_df = pd.DataFrame(new_data)

    if os.path.exists(file_name):
        existing_df = pd.read_excel(file_name)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_excel(file_name, index=False)
    print(f"\n✅ Données sauvegardées dans '{file_name}' ({len(new_data)} nouvelles lignes)")


def read_tags_from_txt(filepath="player_tags.txt"):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def save_tags_to_txt(tags, filepath="player_tags.txt"):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(tags))


def automate_coc_input(text_to_paste: str):
    def wait(): time.sleep(random.uniform(0.5, 1))
    coords = [(75, 62), (1438, 91), (1450, 200), (836, 306), (700, 570), (1, 1)]

    for x, y in coords[:4]:
        pyautogui.click(x=x, y=y)
        wait()

    pyperclip.copy(text_to_paste)
    pyautogui.hotkey('ctrl', 'v')
    wait()
    pyautogui.press('enter')
    wait()
    pyautogui.click(x=coords[4][0], y=coords[4][1])
    pyautogui.click(x=coords[5][0], y=coords[5][1])


# --- MAIN ---

def invite(different_name=10, nb_of_clan_with_the_same_name=10, inviting=True, condition=True, searching_players=True):
    if searching_players:
        l_clans = []
        for _ in tqdm(range(different_name), desc="Recherche de clans"):
            l_clans.extend(random_clan_search(nb_of_clan_with_the_same_name))

        l_player_data = get_all_clan_members_threadpool(l_clans, API_TOKEN, condition=condition)
        player_tags = list({tag for d in l_player_data for tag in d.keys()})
        save_to_excel(l_player_data, file_name="All_Players.xlsx")

        save_tags_to_txt(player_tags)

    if inviting:
        tags_file = Path("player_tags.txt")
        tags = read_tags_from_txt(tags_file)
        print(f"\n{len(tags)} joueur(s) à inviter ...")
        processed = 0
        for tag in tqdm(tags.copy(), desc="Invitation auto"):
            automate_coc_input(tag)
            tags.remove(tag)
            processed += 1

            if processed % 10 == 0 or len(tags) == 0:
                save_tags_to_txt(tags, tags_file)


def spy_my_clan(clan_tag='#2R2YVCLJQ'):
    l_player_data_my_clan = get_all_clan_members_threadpool([clan_tag], API_TOKEN, condition=False)
    epf_player_tags = list({tag for d in l_player_data_my_clan for tag in d.keys()})
    save_to_excel(l_player_data_my_clan, file_name="EPF_Players.xlsx")

    save_clan_war_to_excel(get_last_clan_war_info(clan_tag, API_TOKEN), "gdc.xlsx", clan_tag)
    plot_trophies_evolution("EPF_Players.xlsx", players_to_plot=["P’tit Lulu", "shamim™", "FrysT"])


PlayActions.attaque_with_all_accounts(defaites=0, attaques=20, attaques_night=0, allow_tilu=False, allow_ptitlulu=True, allow_lucas=False, allow_citeor=False)
PlayActions.LecteurPosition(fichier_entree="switchptitlulu.json").rejouer()
time.sleep(3)
PlayActions.LecteurPosition(fichier_entree="cliclefttop.json").rejouer()

invite(500, 50, inviting=True, condition=True, searching_players=False)
#spy_my_clan()