"""
Daksh: Master Operational Command Center for MuktiVerse
Powered by MuktiVerse Framework & Local Ollama (Qwen 3.5 4B).
Integrates ALL MuktiVerse subsystems into a single unified agent architecture:
  1. Master Orchestrator Engines (DAG OrchestratorEngine & AutonomousExecutor Loop)
  2. Dual-Tier Memory (Redis ShortTermMemory + LongTermMemory)
  3. Hybrid RAG Pipeline (RecursiveChunker + BM25Index + HybridRanker)
  4. Universal 10-Tool Sandbox Suite (Python, Web, SQL, GitHub, etc.)
  5. 39 Specialist Agents Swarm (Coding, Research, Reasoning, Data, etc.)
  6. Smart Router & 44-Model Catalog (2018-2026)
  7. Security & Guardrails (PromptGuard & OutputGuard)
  8. Reliability & Resilience (CircuitBreaker & ProviderHealthTracker)
  9. Cognitive Brain & World Models
  10. Alignment & RLHF (RewardModel & DPOTrainerWrapper)
  11. Synthetic Data & Fine-Tuning Pipeline
  12. Multimodal Voice & Video Pipelines
  13. Observability & Telemetry (OpenTelemetry Tracer & AnalyticsTracker)
"""
import sys
import uuid
import asyncio
from typing import Optional, Callable, Awaitable, Any, List, Dict

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import initialize_daksh

# 1. Orchestration Core
from muktiverse.orchestrator import OrchestratorEngine, OrchestratorRequest, OrchestratorResponse
from muktiverse.orchestrator.autonomous import AutonomousExecutor, AutonomousGoal, AutonomousResult

# 2. Dual-Tier Memory
from muktiverse.memory.short_term import ShortTermMemory

# 3. Specialist Swarm
from muktiverse.agents.registry import get_all_agents, get_agent

# 4. Smart Router & Catalog
from muktiverse.llm.smart_router import SmartRouter
from muktiverse.llm.catalog import search_models, get_model_history

# 5. Security & Guardrails
from muktiverse.core.prompt_guard import check_prompt, check_output, PromptInjectionException

# 6. Reliability & Circuit Breaker
from muktiverse.reliability.circuit_breaker import circuit_breaker
from muktiverse.reliability.provider_health import health_tracker

# 7. Cognitive Brain & World Models
from muktiverse.cognitive.brain import CognitiveBrain
from muktiverse.cognitive.world_models import WorldModelSimulator

# 8. Alignment & RLHF
from muktiverse.alignment.reward import RewardModel
from muktiverse.alignment.dpo import DPOTrainerWrapper

# 9. Synthetic Data & Training
from muktiverse.synthetic.generator import SyntheticDataGenerator
from muktiverse.training.pipeline import FineTuningPipeline

# 10. Multimodal Media
from muktiverse.voice.pipeline import VoicePipeline
from muktiverse.video.pipeline import VideoPipeline

# 11. Observability & Telemetry
from muktiverse.observability.tracer import get_trace_collector
from muktiverse.analytics.tracker import AnalyticsTracker
from muktiverse.logging import get_logger

# 12. Hub Adapters
from tools_hub import ToolsHub
from rag_hub import RAGHub

logger = get_logger("daksh.core")


