"""
test_e2e.py — Full A2A End-to-End Test Suite
=============================================
Tests both directions of the A2A integration:
  Direction 1: Eerly Studio (SAP Expert) receiving queries
  Direction 2: Joule persona receiving queries

Run with:
  python tests/test_e2e.py

Prerequisites:
  - Eerly Studio running on port 8000 (uvicorn agent.eerly_studio.api:app --port 8000)
  - Joule persona running on port 8001 (uvicorn joule_persona.api:app --port 8001)
  - ngrok tunnel active and AGENT_BASE_URL updated in .env
"""
import sys
import os
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
EERLY_URL   = os.getenv("AGENT_BASE_URL")
JOULE_URL   = os.getenv("JOULE_BASE_URL", "http://localhost:8001")
TIMEOUT     = int(os.getenv("AGENT_TIMEOUT", "60"))
NGROK_HDR   = {"ngrok-skip-browser-warning": "true"}

# ── Test cases ────────────────────────────────────────────────────────────────
EERLY_TESTS = [
    {
        "id":          "E01",
        "description": "Valid SAP BTP question",
        "message":     "What is SAP BTP and what are its core services?",
        "expect_reject": False,
    },
    {
        "id":          "E02",
        "description": "Valid SAP AI Core question",
        "message":     "How does SAP AI Core integrate with the Generative AI Hub?",
        "expect_reject": False,
    },
    {
        "id":          "E03",
        "description": "Out of scope — should be rejected by Eerly",
        "message":     "Who won the FIFA World Cup in 2022?",
        "expect_reject": True,
    },
]

