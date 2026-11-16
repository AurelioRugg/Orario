# -*- coding: utf-8 -*-
"""
SOSTITUZIONI DOCENTI - Plesso Vittorini
Web app Streamlit per gestire le sostituzioni giornaliere dei docenti.

Avvio locale:   streamlit run app.py
Deploy:         Streamlit Community Cloud (vedi requirements.txt)
Password:       st.secrets["APP_PASSWORD"]  (oppure variabile d'ambiente APP_PASSWORD,
                oppure fallback "vittorini2026" per i test locali)
"""

import hmac
import os
from pathlib import Path

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# CONFIGURAZIONE
# ----------------------------------------------------------------------------
APP_PASSWORD = "vittorini2026"  # fallback per test locali

CSV_FILE = Path(__file__).parent / "orario_plesso.csv"

# Classi che appartengono al nostro edificio (giurisdizione della referente)
PLESSO = {"1A", "1B", "1L", "1MST", "2A", "2L", "2M", "3A", "3L", "3M",
          "4A", "4B", "4LL", "5A", "5M"}

GIORNI = {"Lunedì": "Lun", "Martedì": "Mar", "Mercoledì": "Mer",
          "Giovedì": "Gio", "Venerdì": "Ven"}
ORE = list(range(1, 8))  # 1ª - 7ª ora

TOKEN_DISP = {"DISP.", "DISP", "D"}
TOKEN_RICEV = {"RICEV.", "RICEV"}


# ----------------------------------------------------------------------------
# SICUREZZA
# ----------------------------------------------------------------------------
def password_attesa() -> str:
    """Legge la password da st.secrets, poi da variabile d'ambiente, poi fallback."""
    try:
        return str(st.secrets["APP_PASSWORD"])
    except Exception:
        return os.environ.get("APP_PASSWORD", APP_PASSWORD)


def controlla_accesso() -> None:
    """Mostra il login e ferma l'app finché la password non è corretta."""
    if st.session_state.get("autenticato"):
        return
    st.title("🔒 Accesso riservato")
    st.caption("Area riservata alla referente di plesso.")
    with st.form("login"):
        pwd = st.text_input("Password", type="password")
        invia = st.form_submit_button("Entra", use_container_width=True)
    if invia:
        if hmac.compare_digest(pwd.encode("utf-8"), password_attesa().encode("utf-8")):
            st.session_state["autenticato"] = True
            st.rerun()
        else:
            st.error("Password errata.")
    st.stop()


# ----------------------------------------------------------------------------
# DATI: CARICAMENTO / DATASET DI ESEMPIO
# ----------------------------------------------------------------------------
# Orario base del lunedì per 10 docenti (7 ore). Per gli altri giorni gli orari
# vengono ruotati tra i docenti, così il dataset di esempio resta coerente
# (nessun docente in due classi nella stessa ora).
# "4P" e "3D" sono classi di un altro edificio.
BASE_ESEMPIO = [
    ("Bianchi Laura",   "1A,1A,2A,Disp.,3A,,"),
    ("Rossi Maria",     "2A,1B,Disp.,4P,Disp.,3M,"),
    ("Verdi Paolo",     "3A,Ricev.,1L,1L,,2L,2L"),
    ("Neri Giulia",     "1B,3A,3L,Disp.,1A,,"),
    ("Conti Marco",     ",Disp.,2M,2M,4A,4A,"),
    ("Esposito Anna",   "1L,2L,Ricev.,3M,3M,Disp.,"),
    ("Greco Luca",      "5A,5A,4B,Disp.,5M,5M,"),
    ("Ferrari Sara",    "Disp.,2A,3A,3D,3D,Ricev.,"),
    ("Romano Elena",    "4A,4B,4LL,4LL,Disp.,1MST,1MST"),
    ("Colombo Davide",  "5M,Disp.,5A,1A,2M,,"),
]


def genera_esempio() -> pd.DataFrame:
    n = len(BASE_ESEMPIO)
    righe = []
    for i, (nome, _) in enumerate(BASE_ESEMPIO):
        riga = {"Docente": nome}
        for d, g in enumerate(GIORNI.values()):
            celle = (BASE_ESEMPIO[(i + d) % n][1].split(",") + [""] * 7)[:7]
            for h, c in enumerate(celle, start=1):
                riga[f"{g}_{h}"] = c
        righe.append(riga)
    return pd.DataFrame(righe)


