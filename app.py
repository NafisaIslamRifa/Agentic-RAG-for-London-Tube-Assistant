"""
app.py — Streamlit UI for the London Tube Assistant.

Modes via a radio selector (kept at top level because st.chat_input
cannot live inside tabs/columns):
  - "Smart Assistant"  — agentic routing (LLM picks the right tool)
  - "Live Tube Status" — real-time line status from the TFL API
  - "Fare Calculator"  — real fares between stations from the TFL API
  - "Next Trains"      — live arrival predictions from the TFL API

Run with:  streamlit run app.py
"""

import streamlit as st
from rag import build_or_load_index, answer_question
from tfl_api import get_tube_status, get_arrivals
from fares import get_real_fare, station_names, STATIONS
from agent import agent_answer

# ---------- Page setup ----------
st.set_page_config(page_title="🚇 London Tube Assistant", page_icon="🚇", layout="centered")
st.title("🚇 London Tube Assistant")
st.caption("Ask questions, check live status, find fares, or see the next trains.")

# ---------- Load the RAG index once, cached ----------
@st.cache_resource(show_spinner="Loading TFL knowledge base...")
def get_index():
    return build_or_load_index()

# ---------- Mode selector ----------
mode = st.radio(
    "Choose a mode:",
    ["🤖 Smart Assistant", "🚦 Live Tube Status",
     "💷 Fare Calculator", "🚆 Next Trains"],
    horizontal=True,
)
st.divider()

# =====================================================
# MODE — Live tube status
# =====================================================
if mode == "🚦 Live Tube Status":
    st.subheader("Real-time London Underground line status")
    st.caption("Live data from the Transport for London API.")

    if st.button("🔄 Refresh Live Status", use_container_width=True):
        st.session_state.pop("tube_status", None)

    if "tube_status" not in st.session_state:
        with st.spinner("Fetching live tube status..."):
            try:
                st.session_state.tube_status = get_tube_status()
            except Exception as e:
                st.error(f"Could not fetch live status: {e}")
                st.session_state.tube_status = []

    statuses = st.session_state.get("tube_status", [])
    if statuses:
        for s in statuses:
            if s.status == "Good Service":
                st.success(f"**{s.name}** — {s.status}")
            else:
                msg = f"**{s.name}** — {s.status}"
                if s.reason:
                    msg += f"\n\n_{s.reason}_"
                st.warning(msg)
    else:
        st.info("No status data available. Try refreshing.")

# =====================================================
# MODE — Real fares between stations
# =====================================================
elif mode == "💷 Fare Calculator":
    st.subheader("Find the real fare between stations")
    st.caption("Live fare data from the Transport for London API.")

    stations = station_names()
    col1, col2 = st.columns(2)
    with col1:
        from_station = st.selectbox("From station", stations, index=0)
    with col2:
        to_station = st.selectbox("To station", stations, index=1)

    if st.button("Get fare", use_container_width=True):
        with st.spinner("Fetching live fare from TFL..."):
            result = get_real_fare(from_station, to_station)
        if result.found:
            st.success(f"**{result.from_station} → {result.to_station}**")
            st.markdown(result.fare)
        else:
            st.warning(result.fare)
        st.caption("Live fares from the TFL Unified API. Actual charges may vary with capping and railcards.")

# =====================================================
# MODE — Next trains (live arrival predictions)
# =====================================================
elif mode == "🚆 Next Trains":
    st.subheader("Live arrival predictions")
    st.caption("Real-time 'next train' data from the TFL API.")

    station = st.selectbox("Station", station_names(), index=0)

    if st.button("Show next trains", use_container_width=True):
        station_id = STATIONS.get(station)
        if not station_id:
            st.warning("Station ID not found.")
        else:
            with st.spinner("Fetching live arrivals..."):
                try:
                    arrivals = get_arrivals(station_id)
                except Exception as e:
                    st.error(f"Could not fetch arrivals: {e}")
                    arrivals = []

            if arrivals:
                st.markdown(f"**Next trains at {station}:**")
                for a in arrivals:
                    when = "due now" if a.minutes == 0 else f"in {a.minutes} min"
                    plat = f" · {a.platform}" if a.platform else ""
                    st.info(f"**{a.line}** to {a.destination} — {when}{plat}")
            else:
                st.warning("No arrivals predicted right now (or no data for this station).")

# =====================================================
# MODE — Smart Assistant (agentic routing)  [default]
# =====================================================
else:
    st.subheader("Ask anything about the Tube")
    st.caption("Agentic routing: the AI decides whether to use documents, live status, fares, or arrivals.")

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    for i, msg in enumerate(st.session_state.agent_messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("tool"):
                st.caption(f"🔧 Tool used: {msg['tool']}")
            if msg.get("tool") == "map":
                st.image("data/tube-map.jpg", caption="London Underground Tube Map",
                         use_column_width=True)
                with open("data/tube-map.pdf", "rb") as f:
                    st.download_button(
                        "📄 Download Tube Map (PDF)", data=f,
                        file_name="tube-map.pdf", mime="application/pdf",
                        key=f"agent_map_{i}")

    if prompt := st.chat_input("Ask anything about the Tube..."):
        st.session_state.agent_messages.append({"role": "user", "content": prompt})

        # Show the user's message immediately (before the slow processing)
        with st.chat_message("user"):
            st.markdown(prompt)

        vectordb = get_index()
        with st.spinner("Thinking about which tool to use..."):
            result = agent_answer(vectordb, prompt)

        st.session_state.agent_messages.append({
            "role": "assistant",
            "content": result.text,
            "tool": result.tool_used,
        })
        st.rerun()