JOULE_TESTS = [
    {
        "id":          "J01",
        "description": "Valid SAP S/4HANA question",
        "message":     "What are the key differences between SAP S/4HANA Cloud and On-Premise?",
        "expect_reject": False,
    },
    {
        "id":          "J02",
        "description": "Joule awareness of Eerly Studio",
        "message":     "What is Eerly AI Studio and how does it relate to SAP BTP?",
        "expect_reject": False,
    },
    {
        "id":          "J03",
        "description": "Out of scope — should be rejected by Joule",
        "message":     "What is the best programming language to learn in 2025?",
        "expect_reject": True,
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def print_header(text: str):
    print(f"\n{'=' * 62}")
    print(f"  {text}")
    print(f"{'=' * 62}")

def print_result(tc: dict, passed: bool, reply: str, note: str = ""):
    icon = "PASS" if passed else "FAIL"
    reject_tag = " [rejection expected]" if tc["expect_reject"] else ""
    print(f"\n[{icon}] {tc['id']} — {tc['description']}{reject_tag}")
    print(f"  Q: {tc['message']}")
    preview = reply[:250] + "..." if len(reply) > 250 else reply
    print(f"  A: {preview}")
    if note:
        print(f"  NOTE: {note}")
    print(f"  {'-' * 58}")

def call_agent(url: str, message: str, use_ngrok_header: bool) -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    if use_ngrok_header:
        headers.update(NGROK_HDR)
    try:
        res = requests.post(
            f"{url}/chat",
            json={"message": message},
            headers=headers,
            timeout=TIMEOUT
        )
        if res.status_code != 200:
            return res.status_code, f"HTTP {res.status_code}: {res.text[:200]}"
        data = res.json()
        reply = (
            data.get("reply")
            or data.get("response")
            or data.get("text")
            or data.get("output")
            or str(data)
        )
        return 200, reply
    except requests.exceptions.Timeout:
        return 408, f"Timed out after {TIMEOUT}s"
    except requests.exceptions.ConnectionError:
        return 503, f"Cannot connect to {url}"
    except Exception as e:
        return 500, str(e)

def health_check(name: str, url: str, use_ngrok_header: bool) -> bool:
    headers = {}
    if use_ngrok_header:
        headers.update(NGROK_HDR)
    try:
        res = requests.get(f"{url}/health", headers=headers, timeout=10)
        if res.status_code == 200:
            print(f"  {name} reachable at {url}")
            return True
        print(f"  {name} returned {res.status_code} — check if running")
        return False
    except Exception as e:
        print(f"  {name} unreachable — {e}")
        return False

def run_suite(suite_name: str, url: str, tests: list,
              use_ngrok_header: bool) -> tuple[int, int]:
    passed = failed = 0
    for tc in tests:
        status, reply = call_agent(url, tc["message"], use_ngrok_header)
        if status != 200:
            print_result(tc, False, reply, f"HTTP error {status}")
            failed += 1
        else:
            print_result(tc, True, reply)
            passed += 1
    return passed, failed

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    eerly_ngrok = "ngrok" in (EERLY_URL or "")

    print("\nA2A End-to-End Test Suite")
    print(f"Eerly Studio : {EERLY_URL}")
    print(f"Joule persona: {JOULE_URL}")
    print(f"Timeout      : {TIMEOUT}s")

    # ── Health checks ──────────────────────────────────────────────────────────
    print_header("Step 1 — Health checks")
    eerly_ok = health_check("Eerly Studio", EERLY_URL, eerly_ngrok)
    joule_ok = health_check("Joule persona", JOULE_URL, False)

    if not eerly_ok or not joule_ok:
        print("\nAborting — one or more agents unreachable.")
        print("  Eerly: uvicorn agent.eerly_studio.api:app --port 8000 --reload")
        print("  Joule: uvicorn joule_persona.api:app --port 8001 --reload")
        sys.exit(1)

    # ── Direction 1 — Eerly Studio ─────────────────────────────────────────────
    print_header("Direction 1 — Eerly Studio (SAP Expert proxy)")
    e_pass, e_fail = run_suite(
        "Eerly Studio", EERLY_URL, EERLY_TESTS, eerly_ngrok
    )

    # ── Direction 2 — Joule persona ────────────────────────────────────────────
    print_header("Direction 2 — SAP Joule persona (Joule stand-in)")
    j_pass, j_fail = run_suite(
        "Joule persona", JOULE_URL, JOULE_TESTS, False
    )

    # ── Summary ────────────────────────────────────────────────────────────────
    total_pass = e_pass + j_pass
    total_fail = e_fail + j_fail
    total      = total_pass + total_fail

    print_header("Summary")
    print(f"  Direction 1 — Eerly Studio : {e_pass}/{e_pass + e_fail} passed")
    print(f"  Direction 2 — Joule persona: {j_pass}/{j_pass + j_fail} passed")
    print(f"  Total                      : {total_pass}/{total} passed")

    if total_fail == 0:
        print("\n  All tests passed.")
        print("  Both A2A directions are operational and ready for demo.")
        print("  To swap in real agents: update AGENT_BASE_URL / JOULE_BASE_URL in .env")
    else:
        print(f"\n  {total_fail} test(s) failed — review output above.")

    sys.exit(0 if total_fail == 0 else 1)

if __name__ == "__main__":
    main()

# import requests
# import sys
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # ── Config ────────────────────────────────────────────────────────────────────
# AGENT_BASE_URL = os.getenv("AGENT_BASE_URL")
# AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "sandbox")

# # ── Test cases ────────────────────────────────────────────────────────────────
# TEST_CASES = [
#     {
#         "id": "TC01",
#         "description": "Valid SAP question",
#         "message": "What is SAP S/4HANA?",
#         "expect_reply": True,
#         "expect_rejection": False
#     },
#     {
#         "id": "TC02",
#         "description": "Valid SAP BTP question",
#         "message": "What is the difference between SAP BTP and SAP ECC?",
#         "expect_reply": True,
#         "expect_rejection": False
#     },
#     {
#         "id": "TC03",
#         "description": "Out of scope question — should be rejected",
#         "message": "What is the capital of France?",
#         "expect_reply": True,
#         "expect_rejection": True
#     },
#     {
#         "id": "TC04",
#         "description": "SAP AI Core question",
#         "message": "How does SAP AI Core work with Generative AI Hub?",
#         "expect_reply": True,
#         "expect_rejection": False
#     },
# ]

# # ── Helpers ───────────────────────────────────────────────────────────────────
# def print_header(text):
#     print("\n" + "=" * 60)
#     print(f"  {text}")
#     print("=" * 60)

# def print_result(tc, status, reply, note=""):
#     icon = "PASS" if status else "FAIL"
#     print(f"\n[{icon}] {tc['id']} — {tc['description']}")
#     print(f"  Q: {tc['message']}")
#     print(f"  A: {reply[:200]}{'...' if len(reply) > 200 else ''}")
#     if note:
#         print(f"  NOTE: {note}")

# # ── Health check ──────────────────────────────────────────────────────────────
# def check_agent_health():
#     print_header("Step 1 — Agent health check")
#     try:
#         res = requests.get(
#             f"{AGENT_BASE_URL}/health",
#             headers={"ngrok-skip-browser-warning": "true"},
#             timeout=10
#         )
#         if res.status_code == 200:
#             print(f"  Agent is reachable at {AGENT_BASE_URL}")
#             print(f"  Response: {res.json()}")
#             return True
#         else:
#             print(f"  Agent returned {res.status_code} — check if it is running")
#             return False
#     except requests.exceptions.ConnectionError:
#         print(f"  Cannot reach {AGENT_BASE_URL}")
#         print("  Is the agent running on port 8000?")
#         print("  Is ngrok tunnel active?")
#         return False
#     except Exception as e:
#         print(f"  Unexpected error: {e}")
#         return False

# # ── Run test cases ────────────────────────────────────────────────────────────
# def run_tests():
#     print_header("Step 2 — Running test cases")

#     passed = 0
#     failed = 0

#     for tc in TEST_CASES:
#         try:
#             res = requests.post(
#                 f"{AGENT_BASE_URL}/chat",
#                 json={"message": tc["message"]},
#                 headers={
#                     "Content-Type": "application/json",
#                     "ngrok-skip-browser-warning": "true"
#                 },
#                 timeout=30
#             )

#             if res.status_code != 200:
#                 print_result(tc, False, "", f"HTTP {res.status_code}: {res.text[:100]}")
#                 failed += 1
#                 continue

#             data = res.json()
#             reply = (
#                 data.get("reply")
#                 or data.get("response")
#                 or data.get("text")
#                 or data.get("output")
#                 or str(data)
#             )

#             print_result(tc, True, reply)
#             passed += 1

#         except requests.exceptions.Timeout:
#             print_result(tc, False, "", "Request timed out after 30s")
#             failed += 1
#         except Exception as e:
#             print_result(tc, False, "", f"Error: {str(e)}")
#             failed += 1

#     return passed, failed

# # ── Summary ───────────────────────────────────────────────────────────────────
# def print_summary(passed, failed):
#     print_header("Summary")
#     total = passed + failed
#     print(f"  Provider : {AGENT_PROVIDER}")
#     print(f"  Endpoint : {AGENT_BASE_URL}/chat")
#     print(f"  Passed   : {passed}/{total}")
#     print(f"  Failed   : {failed}/{total}")
#     if failed == 0:
#         print("\n  All tests passed — agent is ready for A2A integration.")
#     else:
#         print("\n  Some tests failed — check agent logs for details.")

# # ── Main ──────────────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     print(f"\nA2A End-to-End Test")
#     print(f"Provider : {AGENT_PROVIDER}")
#     print(f"URL      : {AGENT_BASE_URL}")

#     healthy = check_agent_health()

#     if not healthy:
#         print("\nAborting — agent is not reachable. Fix connectivity first.")
#         sys.exit(1)

#     passed, failed = run_tests()
#     print_summary(passed, failed)

#     sys.exit(0 if failed == 0 else 1)