def carica_dati():
    """Ritorna (DataFrame, is_esempio). Se il CSV manca crea un dataset di esempio."""
    if CSV_FILE.exists():
        try:
            df = pd.read_csv(CSV_FILE, sep=";", dtype=str, keep_default_na=False,
                             encoding="utf-8-sig")
        except UnicodeDecodeError:  # file salvato da Excel in ANSI
            df = pd.read_csv(CSV_FILE, sep=";", dtype=str, keep_default_na=False,
                             encoding="latin-1")
        df.columns = df.columns.str.strip()
        return df, False
    df = genera_esempio()
    try:
        df.to_csv(CSV_FILE, sep=";", index=False, encoding="utf-8-sig")
    except OSError:
        pass  # filesystem in sola lettura: si lavora in memoria
    return df, True


def classifica(raw) -> tuple:
    """Normalizza una cella: ('vuoto'|'disp'|'ricev'|'classe', sigla_classe)."""
    v = str(raw).strip().upper()
    if v in ("", "NAN"):
        return ("vuoto", "")
    if v in TOKEN_DISP:
        return ("disp", "")
    if v in TOKEN_RICEV:
        return ("ricev", "")
    return ("classe", v)


def costruisci_orario(df: pd.DataFrame) -> dict:
    """orario[docente][giorno_abbr][ora] = (tipo, classe); indice 0 inutilizzato."""
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
def calcola(orario: dict, giorno: str, assenze: dict) -> pd.DataFrame:
    """
    giorno  : sigla (Lun, Mar, ...)
    assenze : {docente: set(ore di assenza)}
    Ritorna un DataFrame con una riga per ogni (ora, classe) da gestire.
    """
    g = giorno

    # ---- helper sulle celle -------------------------------------------------
    def cella(doc, h):
        return orario[doc][g][h] if 1 <= h <= 7 else ("vuoto", "")

    def esterna(doc, h):
        k, v = cella(doc, h)
        return k == "classe" and v not in PLESSO

    def interna(doc, h):
        k, v = cella(doc, h)
        return k == "classe" and v in PLESSO

    def valida(doc, h):
        """Disp./Ricev. utilizzabile solo se non serve per spostarsi da/verso altro edificio."""
        return not esterna(doc, h - 1) and not esterna(doc, h + 1)

    def presente_prima(doc, h):
        """Il docente ha già un'attività a scuola in un'ora precedente."""
        return any(cella(doc, x)[0] != "vuoto" for x in range(1, h))

    # ---- orario delle classi del plesso nel giorno -------------------------
    classi_ore = {}  # classe -> {ora: [docenti]}
    for doc in orario:
        for h in ORE:
            k, v = cella(doc, h)
            if k == "classe" and v in PLESSO:
                classi_ore.setdefault(v, {}).setdefault(h, []).append(doc)

    # classi dove ogni docente insegna nella settimana (per priorità "stessa classe")
    classi_docente = {
        doc: {v for gg in GIORNI.values() for (k, v) in orario[doc][gg][1:] if k == "classe"}
        for doc in orario
    }

    # ---- individua le ore da coprire (Filtro: solo classi del PLESSO) -------
    mancanti = {}   # classe -> {ora: [assenti]}
    compres = {}    # (classe, ora) -> [docenti presenti in compresenza]
    for doc, ore_ass in assenze.items():
        for h in ore_ass:
            k, cls = cella(doc, h)
            if k != "classe" or cls not in PLESSO:
                continue  # ignora classi esterne, Disp., Ricev., vuoto
            altri = [d for d in classi_ore[cls][h]
                     if d != doc and not (d in assenze and h in assenze[d])]
            if altri:
                compres[(cls, h)] = altri
            else:
                mancanti.setdefault(cls, {}).setdefault(h, []).append(doc)

    busy = set()   # (docente, ora) già impegnati in una soluzione
    ris = {}       # (classe, ora) -> (soluzione, note)
    da_C = []      # (classe, ora) che richiedono un sostituto

    # ---- candidati sostituti (Regola C) -----------------------------------
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
                etichetta = "Disp. - insegna già in " + cls if stessa else \
                            "Disp. - lezione adiacente nel plesso" if adiac else "Disp."
            else:
                etichetta = "Ricev. (ultima risorsa)"
            out.append(((0 if k == "disp" else 1, sub, doc), doc, etichetta))
        out.sort(key=lambda x: x[0])
        return [(d, e) for _, d, e in out]

    # ---- REGOLE A e B, classe per classe ----------------------------------
    def cerca_anticipo(cls, t, src):
        """Docente della classe all'ora src che può anticipare/posticipare la lezione all'ora t."""
        for doc in classi_ore[cls].get(src, []):
            if doc in assenze or (doc, t) in busy:
                continue
            k, _ = cella(doc, t)
            if k not in ("vuoto", "disp"):
                continue                       # impegnato (lezione o ricevimento)
            if not valida(doc, t):
                continue                       # si sposta da/verso un altro edificio
            if k == "vuoto" and not presente_prima(doc, t):
                continue                       # non è ancora a scuola
            return doc
        return None

    for cls in sorted(mancanti):
        hrs = sorted(classi_ore[cls])
        todo = set(mancanti[cls])
        pending = set()
        while todo:
            if all(h in todo for h in hrs):    # classe senza nessun docente: serve sostituto
                pending |= todo
                break

            # Regola A - prima ora scoperta
            if hrs[0] in todo:
                run = []
                for h in hrs:
                    if h not in todo:
                        break
                    run.append(h)
                entra = hrs[len(run)]
                for h in run:
                    ris[(cls, h)] = (
                        f"ENTRATA POSTICIPATA (la classe entra alla {entra}ª ora)",
                        "Regola A: ora scoperta all'inizio della giornata della classe.")
                todo -= set(run)
                hrs = [h for h in hrs if h not in run]
                continue

            # Regola A - ultima ora scoperta
            if hrs[-1] in todo:
                run = []
                for h in reversed(hrs):
                    if h not in todo:
                        break
                    run.append(h)
                run.sort()
                ultima = hrs[-(len(run) + 1)]
                msg = ("USCITA ANTICIPATA (la classe esce un'ora prima)" if len(run) == 1 else
                       f"USCITA ANTICIPATA (la classe esce {len(run)} ore prima, dopo la {ultima}ª ora)")
                for h in run:
                    ris[(cls, h)] = (msg, "Regola A: ora scoperta alla fine della giornata della classe.")
                todo -= set(run)
                hrs = [h for h in hrs if h not in run]
                continue

            # Regola B - ora intermedia: anticipo dell'ultima (o prima) lezione
            t = min(todo)
            trovato = None
            for src, tipo in ((hrs[-1], "ultima"), (hrs[0], "prima")):
                doc = cerca_anticipo(cls, t, src)
                if doc:
                    trovato = (doc, src, tipo)
                    break
            if trovato:
                doc, src, tipo = trovato
                effetto = "USCIRE UN'ORA PRIMA" if tipo == "ultima" else "ENTRARE UN'ORA DOPO"
                ris[(cls, t)] = (
                    f"ANTICIPO ORA: il Prof. {doc} anticipa la sua lezione dall'ora {src} "
                    f"all'ora {t}, così la classe può {effetto}",
                    f"Regola B: il Prof. {doc} è a scuola, libero alla {t}ª ora e senza "
                    f"spostamenti da/verso altri edifici.")
                busy.add((doc, t))
                hrs.remove(src)
                todo.discard(t)
            else:
                pending.add(t)
                todo.discard(t)
        da_C.extend((cls, h) for h in pending)

    # ---- REGOLA C - sostituzione con docente valido del plesso -------------
    for cls, t in sorted(da_C, key=lambda x: (x[1], x[0])):
        cands = candidati(t, cls)
        if cands:
            doc, etichetta = cands[0]
            busy.add((doc, t))
            ris[(cls, t)] = (f"Prof. {doc}", f"Regola C: {etichetta}.")
        else:
            ris[(cls, t)] = ("SCOPERTO - Nessun docente disponibile nel plesso",
                             "Nessuna Disp./Ricev. valida (o necessaria per spostamenti tra edifici).")

    # ---- Compresenze: classe già presidiata da un altro docente ------------
    for (cls, h), altri in compres.items():
        ris[(cls, h)] = ("NESSUNA SOSTITUZIONE NECESSARIA",
                         f"In classe c'è anche il Prof. {', '.join(altri)} (compresenza): "
                         f"verificare se può restare con la classe.")

    # ---- Costruzione tabella finale ---------------------------------------
    assenti_per_riga = {}
    for cls, d in mancanti.items():
        for h, nomi in d.items():
            assenti_per_riga[(cls, h)] = nomi
    for (cls, h) in compres:
        assenti_per_riga[(cls, h)] = [d for d in assenze
                                      if h in assenze[d] and cella(d, h) == ("classe", cls)]

    righe = []
    for (cls, h) in sorted(ris, key=lambda x: (x[1], x[0])):
        sol, note = ris[(cls, h)]
        alt = [f"{d} ({e})" for d, e in candidati(h, cls)][:6]
        righe.append({
            "Ora": f"{h}ª",
            "Classe": cls,
            "Docente Assente": ", ".join(assenti_per_riga[(cls, h)]),
            "Soluzione / Sostituto": sol,
            "Motivazione / Note": note,
            "Alternative disponibili": "; ".join(alt) if alt else "—",
        })
    return pd.DataFrame(righe, columns=[
        "Ora", "Classe", "Docente Assente", "Soluzione / Sostituto",
        "Motivazione / Note", "Alternative disponibili"])


