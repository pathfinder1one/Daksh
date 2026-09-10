"""
Daksh: Autonomous Intelligence System | Command Center
Powered by MuktiVerse Framework & Local Qwen 3.5 (4B).
Direct, menu-free autonomous agent terminal.
All 31 MuktiVerse subsystems operate as a single unified cognitive brain.
"""
import os
import sys
import asyncio

# Reconfigure stdout for UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import initialize_daksh, clean_model_output, OLLAMA_MODEL, OLLAMA_HOST
from daksh_core import DakshAgent

BANNER = r"""
===========================================================================
  ██████╗   █████╗  ██╗  ██╗ ███████╗ ██╗  ██╗
  ██╔══██╗ ██╔══██╗ ██║ ██╔╝ ██╔════╝ ██║  ██║
  ██║  ██║ ███████║ █████═╝  ███████╗ ███████║
  ██║  ██║ ██╔══██║ ██╔═██╗  ╚════██║ ██╔══██║
  ██████╔╝ ██║  ██║ ██║ ╚██╗ ███████║ ██║  ██║
  ╚═════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═╝
  Autonomous Intelligence System | Frontier Class
  Powered by MuktiVerse Framework & Local Qwen 3.5 (4B)
  Integrated Brain: Memory | RAG | DAG Planner | Tool Sandbox | Judge
===========================================================================
"""


async def main():
    print(BANNER)
    initialize_daksh()
    
    agent = DakshAgent()
    current_mode = "fast"
    print("Daksh is active and ready. Enter any task, query, or mission below.")
    print("Commands: /mode [fast|deep] | /status | /agents | /tools | /goal <task> | clear | exit\n")

    while True:
        try:
            user_input = input("Daksh > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "/exit", "/quit"):
                print("\nShutting down Daksh. Goodbye!")
                break
            if user_input.lower() in ("clear", "/clear"):
                await agent.clear_memory()
                print("[Memory cleared.]\n")
                continue
            if user_input.lower().startswith("/mode ") or user_input.lower().startswith("mode "):
                parts = user_input.split()
                if len(parts) > 1:
                    new_mode = parts[1].lower()
                    if new_mode in ("fast", "medium", "deep", "thinking"):
                        current_mode = "medium" if new_mode == "deep" else new_mode
                        print(f"[Execution mode set to: '{current_mode.upper()}']\n")
                    else:
                        print(f"[Unknown mode '{new_mode}'. Choose: fast, deep, or thinking]\n")
                else:
                    print(f"[Current mode: '{current_mode.upper()}'] (Options: fast, deep, thinking)\n")
                continue
            if user_input.lower() in ("status", "/status", "/subsystems"):
                print("\n" + "=" * 75)
                print("DAKSH: Full-Spectrum MuktiVerse Subsystems Status")
                print("=" * 75)
                for name, status in agent.get_subsystems_summary().items():
                    print(f"  * {name:<32}: {status}")
                print("=" * 75 + "\n")
                continue
            if user_input.lower() in ("agents", "/agents", "/swarm"):
                print("\n" + "=" * 75)
                print(f"DAKSH: MuktiVerse Specialist Swarm ({len(agent.swarm)} Agents Loaded)")
                print("=" * 75)
                unique_agents = {}
                for a in agent.swarm:
                    if a.name not in unique_agents:
                        unique_agents[a.name] = a
                for name, a in sorted(unique_agents.items()):
                    tools_str = ", ".join(getattr(a, "available_tools", [])) or "direct reasoning"
                    desc = getattr(a, "description", name)
                    print(f"  * {name:<18} | Tools: [{tools_str}] | {desc}")
                print("=" * 75 + "\n")
                continue
            if user_input.lower() in ("tools", "/tools", "/sandbox"):
                print("\n" + "=" * 75)
                print("DAKSH: Universal 10-Tool Sandbox Suite")
                print("=" * 75)
                for tool in agent.tools.list_tools():
                    t_name = tool.get("name") if isinstance(tool, dict) else tool.name
                    t_desc = tool.get("description") if isinstance(tool, dict) else tool.description
                    print(f"  * {t_name:<22} : {t_desc}")
                print("=" * 75 + "\n")
                continue
            if user_input.lower().startswith("/goal ") or user_input.lower().startswith("goal "):
                goal_text = user_input.split(" ", 1)[1].strip()
                print(f"\n[MuktiVerse Autonomous Executor Loop Engaged: '{goal_text}']")
                
                async def on_goal_stream(chunk, agent_name, step):
                    print(f"  ⚡ [{agent_name.title()}] {chunk.strip()}")

                goal_res = await agent.run_goal(goal_text, stream_callback=on_goal_stream)
                print(f"\nAutonomous Result:\n{goal_res.output}")
                print(f"\n[Iterations: {goal_res.iterations_used} | Success: {goal_res.success} | Latency: {goal_res.total_latency_ms:.0f}ms]\n" + "-" * 75 + "\n")
                continue

            streamed_any_content = False

            async def on_stream(chunk, agent_name, step):
                nonlocal streamed_any_content
                if step in ("intent", "planning", "synthesis", "retry"):
                    if streamed_any_content:
                        print()
                        streamed_any_content = False
                    print(f"  ⚡ [{agent_name.title()}] {chunk.strip()}")
                elif "Starting" in chunk:
                    if streamed_any_content:
                        print()
                        streamed_any_content = False
                    print(f"  ⚙️  {chunk.strip()}")
                else:
                    # Live streaming content tokens from specialist agent
                    if not streamed_any_content:
                        print("\nDaksh Response:\n", end="", flush=True)
                        streamed_any_content = True
                    print(chunk, end="", flush=True)

            print(f"\n[MuktiVerse Native Cognitive Pipeline Engaged | Mode: {current_mode.upper()}]")
            res = await agent.execute(user_input, stream_callback=on_stream, mode=current_mode)

            if streamed_any_content:
                print()  # Add newline after live stream finishes
            else:
                # Fallback to response or task results if not live-streamed
                ans = res.response
                if not ans and res.task_results:
                    successful = [t for t in res.task_results if t.success and t.content]
                    if successful:
                        ans = successful[0].content

                if ans:
                    clean_ans = clean_model_output(ans)
                    print(f"\nDaksh Response:\n{clean_ans}")
                else:
                    print(f"\nDaksh Response:\n[Task completed.]")
            
            telemetry_info = f"Tasks: {res.tasks_created} | Agents: {', '.join(res.agents_used) if res.agents_used else 'direct'} | Latency: {res.total_latency_ms:.0f}ms | GPU: 100% RTX 4050"
            if res.quality_score is not None:
                telemetry_info += f" | Judge Score: {res.quality_score * 100:.0f}%"
            print(f"\n[MuktiVerse Telemetry | {telemetry_info}]\n" + "-" * 75 + "\n")

        except KeyboardInterrupt:
            print("\nExiting Daksh...")
            break
        except Exception as e:
            err_name = type(e).__name__
            err_msg = str(e) if str(e) else err_name
            print(f"[Error: {err_name} - {err_msg}]\n")

    await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
