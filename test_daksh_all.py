"""
Automated Test Suite for Daksh & MuktiVerse Integration
Tests all core subsystems non-interactively.
"""
import sys
import asyncio

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import initialize_daksh
from daksh_core import DakshAgent
from tools_hub import ToolsHub
from rag_hub import RAGHub


async def test_subsystems():
    print("=" * 70)
    print("      DAKSH COMPREHENSIVE AUTOMATED TEST SUITE")
    print("=" * 70)

    # 1. Config
    print("\n[TEST 1] Initializing Daksh Configuration...")
    cfg = initialize_daksh()
    assert cfg.DEFAULT_PROVIDER == "ollama"
    print("  -> Config OK!")

    # 2. Tools
    print("\n[TEST 2] Testing Tools Hub & Python Sandbox...")
    tools = ToolsHub()
    tool_list = tools.list_tools()
    assert len(tool_list) >= 8, f"Expected >= 8 tools, found {len(tool_list)}"
    res = await tools.execute_python("print('SANDBOX_OK_' + str(7*6))")
    assert "SANDBOX_OK_42" in res
    print(f"  -> Tools OK! ({len(tool_list)} tools active, Sandbox returned: {res.strip()})")

    # 3. RAG
    print("\n[TEST 3] Testing Hybrid RAG Ingestion & BM25 Search...")
    rag = RAGHub()
    doc = "Quantum computing harnesses superposition and entanglement to perform complex computations."
    chunks = rag.ingest_text("quantum_doc", doc)
    assert chunks >= 1
    matches = rag.search("entanglement", top_k=1)
    assert len(matches) > 0
    assert "entanglement" in matches[0]["content"]
    print(f"  -> RAG OK! (Found match with score {matches[0]['score']})")

    # 4. Memory
    print("\n[TEST 4] Testing Redis Short-Term Memory...")
    from muktiverse.memory.short_term import ShortTermMemory
    mem = ShortTermMemory(conversation_id="test_suite_conv")
    await mem.add_message("user", "Unit test memory test")
    messages = await mem.get_messages(limit=5)
    assert len(messages) > 0
    assert messages[-1]["content"] == "Unit test memory test"
    print("  -> Memory OK! (Retrieved recent messages from Redis)")

    # 5. DAG Orchestrator Planning
    print("\n[TEST 5] Testing MuktiVerse DAG Orchestrator Planning...")
    from muktiverse.orchestrator.intent import IntentEngine
    from muktiverse.orchestrator.planner import TaskPlanningEngine
    
    intent_eng = IntentEngine()
    planner = TaskPlanningEngine()
    intent = await intent_eng.analyze(user_message="Build a web scraper and save to CSV")
    plan = await planner.create_plan(user_message="Build a web scraper and save to CSV", intent=intent)
    tasks = plan.get_all_tasks()
    assert len(tasks) >= 1
    print(f"  -> Orchestrator OK! (Generated DAG with {len(tasks)} nodes: {[n.agent_name for n in tasks]})")

    # 6. Judge Agent
    print("\n[TEST 6] Testing Judge Agent Evaluation...")
    from muktiverse.agents.judge import JudgeAgent
    from muktiverse.agents.base import AgentContext
    judge = JudgeAgent()
    verdict = await judge.evaluate(
        original_task="Explain gravity",
        response_to_evaluate="Gravity is a fundamental interaction that causes mutual attraction between all things with mass.",
        context=AgentContext(user_id="test", conversation_id="test_judge")
    )
    assert verdict is not None
    print(f"  -> Judge OK! (Passed: {getattr(verdict, 'passed', True)}, Confidence: {getattr(verdict, 'confidence_score', 1.0):.2f})")

    print("\n" + "=" * 70)
    print("  ALL CORE DAKSH SUBSYSTEMS PASSED AUTOMATED VERIFICATION!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_subsystems())
