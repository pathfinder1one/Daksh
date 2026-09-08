"""
Daksh Configuration Manager
Integrates MuktiVerse framework with local Ollama instance running Qwen 3.5 (4B).
Ensures zero hardcoding, dynamic model routing, and GPU-optimized context limits.
"""
import os
import sys
from pathlib import Path

# Ensure UTF-8 stdout/stderr on Windows to avoid charmap UnicodeEncodeErrors in logging
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure MuktiVerse is imported properly
from muktiverse import configure, MuktiVerseConfig, get_config
from muktiverse.logging import get_logger
import muktiverse.llm.selector as selector_module
from muktiverse.llm.ollama import OllamaProvider
from muktiverse.schemas.llm import LLMUsage, LLMResponse
import httpx

logger = get_logger("daksh.config")

# Project Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = DATA_DIR / "memory"
BENCHMARKS_DIR = DATA_DIR / "benchmarks"

for d in (DATA_DIR, MEMORY_DIR, BENCHMARKS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Default LLM Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("DAKSH_MODEL", "qwen3.5:4b")

# Astra Persona System Prompt
ASTRA_SYSTEM_PROMPT = """You are Daksh, an ultra-frontier autonomous intelligence system powered by the MuktiVerse framework and inspired by the architectural capabilities of GPT-6 Astra.

Core Operating Principles:
1. Deep Chain-of-Thought (CoT): Deconstruct complex questions into first principles before answering.
2. Scientific Rigor: State facts precisely, acknowledge uncertainties, and avoid hallucinations.
3. Autonomous Problem Solving: For tasks requiring execution, formulate a step-by-step DAG plan, execute specialists, and verify outputs.
4. Self-Correction: Continuously evaluate your logic. If a hypothesis is flawed, self-correct before concluding.
5. Persistent Knowledge: Ground your context in verified short-term conversation and long-term memory.
"""


import re


def clean_model_output(text: str) -> str:
    """Strips internal reasoning scratchpads, <think> tags, and 'Thinking Process:' outlines."""
    if not text:
        return text
    # 1. Remove XML think tags
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"^.*?</think>", "", text, flags=re.DOTALL)
    
    # 2. If 'Thinking Process:' is present, slice to the actual answer heading
    if "Thinking Process:" in text or "Thinking Process" in text:
        match = re.search(
            r"(?:###|##|\*\*Executive Summary|\*\*Detailed Findings|\*\*Overview|\*\*Summary|\*\*Introduction).*$",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if match:
            text = match.group(0).strip()
        else:
            paragraphs = text.split("\n\n")
            non_thinking = [
                p for p in paragraphs
                if not re.match(r"^(Thinking Process|[\d\.\s]+|\*+|[A-Z\s]+Process|Rule\s+\d+)", p.strip(), flags=re.IGNORECASE)
            ]
            if non_thinking:
                text = "\n\n".join(non_thinking).strip()

    # 3. Strip any leftover preamble like '*Okay, plan is solid.*'
    text = re.sub(r"^\*?[a-zA-Z\s,']+(?:plan is solid|write the response|draft the content)\.\*?", "", text, flags=re.IGNORECASE).strip()
    return text.strip()


def _patch_ollama_for_local_gpu():
    """
    Optimizes MuktiVerse OllamaProvider for local GPU execution:
      1. Forces num_ctx=4096 so models fit 100% in GPU VRAM (no slow CPU offloading).
      2. Injects anti-scratchpad directives so models do not waste tokens on internal monologues.
      3. Cleanly filters out thinking traces so user receives only finalized content.
    """
    def _prepare_payload_messages(self, messages):
        dicts = self._messages_to_dicts(messages)
        directive = (
            "\n[CRITICAL OUTPUT DIRECTIVE: Output ONLY the final response. "
            "DO NOT include any 'Thinking Process:', reasoning outlines, scratchpad notes, or rule-checking logs. "
            "Begin immediately with the final synthesized answer.]"
        )
        if dicts and dicts[0]["role"] == "system":
            dicts[0]["content"] += directive
        else:
            dicts.insert(0, {"role": "system", "content": directive.strip()})
        return dicts

    async def optimized_complete(self, request):
        elapsed = self._timer()
        max_tok = min(request.max_tokens or 2048, 2048)
        payload = {
            "model": request.model or self._default_model,
            "messages": _prepare_payload_messages(self, request.messages),
            "stream": False,
            "options": {
                "num_gpu": 99,
                "num_ctx": 4096,
                "temperature": request.temperature or 0.6,
                "num_predict": max_tok,
            },
        }
        if request.tools and "ollama.com" not in self._base_url:
            payload["tools"] = request.tools

        async with httpx.AsyncClient(timeout=180.0, headers=self._headers, verify=False) as client:
            response = await client.post(self._chat_url(), json=payload)
            response.raise_for_status()
            data = response.json()

        message = data.get("message", {})
        content = message.get("content", "").strip()
        thinking = message.get("thinking", "").strip()
        
        # Clean response and strip any Thinking Process leakage
        final_answer = clean_model_output(content or thinking)

        tool_calls = message.get("tool_calls", [])
        usage = LLMUsage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        )
        return self._build_response(
            content=final_answer,
            model=data.get("model", request.model or self._default_model),
            usage=usage,
            latency_ms=elapsed(),
            tool_calls=tool_calls,
            raw=data,
        )

    async def optimized_stream(self, request):
        max_tok = min(request.max_tokens or 2048, 2048)
        payload = {
            "model": request.model or self._default_model,
            "messages": _prepare_payload_messages(self, request.messages),
            "stream": True,
            "options": {
                "num_gpu": 99,
                "num_ctx": 4096,
                "temperature": request.temperature or 0.6,
                "num_predict": max_tok,
            },
        }
        import json as _json
        async with httpx.AsyncClient(timeout=180.0, headers=self._headers, verify=False) as client:
            async with client.stream("POST", self._chat_url(), json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = _json.loads(line)
                        msg = data.get("message", {})
                        # Stream only the clean final content, not the internal thinking scratchpad
                        chunk = msg.get("content", "")
                        if chunk:
                            yield chunk
                        if data.get("done"):
                            break

    OllamaProvider.complete = optimized_complete
    OllamaProvider.stream = optimized_stream


def initialize_daksh(model_name: str | None = None):
    """Configures MuktiVerse for local Ollama operation and dynamic agent routing."""
    selected_model = model_name or OLLAMA_MODEL
    
    # 1. Apply GPU optimization patch
    _patch_ollama_for_local_gpu()

    # 2. Base Framework Configuration
    configure(
        default_provider="ollama",
        ollama_url=OLLAMA_HOST,
        ollama_model=selected_model,
        orchestrator_provider="ollama",
        orchestrator_model=selected_model,
        judge_provider="ollama",
        judge_model=selected_model,
        vector_store_backend="memory",
        sandbox_enabled=True,
    )
    
    # 3. Dynamic Model Router Alignment:
    # Route all MuktiVerse task types dynamically to local Ollama without hardcoded fallbacks
    for mode_name, r_map in selector_module.MODE_ROUTING_MAP.items():
        for task_type in r_map:
            r_map[task_type] = [("ollama", selected_model)]

    logger.info("daksh.initialized", provider="ollama", model=selected_model, host=OLLAMA_HOST)
    return get_config()


if __name__ == "__main__":
    cfg = initialize_daksh()
    print("=" * 60)
    print("Daksh Config Initialized Successfully!")
    print(f"Provider          : {cfg.default_provider}")
    print(f"Model             : {cfg.ollama_model}")
    print(f"Host              : {cfg.ollama_url}")
    print(f"Orchestrator Model: {cfg.orchestrator_model}")
    print(f"Judge Model       : {cfg.judge_model}")
    print(f"Vector Store      : {cfg.vector_store_backend}")
    print("=" * 60)
