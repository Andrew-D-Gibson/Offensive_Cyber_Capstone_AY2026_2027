FAIR-LLM Architecture Overview

  1. Core Design Philosophy

  FAIR-LLM is built on four foundational principles implemented through strict interface-driven design:

  ┌───────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────┐
  │   Principle   │                                          Implementation                                           │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Flexible      │ Every component inherits from an Abstract* base class in fairlib.core.interfaces/, enabling       │
  │               │ swapable implementations without modifying core logic.                                            │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Agnostic      │ Model Abstraction Layer (MAL) in modules/mal/ provides uniform AbstractChatModel interface across │
  │               │  providers.                                                                                       │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Interoperable │ Standardized data structures (Message, Document, Thought, Action, Observation, FinalAnswer) flow  │
  │               │ consistently through all components.                                                              │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Reasoning     │ The ReAct pattern is first-class, with planners that produce structured                           │
  │               │ Thought/Action/Observation cycles.                                                                │
  └───────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────┘

  ---
  2. Core Data Structures
  
  Message (fairlib.core.message)

  The central data structure for conversation history:

  @dataclass
  class Message:
      role: Literal["user", "assistant", "system", "tool"]
      content: str
      tool_calls: Optional[List[Dict]] = None  # For function/tool calling APIs
      name: Optional[str] = None               # Tool name when role="tool"
      tool_call_id: Optional[str] = None       # Links requests to results
      metadata: Dict[str, Any] = field(...)    # Custom data
      importance: Literal["pinned", "normal"]  # Signals survival through summarization

  Idiosyncrasy: importance="pinned" is honored by SummarizingMemory.aget_history() but NOT by the sync get_history().
  Agents calling through SimpleAgent.arun() use the async path and get pinning; direct sync callers do not.

  ReAct Loop Types

  The framework treats reasoning steps as first-class data:

  - Thought: Agent's internal monologue explaining the next step
  - Action: Tool selection + input (named tool_name, tool_input)
  - Observation: Tool execution result stored as role="system" message
  - FinalAnswer: Conclusive response ending the cycle

  ---
   3. Interface Layer (fairlib.core.interfaces/)
   
   This directory is the architectural DNA of the framework. Each interface defines a "contract" that concrete
   implementations must fulfill. The framework now has 16 core interfaces, ensuring type-safe composition and
   runtime polymorphism without conditional logic.

   ┌────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
   │         Interface          │                             Purpose                                         │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractChatModel          │ LLM integration (invoke, stream, async variants) with context window warnings       │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractPlanner            │ Brain: analyzes history and decides next Thought/Action or FinalAnswer                │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractTool               │ Effects: execute code with typed input/output schemas, side-effect classification     │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractToolRegistry       │ Registry: manages tools with type-safe and name-based lookups                         │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractMemory             │ Memory: short-term conversation storage + long-term retrieval (RAG)                   │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractVectorStore        │ Vector DB: FAISS/ChromaDB backends for semantic search in RAG                         │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractRetriever          │ Retrieval: semantic search over vector store with optional reranking                   │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractEmbedder           │ Embeddings: Sentence Transformers integration for document representation               │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractSecurityManager    │ Security: input validation (sandboxing is NOT secure - interface only)                 │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractPerception         │ Perception: preprocess raw inputs (text parsing, audio processing, etc.)               │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractCheckpoint         │ Persistence: agent state checkpoints for crash recovery                                 │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractSessionStore       │ Session: store/retrieve complete conversation sessions (JSON format)                   │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractSessionRegistry    │ Session Registry: manage multiple active sessions with status tracking                 │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractEventBus           │ Observability: typed event system (AgentStepEvent, PlannerParseErrorEvent, etc.)      │
   ├────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
   │ AbstractResponsePool       │ Response pool: template cycling for deterministic outputs                               │
   └────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────┘

   Key Design Principles:

   - Async-First Contract: All interfaces define async methods (ainvoke, aplan, arun) as primary. Concrete
     implementations provide native async support where possible (e.g., OpenAIAdapter uses AsyncOpenAI client).

   - Type-Safe Interchangeability: The Framework never checks concrete types at runtime. Consumers depend only on
     interface contracts, enabling hot-swapping:
       - Swap OpenAIAdapter → AnthropicAdapter → OllamaAdapter for different models
       - Swap ReActPlanner → ManagerPlanner for different reasoning strategies
       - Swap WorkingMemory → SummarizingMemory for long conversations

   - Side-Effect Classification: Toolsdeclare one of three side effects (READ_ONLY, MUTATING, EXTERNAL) to enable
     parallel execution where safe. READ_ONLY tools run in parallel; MUTATING/EXTERNAL execute sequentially.

   - Observation Marking: Tool results include a metadata key `fairlib.observation=True` for memory sanitation.
     Summarization and checkpoint recovery recognize observations STRUCTURALLY by this marker, not by text patterns.

  ---
   4. Model Abstraction Layer (MAL)
   
   Located in fairlib.modules.mal/, the Model Abstraction Layer (MAL) provides uniform AbstractChatModel
   interfaces across all LLM providers. The layer includes resilience features (circuit breakers, timeout handling,
   degenerate response classification) and structured observability via AbstractEventBus.

   ┌─────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────┐
   │         Adapter             │                             Key Features                                         │
   ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
   │ OpenAIAdapter               │ Native async (AsyncOpenAI client), tool_calls metadata, resilience via Resilience  │
   ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
   │ AnthropicAdapter            │ Separates system prompts (required by Claude), stream_with_history, resilience      │
   ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
   │ OllamaAdapter               │ Local inference via HTTP/JSON, native async with httpx, streaming support         │
   ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
   │ HuggingFaceAdapter          │ Local models with tokenizer-based token estimation, CUDA/OOM detection (GPU OOM    │
   │                             │ mapped to DegradedResponse.Kind.RESOURCE_EXHAUSTED)                               │
   ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
   │ LoadBalancerAdapter         │ Distributed vLLM clusters, round-robin across endpoints, circuit breaker integration │
   │                             │ tracks healthy/unhealthy endpoints and prevents routing to failing instances      │
   ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────┤
   │ Resilience Layer (resilience.py) │ Circuit breaker, timeout, retry logic for all MAL adapters. DegradedResponse    │
   │                             │ carries typed classification (RATE_LIMIT, TIMEOUT, AUTH, QUOTA, CONTEXT_LENGTH,  │
   │                             │ etc.) and recovery policy (retryable, should_compress, retry_after)              │
   └─────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────┘

   Contract: All adapters implement AbstractChatModel. The critical methods:
   - invoke(messages) → Message (sync single response)
   - ainvoke(messages) → Message (async single response, primary interface)
   - stream(messages) → Iterator[Message] (sync streaming)
   - astream(messages) → AsyncIterator[Message] (async streaming, preferred)

   Error Handling: All adapters raise DegradedResponse (subclass of AdapterError) on failures. The Kind enum
   provides typed classifications:
     - RATE_LIMIT, TIMEOUT, CONNECTION, SERVER_ERROR: retryable=True, should_compress=False
     - AUTH, QUOTA, BAD_REQUEST: retryable=False
     - CONTEXT_LENGTH, RESOURCE_EXHAUSTED: retryable=False, should_compress=True (caller must shrink context)

   Async-First Implementation: All public MAL methods are async. OpenAIAdapter uses AsyncOpenAI directly; OllamaAdapter
   uses httpx.AsyncClient natively. No asyncio.to_thread delegation needed for network-bound I/O.
  
  ---
   5. Planner System
   
   Planners analyze conversation history and decide the next agent step (Thought + Action, or FinalAnswer). They own
   their own memory serialization via format_turn_for_memory(), ensuring complete pluggability without adapter code.

   Multi-Planner Architecture:
   - ReActPlanner: JSON-based planner for powerful models (GPT-4o, Claude Opus)
   - SimpleReActPlanner: Key-value format for smaller/local models (falls back to JSON if KV parsing fails)
   - MultiActionReActPlanner: Issues multiple tool calls in a single turn under one shared Thought
   - ManagerPlanner: For hierarchical multi-agent systems (only outputs delegate or final_answer)

   A. ReActPlanner (modules/planning/react_planner.py)

   JSON-based planner for powerful models (GPT-4, Claude Opus):

   # Mandatory response format:
   {
       "thought": "Reasoning about the next step",
       "action": {
           "tool_name": "safe_calculator",
           "tool_input": "10 + 5 * (2 - 3)"
       }
   }

   Key features:
   - Automatic merging of mandatory JSON instructions with user-provided prompts (via BaseTextPlanner base class)
   - PlannerParseError raised on malformed responses (triggers agent retry-with-corrective-message loop)
   - format_turn_for_memory() serializes steps as the same JSON shape for history consistency
   - Sanitizer integration: optional response sanitization to prevent degenerate output patterns

   B. SimpleReActPlanner (modules/planning/simple_react_planner.py)

   Key-value format for smaller/local models:

   {
       "thought": "Reasoning about the next step",
       "action": {
           "tool_name": "safe_calculator",
           "tool_input": "10 + 5 * (2 - 3)"
       }
   }

   Parses KV format first, falls back to JSON parsing if the KV pattern fails. Designed for models that struggle with
   strict JSON structure but perform better with explicit key-value lines.

   C. MultiActionReActPlanner (modules/planning/multi_action_planner.py)

   Issues multiple tool calls in parallel within a single turn:

   {
       "thought": "I need to gather information from multiple tools",
       "actions": [
           {"tool_name": "safe_calculator", "tool_input": "10 + 5"},
           {"tool_name": "weather_tool", "tool_input": "New York"}
       ]
   }

   Key features:
   - Emits ToolCallBatch instead of (Thought, Action) tuple
   - Side-effect-aware batch dispatch: READ_ONLY tools execute in parallel; MUTATING/EXTERNAL tools run sequentially
   - Memory serialization preserves all actions in one assistant message for round-trip fidelity

   D. ManagerPlanner (modules/planning/manager_planner.py)

   Specialized planner for hierarchical multi-agent systems. Only outputs delegate or final_answer (no regular tool calls).

   Delegate format:
   {
       "thought": "I should delegate to the research worker",
       "action": {
           "tool_name": "delegate",
           "tool_input": {"worker_name": "research_worker", "task": "..."}
       }
   }

   Workers execute in stateless mode (clear memory before each run) and return results as role="system" messages. The
   ManagerPlanner parses JSON robustly with regex fallback to handle non-strict model outputs.

   Architectural Decision: Planners own their memory serialization via format_turn_for_memory(). The agent never
   hard-codes how steps are stored — this keeps planners swappable without modifying core ReAct loop logic.

  ---
   6. Agent Implementation
   
   SimpleAgent (modules/agent/simple_agent.py)

   The core single-agent implementation orchestrating the ReAct loop:

   User Input → Normalize → [ReAct Loop] → Final Answer
                            ├─ Planner.aplan() → (Thought, Action) | ToolCallBatch | FinalAnswer
                            ├─ ToolExecutor.aexecute() → Observation(s)
                            └─ Memory.add_message()

   Key Features:
   - Validator Path: With validator= argument, runs ReAct cycle then validates the final answer. On rejection, retries via
     direct LLM call (bypassing planner) while preserving tool observations in memory.
   - Stateless Mode: clear_memory() before each run for worker agents in multi-agent systems
   - Event Emission: Emits typed events via AbstractEventBus (AgentStepEvent, PlannerParseErrorEvent, ResponseRepeatEvent)
   - Checkpoint/Trace: arun_with_trace() returns structured AbstractAgentRunTrace for observability; save_state() creates
     lightweight checkpoints with history length anchor points
   - Error Handling: Distinct typed exceptions (PlannerParseError, AdapterError, ToolInvocationError, MaxStepsExceeded,
     ValidatorRejectedError, ValidatorError)

   Tool Call Dispatch Lifecycle:
   1. Planner returns (Thought, Action), ToolCallBatch, or FinalAnswer
   2. ToolExecutor dispatches:
      - READ_ONLY tools → run in parallel
      - MUTATING/EXTERNAL tools → run sequentially (barriers between batches)
   3. Each tool result becomes a role="system" observation message with fairlib.observation=True metadata
   4. Memory.add_message() stores all observations in original call order

   State Management:
   - instance-scoped history list (not shared across agent instances)
   - checkpoint system stores only history length, not message content (lightweight)
   - session persistence saves complete conversation as JSON for crash recovery

   Idiosyncrasy: Validator retries do NOT re-run tools or re-enter planner. The contract is "your reasoning was correct,
   only rewrite the wrap-up." Rejected responses are never committed to memory.

  ---
   7. Multi-Agent System
   
   HierarchicalAgentRunner (modules/agent/multi_agent_runner.py)

   Manager-Worker Pattern:

   1. Manager analyzes task and breaks into sub-tasks, planning delegation via ManagerPlanner
   2. Delegates to workers via delegate tool with JSON:
      {"tool_name": "delegate", "tool_input": {"worker_name": "...", "task": "..."}}
   3. Workers execute in stateless mode (memory cleared before run) and return results as role="system" observations
   4. Manager receives observations, synthesizes final answer

   Worker Agents:
   - Created with clear_memory=True (stateless mode)
   - Each worker gets its own instance-scoped memory, preventing cross-contamination
   - Role descriptions (Agent.role_description) identify capabilities to the manager
   - Workers can themselves be multi-step ReAct agents, enabling nested hierarchies

   Manager Planning:
   - ManagerPlanner only outputs delegate or final_answer (no regular tool calls)
   - Worker names must match registered worker agents in the runner
   - Delegation errors (unknown worker name) surface as ValidatorRejectedError or AdapterError

   Event Bus Integration:
   - HierarchicalAgentRunner exposes AbstractEventBus at self.events
   - Emits AgentStepEvent for each manager/worker turn
   - Trace recording (arun_with_trace) captures full multi-agent run structure

   Example Use Cases:
   - Research team: manager delegates to web_searcher, literature_reviewer, data_analyst workers
   - Coding assistant: manager delegates to code_writer, unit_tester, debugger workers
   - Essay grading: manager delegates to outline_builder, draft_writer, rubric_grader workers

  ---
   8. Memory System
   
   A. WorkingMemory (modules/memory/base.py)

   Simple FIFO buffer with system prompt preservation:
   - max_size parameter controls total message count (default=20)
   - Trimming: keeps system prompt at index 0, then most recent (max_size-1) messages
   - Does NOT honor Message.importance="pinned" — simple design for short conversations

   B. SummarizingMemory (modules/memory/summarization.py)

   Smart truncation with LLM-powered summarization:

   [system] + [pinned messages] + [LLM summary of remaining] + [recent n messages]

   Key features:
   - Triggers summarization when history exceeds max_history_length (configurable)
   - Honors Message.importance="pinned" — pinned messages excluded from summarization input and reinserted at original positions
   - Warning emitted if pinned messages exceed 80% of capacity
   - Async path (aget_history) honors pinning; sync fallback logs warning but still works

   Summarization Strategy:
   - Identifies contiguous non-pinned segment to summarize
   - Calls LLM: "Summarize this conversation history concisely, preserving facts and decisions"
   - Replaces segment with single summary message, reinserts pinned messages at original positions

   C. LongTermMemory / RAG (modules/memory/base.py)

   Vector store-backed long-term memory for Retrieval-Augmented Generation:

   - Documents embedded via AbstractEmbedder (SentenceTransformerEmbedder, DummyEmbedder)
   - Stored in vector backends (FaissVectorStore, ChromaDBVectorStore, InMemoryVectorStore)
   - Retrieved via SimpleRetriever (wraps AbstractRetriever interface)
   - Optional cross-encoder reranking in retriever_rerank.py (HybridRetrievalResult with reranked scores)

   Integration:
   - add_document() accepts plain text or list of strings, wraps in Document objects
   - retrieve_relevant_chunks() returns plain text list (not Document objects)
   - metadata_filter parameter enables filtering by document source, tags, etc.

   Vector Store Backends:
   - FaissVectorStore: CPU/GPU acceleration via FAISS, persistent index saving/loading
   - ChromaDBVectorStore: Production-ready with persistence, metadata filtering, full-text search
   - InMemoryVectorStore: Fast for testing/demos, lost on restart

   D. Message.importance="pinned" Design

   Signal from caller that a message must survive summarization verbatim:
   - Honored by SummarizingMemory.aget_history() in async path (preferred)
   - Sync fallback (get_history) logs warning but still works
   - Agents using SimpleAgent.arun() get the async path automatically (pinning honored)
   - Direct callers using get_history() get sync behavior (not pinned)

   Best Practice: Use sparingly. Excessive pinning defeats summarization purpose. SummarizingMemory warns at 80% capacity.

  ---
   9. Tool System
   
   A. AbstractTool Interface (core/interfaces/tools.py)

   Modern typed interface replacing string-based use()/ause():

   class AbstractTool(ABC):
       # Core attributes (class or instance variables)
       name: str
       description: str
       input_schema: Type[BaseModel]      # Pydantic schema for validated input
       output_schema: Type[ToolOutput]    # Pydantic schema for validated output
       side_effect: SideEffect             # READ_ONLY, MUTATING, EXTERNAL
       required_capability: Optional[str]  # For capability-based routing

       # Primary method (async only)
       async def acall(self, tool_input: BaseModel) -> ToolOutput:
           """Run the tool's logic over a validated input model."""
           ...

   Key Improvements Over String-Based Interface:
   - Type Safety: Input/output validated via Pydantic schemas before execution
   - Error Messages: Schema validation failures include rendered schema hints for model feedback
   - Side-Effect Dispatch: READ_ONLY tools run in parallel; MUTATING/EXTERNAL sequential
   - No Raw Strings: Tools receive validated models, return structured outputs

   B. Built-in Tools (modules/action/tools/)

   Core Built-in Tools (13+ total):

   - SafeCalculatorTool: AST-based math evaluation (safe from code injection)
   - AdvancedCalculusTool: Symbolic calculus (differentiation, integration, limits)
   - WebSearcherTool: Google CSE integration with result extraction
   - WeatherTool: Weather API wrapper with location lookup
   - GraphingTool: Plot generation via matplotlib (returns PNG base64)
   - KnowledgeBaseQueryTool: RAG queries against vector store

   File System Tools:
   - ReadFileTool: Safe file reading (path validation, rooted to safe directory)
   - WriteFileTool: Safe file writing (overwrites existing, no path traversal)
   - EditFileTool: Line-by-line file editing with context matching
   - ListDirTool: Directory listing with optional recursive flag
   - GlobTool: Pattern-based file discovery (glob/regex patterns)
   - GrepTool: Text search across files with optional context windows

   Execution & Security:
   - CodeExecutionTool: Sandboxed Python code execution (warning: NOT secure, interface only)
   - ShellTool: Command execution (security warnings apply)

   Data Extraction:
   - WebDataExtractor: Scrapes web pages, extracts tables/time-series, returns structured data
     - Outputs ExtractedData with confidence_score, metadata, columns/rows
     - Supports PDF, Excel, CSV parsing with OCR fallback for image-based docs

   Autograding:
   - GradeEssayFromRubricTool: Essay grading with Pydantic validation rubric
   - GradeCodeFromRubricTool: Code evaluation against rubric with test execution

   System Tools:
   - FinalAnswerTool: Signals task completion (sentinel tool_name="final_answer")

   C. ToolExecutor (modules/action/executor.py)

   Security-validation and dispatch layer between planner decision and tool execution:

   class ToolExecutor:
       def __init__(
           self,
           registry: AbstractToolRegistry,
           security_manager: Optional[AbstractSecurityManager] = None
       ):
           self.registry = registry
           self.security_manager = security_manager

       async def aexecute(self, tool_name: str, tool_input: Any) -> str:
           """Execute a tool and return the observation string."""
           tool = self.registry.get_by_name(tool_name)
           
           # Security validation (optional)
           if self.security_manager and not self.security_manager.validate_input(tool_input):
               return "Error: Input validation failed"
           
           # Validate against tool's Pydantic schema
           try:
               validated_input = tool.input_schema.model_validate(tool_input)
           except ValidationError as e:
               raise ToolInputValidationError(
                   message=str(e),
                   tool_name=tool_name,
                   schema_hint=render_schema_hint(tool.input_schema)
               )
           
           # Dispatch with side-effect awareness
           try:
               output = await tool.acall(validated_input)
               return output.render()  # Default: JSON via model_dump_json()
           except Exception as e:
               raise ToolInvocationError.wrap(tool_name, e)

   Key Features:
   - Schema-based validation before dispatch (prevents invalid inputs reaching tools)
   - Side-effect-aware batch dispatch for parallel execution
   - Typed errors with helpful hints for model feedback (ToolInputValidationError.render_observation())
   - Wraps tool exceptions in ToolInvocationError for consistent error handling

   D. Tool Registry

   AbstractToolRegistry provides type-safe and name-based lookups:

   class ToolRegistry(AbstractToolRegistry):
       def __init__(self):
           self._tools: Dict[str, AbstractTool] = {}
           
       def register_tool(self, tool: AbstractTool) -> None:
           if tool.name in self._tools:
               raise ValueError(f"Tool '{tool.name}' already registered")
           self._tools[tool.name] = tool
           
       def get_all_tools(self) -> Dict[str, AbstractTool]:
           return self._tools.copy()
       
       # Type-safe getters for wiring code
       def get(self, tool_type: Type[T]) -> T:
           """Return single tool instance of type T (raises AmbiguousToolError if multiple)"""
           ...
       
       def try_get(self, tool_type: Type[T]) -> Optional[T]:
           """Like get, but returns None if not found"""
           ...

   CompositeToolRegistry merges multiple registries:
   - Local tools + MCP tools
   - Multiple registry instances for modular tool groups

   E. Side-Effect Classification

   Tools declare exactly one side effect (most restrictive that applies):
   - READ_ONLY: No local state mutation, safe to cache/parallelize (e.g., WebSearcherTool)
   - MUTATING: Modifies local state (e.g., WriteFileTool, EditFileTool)
   - EXTERNAL: Reaches outward to non-deterministic service (e.g., WeatherTool)

   Dispatch Policy:
   - READ_ONLY tools in same batch → execute in parallel
   - MUTATING/EXTERNAL tools → sequential, with barrier before next batch

  ---
   10. Prompt Engineering System
   
   A. Prompt Infrastructure (fairlib.core.prompts/)

   Split by concern across submodules:
   - fairlib.core.prompts.items: Prompt item value types (RoleDefinition, FormatInstruction, etc.)
   - fairlib.core.prompts.builders: PromptBuilder, ManagerPromptBuilder classes
   - fairlib.core.prompts.schema_render: Schema-to-text rendering for tool signatures
   - fairlib.core.prompts.store: Prompt serialization (load/save to YAML)

   B. PromptItem Hierarchy (fairlib.core.prompts.items)

   ┌────────────────────────────┬───────────────────────────────────────────────────────────────────────────┐
   │          Item              │                             Purpose                                          │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ RoleDefinition             │ Agent's role, goal, purpose (e.g., "You are a helpful coding assistant...") │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ FormatInstruction          │ Response format rules (JSON/KV/structured)                                │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ StrictFormatInstruction    │ Explicit DO/DON'T for smaller models (prevents malformed outputs)          │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ Example                    │ Few-shot examples matching agent behavior (assistant-turn format)          │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ ToolInstruction            │ Available tools with descriptions and schemas                              │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ WorkerInstruction          │ Worker agent capabilities (multi-agent systems)                            │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ DelegationExample          │ Single-turn manager delegation demos (multi-agent only)                    │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ EnhancedWorkerInstruction  │ Worker with detailed capability description                                │
   ├────────────────────────────┼───────────────────────────────────────────────────────────────────────────┤
   │ DateContextMixin           │ Auto-adds current date/time to prompts                                     │
   └────────────────────────────┴───────────────────────────────────────────────────────────────────────────┘

   C. PromptBuilder (fairlib.core.prompts.builders)

   Composable, immutable prompt construction with automatic formatting instruction merging:

   PromptBuilder(
       role_definition=RoleDefinition("You are a helpful assistant..."),
       format_instructions=[
           FormatInstruction("Your response MUST be valid JSON..."),
           StrictFormatInstruction.json_output_rules()  # For smaller models
       ],
       examples=[
           Example("user: ..."),  # Few-shot demonstrations
       ],
       tool_instructions=[ToolInstruction("tool_name", "description")]
   )

   Key Features:
   - Immutable (frozen dataclass) for predictable caching
   - Mandatory format instructions always merged (cannot be disabled)
   - User customizations affect only role_definition, examples, tool_instructions
   - Cache prepared prompts (avoids rebuilding per turn)

   D. Schema Rendering

   Tool schemas rendered as text for prompt inclusion via fairlib.core.prompts.schema_render:

   - render_schema_fields(tool.input_schema) → "Input fields: field1: str, field2: int"
   - render_schema_example(tool.input_schema) → "Example: {'field1': 'value', 'field2': 42}"
   - render_schema_hint(tool.input_schema) → Full schema description for validation errors

   Used by ToolExecutor.render_observation() to include expected input shape in tool rejection feedback.

   E. Best Practice: Mandatory format instructions are always merged — user customizations affect only role and examples,
   never parsing structure. This guarantees parser compatibility across all prompts.

  ---
   11. MCP (Model Context Protocol) Integration
   
   Full MCP (Model Context Protocol) support in fairlib.modules.mcp/:
   - fairlib.modules.mcp.client: Client for connecting to MCP servers
   - fairlib.modules.mcp.server: Server implementation for hosting MCP servers

   A. MCP Client (client/mcp_client.py)

   Client for connecting to and interacting with MCP servers:

   - MCPClient(config): Main client class for single server connection
     * Supports stdio and SSE transports
     * Manages connection lifecycle (connect/disconnect)
     * Tool discovery via list_tools()
     * Tool invocation via call_tool(name, arguments)
   
   - Key Methods:
     async connect() → establish connection
     async disconnect() → close connection cleanly
     async list_tools() → list available tools with schemas
     async call_tool(name, arguments) → invoke tool and get result
     async with MCPClient(config) as client: → context manager usage

   - Connection Config:
     Transport: stdio or sse (SSE_AVAILABLE=False if not installed)
     Stdio: command + args (e.g., ["npx", "-y", "@modelcontextprotocol/server-filesystem"])
     SSE: url for server endpoint
     Environment variables passed to stdio processes

   B. MCP Tool Adapter (client/mcp_tool_adapter.py)

   Wraps MCP tools as FAIR AbstractTool for seamless integration:

   - MCPToolAdapter(mcp_client, tool_definition)
     *tool_definition: MCP protocol tool schema
     * Adapts MCP tool schemas to Pydantic input/output schemas
     * Implements acall() via MCP client call_tool()

   Integration:
   - MCPToolRegistry combines local tools + MCP tools
   - CompositeToolRegistry merges multiple registries (local, MCP, etc.)

   C. MCP Server (server/mcp_server.py)

   Server implementation for hosting MCP-compatible services:

   - Standalone server mode (uvicorn ASGI app)
   - Handles stdio or SSE transport connections
   - Tool registry integration (exposes local tools via MCP protocol)
   - Type-safe tool schemas via Pydantic

   D. Configuration in config/settings.yml:
   mcp:
     enabled: true
     servers: 
       - name: filesystem
         transport: stdio
         command: npx
         args: ["-y", "@modelcontextprotocol/server-filesystem"]
       - name: sql_database
         transport: sse
         url: "http://localhost:8000/mcp"

   Example Usage:
   from fairlib import MCPClient, MCPToolAdapter, ToolRegistry
   
   # Connect to MCP server
   config = MCPServerConfig(name="filesystem", transport="stdio", ...)
   async with MCPClient(config) as client:
       tools = await client.list_tools()
       result = await client.call_tool("read_file", {"path": "/path/to/file.txt"})

   # Wrap as FAIR tool and add to registry
   for tool_def in tools:
       adapter = MCPToolAdapter(client, tool_def)
       registry.register_tool(adapter)
        
  ---
   12. Configuration System
   
   A. Pydantic Schemas (core/config_schemas.py)

   Canonical configuration schema with Pydantic validation:

   - AppSettings: Top-level settings container
     * api_keys: OpenAI, Anthropic keys (optional)
     * models: Dict of model names to ModelSettings
     * security: Input validation, max input length
     * search_engine: Google CSE credentials and cache settings
     * rag_system: Document paths, embedding settings, vector store config
     * mcp: MCP server configurations

   - ModelSettings:
     * provider: "openai", "anthropic", "ollama", "huggingface"
     * model_name: Specific model identifier (e.g., "gpt-4o")
     * temperature: Sampling temperature (0.0-2.0, default 0.7)
     * max_tokens: Generation length limit

   - SecuritySettings:
     * enable_input_validation: Enable prompt injection detection
     * max_input_length: Maximum user input characters (default 10000)

   - RAG System Settings:
     * paths: files_directory, vector_store_dir
     * document_processing: supported_extensions, max_chunk_chars, OCR settings
     * embedding: model_name (Sentence Transformers), dimensionality
     * vector_store: faiss, chromadb, or inmemory

   B. Configuration Loading (core/config.py)

   Simple direct loading from YAML:

   from fairlib import settings  # Single, validated AppSettings instance

   def load_settings() -> AppSettings:
       config_path = Path(__file__).parent.parent / "config/settings.yml"
       with open(config_path, 'r') as f:
           config_data = yaml.safe_load(f)
       return AppSettings(**config_data)  # Pydantic validates and raises on errors

   settings = load_settings()  # Module-level singleton for import convenience

   No PEP 562 lazy loading of configuration — YAML loads upfront for validation.

   C. Lazy Loading (fairlib/__init__.py)

   FAIR-LLM components use PEP 562 lazy imports for performance:

   - Eagerly loaded: Core types, exceptions, settings (no heavy dependencies)
   - Lazily loaded: Model adapters, planners, tools (import on first use)

   Example:
   from fairlib import settings  # Eager (fast startup)
   from fairlib import OpenAIAdapter  # Lazy, loads on first access

   Benefits:
   - Fast startup (only imports needed modules)
   - IDE autocomplete via TYPE_CHECKING block
   - No circular import issues

   D. Configuration File Structure (config/settings.yml):

   # API Keys (optional - use environment variables for sensitive data)
   api_keys:
     openai_api_key: "sk-..."
     anthropic_api_key: "..."

   # Model configuration
   models:
     openai_gpt4: {provider: openai, model_name: gpt-4o}
     anthropic_claude: {provider: anthropic, model_name: claude-3-opus-20240229}
     local_llama: {provider: ollama, model_name: llama3}

   # Security settings
   security:
     enable_input_validation: true
     max_input_length: 10000

   # Search engine (Google CSE)
   search_engine:
     google_cse_search_api: "..."
     google_cse_search_engine_id: "..."

   # RAG system
   rag_system:
     paths:
       files_directory: "/app/docs"
       vector_store_dir: "/app/vector_store"
     document_processing:
       supported_extensions: [".pdf", ".docx", ".txt", ".csv"]
       max_chunk_chars: 1500
       enable_ocr: true

   # MCP server configuration
   mcp:
     enabled: true
     servers:
       - name: filesystem
         transport: stdio
         command: npx
         args: ["-y", "@modelcontextprotocol/server-filesystem"]

  ---
   13. Error Taxonomy (core/errors.py)
   
   All exceptions inherit from FairlibError for unified error handling:

   ┌───────────────────────────────┬─────────────────────────────────────────────────────────────────────────┐
   │          Exception            │                            When Raised                                  │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ FairlibError                  │ Base class for all framework-raised errors                             │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ PlannerParseError             │ LLM response doesn't match expected format (triggers retry loop)       │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ AdapterError                  │ LLM provider failure (timeout, quota, auth, malformed response)        │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ DegradedResponse              │ Typed adapter degradation signal (subclass of AdapterError)            │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ MCPError                      │ MCP server communication failure                                       │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ ToolInvocationError           │ Tool.acall() raised exception during execution                         │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ ToolInputValidationError      │ tool_input did not match tool's Pydantic input schema                  │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ MaxStepsExceeded              │ Agent reached max_steps without producing FinalAnswer                  │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ InvalidAgentInputError        │ Wrong Message role at agent entry point (expected "user")              │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ ValidatorRejectedError        │ All validator attempts exhausted, all rejected                         │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ ValidatorError                │ Consumer-supplied validator itself raised                              │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ EventBusError                 │ Event bus API misused (non-event type subscribed, non-event emitted)   │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ ConfigurationError            │ Missing/invalid configuration (API key absent, unreadable settings)     │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ DocumentProcessingError       │ Document unreadable, unsupported type, OCR failed                      │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ ToolLookupError               │ Tool registry lookup failure (base for subclass errors)                │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ ToolNotFoundError             │ No tool matches requested type or name                                 │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ AmbiguousToolError            │ Type lookup matched multiple registered tools                          │
   ├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
   │ ToolGroupNotFoundError        │ No tool group registered under requested name                          │
   └───────────────────────────────┴─────────────────────────────────────────────────────────────────────────┘

   DegradedResponse Special Case:

   Typed subclass of AdapterError for provider failures with recovery policy:

   class DegradedResponse(AdapterError):
       kind: Kind  # What went wrong (RATE_LIMIT, TIMEOUT, AUTH, QUOTA, etc.)
       retryable: bool  # True if resending same request may succeed
       should_compress: bool  # True if caller must shrink context first
       retry_after: Optional[float]  # Suggested back-off in seconds
       status_code: Optional[int]  # HTTP status code when available

   Kind Enum:
   - RATE_LIMIT (HTTP 429, transient): retryable=True, should_compress=False
   - TIMEOUT (HTTP 408): retryable=True, should_compress=False
   - CONNECTION: retryable=True, should_compress=False
   - SERVER_ERROR (5xx): retryable=True, should_compress=False
   - AUTH (401/403): retryable=False
   - QUOTA (insufficient credit/billing): retryable=False
   - CONTEXT_LENGTH (prompt too long): retryable=False, should_compress=True
   - RESOURCE_EXHAUSTED (GPU OOM): retryable=False, should_compress=True
   - BAD_REQUEST (400): retryable=False
   - MALFORMED_RESPONSE: retryable=False
   - CIRCUIT_OPEN (fail-fast): retryable=False

   Recovery Policy:
   - retryable=True: Resend same request unchanged after back-off
   - should_compress=True: Shrink context (remove messages, summarize) then retry
   - both flags independent: CONTEXT_LENGTH is should_compress=True, retryable=False

   Example Recovery Flow:
   try:
       result = await agent.arun(user_query)
   except DegradedResponse as e:
       if e.should_compress:
           context = shrink_context(e.history)  # Caller logic
           result = await agent.arun_with_context(user_query, context)
       elif e.retryable:
           await asyncio.sleep(e.retry_after or e.compute_default_backoff())
           result = await agent.arun(user_query)
       else:
           raise UserFacingError(f"Permanent failure: {e.kind}")

   Best Practice: Catch specific exceptions to implement custom recovery logic. DegradedResponse
   provides typed information (kind, retryable, should_compress) instead of parsing error strings.

  ---
   14. Architectural Patterns Summary
   
   A. The ReAct Cycle (Single Agent)

   User Input → Normalize → [ReAct Loop] → Final Answer
                            ├─ Planner.aplan(history) → (Thought, Action) | ToolCallBatch | FinalAnswer
                            ├─ ToolExecutor.aexecute(action) → Observation(s)
                            │   └─ Memory.add_message(observation_msg)
                            └─ Memory.add_message(assistant_turn)
              ↓
         Loop until FinalAnswer

   Details:
   - Entry point: user Message with role="user" (or string auto-converted)
   - Planner decides next step, returns (Thought, Action) or ToolCallBatch or FinalAnswer
   - ToolExecutor dispatches tools based on side_effect classification
   - Each tool result becomes role="system" observation with fairlib.observation=True metadata
   - format_turn_for_memory() serializes step as assistant message for history
   - Loop continues until FinalAnswer (sentinel tool_name="final_answer")

   B. Event Bus System (Observability)

   Typed event system via AbstractEventBus for observability and debugging:

   Events Emitted:
   - AgentStepEvent: Each planner decision + tool execution (thought, actions, observations)
   - PlannerParseErrorEvent: Planner could not parse LLM response (before retry)
   - ResponseRepeatEvent: Same response text observed twice (degenerate output warning)
   - MemorySummarizedEvent: Summarization triggered, with summary and token savings
   - DegradedResponseEvent: Adapter degradation, with kind and recovery policy
   - ToolCallPreEvent, ToolCallPostEvent: Tool execution boundaries (before/after)

   Example Usage:
   from fairlib import AgentEventBus, AgentStepEvent
   
   # subscribe to events
   event_bus = AgentEventBus()
   
   @event_bus.subscribe(AgentStepEvent)
   async def log_step(event: AgentStepEvent):
       print(f"Step {event.step}: {event.thought}")
       for action in event.actions:
           print(f"  → {action.tool_name}({action.tool_input})")
       if event.observations:
           print(f"  ← {event.observations[0].content[:50]}...")

   Arun Options:
   - arun(user_input): Run agent, return final answer
   - arun_with_trace(user_input, trace_metadata=...): Return structured AbstractAgentRunTrace
     * Captures all events during run
     * Includes metadata (timestamp, input text, output)
     * On error: stores failure in trace.last_error

   C. Checkpoint System (Crash Recovery)

   Lightweight state snapshots for agent crash recovery:

   - AgentCheckpoint: history_length + optional metadata
     * stores only length, not message content (lightweight)
     * no serialization overhead of full conversation
   
   - save_state(path=None, metadata=...): Create checkpoint
     * instance-scoped: memory list truncated to history_length
     * path: optional JSON path for persistence

   - load_state(path): Restore from checkpoint
     * truncates in-memory history to saved length
     * replay remaining messages after load

   Usage:
   # crash recovery flow
   try:
       await agent.arun(query)
   except Exception as e:
       checkpoint = agent.save_state(metadata={"error": str(e)})
       # persist checkpoint (e.g., to disk, DB, cloud storage)
       # later...
       agent.load_state(checkpoint_path)
       result = await agent.arun(query)  # continues from saved point

   D. Session Persistence (Complete Conversation Restore)

   Full conversation sessions with JsonSessionStore:

   - SessionRecord: Complete conversation history
     * Messages stored per message.to_dict() (stable JSON shape)
     * role, content, tool_calls, name, tool_call_id, metadata, importance
   
   - SessionStatus: ACTIVE, COMPLETED, CRASHED
   - SessionRegistry: manage multiple sessions by ID

   Usage:
   from fairlib import JsonSessionStore, SessionRegistry
   
   store = JsonSessionStore("out/sessions")
   registry = SessionRegistry(store)
   
   # during run
   registry.set_active(session_id, conversation_history)
   
   # after crash
   state = registry.get(session_id)
   if state == SessionStatus.CRASHED:
       history = store.load(session_id)
       agent = SimpleAgent(..., memory=WorkingMemory.from_history(history))
       result = await agent.arun_with_history(history)

   E. Swapping Components

   Because everything is interface-based, components are swappable without code changes:

   1. Swap LLM Adapters:
      - OpenAIAdapter → AnthropicAdapter → OllamaAdapter
      - All implement AbstractChatModel (ainvoke, astream)
      - No planner changes needed

   2. Swap Planners:
      - ReActPlanner → ManagerPlanner for multi-agent
      - All implement AbstractPlanner (aplan, format_turn_for_memory)
      - AgentReAct loop unchanged

   3. Swap Vector Stores:
      - FaissVectorStore → ChromaDBVectorStore
      - All implement AbstractVectorStore (add_documents, similarity_search)
      - RAG queries work identically

   4. Swap Memory Systems:
      - WorkingMemory → SummarizingMemory for long conversations
      - Both implement AbstractMemory (add_message, get_history)
      - Agent ReAct loop unchanged

   F. Async-First Design

   All public APIs are async-first; sync variants exist for convenience:

   Primary Interface: Async methods
   - ainvoke(messages) → Message (primary)
   - aplan(history) → (Thought, Action) | ToolCallBatch | FinalAnswer
   - arun(user_input, ...) → response
   - aexecute(tool_name, tool_input) → observation

   Sync Wrappers (convenience):
   - invoke(messages) → Message (delegates to async via asyncio.run() or httpx sync client)
   - plan(history) → result (runs in thread pool for async calls)
   - run(user_input, ...) → response
   - execute(tool_name, tool_input) → observation

   Best Practice: Use async in asyncio applications to avoid contention and enable true parallelism.
   Sync wrappers are for REPLs, simple scripts, or integrations that cannot use async.

   G. Response Pool (Deterministic Outputs)

   Template cycling for deterministic responses where desired:

   - ResponsePool: Maintain multiple response templates
     * response_pool=[Template("Option A"), Template("Option B"), ...]
   
   - ResponsePoolState: Track current position, cycle通过 templates
   
   - Usage: Configure agent to use response pool for certain planners or scenarios

   When enabled, agent cycles through templates when generating final response:
   1. Planner produces content
   2. ResponsePool.next_template() → current template
   3. Template.format(content=planner_output) → final output

   Used in scenarios where deterministic output format is required (e.g., rubric-based grading).

  ---
   15. Development & Usage Best Practices
   
   ┌────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┐
   │                        Practice                        │                        Rationale                        │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Use from fairlib import * via lazy loading             │ Fast startup + IDE autocomplete                         │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Implement custom tools as classes                      │ State management, type safety, async support            │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Set Agent.role_description                             │ Crucial for worker identification in multi-agent        │
   │                                                        │ systems                                                 │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Honor Message.importance="pinned"                      │ Critical for preserving key messages through            │
   │                                                        │ summarization                                           │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Use typed exceptions for recovery                      │ Distinct handling of parse failures vs. provider errors │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Preface custom prompts with mandatory format           │ Parser compatibility guaranteed                         │
   │ instructions                                           │                                                         │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Subscribe to event bus for observability               │ Debugging, logging, and monitoring via typed events     │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Use arun_with_trace() for structured tracing           │ Post-run analysis and debugging with full context       │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Save/checkpoint during long runs                       │ Crash recovery without losing progress                  │
   ├────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
   │ Prefer async methods (ainvoke, aplan, arun)            │ No thread pool overhead, true concurrent I/O            │
   └────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────┘

   ---
   This architecture enables building sophisticated agentic systems from simple calculators to complex multi-agent teams —
    all while maintaining type safety, modularity, and the ability to swap implementations without rewriting core logic.


   Advanced Features Reference
   
   A. Response Pool (fairlib.utils.response_pool)
   
   Template cycling for deterministic outputs where desired:

   - ResponsePool: Maintain multiple response templates
     * response_pool=[Template("Option A"), Template("Option B"), ...]
   
   - ResponsePoolState: Track current position, cycle through templates
   
   - Usage: Configure agent to use response pool for certain planners or scenarios

   When enabled, agent cycles through templates when generating final response:
   1. Planner produces content
   2. ResponsePool.next_template() → current template
   3. Template.format(content=planner_output) → final output

   Used in scenarios where deterministic output format is required (e.g., rubric-based grading,
   multiple-choice responses, or A/B testing response formats).

   B. Side-Effect-Aware Batch Dispatch (core/interfaces/tools.py)

   Multi-action planners can issue several tool calls under one turn:

   - READ_ONLY tools: Safe to run in parallel (no local state mutation)
     * Example: WebSearcherTool, KnowledgeBaseQueryTool
   
   - MUTATING tools: Modify local state, must run sequentially
     * Example: WriteFileTool, EditFileTool
   
   - EXTERNAL tools: Reach outward to non-deterministic services
     * Example: WeatherTool, WebDataExtractor

   Dispatch Policy:
   1. Group actions by side_effect
   2. Execute all READ_ONLY in parallel (asyncio.gather)
   3. Execute MUTATING/EXTERNAL sequentially with barrier between batches
   4. Return observations in original call order

   Example Multi-Action Turn:
   {
       "thought": "I need to get weather and do a calculation",
       "actions": [
           {"tool_name": "weather_tool", "tool_input": "New York"},     # EXTERNAL
           {"tool_name": "safe_calculator", "tool_input": "10 + 5"}      # READ_ONLY
       ]
   }

   Execution order:
   - safe_calculator runs in parallel (READ_ONLY batch)
   - weather_tool runs after (EXTERNAL, sequential batch)
   - Observations returned: [calculator_result, weather_result] (original order)

   C. Observation Metadata Marker (fairlib.core.message)

   Every observation includes fairlib.observation=True metadata:

   - Used by memory sanitation to identify observation messages
   - Summarization excludes observations from summarization input
   - Checkpoint recovery preserves observation structure
   - Works regardless of role ("system" text observations or "tool" keyed observations)

   D. Tool Input Validation Error Feedback (core/errors.py)

   ToolInputValidationError.render_observation() includes expected input shape:

   Example error message:
   Error in tool 'write_file': Validation failed
   Expected input for 'write_file':
   path: str
   content: str

   This schema hint travels with the observation to memory, helping the model
   correct its tool_input format on retry.

   E. Degenerate Response Detection (modules/mal/degenerate_output.py)
   
   Detects loop scenarios where same output repeats:

   - ResponseRepeatGuard: Tracks recent responses, flags repetitions
   - Configurable: max_repetitions, min_length for detection
   - Emits ResponseRepeatEvent with context

   Prevents infinite loops on sticky models that generate same text repeatedly.

   F. Circuit Breaker (modules/mal/circuit_breaker.py)
   
   Fail-fast protection for failing adapters:

   - Open when failure_rate > threshold (default 50% in last 100 calls)
   - Half-open: allow test call, close if success, reopen if fail
   - Stays open for cooldown period (configurable)

   Integration with Resilience layer for all MAL adapters.

   G. Checkpoint/Trace Structuring (core/checkpoint.py, core/trace.py)
   
   - AgentCheckpoint: Lightweight (history_length only)
   - AgentRunTrace: Full structured trace with metadata

   Arun options:
   - arun(user_input): Return just the answer
   - arun_with_trace(user_input, metadata=...): Return AbstractAgentRunTrace
     * Contains: input_text, output, events, metadata, last_error (if failed)