# ----------------------------------------------------------------------------
# OUTPUT: TESTO WHATSAPP E STILE TABELLA
# ----------------------------------------------------------------------------
def testo_whatsapp(nome_giorno: str, df: pd.DataFrame) -> str:
    righe = [f"📋 *SOSTITUZIONI - {nome_giorno.upper()}*", ""]
    for ora, blocco in df.groupby("Ora", sort=False):
        righe.append(f"🕐 *{ora} ora*")
        for _, r in blocco.iterrows():
            righe.append(f"• {r['Classe']} (assente {r['Docente Assente']}): "
                         f"{r['Soluzione / Sostituto']}")
        righe.append("")
    righe.append("Grazie per la collaborazione 🙏")
    return "\n".join(righe)


def colora_riga(riga):
    s = riga["Soluzione / Sostituto"]
    if s.startswith("SCOPERTO"):
        stile = "background-color:#ffd6d6;color:#7a0000"
    elif s.startswith(("ENTRATA", "USCITA")):
        stile = "background-color:#fff4cc;color:#5c4500"
    elif s.startswith("ANTICIPO"):
        stile = "background-color:#d9ecff;color:#0b3a66"
    elif s.startswith("NESSUNA"):
        stile = "background-color:#eeeeee;color:#333333"
    else:
        stile = "background-color:#dcf5dc;color:#0b4d0b"
    return [stile] * len(riga)


