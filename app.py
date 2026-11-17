# -*- coding: utf-8 -*-
"""
SOSTITUZIONI DOCENTI - Plesso Vittorini
Web app Streamlit con eventi flessibili per classi/anni, tracciamento completo
delle ore dei docenti assenti e priorità entrata/uscita.
"""

import hmac
import os
from pathlib import Path

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# CONFIGURAZIONE
# ----------------------------------------------------------------------------
APP_PASSWORD = "vittorini2026"
CSV_FILE = Path(__file__).parent / "orario_plesso.csv"

# Classi del plesso (giurisdizione della referente)
PLESSO = {
    "1A", "1B", "1L", "1MST",
    "2A", "2L", "2M",
    "3A", "3L", "3M",
    "4A", "4B", "4LL", "4LM",
    "5A", "5M",
}

GIORNI = {
    "LUN": ("Lunedì", "Lun"),
    "MAR": ("Martedì", "Mar"),
    "MER": ("Mercoledì", "Mer"),
    "GIO": ("Giovedì", "Gio"),
    "VEN": ("Venerdì", "Ven"),
}
ORE = list(range(1, 8))  # 1ª - 7ª ora

TOKEN_DISP = {"DISP.", "DISP", "D"}
TOKEN_RICEV = {"RICEV.", "RICEV"}

# Cognomi dei docenti le cui ore buche sono sempre utilizzabili per supplenze
# (purché non adiacenti a classi fuori dal plesso)
DOCENTI_BUCHE_ATTIVE = {"SCAVO", "INNOCENTI"}

ORDINALI_MIN = {
    1: "prima",
    2: "seconda",
    3: "terza",
    4: "quarta",
    5: "quinta",
    6: "sesta",
    7: "settima",
}


