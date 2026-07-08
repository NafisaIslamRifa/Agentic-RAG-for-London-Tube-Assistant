"""
agent.py — Simple agentic router for the London Tube Assistant.

The LLM reads the user's question and decides which tool to use:
  - "status"   -> live tube line status (TFL API)
  - "fare"     -> real fare between two stations (TFL API)
  - "arrivals" -> next trains at a station (TFL API)
  - "rag"      -> answer from documents (default / fallback)

Then the chosen tool runs and the result is returned. Designed to degrade
gracefully: if routing is uncertain or fails, it falls back to RAG.


"""

import re
from dataclasses import dataclass
from langchain_ollama import ChatOllama

from rag import build_or_load_index, answer_question, LLM_MODEL
from tfl_api import get_tube_status, get_arrivals
from fares import get_real_fare, STATIONS


@dataclass
class AgentResult:
    tool_used: str
    text: str
    sources: list


# ---- The router: ask the LLM to classify the question into one tool ----
def route_question(question: str) -> str:

    map_keywords = ["map", "tube map", "underground map", "network map"]
    if any(k in question.lower() for k in map_keywords):
        return "map"
    """Ask the LLM which tool best fits the question. Returns a tool name."""
    # In route_question, add "map" to the tool list in the prompt:
    router_prompt = (
        "You are a router for a London transport assistant. "
        "Choose EXACTLY ONE tool for the user's question:\n"
        "- status: whether lines are running, delays, disruptions\n"
        "- fare: the cost/price/fare of a journey between two stations\n"
        "- arrivals: next train or arrival times at a station\n"
        "- map: ONLY when the user explicitly asks to see a map or tube map\n"
        "- rag: everything else — how to get somewhere, airport travel, zones, "
        "accessibility, night tube, payment methods, general info\n\n"
        "Examples:\n"
        "Q: Is the Victoria line running? -> status\n"
        "Q: How much is the fare from Bank to Victoria? -> fare\n"
        "Q: When is the next train at Oxford Circus? -> arrivals\n"
        "Q: Show me the tube map -> map\n"
        "Q: How do I get to Heathrow airport? -> rag\n"
        "Q: How do I travel to Gatwick? -> rag\n"
        "Q: What is the Hopper fare? -> rag\n\n"
        "Reply with ONLY the tool name.\n\n"
        f"Question: {question}\n"
        "Tool:"
    )
    llm = ChatOllama(model=LLM_MODEL, temperature=0)
    try:
        response = llm.invoke([{"role": "user", "content": router_prompt}])
        choice = response.content.strip().lower()
        # extract the first valid tool word (robust to extra text)
        for tool in ["status", "fare", "arrivals","map", "rag"]:
            if tool in choice:
                return tool
    except Exception:
        pass
    return "rag"   # safe default


# ---- Helper: find station names mentioned in the question ----
def _find_stations(question: str):
    """Return station names from STATIONS that appear in the question."""
    found = []
    q = question.lower()
    for name in STATIONS:
        if name.lower() in q:
            found.append(name)
    return found


# ---- The main agent function ----
def agent_answer(vectordb, question: str) -> AgentResult:
    tool = route_question(question)

    # --- STATUS ---
    if tool == "status":
        try:
            statuses = get_tube_status()
            lines = [f"{s.name}: {s.status}" for s in statuses]
            text = "Current line status:\n\n" + "\n\n".join(lines)
            return AgentResult("status", text, [])
        except Exception as e:
            return AgentResult("status", f"Could not fetch live status: {e}", [])

    # --- FARE --- (needs two stations)
    if tool == "fare":
        stations = _find_stations(question)
        if len(stations) >= 2:
            result = get_real_fare(stations[0], stations[1])
            if result.found:
                return AgentResult("fare",
                    f"Fare from {result.from_station} to {result.to_station}:\n\n{result.fare}", [])
            return AgentResult("fare", result.fare, [])
        else:
            return AgentResult("fare",
                "I can find a fare, but I need two station names. "
                "Try: 'fare from Bank to Victoria'.", [])

    # --- ARRIVALS --- (needs one station)
    if tool == "arrivals":
        stations = _find_stations(question)
        if stations:
            station_id = STATIONS.get(stations[0])
            try:
                arrivals = get_arrivals(station_id)
                if arrivals:
                    lines = [f"{a.line} to {a.destination} — "
                             f"{'due' if a.minutes == 0 else f'in {a.minutes} min'}"
                             for a in arrivals[:6]]
                    text = f"Next trains at {stations[0]}:\n\n" + "\n\n".join(lines)
                    return AgentResult("arrivals", text, [])
                return AgentResult("arrivals",
                    f"No arrivals predicted at {stations[0]} right now.", [])
            except Exception as e:
                return AgentResult("arrivals", f"Could not fetch arrivals: {e}", [])
        else:
            return AgentResult("arrivals",
                "I can show next trains, but I need a station name. "
                "Try: 'next trains at Victoria'.", [])

    # --- MAP ---
    if tool == "map":
        text = (
            "You can find the London Tube map on Transport for London's website, "
            "tfl.gov.uk. Alternatively, you can download a copy from their website "
            "or request one by calling 0343 222 1234. The map is available in various "
            "formats, including large print and audio versions. For your convenience, "
            "the map is shown below with a download option."
        )
        return AgentResult("map", text, [])
    # --- RAG (default / fallback) ---
    result = answer_question(vectordb, question)
    return AgentResult("rag", result.text, result.sources)