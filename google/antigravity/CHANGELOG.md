# Changelog

<!-- disableFinding(LINE_OVER_80) -->
<!-- disableFinding(LIST_NO_LINE) -->

All notable changes to the Google Antigravity Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.7] - 2026-07-14

Release 0.1.7 of the Google Antigravity Python SDK expands end-user control over agent execution environments, strengthens concurrency safety for stateful tools, and introduces deeper reasoning capabilities. Key highlights include atomic multi-threaded state handling for tools and hooks, customizable subprocess environment variable isolation, support for an "extra_high" thinking severity level, and full Model Context Protocol (MCP) and subagent support across local model backends. This release also resolves interactive console prompt clobbering and improves socket discovery under containerized setups.

### 🌟 Key Highlights
- **Multi-threaded Hook & Tool State Handling**: Developers can now safely read and mutate shared context variables across multi-threaded tools (`asyncio.to_thread` or `ThreadPoolExecutor`) using atomic updates and thread locking:
  ```python
  def my_tool(ctx: ToolContext) -> str:
      with ctx.lock():
          ctx.update_state("count", lambda c: (c or 0) + 1)
      return "Success"
  ```
- **Custom Subprocess Environment Variables**: Developers can now pass custom environment variables directly to isolated agent instances via `LocalAgentConfig`, avoiding pollution of the global parent environment:
  ```python
  config = LocalAgentConfig(env={"PATH": "/custom/bin", "MY_API_KEY": "secret"})
  ```
- **Extra High Thinking Severity Support**: Developers can now configure an `"extra_high"` thinking severity level for complex reasoning tasks without needing to specify or override the model name:
  ```python
  config = LocalAgentConfig(
      model=ModelTarget(
          endpoint=GeminiAPIEndpoint(
              options=GeminiModelOptions(thinking_level="extra_high")
          )
      )
  )
  ```
- **MCP & Subagent Support for Local Models (LiteRT & OpenAI)**: Developers using local Gemma (`LiteRTAgentConfig`) or local OpenAI-compatible endpoints (`LocalOpenAIAgentConfig`, such as Ollama or LM Studio) can now directly configure subagents and register Model Context Protocol (MCP) servers, enabling full local multi-agent and MCP tool workflows.

---

### 📋 Detailed Changes

#### Features & Enhancements
- **Environment Hydration**: Hydrates GCP/Vertex parameters (project, location, routing) dynamically from standard GOOGLE_CLOUD environment variables when not explicitly passed during LocalAgentConfig initialization.
- **Default Image Generation Model Optimization**: Updated the default image generation model (`DEFAULT_IMAGE_GENERATION_MODEL`) to `"gemini-3.1-flash-lite-image"`. Previous default image models often took too long to run on average during standard agent execution loops; this lightweight model ensures dependable, high-speed image generation by default while remaining fully replaceable via explicit model configuration if higher fidelity is required.

#### Robustness & Usability
- **Local WebSocket Connections**: Retries socket connections by resolving to both "localhost" and "127.0.0.1", ensuring dependable harness discovery under containerized setups.
- **Tool Runner Public Asyncness**: Preserves original asynchronous and synchronous execution interfaces of tools when accessed via ToolRunner.get_public_callable.
- **Config Inheritance and Gaps**: Cleaned up redundant base overrides in LocalAgentConfig and corrected Pydantic validation failures arising from None initialization variables.

#### Bug Fixes
- **Interactive Console Spinner Clobbering**: Fixed a bug in `run_interactive_loop` where background spinner animation frames (`⠼ Reasoning...`) continuously clobbered user confirmation prompts (`async_input` and `ASK_USER` policy checks) every 80ms. The active spinner is now explicitly cleared (`\r\033[K`) and paused when an interactive input prompt opens, keeping confirmation lines readable and resuming the spinner smoothly after input is submitted.
- **Duplicate Tool Call Events**: Fixed client rendering issues by filtering out custom tool events from StepUpdate payloads to prevent duplicate event dispatches.
- **SDK Idle Transitions**: Corrected premature agent shutdown situations by properly checking and clearing idling flags once a TrajectoryStateUpdate signals transition to running.
- **LiteRT Connection Engine**: Rectified local engine initialization bugs, including a missing protobuf import, a token constructor argument mismatch, and OpenAITool inheritance.
- **Shutdown Connection Handshake**: Added extra execution buffer to local connections during agent shutdown, ensuring safe persistent state storage actions.