# ----------------------------------------------------------------------------
# INTERFACCIA
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Sostituzioni docenti", page_icon="📋", layout="centered")
    controlla_accesso()

    st.title("📋 Sostituzioni docenti")
    df_orario, is_esempio = carica_dati()
    if is_esempio:
        st.info("File `orario_plesso.csv` non trovato: sto usando un **dataset di esempio**. "
                "Carica il tuo file nella cartella dell'app per usare l'orario reale.")
    orario = costruisci_orario(df_orario)

    nome_giorno = st.selectbox("Giorno della settimana", list(GIORNI.keys()))
    assenti = st.multiselect("Docenti assenti", sorted(orario),
                             placeholder="Cerca e seleziona i docenti assenti...")

    assenze = {}
    for doc in assenti:
        with st.container(border=True):
            st.markdown(f"**{doc}**")
            modo = st.radio("Tipo di assenza", ["Tutto il giorno", "Solo alcune ore"],
                            horizontal=True, key=f"modo_{doc}", label_visibility="collapsed")
            if modo == "Tutto il giorno":
                assenze[doc] = set(ORE)
            else:
                ore = st.multiselect("Ore di assenza", ORE, key=f"ore_{doc}",
                                     placeholder="Scegli le ore")
                assenze[doc] = set(ore)

    if not assenti:
        st.caption("Seleziona almeno un docente assente per vedere le proposte.")
        return

    df = calcola(orario, GIORNI[nome_giorno], assenze)
    st.divider()
    if df.empty:
        st.success("Nessuna ora da coprire nelle classi del plesso. ✅")
        return

    da_gestire = df[~df["Soluzione / Sostituto"].str.startswith("NESSUNA")]
    scoperte = int(df["Soluzione / Sostituto"].str.startswith("SCOPERTO").sum())
    c1, c2 = st.columns(2)
    c1.metric("Ore da gestire", len(da_gestire))
    c2.metric("Ore scoperte", scoperte)

    st.subheader(f"Proposte per {nome_giorno}")
    st.dataframe(df.style.apply(colora_riga, axis=1), use_container_width=True, hide_index=True)
    st.caption("Docenti assenti (anche solo in parte) non sono considerati come risorse.")

    st.download_button(
        "⬇️ Scarica CSV (Excel)",
        data=df.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"sostituzioni_{nome_giorno.lower()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.subheader("Messaggio per WhatsApp")
    st.caption("Usa l'icona in alto a destra del riquadro per copiare, poi incolla nel gruppo.")
    st.code(testo_whatsapp(nome_giorno, df), language=None)


if __name__ == "__main__":
    main()
