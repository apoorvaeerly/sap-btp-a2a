"""
app.py — Eerly Studio
Clean ChatGPT-style UI with logo, no sidebar.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from a2a_bridge import bridge
from graph import graph, EerlyState

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Eerly Studio",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Clean ChatGPT-style, dark background, no sidebar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

/* ── Reset & base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #111111 !important;
    color: #ECECEC;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header,
section[data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none !important; }

/* ── Fixed top navbar ── */
.top-nav {
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 64px;
    background: #111111;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    display: flex;
    align-items: center;
    padding: 0 28px;
    z-index: 9999;
}
.top-nav img {
    height: 40px;
    width: auto;
    /* Invert dark logo to white on dark bg */
    filter: brightness(0) invert(1);
    opacity: 0.88;
}

/* ── Push content below navbar ── */
.main .block-container {
    max-width: 720px !important;
    padding: 80px 24px 140px 24px !important;
    margin: 0 auto !important;
}

/* ── Welcome text ── */
.welcome-wrap {
    text-align: center;
    padding: 80px 0 32px 0;
}
.welcome-title {
    font-size: 26px;
    font-weight: 600;
    color: #ECECEC;
    margin-bottom: 8px;
    letter-spacing: -0.3px;
}
.welcome-sub {
    font-size: 13px;
    color: rgba(255,255,255,0.35);
}

/* ── Message bubbles ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 2px 0 !important;
}

/* ── Agent badge ── */
.agent-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
    margin-bottom: 5px;
    background: rgba(0,112,242,0.12);
    color: #5BA4F5;
    border: 1px solid rgba(0,112,242,0.2);
}
.agent-badge-offline {
    background: rgba(255,140,0,0.1);
    color: #FFA040;
    border: 1px solid rgba(255,140,0,0.2);
}

/* ── Bridge note ── */
.bridge-note {
    border-left: 3px solid rgba(255,140,0,0.4);
    padding: 8px 12px;
    margin: 4px 0 10px 0;
    font-size: 13px;
    color: rgba(255,200,120,0.8);
    background: rgba(255,140,0,0.05);
    border-radius: 0 8px 8px 0;
}

/* ── Chat input ── */
.stChatInput > div {
    background: #1E1E1E !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 14px !important;
}

/* ── Spinner ── */
.stSpinner p { color: rgba(255,255,255,0.45) !important; font-size: 13px !important; }

hr { border-color: rgba(255,255,255,0.06) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def _init():
    if "lc_messages"      not in st.session_state:
        st.session_state.lc_messages      = []
    if "display_messages" not in st.session_state:
        st.session_state.display_messages = []

# ─────────────────────────────────────────────────────────────────────────────
# SAP LLM CHECK (cached)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource(ttl=3000, show_spinner="Connecting to SAP AI Core...")
def _llm_check():
    from sap_llm import SAPChatOpenAI
    SAPChatOpenAI()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# @MENTION PARSER
# ─────────────────────────────────────────────────────────────────────────────
def parse_mention(raw: str) -> tuple[str, str]:
    r = raw.strip()
    if r.lower().startswith("@joule "):
        return "joule",  r[7:].strip()
    return "studio", r


# ─────────────────────────────────────────────────────────────────────────────
# RENDER A SINGLE MESSAGE
# ─────────────────────────────────────────────────────────────────────────────
def render_message(msg: dict):
    role  = msg["role"]
    agent = msg.get("agent", "studio")
    card  = bridge.get_card(agent)

    if role == "user":
        with st.chat_message("user", avatar="🧑"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar=card.get("icon", "🤖")):
            b_status = msg.get("bridge_status", "ok")
            delegated = msg.get("delegated", False)

            # Badge
            if b_status == "offline":
                badge_html = (
                    f'<div class="agent-badge agent-badge-offline">'
                    f'🔌 {card["name"]} · Offline — via A2A Bridge</div>'
                )
            else:
                badge_html = (
                    f'<div class="agent-badge">'
                    f'{card["icon"]} {card["name"]}</div>'
                )
            st.markdown(badge_html, unsafe_allow_html=True)

            # Bridge fallback note
            if msg.get("bridge_note"):
                st.markdown(
                    f'<div class="bridge-note">{msg["bridge_note"]}</div>',
                    unsafe_allow_html=True
                )

            st.markdown(msg["content"])


# ─────────────────────────────────────────────────────────────────────────────
# HANDLE USER MESSAGE → LANGGRAPH
# ─────────────────────────────────────────────────────────────────────────────
def handle_message(raw: str):
    target_agent, clean = parse_mention(raw)

    st.session_state.display_messages.append({"role": "user", "content": raw})

    lc_history = list(st.session_state.lc_messages) + [HumanMessage(content=clean)]

    card = bridge.get_card(target_agent)
    with st.spinner(f"{card['icon']} Thinking..."):
        try:
            result: EerlyState = graph.invoke({
                "messages":      lc_history,
                "user_input":    clean,
                "target_agent":  target_agent,
                "response":      "",
                "agent_used":    target_agent,
                "delegated":     False,
                "bridge_status": "ok",
                "bridge_note":   "",
            })
        except Exception as e:
            st.session_state.display_messages.pop()
            st.error(f"❌ {e}")
            return

    st.session_state.lc_messages = list(result.get("messages", lc_history))
    st.session_state.display_messages.append({
        "role":          "assistant",
        "content":       result.get("response", ""),
        "agent":         result.get("agent_used", "studio"),
        "delegated":     result.get("delegated", False),
        "bridge_status": result.get("bridge_status", "ok"),
        "bridge_note":   result.get("bridge_note", ""),
    })
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    _init()

    # ── Validate credentials ──
    try:
        _llm_check()
    except Exception as e:
        st.error(f"❌ Cannot connect to SAP AI Core: {e}")
        st.stop()

    # ── Fixed top navbar with logo ──
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
    if os.path.exists(logo_path):
        import base64
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<div class="top-nav">'
            f'<img src="data:image/png;base64,{logo_b64}" />'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="top-nav"><span style="color:#fff;font-size:18px;font-weight:700;">eerly.ai</span></div>', unsafe_allow_html=True)

    # ── Welcome screen (shown when no messages) ──
    if not st.session_state.display_messages:
        st.markdown("""
<div class="welcome-wrap">
    <div class="welcome-title">How can I help you today?</div>
    <div class="welcome-sub">
        Type freely &nbsp;·&nbsp; Use <code>@joule</code> to route via A2A Bridge
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Chat history ──
    for msg in st.session_state.display_messages:
        render_message(msg)

    # ── Input ──
    if prompt := st.chat_input("Message Eerly Studio..."):
        handle_message(prompt)


if __name__ == "__main__":
    main()