## [0.1.6] - 2026-07-09

This release expands local execution capabilities by broadening support for multimodal and web-connected tool workflows. Developers can now run Gemma models locally using LiteRT or integrate with local OpenAI-compatible APIs, natively return multimodal media from custom tools, and leverage a more robust, streamlined lifecycle hooks framework that is fully aligned with Model Context Protocol (MCP) workflows.

### Added
- **Local Model Connectivity**: Introduced `LiteRTAgentConfig` and `LiteRTConnectionStrategy` for LiteRT-LM (supporting local Gemma execution), `LocalOpenAIAgentConfig` and `LocalOpenAIConnectionStrategy` for OpenAI-compatible APIs (supporting Ollama and LM Studio), and a background loopback HTTP translation server.
- **Multimodal Tool Outputs**: Enabled custom tools to return media assets (`Image`, `Document`, `Audio`, `Video`) directly via a single tool response without needing separate follow-up turns (`supplemental_media`).
- **Built-in Web Fetch Tool**: Integrated the `read_url_content` tool end-to-end for fetching structured web content natively with the `ReadUrlContentResult` Pydantic model.

### Changed
- **MCP String Prefix Modernization**: Decoupled tool calls and safety policy engines from legacy `"mcp_"` string synthesis, resolving name mismatch issues by utilizing explicit `server_name` attributes in tool evaluation.

### Fixed
- **Python 3.14 Compatibility**: Resolved namespace class conflicts and typing normalization issues in `agent.py` and `public_api_test.py` under Python 3.14 deferred annotations evaluation.
- **Vertex Validation Errors**: Cleared a misleading reference to API keys in `VertexEndpoint` validation error messages, limiting fields to project and location.
- **OTel Trace Warnings**: Resolved detached `contextvars` warnings and set-status race conditions by removing `use_span` context managers from Turn/Session hooks and checking span recording readiness.
- **Exception Wrapping Mapping**: Fixed `agent_middleware` integration check failures by making the example check for error message substrings instead of strict exception types.

---

## [0.1.5] - 2026-06-25

This release introduces native OpenTelemetry tracing support, declarative subagent configurations, improved type safety, and critical robustness and compatibility updates.

### Added
- **OpenTelemetry Tracing Support**: Integrates OpenTelemetry tracing into the SDK to translate session, turn, step, and tool lifecycle events into standard GenAI-compliant semantic spans for advanced monitoring and performance debugging, with custom task-safe active span propagation for tool execution.
- **Declarative Subagent Configurations**: Added `SubagentConfig` and `SubagentCapabilities` in `types.py` to support constructing static subagents with declarative instructions and tools directly.

### Changed
- **Type Safety in `AgentConfig`**: Type-annotated policies, hooks, and triggers parameters on `AgentConfig` and its subclasses to improve type safety and overall developer experience.
- **Lifecycle Hook Routing**: Shifted core orchestration of `OnSessionStartHook`, turn-level hooks (`PRE_TURN` and `POST_TURN`), and `OnSessionEndHook` to the connection layer, implementing the Python-side `HookRouter` for event routing.
- **Public API Cleanup**: Hid internal validation methods on media and error classes by prefixing them with an underscore (`_validate_mime_type` and `_from_pydantic` on validation errors).

### Fixed
- **Historical Step Absorption**: Ensured historical step absorption is properly drained during initialization to prevent persistence non-linearity issues in `Conversation`.
- **Python 3.14 Compatibility**: Resolved potential name shadowing in the `Conversation` class by renaming the top-level connection module import.

---

## [0.1.4] - 2026-06-18

This release introduces major architectural refactorings, public API standardizations, and key new capabilities centered on centralizing model configurations to natively support multi-model backends, exposing a new built-in Google Web Search capability, enabling environment variable passing for Model Context Protocol (MCP) servers, and simplifying the agent initialization flow by removing dynamic runtime registrations.

### Added
- **Built-in Web Search Tool**: Exposes the `SEARCH_WEB` tool directly within the SDK, enabling agents to leverage Google Search for grounded real-time information retrieval, complete with new developer examples (`web_tools.py`).
- **MCP Server Environment Variables**: Added support for configuring and passing custom environment variables to launched stdio servers via the new `env` field in `McpStdioServer`.
- **Base URL and HTTP Headers Support**: Out-of-the-box support for setting custom base URLs and HTTP headers.
- **Image Generation Aspect Ratio**: Updated the SDK model config and wrapper to support specifying `aspect_ratio` within the image creation tool configuration.

