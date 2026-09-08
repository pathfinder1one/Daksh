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
    print("Daksh is active and ready. Enter any task, query, or mission below.")
    print("Commands: /status (Subsystems) | /agents (Swarm) | /tools (Sandbox) | /goal <task> (Autonomous Loop) | clear | exit\n")

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

            async def on_stream(chunk, agent_name, step):
                if step in ("intent", "planning", "synthesis", "retry"):
                    print(f"  ⚡ [{agent_name.title()}] {chunk.strip()}")
                elif "Starting" in chunk:
                    print(f"  ⚙️  {chunk.strip()}")

            print("\n[MuktiVerse Native Cognitive Pipeline Engaged]")
            res = await agent.execute(user_input, stream_callback=on_stream)

            if res.response:
                clean_ans = clean_model_output(res.response)
                print(f"\nDaksh Response:\n{clean_ans}")
            
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
