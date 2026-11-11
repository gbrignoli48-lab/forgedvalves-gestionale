import streamlit as st
from google import genai
from google.genai import types
from supabase import create_client

st.set_page_config(page_title="ForgedValves Gestionale", page_icon="🔧", layout="centered")

STATI = ["bozza", "approvata", "inviata", "confermata", "rifiutata"]

ISTRUZIONI_COMMERCIALE = """
Sei l'Ufficio Commerciale di ForgedValves, azienda con sede a Gorla Minore (VA) che
fornisce valvole forgiate (saracinesca, globo, ritegno, sfera, farfalla) per oil & gas,
energia, chimico e navale.
Ricevi la richiesta di un cliente e prepari una BOZZA di risposta in italiano.

Contatti ufficiali (gli UNICI che puoi usare): info@forgedvalves.it - +39 392 178 7273.

Regole:
1. Inizia con una riga "Oggetto:" scritta dal punto di vista di ForgedValves
   (es. "Oggetto: Vs. richiesta di offerta - valvole a sfera e ritegno").
2. Estrai i dati tecnici: tipo valvola, diametro, rating ASME, estremità, materiale,
   quantità, norme richieste (es. NACE, fire-safe, criogenico), attuatore.
3. Elenca chiaramente i dati MANCANTI da chiedere al cliente.
4. NON inventare mai prezzi, tempi di consegna, conformità, indirizzi email, numeri di
   telefono o nomi di persone: se un dato non è noto scrivi [DA DEFINIRE].
5. Tono professionale e sintetico. Firma: Ufficio Commerciale - ForgedValves.
"""


# ---------------------------------------------------------------
# MODELLI GEMINI: l'app chiede a Google quali modelli può usare la tua chiave
# ---------------------------------------------------------------
def elenco_modelli(client):
    candidati = []
    for m in client.models.list():
        nome = m.name.replace("models/", "")
        azioni = getattr(m, "supported_actions", None) or []
        if "generateContent" not in azioni or "flash" not in nome:
            continue
        if any(x in nome for x in ["image", "tts", "audio", "live", "robotics", "embedding", "computer", "omni"]):
            continue
        candidati.append(nome)
    candidati.sort(reverse=True)
    candidati.sort(key=lambda n: (("preview" in n or "exp" in n), ("lite" in n)))
    return candidati


def genera(client, testo, istruzioni):
    ultimo_errore = None
    for nome in elenco_modelli(client)[:5]:
        try:
            r = client.models.generate_content(
                model=nome,
                contents=testo,
                config=types.GenerateContentConfig(system_instruction=istruzioni),
            )
            return r.text, nome
        except Exception as e:
            ultimo_errore = e
    raise ultimo_errore or RuntimeError("Nessun modello disponibile per questa chiave.")


# ---------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------
@st.cache_resource
def db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def numero(o):
    return f"OFF-{o['creato_il'][:4]}-{o['id']:04d}"


# ---------------------------------------------------------------
# PASSWORD
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
    st.caption("Piano gratuito Google: per ora usa solo richieste di prova o dati non sensibili.")

    if "msg" in st.session_state:
        st.success(st.session_state.pop("msg"))

    cliente = st.text_input("Cliente")
    richiesta = st.text_area(
        "Richiesta cliente",
        height=180,
        placeholder='Es: Buongiorno, ci servono 10 valvole a sfera trunnion 6" classe 600, '
        "flangiate, in A105, servizio NACE...",
    )

    if st.button("Genera bozza offerta"):
        if not richiesta.strip():
            st.warning("Scrivi prima una richiesta.")
        else:
            with st.spinner("L'agente sta lavorando..."):
                try:
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    testo, modello = genera(client, richiesta, ISTRUZIONI_COMMERCIALE)
                    st.session_state["n_bozza"] = st.session_state.get("n_bozza", 0) + 1
                    st.session_state["bozza"] = {
                        "cliente": cliente,
                        "richiesta": richiesta,
                        "testo": testo,
                        "modello": modello,
                    }
                except Exception as e:
                    st.error(f"Errore: {e}")

    if "bozza" in st.session_state:
        b = st.session_state["bozza"]
        st.success("Bozza pronta: controllala, correggila se serve, poi salvala.")
        testo_mod = st.text_area(
            "Bozza (modificabile)",
            value=b["testo"],
            height=400,
            key=f"testo_mod_{st.session_state['n_bozza']}",
        )
        st.caption(f"Modello usato: {b['modello']}")
        if st.button("💾 Salva offerta"):
            try:
                db().table("offerte").insert(
                    {
                        "cliente": b["cliente"],
                        "richiesta": b["richiesta"],
                        "bozza": testo_mod,
                        "modello_ai": b["modello"],
                    }
                ).execute()
                del st.session_state["bozza"]
                st.session_state["msg"] = "✅ Offerta salvata."
                st.rerun()
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")

    st.divider()
    st.subheader("Offerte salvate")
    try:
        offerte = db().table("offerte").select("*").order("id", desc=True).limit(20).execute().data
    except Exception as e:
        offerte = []
        st.error(f"Errore database: {e}")

    if not offerte:
        st.caption("Nessuna offerta salvata.")
    for o in offerte:
        titolo = f"{numero(o)} · {o.get('cliente') or 'senza nome'} · {o['stato'].upper()}"
        with st.expander(titolo):
            st.write(o["bozza"])
            nuovo = st.selectbox(
                "Stato", STATI, index=STATI.index(o["stato"]), key=f"stato_{o['id']}"
            )
            if st.button("Aggiorna stato", key=f"agg_{o['id']}"):
                try:
                    db().table("offerte").update({"stato": nuovo}).eq("id", o["id"]).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")

with tab_vend:
    st.info("Ufficio Vendite: in arrivo nella tappa 4.")

with tab_pian:
    st.info("Ufficio Pianificazione: in arrivo nella tappa 5.")

with tab_qual:
    st.info("Ufficio Qualità: in arrivo nella tappa 6.")