### Changed
- **Centralized Multi-Model Configuration**: Replaces legacy singular `gemini_config` options with a unified, repeated `models` collection on `AgentConfig` and `LocalAgentConfig` to support multi-model routing, fallback strategies, and automated selection helpers.
- **Agent Session Lifecycle & API Standardization**: Improves runtime safety by removing dynamic post-initialization hook and trigger registration in favor of session creation-time declarations.
- **Top-Level Package Exports**: Exposed core SDK constructs (including `Content`, `Image`, `Document`, `Audio`, `Video`, `from_file`, `BuiltinTools`, and `SystemInstructions`) directly under the `google.antigravity` root module for easier access.
- **Hook Base Class Exports**: Consolidated the base hooks implementation by exporting `DecideHook`, `InspectHook`, and `TransformHook` from the hooks package root.
- **Top-Level Policy Package**: Created a new top-level policy package to clean up hook and workspace path validation dependencies.
- **Relocated Trigger Types**: Moved the `FileChange` model and `FileChangeKind` enum from `types.py` to the specialized triggers package.

---

## [0.1.3] - 2026-06-11

This release introduces per-server MCP timeout configurations and improves local connection error handling.

### Added
- **Per-Server MCP Timeout**: Added configuration support to set custom timeouts (in seconds) for individual MCP servers (`BaseMcpServerConfig.timeout_seconds`).
- **Terminal Error Propagation**: The local connection now propagates terminal trajectory errors from the `localharness` binary as structured `AntigravityExecutionError` exceptions in the Python SDK during step collection.

---

## [0.1.2] - 2026-06-04

This release adds Windows platform support, introduces programmatic turn-level stream cancellation, simplifies safety policy configurations for the Model Context Protocol (MCP), and removes the deprecated MCP SSE transport.

### Added
- **Windows Platform Support**: Native compatibility added for Windows x86_64 and ARM64 environments. Path and file URI resolution now correctly handles drive letters and directory separators under Windows.
- **Programmatic Turn-Level Cancellation**: Added programmatic stream cancellation via `ChatResponse.cancel()`. This programmatically aborts active generation turns directly from the client and raises `AntigravityCancelledError` (subclass of `asyncio.CancelledError`) to cleanly signal cancellation in the async flow (`examples/getting_started/cancellation.py`).

### Changed
- **Direct MCP Safety Policy Configuration**: Overloaded `policy.allow`, `policy.deny`, and `policy.ask_user` to accept server configurations (`BaseMcpServerConfig`) directly instead of typing namespaced string paths. Policy evaluation follows a 9-level precedence model (Specific > Prefix Wildcard > Global Wildcard) with longest-match prefix validation to protect against collisions.

### Removed
- **Deprecation of SSE Transport**: Removed the legacy `McpSseServer` configuration and connection handlers in favor of standard Stdio and Streamable HTTP connection strategies.

---

## [0.1.1] - 2026-05-29

This release focuses on significant enhancements to the Model Context Protocol (MCP) integration, adds native Vertex AI authentication support, improves robustness with better error handling, and includes critical fixes for token usage tracking.

### Added
- **MCP Tool Filtering & Simplified Policies**: Added support for `enabled_tools` (allowlist) and `disabled_tools` (denylist) in server configurations, and overloaded safety policy helpers (`policy.allow`, `policy.deny`, `policy.ask_user`) to accept the MCP server configuration object directly.
- **Vertex AI Authentication**: Integrated native support for Vertex AI authentication in the Python SDK.

### Changed
- **MCP Tool Prefixing & Validation**: The SDK now automatically namespaces and prefixes MCP tools (`mcp_{server_name}_{tool_name}`) to prevent name collisions when connecting multiple MCP servers. The `name` field is now mandatory in MCP server configurations and validated as a proper Python identifier.
- **Improved Error Handling**: The SDK now raises explicit, descriptive exceptions for terminal errors rather than failing silently.

### Fixed
- **Structured Output Token Tracking**: Fixed a bug where token `usage_metadata` was not correctly returned when structured output (`response.structured_output()`) was requested.
- **Type Checking Warnings**: Fixed `pytype` warnings (including `wrong-keyword-args` in `LocalAgentConfig`) across several modules.
