# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Example demonstrating programmatic and native task cancellation.

This example shows:
- Differentiating programmatic cancellation (aborted via response.cancel())
  from native Python task cancellation (aborted via task.cancel()).
- How to structure robust async exception handling for both scenarios using
  a centralized response rendering helper.
- Catching the custom AntigravityCancelledError (inheriting from CancelledError)
  to capture SDK-specific cancellation events.

To run:
  python cancellation.py
"""

import asyncio

from google.antigravity import Agent
from google.antigravity import LocalAgentConfig
from google.antigravity import types


async def render_chat(response: types.ChatResponse) -> None:
  """Streams the reasoning thoughts and response deltas to the console."""
  print("  Agent Thoughts: ", end="", flush=True)
  async for thought in response.thoughts:
    print(thought, end="", flush=True)

  print("\n  Agent Response: ", end="", flush=True)
  async for text in response:
    print(text, end="", flush=True)
  print(flush=True)


async def main() -> None:
  """Executes both cancellation scenarios sequentially."""
  config = LocalAgentConfig()

  async with Agent(config) as my_agent:
    # -------------------------------------------------------------------------
    # Scenario 1: Programmatic Cancellation (response.cancel())
    # -------------------------------------------------------------------------
    print("\n=== Scenario 1: Programmatic Cancellation ===", flush=True)
    prompt = "Write a very long story about a character named cancellation."
    print(f"  User: {prompt}", flush=True)

    response = await my_agent.chat(prompt)
    chat_task = asyncio.create_task(render_chat(response))

    # Wait for a short duration to let generation start.
    print(
        "\n  [Waiting for 10 seconds before programmatically aborting...]",
        flush=True,
    )
    await asyncio.sleep(10)

    # Cancel the turn programmatically using the response's cancel() method.
    if not chat_task.done():
      print("\n  [Aborting the turn via response.cancel()]", flush=True)
      await response.cancel()
    else:
      print(
          "\n  [Chat task already completed, skipping cancellation.]",
          flush=True,
      )

    try:
      await chat_task
    except types.AntigravityCancelledError as e:
      # Programmatic cancellation raises the SDK's custom CancelledError
      # subclass.
      print(
          f"\n  [Programmatic Cancel Caught] Turn was aborted by the client: "
          f"{e}",
          flush=True,
      )
    except asyncio.CancelledError as e:
      print(
          f"\n  [Native Cancel Caught] The Python task itself was cancelled: "
          f"{repr(e)}",
          flush=True,
      )

    # -------------------------------------------------------------------------
    # Scenario 2: Native Python Task Cancellation (task.cancel())
    # -------------------------------------------------------------------------
    print(
        "\n=== Scenario 2: Native Python Task Cancellation ===",
        flush=True,
    )
    prompt = "Write a very long poem about a character named interruption."
    print(f"  User: {prompt}", flush=True)

    response = await my_agent.chat(prompt)
    chat_task = asyncio.create_task(render_chat(response))

    # Wait for a short duration to let generation start.
    print(
        "\n  [Waiting for 10 seconds before natively cancelling the task...]",
        flush=True,
    )
    await asyncio.sleep(10)

    # Cancel the Python task itself.
    if not chat_task.done():
      print("\n  [Cancelling the Python task via task.cancel()]", flush=True)
      chat_task.cancel()
    else:
      print(
          "\n  [Chat task already completed, skipping cancellation.]",
          flush=True,
      )

    try:
      await chat_task
    except types.AntigravityCancelledError as e:
      print(
          f"\n  [Programmatic Cancel Caught] Turn was aborted by the client: "
          f"{e}",
          flush=True,
      )
    except asyncio.CancelledError as e:
      # Native task cancellation raises the standard asyncio.CancelledError.
      # Because AntigravityCancelledError inherits from CancelledError,
      # placing this second ensures we only catch non-SDK cancellations here.
      print(
          f"\n  [Native Cancel Caught] The Python task itself was cancelled: "
          f"{repr(e)}",
          flush=True,
      )

    print("\n  Finished cancellation example.", flush=True)


if __name__ == "__main__":
  asyncio.run(main())
