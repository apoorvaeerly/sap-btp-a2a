"""
test_adapter.py — Quick isolation test for both bridge adapters.
Run before the full E2E test to confirm each agent is reachable
and responding correctly through the bridge contract.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from bridge.adapter import AgentAdapter, JouleAdapter

DIVIDER = "-" * 60

def test_adapter(name: str, adapter, questions: list[str]):
    print(f"\n{'=' * 60}")
    print(f"  Testing: {name}")
    print(f"  URL    : {adapter.base_url}")
    print(f"{'=' * 60}")

    for q in questions:
        print(f"\nQ: {q}")
        reply = adapter.chat(q)
        preview = reply[:300] + "..." if len(reply) > 300 else reply
        print(f"A: {preview}")
        print(DIVIDER)


if __name__ == "__main__":
    eerly_questions = [
        "What is SAP BTP?",
        "What is the capital of France?",  # should be rejected
    ]

    joule_questions = [
        "What is SAP S/4HANA?",
        "Tell me about Eerly AI Studio.",   # should acknowledge Eerly
        "What is the weather today?",       # should be rejected
    ]

    test_adapter("Eerly Studio (AgentAdapter)", AgentAdapter(), eerly_questions)
    test_adapter("SAP Joule persona (JouleAdapter)", JouleAdapter(), joule_questions)

    print("\nBoth adapters tested. Check responses above.")
    
# from bridge.adapter import AgentAdapter

# def test_chat():
#     adapter = AgentAdapter()
#     print(f"Provider : {adapter.provider}")
#     print(f"Endpoint : {adapter.base_url}/chat")
#     print()

#     test_questions = [
#         "What is SAP S/4HANA?",
#         "How does SAP BTP differ from SAP ECC?",
#         "What is the weather today?",  # should be rejected by SAP Expert persona
#     ]

#     for question in test_questions:
#         print(f"Q: {question}")
#         reply = adapter.chat(question)
#         print(f"A: {reply}")
#         print("-" * 60)

# if __name__ == "__main__":
#     test_chat()