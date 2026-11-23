"""MEGATRON × SYNDICATE — dashboard; reads real generated results only."""
import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="MEGATRON × SYNDICATE", layout="wide")
st.title("⚽ MEGATRON × SYNDICATE")
st.caption("BTTS OUI — estimations expérimentales, non calibrées. Aucun pari automatique.")
data_file = Path(__file__).resolve().parent / "data" / "predictions.json"
if not data_file.exists():
    st.warning("Aucune prédiction disponible. Exécuter le pipeline avec une clé API football-data.org.")
    st.stop()
try:
    payload = json.loads(data_file.read_text(encoding="utf-8"))
    rows = payload.get("results", [])
except (ValueError, OSError) as exc:
    st.error(f"Impossible de charger les prédictions : {exc}")
    st.stop()
rows = [r for r in rows if isinstance(r.get("p_btts_oui"), (int, float))]
rows.sort(key=lambda r: r["p_btts_oui"], reverse=True)
st.metric("Rencontres avec estimation", len(rows))\nst.caption("Couverture limitée aux compétitions accessibles par la clé API.")
st.caption("Calculées le : " + str(payload.get("generated_at", "inconnu")))
st.dataframe([{"Date UTC": r.get("date"), "Ligue": r.get("league"), "Domicile": r.get("home"), "Extérieur": r.get("away"), "BTTS OUI (%)": round(r["p_btts_oui"] * 100, 1), "Statut": r.get("status")} for r in rows[:10]], use_container_width=True, hide_index=True)
if payload.get("errors"):\n    st.warning("Certaines compétitions n’ont pas pu être chargées : " + ", ".join(e.get("competition", "?") for e in payload["errors"]))\nif not rows:\n    st.warning("Aucune estimation BTTS exploitable aujourd’hui. Pas de sélection artificielle.")\nst.info("SYNDICATE MAX/TTF exige validation humaine des H2H, compositions, absences et motivation.")
