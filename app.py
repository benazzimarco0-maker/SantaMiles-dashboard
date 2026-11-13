import streamlit as st
import pandas as pd
import requests

# 🎅 INSERISCI QUI I TUOI DATI TRA LE VIRGOLETTE
API_TOKEN = "LKRVUWRS24VKZZ3QUJ7I"
EVENT_ID = "2004062595170"
TARGET_GOAL = 300

# 🎅 CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="Santa Miles 🎅 - Dashboard Iscrizioni", 
    page_icon="🎄", 
    layout="wide"
)

# 🎨 STILE CSS NATALIZIO PERSONALIZZATO
st.markdown("""
    <style>
    .main { background-color: #0f172a; }
    h1 { color: #ef4444 !important; font-family: 'Helvetica Neue', sans-serif; }
    h2, h3 { color: #22c55e !important; }
    .stMetric { background-color: #1e293b; padding: 15px; border-radius: 12px; border: 1px solid #ef4444; }
    div[data-testid="stMetricValue"] { color: #f59e0b !important; }
    </style>
""", unsafe_allow_html=True)

# 🎄 INTESTAZIONE SANTA MILES
st.title("🎄 Santa Miles – Dashboard Ufficiale Iscrizioni 🏃‍♂️🎅")
st.markdown("### *“Stai al sicuro durante le feste: corri con noi!”* 🎁")
st.markdown("---")

@st.cache_data(ttl=60)
def load_attendees(token, event_id):
    if not token or not event_id:
        return None
    
    url = f"https://www.eventbriteapi.com/v3/events/{event_id}/attendees/"
    headers = {"Authorization": f"Bearer {token}"}
    attendees_list = []
    has_more_items = True
    continuation_token = None

    while has_more_items:
        params = {}
        if continuation_token:
            params['continuation'] = continuation_token
            
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            st.error(f"⚠️ Errore di connessione a Eventbrite ({res.status_code}). Controlla Token ed Event ID.")
            return None
        
        data = res.json()
        for a in data.get('attendees', []):
            # 🚫 SALTA BIGLIETTI ANNULLATI O RIMBORSATI
            is_cancelled = a.get('cancelled', False)
            is_refunded = a.get('refunded', False)
            status = str(a.get('status', '')).lower()
            
            if is_cancelled or is_refunded or status not in ['attending', 'checked in']:
                continue

            prof = a.get('profile', {})
            attendees_list.append({
                "Nome": prof.get('first_name', '').strip(),
                "Cognome": prof.get('last_name', '').strip(),
                "Email": prof.get('email', ''),
                "Percorso": a.get('ticket_class_name', 'Generico'),
                "Data Iscrizione": a.get('created', '')[:10],
                "Stato": a.get('status', '')
            })
        
        pagination = data.get('pagination', {})
        has_more_items = pagination.get('has_more_items', False)
        continuation_token = pagination.get('continuation', None)

    df = pd.DataFrame(attendees_list)

    # 🧹 RIMOZIONE DOPPIONI CON PRIORITÀ AL BIGLIETTO PROMO
    if not df.empty:
        # Creiamo colonne temporanee per confrontare nomi e individuare i "promo"
        df['_nome_norm'] = df['Nome'].str.lower().str.strip()
        df['_cognome_norm'] = df['Cognome'].str.lower().str.strip()
        df['_is_promo'] = df['Percorso'].str.lower().str.contains('promo', na=False)
        
        # Ordiniamo mettendo i "promo" (True) in cima rispetto ai normali (False)
        df = df.sort_values(by=['_is_promo', 'Data Iscrizione'], ascending=[False, True])
        
        # Rimuoviamo i duplicati di Nome+Cognome tenendo il primo (quindi il promo se esiste)
        df = df.drop_duplicates(subset=['_nome_norm', '_cognome_norm'], keep='first')
        
        # Ripuliamo le colonne temporanee e riordiniamo per data di iscrizione
        df = df.drop(columns=['_nome_norm', '_cognome_norm', '_is_promo'])
        df = df.sort_values(by='Data Iscrizione', ascending=False).reset_index(drop=True)

    return df

# 📊 CONTENUTO PRINCIPALE
df = load_attendees(API_TOKEN, EVENT_ID)

if df is not None and not df.empty:
    total_iscritti = len(df)
    percentuale = min(int((total_iscritti / TARGET_GOAL) * 100), 100)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🎁 Totale Babbi Runner", f"{total_iscritti}", delta=f"{total_iscritti - TARGET_GOAL} al Target")
    col2.metric("🎯 Traguardo Iscritti", f"{TARGET_GOAL}")
    col3.metric("✨ Completamento Target", f"{percentuale}%")

    st.markdown(f"**Progresso verso il Traguardo ({total_iscritti}/{TARGET_GOAL} iscrizioni):**")
    st.progress(percentuale / 100)
    
    if percentuale >= 100:
        st.balloons()
        st.success("🎉 SOLD OUT NATALIZIO RAGGIUNTO! 🎉")

    st.markdown("---")
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("🏃 Ripartizione Percorsi")
        ticket_counts = df['Percorso'].value_counts()
        st.bar_chart(ticket_counts)
        
    with col_right:
        st.subheader("📋 Elenco Babbi Natale Iscritti")
        st.dataframe(df[["Nome", "Cognome", "Percorso", "Data Iscrizione"]], use_container_width=True)
        
elif df is not None and df.empty:
    st.warning("❄️ Nessun iscritto trovato al momento per questo Event ID.")
