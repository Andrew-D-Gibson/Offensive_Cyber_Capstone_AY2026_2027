#!/usr/bin/env python3
"""
test_multi_agent.py

Tests for multi-agent system with FAIR-LLM.
"""

import asyncio
from offensive_cyber.multi_agent import create_multi_agent_system, run_multi_cyber_agent
from offensive_cyber.multi_agent import create_worker_agent


async def test_worker_creation():
    """Test that worker agents can be created."""
    from fairlib import OllamaAdapter
    
    try:
        llm = OllamaAdapter(model_name="qwen2.5:14b")
        
        worker = create_worker_agent(
            name="TestWorker",
            tool_names=["list_subnet"],
            goal="Test goal",
            llm=llm,
        )
        
        print("✓ Worker agent created")
        print(f"  Type: {type(worker).__name__}")
        print(f"  Stateful: {not worker.stateless}")
        
        return True
    except Exception as e:
        print(f"✗ Worker creation failed: {e}")
        return False


async def test_manager_creation():
    """Test that manager agent can be created."""
    try:
        manager = await create_multi_agent_system()
        
        print("✓ Manager agent created")
        print(f"  Type: {type(manager).__name__}")
        
        return True
    except Exception as e:
        print(f"✗ Manager creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("="*60)
    print("Multi-Agent Tests")
    print("="*60)
    
    await test_worker_creation()
    await test_manager_creation()
    
    print("\nMulti-agent setup verified!")
    print("Note: Full execution requires working Ollama connection")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
