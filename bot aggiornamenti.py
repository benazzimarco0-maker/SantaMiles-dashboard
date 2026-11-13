import json
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd

# 🎅 CONFIGURAZIONE EVENTBRITE
EVENTBRITE_TOKEN = "LKRVUWRS24VKZZ3QUJ7I"
EVENT_ID = "2004062595170"

# 🤖 CONFIGURAZIONE TELEGRAM
TELEGRAM_TOKEN = "9046510007:AAE6cRiUkYbqzVO1BUq2uIlJR7tb4ej7iJA"
TELEGRAM_CHAT_ID = "-1004476875405"

FILE_MEMORIA = "iscritti_notificati.json"

# 🔄 SESSIONE HTTP CON RETRY AUTOMATICI
session = requests.Session()
retry_strategy = Retry(
    total=5,
    backoff_factor=1,                           # Attende 1s, 2s, 4s, 8s... tra i tentativi
    status_forcelist=[429, 500, 502, 503, 504], # Riprova su rate-limit ed errori temporanei
    allowed_methods=["GET", "POST"]             # Abilita retry sia su Eventbrite (GET) che Telegram (POST)
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)


def invia_telegram(nome, cognome):
    testo = f"🎅 <b>{nome} {cognome}</b> parteciperà alla Santa Miles!"
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": testo,
        "parse_mode": "HTML"
    }
    try:
        res = session.post(url, json=payload, timeout=15)
        if res.status_code == 200:
            print(f"✅ Inviato: {nome} {cognome}")
            time.sleep(0.15)  # Piccola pausa per evitare blocchi da invii troppo ravvicinati
            return True
        else:
            print(f"❌ Errore Telegram ({res.status_code}): {res.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore di rete durante l'invio a {nome} {cognome}: {e}")
        return False


def carica_memoria():
    if os.path.exists(FILE_MEMORIA):
        with open(FILE_MEMORIA, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def salva_memoria(memoria_set):
    with open(FILE_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(list(memoria_set), f, indent=2)


def scarica_iscritti_puliti():
    url = f"https://www.eventbriteapi.com/v3/events/{EVENT_ID}/attendees/"
    headers = {"Authorization": f"Bearer {EVENTBRITE_TOKEN}"}
    attendees_list = []
    has_more_items = True
    continuation_token = None

    while has_more_items:
        params = {'continuation': continuation_token} if continuation_token else {}
        try:
            res = session.get(url, headers=headers, params=params, timeout=15)
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Errore di connessione Eventbrite: {e}")
            return pd.DataFrame()

        if res.status_code != 200:
            print(f"⚠️ Errore Eventbrite ({res.status_code})")
            return pd.DataFrame()

        data = res.json()
        for a in data.get('attendees', []):
            is_cancelled = a.get('cancelled', False)
            is_refunded = a.get('refunded', False)
            status = str(a.get('status', '')).lower()

            if is_cancelled or is_refunded or status not in ['attending', 'checked in']:
                continue

            prof = a.get('profile', {})
            created_full = a.get('created', '')
            attendees_list.append({
                "Nome": prof.get('first_name', '').strip(),
                "Cognome": prof.get('last_name', '').strip(),
                "Email": prof.get('email', '').strip(),
                "Percorso": a.get('ticket_class_name', 'Generico'),
                "_timestamp": created_full
            })

        pagination = data.get('pagination', {})
        has_more_items = pagination.get('has_more_items', False)
        continuation_token = pagination.get('continuation', None)

    df = pd.DataFrame(attendees_list)

    if not df.empty:
        df['_nome_norm'] = df['Nome'].str.lower().str.strip()
        df['_cognome_norm'] = df['Cognome'].str.lower().str.strip()
        df['_email_norm'] = df['Email'].str.lower().str.strip()
        df['_is_promo'] = df['Percorso'].str.lower().str.contains('promo', na=False)

        df = df.sort_values(by=['_is_promo', '_timestamp'], ascending=[False, True])
        df = df.drop_duplicates(subset=['_nome_norm', '_cognome_norm', '_email_norm'], keep='first')
        df = df.sort_values(by='_timestamp', ascending=True).reset_index(drop=True)

    return df


if __name__ == "__main__":
    notificati = carica_memoria()
    df = scarica_iscritti_puliti()

    if not df.empty:
        # Al primissimo avvio memorizza tutti tranne l'ultimo, così invia 1 messaggio di test
        if not notificati:
            for _, row in df.iloc[:-1].iterrows():
                chiave = f"{row['_nome_norm']}|{row['_cognome_norm']}|{row['_email_norm']}"
                notificati.add(chiave)

        for _, row in df.iterrows():
            chiave = f"{row['_nome_norm']}|{row['_cognome_norm']}|{row['_email_norm']}"
            if chiave not in notificati:
                if invia_telegram(row['Nome'], row['Cognome']):
                    notificati.add(chiave)
                    salva_memoria(notificati)  # Salva subito dopo ogni invio riuscito
