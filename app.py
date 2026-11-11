import streamlit as st
from google import genai
from google.genai import types

# ---------------------------------------------------------------
# IMPOSTAZIONI (se un giorno il modello non funziona, cambia solo qui)
# ---------------------------------------------------------------
MODELLO = "gemini-flash-latest"

ISTRUZIONI_COMMERCIALE = """
Sei l'Ufficio Commerciale di ForgedValves, azienda che fornisce valvole forgiate
(saracinesca, globo, ritegno, sfera, farfalla) per oil & gas, energia, chimico e navale.
Ricevi la richiesta di un cliente e prepari una BOZZA di risposta in italiano.
Regole:
1. Estrai i dati tecnici: tipo valvola, diametro, rating ASME, estremità, materiale,
   quantità, norme richieste (es. NACE, fire-safe, criogenico), attuatore.
2. Elenca chiaramente i dati MANCANTI da chiedere al cliente.
3. NON inventare mai prezzi, tempi di consegna o conformità: scrivi [DA DEFINIRE].
4. Tono professionale e sintetico.
"""

st.set_page_config(page_title="ForgedValves Gestionale", page_icon="🔧", layout="centered")


# ---------------------------------------------------------------
# PASSWORD: protegge l'app e la tua chiave API
# ---------------------------------------------------------------
def controlla_password():
    if st.session_state.get("autorizzato"):
        return True
    st.title("🔧 ForgedValves")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state["autorizzato"] = True
            st.rerun()
        else:
            st.error("Password errata")
    return False


if not controlla_password():
    st.stop()

# ---------------------------------------------------------------
# SCHERMATA PRINCIPALE
# ---------------------------------------------------------------
st.title("🔧 ForgedValves Gestionale")

tab_comm, tab_vend, tab_pian, tab_qual = st.tabs(
    ["💼 Commerciale", "🧾 Vendite", "📅 Pianificazione", "✅ Qualità"]
)

with tab_comm:
    st.subheader("Agente Commerciale")
    st.caption("Incolla qui la richiesta del cliente (email o RFQ).")
    richiesta = st.text_area(
        "Richiesta cliente",
        height=180,
        placeholder="Es: Buongiorno, ci servono 10 valvole a sfera trunnion 6\" classe 600, "
        "flangiate, in A105, servizio NACE...",
    )
    if st.button("Genera bozza offerta"):
        if not richiesta.strip():
            st.warning("Scrivi prima una richiesta.")
        else:
            with st.spinner("L'agente sta lavorando..."):
                try:
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    risposta = client.models.generate_content(
                        model=MODELLO,
                        contents=richiesta,
                        config=types.GenerateContentConfig(
                            system_instruction=ISTRUZIONI_COMMERCIALE
                        ),
                    )
                    st.success("Bozza pronta (da verificare prima dell'invio)")
                    st.write(risposta.text)
                except Exception as e:
                    st.error(f"Errore: {e}")

with tab_vend:
    st.info("Ufficio Vendite: in arrivo nella tappa 4.")

with tab_pian:
    st.info("Ufficio Pianificazione: in arrivo nella tappa 5.")

with tab_qual:
    st.info("Ufficio Qualità: in arrivo nella tappa 6.")
