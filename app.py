# -*- coding: utf-8 -*-
"""
SOSTITUZIONI DOCENTI - Plesso Vittorini
Web app Streamlit con interfaccia curata mobile-first.
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
    "Lunedì": "Lun",
    "Martedì": "Mar",
    "Mercoledì": "Mer",
    "Giovedì": "Gio",
    "Venerdì": "Ven",
}
ORE = list(range(1, 8))  # 1ª - 7ª ora

TOKEN_DISP = {"DISP.", "DISP", "D"}
TOKEN_RICEV = {"RICEV.", "RICEV"}

ORDINALI_MIN = {
    1: "prima",
    2: "seconda",
    3: "terza",
    4: "quarta",
    5: "quinta",
    6: "sesta",
    7: "settima",
}

# Inserisci qui i nomi ESATTI (come nel CSV) dei docenti uomini
MASCHI = set()

COLONNE_TABELLA = ["Ora", "Classe", "Assente", "Soluzione", "Note / Alternative"]


# ----------------------------------------------------------------------------
# ESTETICA E STILE CUSTOM (CSS)
# ----------------------------------------------------------------------------
def applica_stile() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f4f6f9;
            color: #1e293b;
        }
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
            max-width: 720px;
        }

        /* Header istituzionale */
        .header-card {
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
            color: white;
            padding: 1.35rem 1.6rem;
            border-radius: 16px;
            margin-bottom: 1.4rem;
            box-shadow: 0 4px 14px rgba(30, 58, 138, 0.18);
        }
        .header-card h1 {
            margin: 0;
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: white;
        }
        .header-card p {
            margin: 0.25rem 0 0 0;
            font-size: 0.9rem;
            color: #dbeafe;
        }

        /* Card dei docenti assenti */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px !important;
            padding: 0.4rem 0.6rem;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
            margin-bottom: 0.6rem;
        }

        /* Riquadro Bollettino WhatsApp */
        [data-testid="stCode"] {
            background-color: #ffffff !important;
            border: 1.5px solid #cbd5e1 !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
        }
        [data-testid="stCode"] pre {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            font-size: 0.98rem !important;
            line-height: 1.55 !important;
            color: #0f172a !important;
            padding: 1rem !important;
        }

        /* Card informativa ore buche nel plesso */
        .buche-card {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-left: 4px solid #3b82f6;
            border-radius: 12px;
            padding: 1rem 1.2rem;
            margin-top: 1rem;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
        }
        .buche-card h4 {
            margin: 0 0 0.4rem 0;
            font-size: 1rem;
            color: #1e3a8a;
        }
        .buche-card p {
            margin: 0 0 0.6rem 0;
            font-size: 0.85rem;
            color: #64748b;
        }

        /* Bottoni comodi da smartphone */
        .stButton > button {
            background-color: #1e3a8a;
            color: white;
            border-radius: 10px;
            border: none;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            background-color: #1d4ed8;
            color: white;
        }

        /* Badge esito */
        .badge-ok {
            background-color: #dcfce7;
            color: #166534;
            padding: 0.8rem 1rem;
            border-radius: 12px;
            border-left: 4px solid #16a34a;
            font-weight: 500;
            margin: 0.8rem 0;
        }
        .badge-warn {
            background-color: #fee2e2;
            color: #991b1b;
            padding: 0.8rem 1rem;
            border-radius: 12px;
            border-left: 4px solid #dc2626;
            font-weight: 600;
            margin: 0.8rem 0;
        }
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
        invia = st.form_submit_button("Entra", use_container_width=True)
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
@st.cache_data
def carica_dati() -> pd.DataFrame:
    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"File '{CSV_FILE.name}' non trovato nella cartella dell'app."
        )
    
    # Legge le prime righe per capire se il separatore è ';' oppure ','
    raw_text = None
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
            g: [None] + [classifica(r.get(f"{g}_{h}", "")) for h in ORE]
            for g in GIORNI.values()
        }
    return orario


# ----------------------------------------------------------------------------
# MOTORE DELLE SOSTITUZIONI
# ----------------------------------------------------------------------------
def calcola(orario: dict, giorno: str, assenze: dict) -> tuple[pd.DataFrame, dict]:
    """
    Ritorna (DataFrame_risultati, dict_ore_buche_interne).
    dict_ore_buche_interne: {ora: [(docente, classe_prima, classe_dopo), ...]}
    """
    g = giorno

    def cella(doc, h):
        return orario[doc][g][h] if 1 <= h <= 7 else ("vuoto", "")

    def esterna(doc, h):
        k, v = cella(doc, h)
        return k == "classe" and v not in PLESSO

    def interna(doc, h):
        k, v = cella(doc, h)
        return k == "classe" and v in PLESSO

    def valida(doc, h):
        """Disp./Ricev. valida solo se non adiacente a classi di un altro edificio."""
        return not esterna(doc, h - 1) and not esterna(doc, h + 1)

    def presente_prima(doc, h):
        return any(cella(doc, x)[0] != "vuoto" for x in range(1, h))

    # Mappa orario giornaliero delle classi del plesso
    classi_ore = {}
    for doc in orario:
        for h in ORE:
            k, v = cella(doc, h)
            if k == "classe" and v in PLESSO:
                classi_ore.setdefault(v, {}).setdefault(h, []).append(doc)

    classi_docente = {
        doc: {
            v
            for gg in GIORNI.values()
            for (k, v) in orario[doc][gg][1:]
            if k == "classe"
        }
        for doc in orario
    }

    # Individua ore scoperte e compresenze
    mancanti = {}
    compres = {}
    for doc, ore_ass in assenze.items():
        for h in ore_ass:
            k, cls = cella(doc, h)
            if k != "classe" or cls not in PLESSO:
                continue
            altri = [
                d
                for d in classi_ore[cls][h]
                if d != doc and not (d in assenze and h in assenze[d])
            ]
            if altri:
                compres[(cls, h)] = altri
            else:
                mancanti.setdefault(cls, {}).setdefault(h, []).append(doc)

    busy = set()
    ris = {}
    da_C = []

    def candidati(t, cls):
        out = []
        for doc in orario:
            if doc in assenze or (doc, t) in busy:
                continue
            k, _ = cella(doc, t)
            if k not in ("disp", "ricev") or not valida(doc, t):
                continue
            stessa = cls in classi_docente[doc]
            adiac = interna(doc, t - 1) or interna(doc, t + 1)
            sub = 0 if stessa else (1 if adiac else 2)
            if k == "disp":
                etichetta = (
                    f"Disp. (già docente in {cls})"
                    if stessa
                    else "Disp. (ora adiacente nel plesso)"
                    if adiac
                    else "Disp."
                )
            else:
                etichetta = (
                    f"Ricev. (già docente in {cls})"
                    if stessa
                    else "Ricev. (ora adiacente nel plesso)"
                    if adiac
                    else "Ricev."
                )
            out.append(((0 if k == "disp" else 1, sub, doc), doc, etichetta))
        out.sort(key=lambda x: x[0])
        return [(d, e) for _, d, e in out]

    def cerca_anticipo(cls, t, src):
        for doc in classi_ore[cls].get(src, []):
            if doc in assenze or (doc, t) in busy:
                continue
            k, _ = cella(doc, t)
            if k not in ("vuoto", "disp"):
                continue
            if not valida(doc, t):
                continue
            if k == "vuoto" and not presente_prima(doc, t):
                continue
            return doc
        return None

    # ---- REGOLE A e B (continuità e max 1 ora ingresso/uscita) ------------
    for cls in sorted(mancanti):
        hrs = sorted(classi_ore[cls])
        todo = set(mancanti[cls])
        ha_tagliato_ingresso = False
        ha_tagliato_uscita = False

        if all(h in todo for h in hrs):
            da_C.extend((cls, h) for h in sorted(todo))
            continue

        # 1. Entrata posticipata: max 1 ora (solo 1ª ora della classe, entra alla 2ª)
        prima_ora_classe = hrs[0]
        if prima_ora_classe in todo and prima_ora_classe == 1 and len(hrs) > 1:
            entra = hrs[1]
            ris[(cls, prima_ora_classe)] = (
                "ENTRATA_POST",
                f"Entrata posticipata (entra alla {entra}ª ora)",
                "Max 1 ora di posticipo ingresso consentita.",
                "",
                None,
            )
            todo.remove(prima_ora_classe)
            hrs.remove(prima_ora_classe)
            ha_tagliato_ingresso = True

        # 2. Uscita anticipata: max 1 ora (solo ultima ora della classe)
        ultima_ora_classe = hrs[-1]
        if ultima_ora_classe in todo and len(hrs) > 1:
            ris[(cls, ultima_ora_classe)] = (
                "USCITA_ANT",
                "Uscita anticipata (esce un'ora prima)",
                "Max 1 ora di uscita anticipata consentita.",
                "",
                None,
            )
            todo.remove(ultima_ora_classe)
            hrs.remove(ultima_ora_classe)
            ha_tagliato_uscita = True

        # 3. Anticipo/Posticipo ora per garantire continuità ed evitare buchi
        for t in sorted(list(todo)):
            trovato = None
            if not ha_tagliato_uscita and len(hrs) > 1:
                src = hrs[-1]
                doc = cerca_anticipo(cls, t, src)
                if doc:
                    trovato = (doc, src, "ultima")

            if not trovato and not ha_tagliato_ingresso and hrs[0] == 1 and len(hrs) > 1:
                src = hrs[0]
                doc = cerca_anticipo(cls, t, src)
                if doc:
                    trovato = (doc, src, "prima")

            if trovato:
                doc, src, tipo = trovato
                if tipo == "ultima":
                    ris[(cls, t)] = (
                        "ANTICIPO",
                        f"Prof. {doc} anticipa dalla {src}ª ora (classe esce un'ora prima)",
                        f"Spostamento lezione dalla {src}ª alla {t}ª ora per continuità.",
                        doc,
                        src,
                    )
                    ha_tagliato_uscita = True
                else:
                    ris[(cls, t)] = (
                        "POSTICIPO",
                        f"Prof. {doc} sposta dalla {src}ª ora (classe entra alla 2ª ora)",
                        f"Spostamento lezione dalla {src}ª alla {t}ª ora per continuità.",
                        doc,
                        src,
                    )
                    ha_tagliato_ingresso = True
                busy.add((doc, t))
                hrs.remove(src)
                todo.remove(t)

        da_C.extend((cls, h) for h in sorted(todo))

    # ---- REGOLA C - Sostituzione con Disp./Ricev. validi nel plesso --------
    for cls, t in sorted(da_C, key=lambda x: (x[1], x[0])):
        cands = candidati(t, cls)
        if cands:
            doc, etichetta = cands[0]
            busy.add((doc, t))
            ris[(cls, t)] = (
                "SOSTITUTO",
                f"Prof. {doc}",
                etichetta,
                doc,
                None,
            )
        else:
            ris[(cls, t)] = (
                "SCOPERTO",
                "SCOPERTO - Nessun docente disponibile",
                "Nessuna Disp./Ricev. valida nel plesso.",
                "",
                None,
            )

    # ---- Compresenze --------------------------------------------------------
    for (cls, h), altri in compres.items():
        ris[(cls, h)] = (
            "COMPRESENZA",
            f"Compresenza con Prof. {', '.join(altri)}",
            "Classe già coperta dal docente in compresenza.",
            "",
            None,
        )

    # ---- Calcolo docenti con ORA BUCA ('vuoto') tra due classi del PLESSO ---
    ore_coinvolte = sorted({h for (_, h) in ris})
    buche_plesso = {}
    for h in ore_coinvolte:
        trovati_ora = []
        for doc in sorted(orario):
            if doc in assenze or (doc, h) in busy:
                continue
            k, _ = cella(doc, h)
            if k != "vuoto":
                continue
            # Cerca l'ultima attività prima di h e la prima attività dopo h
            prima = [cella(doc, x) for x in range(h - 1, 0, -1) if cella(doc, x)[0] != "vuoto"]
            dopo = [cella(doc, x) for x in range(h + 1, 8) if cella(doc, x)[0] != "vuoto"]
            if prima and dopo:
                k_p, v_p = prima[0]
                k_d, v_d = dopo[0]
                # Entrambe adiacenti a classi del nostro plesso
                if k_p == "classe" and v_p in PLESSO and k_d == "classe" and v_d in PLESSO:
                    trovati_ora.append((doc, v_p, v_d))
        if trovati_ora:
            buche_plesso[h] = trovati_ora

    # ---- Costruzione DataFrame ----------------------------------------------
    assenti_per_riga = {}
    for cls, d in mancanti.items():
        for h, nomi in d.items():
            assenti_per_riga[(cls, h)] = nomi
    for (cls, h) in compres:
        assenti_per_riga[(cls, h)] = [
            d for d in assenze if h in assenze[d] and cella(d, h) == ("classe", cls)
        ]

    righe = []
    for (cls, h) in sorted(ris, key=lambda x: (x[1], x[0])):
        tipo, sol_tab, note_tab, doc_coinv, ora_orig = ris[(cls, h)]
        alt = [f"{d} ({e})" for d, e in candidati(h, cls)][:5]
        righe.append(
            {
                "Ora": f"{h}ª",
                "Classe": cls,
                "Assente": ", ".join(assenti_per_riga[(cls, h)]),
                "Soluzione": sol_tab,
                "Note / Alternative": (
                    f"{note_tab} | Alt: {'; '.join(alt)}" if alt else note_tab
                ),
                "_Ora": h,
                "_Assenti": assenti_per_riga[(cls, h)],
                "_Tipo": tipo,
                "_DocCoinv": doc_coinv,
                "_OraOrig": ora_orig,
            }
        )
    df_ris = pd.DataFrame(
        righe,
        columns=COLONNE_TABELLA
        + ["_Ora", "_Assenti", "_Tipo", "_DocCoinv", "_OraOrig"],
    )
    return df_ris, buche_plesso


# ----------------------------------------------------------------------------
# FORMATTAZIONE OUTPUT TASCABILE
# ----------------------------------------------------------------------------
def titolo_prof(doc: str) -> str:
    return f"prof {doc}" if doc in MASCHI else f"prof.ssa {doc}"


def genera_bollettino(nome_giorno: str, df: pd.DataFrame, ordine_assenti: list) -> str:
    blocchi = [f"SOSTITUZIONI {nome_giorno.upper()}"]

    for doc in ordine_assenti:
        righe_doc = df[df["_Assenti"].apply(lambda a: doc in a)]
        if righe_doc.empty:
            blocchi.append(
                f"\nManca {titolo_prof(doc)}\nNessuna ora da coprire nel plesso."
            )
            continue

        righe_testo = [f"\nManca {titolo_prof(doc)}"]
        for _, r in righe_doc.sort_values(["_Ora", "Classe"]).iterrows():
            ora_txt = ORDINALI_MIN[r["_Ora"]]
            cls = r["Classe"]
            tipo = r["_Tipo"]
            sost = r["_DocCoinv"]
            ora_orig = r["_OraOrig"]

            if tipo == "ENTRATA_POST":
                righe_testo.append(f"A {ora_txt} ora entrata posticipata in {cls}")
            elif tipo == "USCITA_ANT":
                righe_testo.append(f"A {ora_txt} ora uscita anticipata in {cls}")
            elif tipo == "ANTICIPO":
                righe_testo.append(
                    f"A {ora_txt} ora anticipa {titolo_prof(sost)} (dalla {ora_orig}ª) in {cls} -> uscita anticipata"
                )
            elif tipo == "POSTICIPO":
                righe_testo.append(
                    f"A {ora_txt} ora posticipa {titolo_prof(sost)} (dalla {ora_orig}ª) in {cls} -> entrata posticipata"
                )
            elif tipo == "SOSTITUTO":
                righe_testo.append(
                    f"A {ora_txt} ora sostituisce {titolo_prof(sost)} in {cls}"
                )
            elif tipo == "COMPRESENZA":
                righe_testo.append(
                    f"A {ora_txt} ora in {cls} resta il docente in compresenza"
                )
            else:
                righe_testo.append(
                    f"A {ora_txt} ora SCOPERTA in {cls} (nessun sostituto disponibile)"
                )

        blocchi.append("\n".join(righe_testo))

    return "\n".join(blocchi)


def colora_riga(riga):
    s = riga["Soluzione"]
    if s.startswith("SCOPERTO"):
        stile = "background-color:#ffd6d6;color:#7a0000"
    elif s.startswith(("Entrata", "Uscita")):
        stile = "background-color:#fff4cc;color:#5c4500"
    elif "anticipa" in s or "sposta" in s:
        stile = "background-color:#d9ecff;color:#0b3a66"
    elif s.startswith("Compresenza"):
        stile = "background-color:#eeeeee;color:#333333"
    else:
        stile = "background-color:#dcf5dc;color:#0b4d0b"
    return [stile] * len(riga)


# ----------------------------------------------------------------------------
# INTERFACCIA
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Sostituzioni Plesso", page_icon="📋", layout="centered"
    )
    applica_stile()
    controlla_accesso()

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

    nome_giorno = st.selectbox("Giorno della settimana", list(GIORNI.keys()))
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
                    key=f"ore_{doc}",
                    placeholder="Seleziona le ore",
                )
                assenze[doc] = set(ore)

    if not assenti:
        return

    df, buche_plesso = calcola(orario, GIORNI[nome_giorno], assenze)
    st.divider()

    if df.empty:
        st.markdown(
            '<div class="badge-ok">✅ Nessuna ora da coprire nelle classi del plesso.</div>',
            unsafe_allow_html=True,
        )
        return

    scoperte = int((df["_Tipo"] == "SCOPERTO").sum())
    if scoperte > 0:
        st.markdown(
            f'<div class="badge-warn">⚠️ Attenzione: {scoperte} ore risultano scoperte.</div>',
            unsafe_allow_html=True,
        )

    st.subheader("Prospetto da copiare")
    st.code(genera_bollettino(nome_giorno, df, assenti), language=None)

    # Box informativo sui docenti che hanno un'ora buca tra due classi del plesso
    if buche_plesso:
        righe_buche = []
        for h, lista in buche_plesso.items():
            nomi = ", ".join(
                f"<b>{doc}</b> (tra {c1} e {c2})" for doc, c1, c2 in lista
            )
            righe_buche.append(f"• <b>{h}ª ora:</b> {nomi}")
        st.markdown(
            f"""
            <div class="buche-card">
                <h4>💡 Docenti con ora buca nel plesso (non a disposizione)</h4>
                <p>Sono già nell'edificio tra due classi del plesso; utili solo per eventuali accordi informali o recuperi.</p>
                <div style="font-size:0.92rem; line-height:1.6;">{"<br>".join(righe_buche)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Dettaglio tecnico e alternative disponibili"):
        st.dataframe(
            df[COLONNE_TABELLA].style.apply(colora_riga, axis=1),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
