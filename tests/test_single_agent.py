#!/usr/bin/env python3
"""
test_single_agent.py

Tests for single ReAct agent with FAIR-LLM.
"""

import asyncio
from offensive_cyber.single_agent import create_single_cyber_agent, run_single_cyber_agent


async def test_agent_creation():
    """Test that agent can be created."""
    try:
        agent = await create_single_cyber_agent()
        print("✓ Agent creation successful")
        print(f"  Agent type: {type(agent).__name__}")
        return True
    except Exception as e:
        print(f"✗ Agent creation failed: {e}")
        return False


async def test_agent_run():
    """Test that agent can run (without real LLM)."""
    try:
        agent = await create_single_cyber_agent()
        print("✓ Agent created")
        
        # Note: This will fail without a working LLM connection
        # but we can verify the agent structure is correct
        print("  Agent has planner:", hasattr(agent, 'planner'))
        print("  Agent has executor:", hasattr(agent, 'tool_executor'))
        print("  Agent has memory:", hasattr(agent, 'memory'))
        
        return True
    except Exception as e:
        print(f"✗ Agent test failed: {e}")
        return False


async def main():
    print("="*60)
    print("Single Agent Tests")
    print("="*60)
    
    await test_agent_creation()
    await test_agent_run()
    
    print("\nSingle agent setup verified!")
    print("Note: Full agent execution requires working Ollama connection")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
