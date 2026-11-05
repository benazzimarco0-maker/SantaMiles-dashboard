import streamlit as st
import pandas as pd
import requests

# 🎅 CONFIGURAZIONE PAGINA (Tema Natalizio)
st.set_page_config(
    page_title="Santa Miles 🎅 - Dashboard Iscrizioni", 
    page_icon="🎄", 
    layout="wide"
)

# 🎨 STILE CSS NATALIZIO PERSONALIZZATO
st.markdown("""
    <style>
    .main {
        background-color: #0f172a;
    }
    h1 {
        color: #ef4444 !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    h2, h3 {
        color: #22c55e !important;
    }
    .stMetric {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #ef4444;
    }
    div[data-testid="stMetricValue"] {
        color: #f59e0b !important;
    }
    </style>
""", unsafe_allow_html=True)

# 🎄 INTESTAZIONE SANTA MILES
st.title("🎄 Santa Miles – Dashboard Ufficiale Iscrizioni 🏃‍♂️🎅")
st.markdown("### *“Stai al sicuro durante le feste: corri con noi!”* 🎁")
st.markdown("---")

# ⚙️ SIDEBAR - CONFIGURAZIONE
st.sidebar.header("🎅 Impostazioni Evento")
API_TOKEN = st.sidebar.text_input("🔑 Private Token Eventbrite", type="password")
EVENT_ID = st.sidebar.text_input("🎟️ Event ID (es. 1234567890)")
TARGET_GOAL = st.sidebar.number_input("🎯 Obiettivo Runner", value=300, step=10)

@st.cache_data(ttl=60)  # Aggiorna i dati ogni minuto
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
            prof = a.get('profile', {})
            attendees_list.append({
                "Nome": prof.get('first_name', ''),
                "Cognome": prof.get('last_name', ''),
                "Email": prof.get('email', ''),
                "Percorso": a.get('ticket_class_name', 'Generico'),
                "Data Iscrizione": a.get('created', '')[:10],
                "Stato": a.get('status', '')
            })
        
        pagination = data.get('pagination', {})
        has_more_items = pagination.get('has_more_items', False)
        continuation_token = pagination.get('continuation', None)

    return pd.DataFrame(attendees_list)

# 📊 CONTENUTO PRINCIPALE
if API_TOKEN and EVENT_ID:
    df = load_attendees(API_TOKEN, EVENT_ID)
    
    if df is not None and not df.empty:
        total_iscritti = len(df)
        percentuale = min(int((total_iscritti / TARGET_GOAL) * 100), 100)
        
        # CARD METRICHE NATALIZIE
        col1, col2, col3 = st.columns(3)
        col1.metric("🎁 Totale Babbi Runner", f"{total_iscritti}", delta=f"{total_iscritti - TARGET_GOAL} al Target")
        col2.metric("🎯 Traguardo Iscritti", f"{TARGET_GOAL}")
        col3.metric("✨ Completamento Target", f"{percentuale}%")

        # BARRA DI AVANZAMENTO NATALIZIA
        st.markdown(f"**Progresso verso il Traguardo ({total_iscritti}/{TARGET_GOAL} iscrizioni):**")
        st.progress(percentuale / 100)
        
        if percentuale >= 100:
            st.balloons()
            st.success("🎉 SOLD OUT NATALIZIO RAGGIUNTO! 🎉")

        st.markdown("---")
        
        # GRAFICO E TABELLA
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.subheader("🏃 Ripartizione Percorsi")
            ticket_counts = df['Percorso'].value_counts()
            st.bar_chart(ticket_counts)
            
        with col_right:
            st.subheader("📋 Elenco Babbi Natale Iscritti")
            st.dataframe(
                df[["Nome", "Cognome", "Percorso", "Data Iscrizione"]], 
                use_container_width=True
            )
            
    elif df is not None and df.empty:
        st.warning("❄️ Nessun iscritto trovato al momento per questo Event ID.")
else:
    st.info("👈 Inserisci il tuo Private Token e l'Event ID nella barra a sinistra per accendere la magia di Santa Miles!")

