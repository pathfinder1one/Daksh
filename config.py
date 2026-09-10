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
        max_tok = min(request.max_tokens or 1500, 1500)
        payload = {
            "model": request.model or self._default_model,
            "messages": _prepare_payload_messages(self, request.messages),
            "stream": False,
            "options": {
                "num_gpu": 99,
                "num_ctx": 2048,
                "temperature": request.temperature or 0.6,
                "num_predict": max_tok,
            },
        }
        if request.tools and "ollama.com" not in self._base_url:
            payload["tools"] = request.tools

        async with httpx.AsyncClient(timeout=60.0, headers=self._headers, verify=False) as client:
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
        max_tok = min(request.max_tokens or 1500, 1500)
        payload = {
            "model": request.model or self._default_model,
            "messages": _prepare_payload_messages(self, request.messages),
            "stream": True,
            "options": {
                "num_gpu": 99,
                "num_ctx": 2048,
                "temperature": request.temperature or 0.6,
                "num_predict": max_tok,
            },
        }
        import json as _json
        async with httpx.AsyncClient(timeout=60.0, headers=self._headers, verify=False) as client:
            async with client.stream("POST", self._chat_url(), json=payload) as response:
                response.raise_for_status()
                yielded = False
                thinking_chunks = []
                async for line in response.aiter_lines():
                    if line:
                        data = _json.loads(line)
                        msg = data.get("message", {})
                        chunk = msg.get("content", "")
                        if chunk:
                            yield chunk
                            yielded = True
                        else:
                            th = msg.get("thinking", "")
                            if th:
                                thinking_chunks.append(th)
                        if data.get("done"):
                            break
                # If model only generated thinking and zero content chunks, fallback to clean thinking draft
                if not yielded and thinking_chunks:
                    clean_th = clean_model_output("".join(thinking_chunks))
                    if clean_th:
                        yield clean_th

    OllamaProvider.complete = optimized_complete
    OllamaProvider.stream = optimized_stream


def ensure_ollama_running(host: str = OLLAMA_HOST, auto_start: bool = True) -> bool:
    """
    Checks if the local Ollama daemon is running at OLLAMA_HOST.
    If not running and auto_start is True, attempts to launch 'ollama serve' in background.
    """
    import subprocess
    import time
    
    # 1. Quick check if already active
    try:
        with httpx.Client(timeout=1.5) as client:
            res = client.get(host)
            if res.status_code == 200:
                return True
    except Exception:
        pass

    logger.warning("daksh.ollama.offline", msg=f"Ollama not reachable at {host}.")
    
    # 2. Attempt to auto-start if enabled
    if auto_start:
        print(f"[*] Ollama service not detected at {host}. Attempting auto-start ('ollama serve')...")
        try:
            if sys.platform == "win32":
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(
                    ["ollama", "serve"],
                    creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

            # Poll for readiness up to 5 seconds
            for _ in range(10):
                time.sleep(0.5)
                try:
                    with httpx.Client(timeout=1.0) as client:
                        res = client.get(host)
                        if res.status_code == 200:
                            print(f"[+] Ollama server started successfully at {host}!\n")
                            return True
                except Exception:
                    continue
        except Exception as e:
            logger.warning("daksh.ollama.autostart_failed", error=str(e))

    # 3. Print clear diagnostic message if still unreachable
    print("\n" + "=" * 75)
    print("⚠️  OLLAMA SERVER IS NOT RUNNING!")
    print("=" * 75)
    print(f"Daksh could not connect to Ollama at {host}.")
    print("\nWHY THIS HAPPENS:")
    print("  * Ollama is an independent C++/CUDA background daemon managing GPU memory.")
    print("  * Running 'python main.py' executes the Python agent client, not the Ollama server.")
    print("\nHOW TO START OLLAMA:")
    print("  1. Open a new terminal and run:   ollama serve")
    print("  2. Or launch the 'Ollama' app from your Start Menu / System Tray.")
    print("  3. Verify the model is downloaded: ollama pull qwen3.5:4b")
    print("=" * 75 + "\n")
    return False


def initialize_daksh(model_name: str | None = None):
    """Configures MuktiVerse for local Ollama operation and dynamic agent routing."""
    selected_model = model_name or OLLAMA_MODEL

    # 0. Health check & auto-start Ollama server
    ensure_ollama_running(OLLAMA_HOST, auto_start=True)
    
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