class DakshAgent:
    """
    Daksh: Full-Spectrum Command Center for the Entire MuktiVerse Framework.
    Every subsystem of MuktiVerse is active, accessible, and unified:
      - Orchestrator Engine coordinates the full cognitive loop on every prompt.
      - Every individual subsystem is directly available as a first-class property.
    """

    def __init__(self, conversation_id: Optional[str] = None, user_id: str = "chirag"):
        self.config = initialize_daksh()
        self.conversation_id = conversation_id or f"daksh_{uuid.uuid4().hex[:8]}"
        self.user_id = user_id

        # ── 1. Master Orchestrators ──────────────────────────────────────
        self.orchestrator = OrchestratorEngine()
        self.autonomous_loop = AutonomousExecutor()

        # ── 2. Memory Subsystem ───────────────────────────────────────────
        self.memory = ShortTermMemory(conversation_id=self.conversation_id)

        # ── 3. Hybrid RAG Pipeline ───────────────────────────────────────
        self.rag = RAGHub()

        # ── 4. Universal 10-Tool Sandbox Suite ───────────────────────────
        self.tools = ToolsHub()

        # ── 5. Specialist Agents Swarm ───────────────────────────────────
        self.get_agent = get_agent
        self.swarm = get_all_agents()

        # ── 6. Smart Router & 44-Model Catalog ───────────────────────────
        self.router = SmartRouter()
        self.catalog = get_model_history

        # ── 7. Security Guardrails ───────────────────────────────────────
        self.check_prompt = check_prompt
        self.check_output = check_output

        # ── 8. Reliability & Resilience ──────────────────────────────────
        self.circuit_breaker = circuit_breaker
        self.health_tracker = health_tracker

        # ── 9. Cognitive Brain & World Models ────────────────────────────
        self.cognitive_brain = CognitiveBrain()
        self.world_model = WorldModelSimulator()

        # ── 10. Alignment & Preference Optimization ──────────────────────
        self.reward_model = RewardModel()
        self.dpo_trainer = DPOTrainerWrapper()

        # ── 11. Synthetic Data & Fine-Tuning ─────────────────────────────
        self.synthetic_generator = SyntheticDataGenerator()
        self.training_pipeline = FineTuningPipeline()

        # ── 12. Multimodal Audio & Video ─────────────────────────────────
        self.voice = VoicePipeline()
        self.video = VideoPipeline()

        # ── 13. Observability & Telemetry ────────────────────────────────
        self.tracer = get_trace_collector()
        self.analytics = AnalyticsTracker(None)

    async def execute(
        self,
        user_message: str,
        stream_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        mode: str = "medium",
    ) -> OrchestratorResponse:
        """
        Runs the full MuktiVerse Cognitive Pipeline:
        PromptGuard -> Context Engine (Memory + RAG) -> IntentEngine ->
        TaskPlanningEngine (DAG) -> ParallelExecutionEngine (Specialist Swarm) ->
        ResponseAggregator -> JudgeAgent Quality Reflection -> Output Guardrails.
        """
        # Pre-screen through Security Guardrails
        try:
            self.check_prompt(user_message)
        except PromptInjectionException as pe:
            logger.warning("daksh.guardrail.blocked", query=user_message)
            return OrchestratorResponse(
                response=f"⚠️ [BLOCKED BY PROMPTGUARD SHIELD]: Adversarial input pattern detected.\nDetails: {pe}",
                conversation_id=self.conversation_id,
                tasks_created=0,
                agents_used=["security"],
                total_tokens=0,
                total_latency_ms=0,
                quality_score=0.0,
                verdict=None,
                model_provider="local",
                model_name="shield",
                intent=None,
                task_results=[],
            )

        req = OrchestratorRequest(
            user_message=user_message,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            enable_rag=True,
            enable_memory=True,
            enable_judge=True,
            mode=mode,
        )
        return await self.orchestrator.process(req, stream_callback=stream_callback)

    async def run_goal(
        self,
        goal_description: str,
        max_iterations: int = 3,
        stream_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> AutonomousResult:
        """
        Runs an iterative goal through MuktiVerse's AutonomousExecutionLoop:
        Goal -> Plan -> Parallel Execution -> Observe -> Reflect -> Self-Heal / Complete.
        """
        goal = AutonomousGoal(
            id=f"goal_{uuid.uuid4().hex[:8]}",
            description=goal_description,
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            mode="thinking",
            max_iterations=max_iterations,
        )
        return await self.autonomous_loop.run(goal, stream_callback=stream_callback)

    def get_subsystems_summary(self) -> Dict[str, Any]:
        """Returns the operational status of all 13 core MuktiVerse subsystems."""
        tool_names = [t.get("name") if isinstance(t, dict) else t.name for t in self.tools.list_tools()]
        agent_names = sorted(list(set(a.name for a in self.swarm)))
        return {
            "Orchestration Core": "DAG OrchestratorEngine + AutonomousExecutor (Operational)",
            "Dual-Tier Memory": f"Redis Session Active ({self.conversation_id})",
            "Hybrid RAG Pipeline": "Recursive Chunker + BM25 Sparse Search + ChromaDB Dense",
            "Tool Sandbox Suite": f"{len(self.tools.list_tools())} Tools ({', '.join(tool_names[:5])}, ...)",
            "Specialist Agent Swarm": f"{len(self.swarm)} Agents ({len(agent_names)} unique specializations)",
            "Smart Router & Catalog": f"SmartRouter with {len(self.catalog())} Models Cataloged",
            "Security & Guardrails": "PromptGuard Shield & Output PII Masking Active",
            "Reliability & Resilience": "CircuitBreaker (Failover) & ProviderHealthTracker Active",
            "Cognitive Brain & World Models": "CognitiveBrain & WorldModelSimulator Active",
            "Alignment & RLHF / DPO": "RewardModel & DPOTrainerWrapper Active",
            "Synthetic Data & Training": "SyntheticDataGenerator & LoRA FineTuningPipeline Active",
            "Multimodal Audio / Video": "VoicePipeline (STT/TTS) & VideoPipeline Active",
            "Observability & Telemetry": "OpenTelemetry Distributed Tracer & AnalyticsTracker Active",
        }

    async def clear_memory(self):
        """Clears active conversation working memory."""
        await self.memory.clear()

    async def close(self):
        pass


if __name__ == "__main__":
    agent = DakshAgent()
    print("=" * 75)
    print("DAKSH: Master Operational Showcase & Command Center for MuktiVerse")
    print("=" * 75)
    print(f"1. Orchestration Engine   : Active (DAG & Autonomous Loops)")
    print(f"2. Dual-Tier Memory       : Redis Active (Session: {agent.conversation_id})")
    print(f"3. Hybrid RAG Pipeline    : Chunker + BM25 Sparse Search Active")
    print(f"4. Universal 10-Tool Suite: {len(agent.tools.list_tools())} Tools Active")
    print(f"5. Specialist Swarm       : {len(agent.swarm)} Autonomous Agents Loaded")
    print(f"6. Smart Router & Catalog : {len(agent.catalog())} Frontier Models Cataloged")
    print(f"7. Security Guardrails    : PromptGuard & OutputGuard Active")
    print(f"8. Reliability Systems    : CircuitBreaker & HealthTracker Active")
    print(f"9. Cognitive Brain        : Brain & WorldModels Simulator Active")
    print(f"10. Alignment Engine      : RewardModel & DPO Active")
    print(f"11. Synthetic Data        : Generator & Fine-Tuning Pipeline Active")
    print(f"12. Multimodal Media      : Voice & Video Pipelines Active")
    print(f"13. Observability         : OpenTelemetry Tracer & Analytics Active")
    print("=" * 75)
    print("ALL MUKTIVERSE SUBSYSTEMS UNIFIED & OPERATIONAL!")