# ----------------------------------------------------------------------------
# ESTETICA E TEMA CHIARO / SCURO
# ----------------------------------------------------------------------------
def applica_stile(dark_mode: bool) -> None:
    if dark_mode:
        bg_app = "#0f172a"
        bg_card = "#1e293b"
        bg_input = "#1e293b"
        border_col = "#334155"
        text_main = "#f1f5f9"
        text_muted = "#94a3b8"
        code_bg = "#1e293b"
        code_text = "#f8fafc"
        alt_title = "#60a5fa"
        sec_btn_bg = "#1e293b"
        sec_btn_text = "#f1f5f9"
    else:
        bg_app = "#f4f6f9"
        bg_card = "#ffffff"
        bg_input = "#ffffff"
        border_col = "#cbd5e1"
        text_main = "#1e293b"
        text_muted = "#64748b"
        code_bg = "#ffffff"
        code_text = "#0f172a"
        alt_title = "#1e3a8a"
        sec_btn_bg = "#ffffff"
        sec_btn_text = "#1e293b"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {bg_app} !important;
            color: {text_main} !important;
        }}
        .block-container {{
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 720px;
        }}

        /* Testi ed etichette */
        h1, h2, h3, h4, p, span, label, [data-testid="stWidgetLabel"] p {{
            color: {text_main} !important;
        }}
        .stCaption, small {{
            color: {text_muted} !important;
        }}

        /* Input e Multiselect */
        [data-baseweb="select"] > div,
        [data-baseweb="input"] > div,
        input {{
            background-color: {bg_input} !important;
            color: {text_main} !important;
            border-color: {border_col} !important;
        }}
        [data-baseweb="select"] span,
        [data-baseweb="select"] div {{
            color: {text_main} !important;
        }}

        /* Header istituzionale */
        .header-card {{
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
            padding: 1.35rem 1.6rem;
            border-radius: 16px;
            margin-bottom: 1.2rem;
            box-shadow: 0 4px 14px rgba(30, 58, 138, 0.22);
        }}
        .header-card h1 {{
            margin: 0;
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #ffffff !important;
        }}
        .header-card p {{
            margin: 0.25rem 0 0 0;
            font-size: 0.9rem;
            color: #dbeafe !important;
        }}

        /* Pulsanti giorni */
        button[kind="primary"] {{
            background-color: #1e3a8a !important;
            color: #ffffff !important;
            border: 2px solid #1e3a8a !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            padding: 0.55rem 0.2rem !important;
        }}
        button[kind="primary"] p {{
            color: #ffffff !important;
        }}
        button[kind="secondary"] {{
            background-color: {sec_btn_bg} !important;
            color: {sec_btn_text} !important;
            border: 1.5px solid {border_col} !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 0.55rem 0.2rem !important;
        }}
        button[kind="secondary"]:hover {{
            border-color: #2563eb !important;
        }}

        /* Card dei docenti assenti / sezioni */
        [data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {bg_card} !important;
            border: 1px solid {border_col} !important;
            border-radius: 12px !important;
            padding: 0.4rem 0.6rem;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
            margin-bottom: 0.6rem;
        }}

        /* Riquadro Bollettino WhatsApp */
        [data-testid="stCode"] {{
            background-color: {code_bg} !important;
            border: 1.5px solid {border_col} !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
        }}
        [data-testid="stCode"] pre {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            font-size: 0.98rem !important;
            line-height: 1.55 !important;
            color: {code_text} !important;
            background-color: {code_bg} !important;
            padding: 1rem !important;
        }}

        /* Card alternative ora per ora */
        .ora-card {{
            background-color: {bg_card};
            border: 1px solid {border_col};
            border-left: 4px solid #2563eb;
            border-radius: 12px;
            padding: 0.9rem 1.1rem;
            margin-bottom: 0.75rem;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05);
        }}
        .ora-card h4 {{
            margin: 0 0 0.45rem 0;
            font-size: 1rem;
            color: {alt_title} !important;
        }}
        .ora-card ul {{
            margin: 0;
            padding-left: 1.2rem;
            font-size: 0.92rem;
            line-height: 1.55;
        }}

        /* Badge esito e avviso giorno mancante */
        .badge-ok {{
            background-color: #dcfce7;
            color: #166534 !important;
            padding: 0.8rem 1rem;
            border-radius: 12px;
            border-left: 4px solid #16a34a;
            font-weight: 500;
            margin: 0.8rem 0;
        }}
        .badge-warn {{
            background-color: #fee2e2;
            color: #991b1b !important;
            padding: 0.85rem 1rem;
            border-radius: 12px;
            border: 1px solid #fca5a5;
            border-left: 5px solid #dc2626;
            font-weight: 600;
            margin: 0.7rem 0 1rem 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# SICUREZZA
# ----------------------------------------------------------------------------
def password_attesa() -> str:
    try:
        return str(st.secrets["APP_PASSWORD"])
    except Exception:
        return os.environ.get("APP_PASSWORD", APP_PASSWORD)


def controlla_accesso() -> None:
    if st.session_state.get("autenticato"):
        return
    st.markdown(
        """
        <div class="header-card">
            <h1>🔒 Accesso Riservato</h1>
            <p>Gestione Sostituzioni Docenti • Plesso Vittorini</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login"):
        pwd = st.text_input("Inserisci la password di accesso", type="password")
        invia = st.form_submit_button("Entra", type="primary", use_container_width=True)
    if invia:
        if hmac.compare_digest(pwd.encode("utf-8"), password_attesa().encode("utf-8")):
            st.session_state["autenticato"] = True
            st.rerun()
        else:
            st.error("Password non corretta.")
    st.stop()


# ----------------------------------------------------------------------------
# CARICAMENTO DATI
# ----------------------------------------------------------------------------
@st.cache_data
def carica_dati() -> pd.DataFrame:
    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"File '{CSV_FILE.name}' non trovato nella cartella dell'app."
        )

    raw_text = ""
    used_enc = "utf-8-sig"
    for enc in ("utf-8-sig", "latin-1"):
        try:
            raw_text = CSV_FILE.read_text(encoding=enc)
            used_enc = enc
            break
        except UnicodeDecodeError:
            continue

    prima_riga = raw_text.splitlines()[0] if raw_text else ""
    separatore = ";" if prima_riga.count(";") >= prima_riga.count(",") else ","

    df = pd.read_csv(
        CSV_FILE,
        sep=separatore,
        dtype=str,
        keep_default_na=False,
        encoding=used_enc,
        on_bad_lines="skip",
    )
    df.columns = df.columns.str.strip()
    return df


def classifica(raw) -> tuple:
    v = str(raw).strip().upper()
    if v in ("", "NAN"):
        return ("vuoto", "")
    if v in TOKEN_DISP:
        return ("disp", "")
    if v in TOKEN_RICEV:
        return ("ricev", "")
    return ("classe", v)


def costruisci_orario(df: pd.DataFrame) -> dict:
    orario = {}
    for _, r in df.iterrows():
        nome = str(r.get("Docente", "")).strip()
        if not nome:
            continue
        orario[nome] = {
            abbr: [None] + [classifica(r.get(f"{abbr}_{h}", "")) for h in ORE]
            for (_, abbr) in GIORNI.values()
        }
    return orario


def is_docente_buca_attiva(doc: str) -> bool:
    doc_upper = doc.upper()
    return any(cognome in doc_upper for cognome in DOCENTI_BUCHE_ATTIVE)


# ----------------------------------------------------------------------------
# MOTORE DELLE SOSTITUZIONI
# ----------------------------------------------------------------------------
def calcola(
    orario: dict,
    giorno: str,
    assenze: dict,
    ore_escluse_classe: dict,
) -> tuple[pd.DataFrame, dict]:
    """
    ore_escluse_classe: {classe: set(ore in cui la classe non fa lezione per assemblea/attività extra)}
    """
    g = giorno

    def cella(doc, h):
        return orario[doc][g][h] if 1 <= h <= 7 else ("vuoto", "")

    def is_classe_esclusa(cls, h):
        return h in ore_escluse_classe.get(cls, set())

    def esterna(doc, h):
        k, v = cella(doc, h)
        return k == "classe" and v not in PLESSO

    def interna(doc, h):
        k, v = cella(doc, h)
        return k == "classe" and v in PLESSO and not is_classe_esclusa(v, h)

    def valida(doc, h):
        return not esterna(doc, h - 1) and not esterna(doc, h + 1)

    def presente_prima(doc, h):
        return any(cella(doc, x)[0] != "vuoto" for x in range(1, h))

    # Mappa orario giornaliero effettivo delle classi del plesso
    classi_ore = {}
    for doc in orario:
        for h in ORE:
            k, v = cella(doc, h)
            if k == "classe" and v in PLESSO and not is_classe_esclusa(v, h):
                classi_ore.setdefault(v, {}).setdefault(h, []).append(doc)

    classi_docente = {
        doc: {
            v
            for (_, gg) in GIORNI.values()
            for (k, v) in orario[doc][gg][1:]
            if k == "classe"
        }
        for doc in orario
    }

    # Individua:
    # 1. Ore da coprire (mancanti)
    # 2. Compresenze
    # 3. Ore in cui il docente assente aveva una classe del plesso impegnata in attività extra/assemblea
    mancanti = {}
    compres = {}
    extra_att = {}  # (cls, h) -> [docenti_assenti]

    for doc, ore_ass in assenze.items():
        for h in ore_ass:
            k, cls = cella(doc, h)
            if k != "classe" or cls not in PLESSO:
                continue
            if is_classe_esclusa(cls, h):
                extra_att.setdefault((cls, h), []).append(doc)
                continue
            altri = [
                d
                for d in classi_ore.get(cls, {}).get(h, [])
                if d != doc and not (d in assenze and h in assenze[d])
            ]
            if altri:
                compres[(cls, h)] = altri
            else:
                mancanti.setdefault(cls, {}).setdefault(h, []).append(doc)

    busy = set()
    ris = {}
    da_C = []

    def risorse_ora(t, cls_target=None):
        """
        Restituisce le risorse valide all'ora t:
        0: Disp. valida nel plesso
        1: Ora buca ('vuoto') per Scavo / Innocenti se non adiacente a classi fuori plesso
        2: Classe in assemblea/attività extra (docente nel plesso libero da lezione)
        3: Ricev. valido nel plesso
        """
        out = []
        for doc in orario:
            if doc in assenze or (doc, t) in busy:
                continue
            k, v = cella(doc, t)

            if k == "disp" and valida(doc, t):
                tipo_ris = "Disp."
                cat = 0
            elif k == "vuoto" and is_docente_buca_attiva(doc) and valida(doc, t):
                tipo_ris = "Buca valida"
                cat = 1
            elif k == "classe" and v in PLESSO and is_classe_esclusa(v, t) and valida(doc, t):
                tipo_ris = f"Libero ({v} in attività extra/assente)"
                cat = 2
            elif k == "ricev" and valida(doc, t):
                tipo_ris = "Ricev."
                cat = 3
            else:
                continue

            stessa = (cls_target in classi_docente[doc]) if cls_target else False
            adiac = interna(doc, t - 1) or interna(doc, t + 1)
            sub = 0 if stessa else (1 if adiac else 2)

            if stessa:
                dettaglio = f"{tipo_ris} • già docente in {cls_target}"
            elif adiac:
                dettaglio = f"{tipo_ris} • ora adiacente nel plesso"
            else:
                dettaglio = tipo_ris

            out.append(((cat, sub, doc), doc, dettaglio))

        out.sort(key=lambda x: x[0])
        return [(d, det) for _, d, det in out]

    def cerca_anticipo(cls, t, src):
        for doc in classi_ore[cls].get(src, []):
            if doc in assenze or (doc, t) in busy:
                continue
            k, v = cella(doc, t)
            libero_per_extra = (k == "classe" and v in PLESSO and is_classe_esclusa(v, t))
            if k not in ("vuoto", "disp") and not libero_per_extra:
                continue
            if not valida(doc, t):
                continue
            if k == "vuoto" and not presente_prima(doc, t):
                continue
            return doc
        return None

    # ---- PRIORITÀ 1 e 2: ENTRATA POSTICIPATA / USCITA ANTICIPATA ------------
    # (Sempre preferite rispetto a sostituzioni a 4ª, 5ª ora o ore intermedie)
    for cls in sorted(mancanti):
        hrs = sorted(classi_ore.get(cls, {}))
        todo = set(mancanti[cls])
        ha_tagliato_ingresso = False
        ha_tagliato_uscita = False

        if not hrs:
            continue

        if all(h in todo for h in hrs):
            da_C.extend((cls, h) for h in sorted(todo))
            continue

        # 1. Regola A: Entrata posticipata diretta (prima ora effettiva della classe)
        prima_ora_classe = hrs[0]
        if prima_ora_classe in todo and len(hrs) > 1:
            ris[(cls, prima_ora_classe)] = ("ENTRATA_POST", "", None)
            todo.remove(prima_ora_classe)
            hrs.remove(prima_ora_classe)
            ha_tagliato_ingresso = True

        # 2. Regola A: Uscita anticipata diretta (ultima ora effettiva della classe)
        ultima_ora_classe = hrs[-1]
        if ultima_ora_classe in todo and len(hrs) > 1:
            ris[(cls, ultima_ora_classe)] = ("USCITA_ANT", "", None)
            todo.remove(ultima_ora_classe)
            hrs.remove(ultima_ora_classe)
            ha_tagliato_uscita = True

        # 3. Regola B: Anticipo dell'ultima ora (per uscita anticipata) o posticipo della prima
        # (Preferito rispetto a mettere un sostituto a 4ª o 5ª ora!)
        for t in sorted(list(todo)):
            trovato = None
            if not ha_tagliato_uscita and len(hrs) > 1:
                src = hrs[-1]
                doc = cerca_anticipo(cls, t, src)
                if doc:
                    trovato = (doc, src, "ultima")

            if not trovato and not ha_tagliato_ingresso and len(hrs) > 1:
                src = hrs[0]
                doc = cerca_anticipo(cls, t, src)
                if doc:
                    trovato = (doc, src, "prima")

            if trovato:
                doc, src, tipo = trovato
                if tipo == "ultima":
                    ris[(cls, t)] = ("ANTICIPO", doc, src)
                    ha_tagliato_uscita = True
                else:
                    ris[(cls, t)] = ("POSTICIPO", doc, src)
                    ha_tagliato_ingresso = True
                busy.add((doc, t))
                hrs.remove(src)
                todo.remove(t)

        # Solo le ore che non possono portare a uscita anticipata / entrata posticipata
        # passano alla Regola C (sostituzione classica)
        da_C.extend((cls, h) for h in sorted(todo))

    # ---- PRIORITÀ 3 (Regola C): Sostituzione con risorse valide ------------
    for cls, t in sorted(da_C, key=lambda x: (x[1], x[0])):
        cands = risorse_ora(t, cls)
        if cands:
            doc, _ = cands[0]
            busy.add((doc, t))
            ris[(cls, t)] = ("SOSTITUTO", doc, None)
        else:
            ris[(cls, t)] = ("SCOPERTO", "", None)

    # ---- Compresenze --------------------------------------------------------
    for (cls, h), altri in compres.items():
        ris[(cls, h)] = ("COMPRESENZA", ", ".join(altri), None)

    # ---- Classi in attività extra / assemblea -------------------------------
    for (cls, h), _ in extra_att.items():
        ris[(cls, h)] = ("ATTIVITA_EXTRA", "", None)

    # ---- Alternative disponibili ORA PER ORA (solo sulle ore con sostituzione)
    ore_sostituzione = sorted(
        {h for (_, h), (tipo, _, _) in ris.items() if tipo in ("SOSTITUTO", "SCOPERTO", "ANTICIPO", "POSTICIPO")}
    )
    alternative_per_ora = {}

    for h in ore_sostituzione:
        valide_rimaste = risorse_ora(h)

        buche_interne = []
        for doc in sorted(orario):
            if doc in assenze or (doc, h) in busy or is_docente_buca_attiva(doc):
                continue
            k, _ = cella(doc, h)
            if k != "vuoto":
                continue
            prima = [cella(doc, x) for x in range(h - 1, 0, -1) if cella(doc, x)[0] != "vuoto"]
            dopo = [cella(doc, x) for x in range(h + 1, 8) if cella(doc, x)[0] != "vuoto"]
            if prima and dopo:
                k_p, v_p = prima[0]
                k_d, v_d = dopo[0]
                if k_p == "classe" and v_p in PLESSO and k_d == "classe" and v_d in PLESSO:
                    buche_interne.append(f"{doc} (buca tra {v_p} e {v_d})")

        alternative_per_ora[h] = {
            "valide": [f"{d} ({det})" for d, det in valide_rimaste],
            "buche_plesso": buche_interne,
        }

    # ---- Costruzione DataFrame di servizio ----------------------------------
    assenti_per_riga = {}
    for cls, d in mancanti.items():
        for h, nomi in d.items():
            assenti_per_riga[(cls, h)] = nomi
    for (cls, h) in compres:
        assenti_per_riga[(cls, h)] = [
            d for d in assenze if h in assenze[d] and cella(d, h) == ("classe", cls)
        ]
    for (cls, h), nomi in extra_att.items():
        assenti_per_riga[(cls, h)] = nomi

    righe = []
    for (cls, h) in sorted(ris, key=lambda x: (x[1], x[0])):
        tipo, doc_coinv, ora_orig = ris[(cls, h)]
        righe.append(
            {
                "Ora": h,
                "Classe": cls,
                "Assenti": assenti_per_riga[(cls, h)],
                "Tipo": tipo,
                "DocCoinv": doc_coinv,
                "OraOrig": ora_orig,
            }
        )

    return pd.DataFrame(righe), alternative_per_ora


# ----------------------------------------------------------------------------
# FORMATTAZIONE BOLLETTINO TASCABILE (TUTTE LE ORE DEL DOCENTE ASSENTE)
# ----------------------------------------------------------------------------
def genera_bollettino(nome_giorno: str, df: pd.DataFrame, ordine_assenti: list) -> str:
    blocchi = [f"SOSTITUZIONI {nome_giorno.upper()}"]

    for doc in ordine_assenti:
        righe_doc = df[df["Assenti"].apply(lambda a: doc in a)]
        if righe_doc.empty:
            continue

        righe_testo = [f"\nManca {doc}"]
        for _, r in righe_doc.sort_values(["Ora", "Classe"]).iterrows():
            ora_txt = ORDINALI_MIN[r["Ora"]]
            cls = r["Classe"]
            tipo = r["Tipo"]
            sost = r["DocCoinv"]
            ora_orig = r["OraOrig"]

            if tipo == "ENTRATA_POST":
                righe_testo.append(f"A {ora_txt} ora entrata posticipata in {cls}")
            elif tipo == "USCITA_ANT":
                righe_testo.append(f"A {ora_txt} ora uscita anticipata in {cls}")
            elif tipo == "ANTICIPO":
                righe_testo.append(
                    f"A {ora_txt} ora anticipa {sost} (dalla {ora_orig}ª) in {cls} -> uscita anticipata"
                )
            elif tipo == "POSTICIPO":
                righe_testo.append(
                    f"A {ora_txt} ora posticipa {sost} (dalla {ora_orig}ª) in {cls} -> entrata posticipata"
                )
            elif tipo == "SOSTITUTO":
                righe_testo.append(f"A {ora_txt} ora sostituisce {sost} in {cls}")
            elif tipo == "COMPRESENZA":
                righe_testo.append(f"A {ora_txt} ora in {cls} resta {sost} (compresenza)")
            elif tipo == "ATTIVITA_EXTRA":
                righe_testo.append(
                    f"A {ora_txt} ora {cls} in assemblea / attività extra (nessuna sostituzione)"
                )
            else:
                righe_testo.append(f"A {ora_txt} ora SCOPERTA in {cls}")

        blocchi.append("\n".join(righe_testo))

    return "\n".join(blocchi)


# ----------------------------------------------------------------------------
# INTERFACCIA
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Sostituzioni Plesso", page_icon="📋", layout="centered"
    )

    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False
    if "giorno_scelto" not in st.session_state:
        st.session_state["giorno_scelto"] = None

    applica_stile(st.session_state["dark_mode"])
    controlla_accesso()

    _, col_tema = st.columns([3, 1])
    with col_tema:
        st.toggle("🌙 Scuro", key="dark_mode")

    st.markdown(
        """
        <div class="header-card">
            <h1>📋 Sostituzioni Docenti</h1>
            <p>Plesso Vittorini • Gestione rapida assenze</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        df_orario = carica_dati()
    except Exception as e:
        st.error(f"Errore nel caricamento dell'orario: {e}")
        st.stop()

    orario = costruisci_orario(df_orario)

    # 1. Selezione giorno tramite 5 pulsanti
    st.markdown("**Seleziona il giorno**")
    cols_giorni = st.columns(5)
    for idx, codice_g in enumerate(GIORNI.keys()):
        is_selected = st.session_state["giorno_scelto"] == codice_g
        with cols_giorni[idx]:
            if st.button(
                codice_g,
                key=f"btn_{codice_g}",
                type="primary" if is_selected else "secondary",
                use_container_width=True,
            ):
                st.session_state["giorno_scelto"] = codice_g
                st.rerun()

    if st.session_state["giorno_scelto"] is None:
        st.markdown(
            '<div class="badge-warn">⚠️ Seleziona il giorno della settimana per calcolare le sostituzioni.</div>',
            unsafe_allow_html=True,
        )

    # 2. Eventi, Assemblee e Classi Assenti (flessibile su qualsiasi gruppo di classi)
    ore_escluse_classe = {c: set() for c in PLESSO}
    with st.expander("🏫 Eventi, Assemblee o Classi fuori aula (opzionale)", expanded=False):
        st.caption(
            "Seleziona un intero anno (es. tutte le Seconde, o Prime e Quinte) oppure singole classi impegnate in assemblee o uscite."
        )

        # Selezione rapida per anno di corso
        anni_disponibili = {
            "Tutte le 1ª": {c for c in PLESSO if c.startswith("1")},
            "Tutte le 2ª": {c for c in PLESSO if c.startswith("2")},
            "Tutte le 3ª": {c for c in PLESSO if c.startswith("3")},
            "Tutte le 4ª": {c for c in PLESSO if c.startswith("4")},
            "Tutte le 5ª": {c for c in PLESSO if c.startswith("5")},
        }

        anni_scelti = st.multiselect(
            "Interi anni coinvolti (es. 2ª, oppure 1ª e 5ª)",
            list(anni_disponibili.keys()),
            placeholder="Nessun anno intero selezionato",
        )

        if anni_scelti:
            ore_anni = set(
                st.multiselect(
                    "Ore senza lezione per gli anni selezionati",
                    ORE,
                    format_func=lambda x: f"{x}ª ora",
                    placeholder="Seleziona le ore (es. 2ª, 3ª)",
                    key="ore_anni_evento",
                )
            )
            for label_anno in anni_scelti:
                for c in anni_disponibili[label_anno]:
                    ore_escluse_classe[c] |= ore_anni

        st.markdown("---")
        classi_singole = st.multiselect(
            "Singole classi assenti / in uscita",
            sorted(PLESSO),
            placeholder="Seleziona singole classi...",
        )
        if classi_singole:
            modo_cls = st.radio(
                "Durata assenza classi singole",
                ["Tutto il giorno", "Solo alcune ore"],
                horizontal=True,
                key="modo_cls_singole",
            )
            if modo_cls == "Tutto il giorno":
                ore_cls = set(ORE)
            else:
                ore_cls = set(
                    st.multiselect(
                        "Ore per le singole classi selezionate",
                        ORE,
                        format_func=lambda x: f"{x}ª ora",
                        placeholder="Scegli le ore",
                        key="ore_cls_singole",
                    )
                )
            for c in classi_singole:
                ore_escluse_classe[c] |= ore_cls

    # 3. Selezione Docenti Assenti
    assenti = st.multiselect(
        "Docenti assenti",
        sorted(orario),
        placeholder="Cerca e seleziona i docenti...",
    )

    assenze = {}
    for doc in assenti:
        with st.container(border=True):
            st.markdown(f"**{doc}**")
            modo = st.radio(
                "Tipo assenza",
                ["Tutto il giorno", "Solo alcune ore"],
                horizontal=True,
                key=f"modo_{doc}",
                label_visibility="collapsed",
            )
            if modo == "Tutto il giorno":
                assenze[doc] = set(ORE)
            else:
                ore = st.multiselect(
                    "Ore di assenza",
                    ORE,
                    format_func=lambda x: f"{x}ª ora",
                    key=f"ore_{doc}",
                    placeholder="Seleziona le ore",
                )
                assenze[doc] = set(ore)

    if st.session_state["giorno_scelto"] is None or not assenti:
        return

    nome_giorno, abbr_giorno = GIORNI[st.session_state["giorno_scelto"]]
    df, alternative_per_ora = calcola(
        orario, abbr_giorno, assenze, ore_escluse_classe
    )
    st.divider()

    if df.empty:
        st.markdown(
            '<div class="badge-ok">✅ Nessuna ora nel plesso prevista per i docenti selezionati.</div>',
            unsafe_allow_html=True,
        )
        return

    scoperte = int((df["Tipo"] == "SCOPERTO").sum())
    if scoperte > 0:
        st.markdown(
            f'<div class="badge-warn">⚠️ Attenzione: {scoperte} ore risultano scoperte.</div>',
            unsafe_allow_html=True,
        )

    # 1. Prospetto completo pronto per WhatsApp
    st.subheader(f"Prospetto {nome_giorno}")
    st.code(genera_bollettino(nome_giorno, df, assenti), language=None)

    # 2. Alternative disponibili ora per ora
    if alternative_per_ora:
        st.subheader("Alternative disponibili ora per ora")
        st.caption(
            "Risorse ancora libere nelle ore in cui è stata assegnata una sostituzione."
        )

        for h, info in alternative_per_ora.items():
            voci = []
            if info["valide"]:
                voci.append(f"<li><b>Risorse valide:</b> {', '.join(info['valide'])}</li>")
            else:
                voci.append("<li><b>Risorse valide:</b> Nessuna rimasta</li>")

            if info["buche_plesso"]:
                voci.append(
                    f"<li><b>Ore buche nel plesso (non a disp.):</b> {', '.join(info['buche_plesso'])}</li>"
                )

            st.markdown(
                f"""
                <div class="ora-card">
                    <h4>🕐 {h}ª ora ({ORDINALI_MIN[h]} ora)</h4>
                    <ul>{"".join(voci)}</ul>
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
