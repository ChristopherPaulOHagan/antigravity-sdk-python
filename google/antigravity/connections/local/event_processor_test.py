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

"""Tests for event_processor that translates wire events to SDK events."""

from absl.testing import absltest

from google.antigravity.connections.local import localharness_pb2
from google.antigravity import types
from google.antigravity.connections.local import event_processor


class EventProcessorHelperTest(absltest.TestCase):
  """Tests for standalone helper functions in event_processor."""

  def test_normalize_wire_path_file_uri(self):
    self.assertEqual(
        event_processor.normalize_wire_path("file:///dev/shm/workspace/foo.py"),
        "/dev/shm/workspace/foo.py",
    )

  def test_normalize_wire_path_cns_uri(self):
    self.assertEqual(
        event_processor.normalize_wire_path(
            "cns://el-d/home/user/workspace/kittens.md"
        ),
        "/cns/el-d/home/user/workspace/kittens.md",
    )

  def test_normalize_wire_path_plain_path(self):
    self.assertEqual(
        event_processor.normalize_wire_path("/tmp/clean-path"),
        "/tmp/clean-path",
    )

  def test_make_step_id_with_trajectory(self):
    self.assertEqual(event_processor._make_step_id("traj_1", 5), "traj_1:5")

  def test_make_step_id_without_trajectory(self):
    self.assertEqual(event_processor._make_step_id("", 5), "5")

  def test_parse_usage_metadata_full(self):
    pb = localharness_pb2.UsageMetadata(
        prompt_token_count=100,
        cached_content_token_count=50,
        candidates_token_count=75,
        thoughts_token_count=25,
        total_token_count=250,
    )
    meta = event_processor._parse_usage_metadata(pb)
    self.assertEqual(meta.prompt_token_count, 100)
    self.assertEqual(meta.cached_content_token_count, 50)
    self.assertEqual(meta.candidates_token_count, 75)
    self.assertEqual(meta.thoughts_token_count, 25)
    self.assertEqual(meta.total_token_count, 250)

  def test_parse_usage_metadata_empty(self):
    pb = localharness_pb2.UsageMetadata()
    meta = event_processor._parse_usage_metadata(pb)
    self.assertIsNone(meta.prompt_token_count)
    self.assertIsNone(meta.cached_content_token_count)
    self.assertIsNone(meta.candidates_token_count)
    self.assertIsNone(meta.thoughts_token_count)
    self.assertIsNone(meta.total_token_count)


class LocalConnectionStepFromDictTest(absltest.TestCase):
  """Tests for LocalConnectionStep.from_dict derivation logic.

  Specifically targets the is_complete_response calculation and edge cases in
  step type detection.
  """

  def test_is_complete_response_true(self):
    """Verifies is_complete_response is True when source=MODEL, state=DONE, target=TARGET_USER, and text is present.

    Why: This is the canonical "agent finished speaking" signal that callers
    rely on to surface the final answer. All four conditions must hold:
    source is MODEL, status is DONE, text is present, and target is USER.
    """
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_MODEL",
        "state": "STATE_DONE",
        "text": "Here is my answer.",
        "target": "TARGET_USER",
    })
    self.assertTrue(step.is_complete_response)

  def test_is_complete_response_false_when_source_not_model(self):
    """Verifies is_complete_response is False when source is not MODEL.

    Why: System or user steps that are done and have text should not be
    treated as a completed model response.
    """
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_USER",
        "state": "STATE_DONE",
        "text": "Some user text.",
    })
    self.assertFalse(step.is_complete_response)

  def test_is_complete_response_false_when_not_done(self):
    """Verifies is_complete_response is False when state is not DONE.

    Why: An active model step is still streaming; it should not be treated
    as complete until the harness marks it done.
    """
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_MODEL",
        "state": "STATE_ACTIVE",
        "text": "Partial response...",
    })
    self.assertFalse(step.is_complete_response)

  def test_is_complete_response_false_when_no_text(self):
    """Verifies is_complete_response is False when text is empty.

    Why: A done model step with no text is a structural step (e.g. tool use
    completion), not a completed textual response.
    """
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_MODEL",
        "state": "STATE_DONE",
    })
    self.assertFalse(step.is_complete_response)

  def test_is_complete_response_false_when_error_state(self):
    """Verifies is_complete_response is False when state is ERROR."""
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_MODEL",
        "state": "STATE_ERROR",
        "text": "Something went wrong",
        "error_message": "internal error",
    })
    self.assertFalse(step.is_complete_response)

  def test_is_complete_response_false_when_target_environment(self):
    """Verifies is_complete_response is False for TARGET_ENVIRONMENT steps.

    Why: Tool execution steps (view_file, run_command, etc.) are targeted at
    the environment, not the user. Even when they are source=MODEL, state=DONE,
    and have text (e.g. "Requesting permission to make tool call"), they must
    not be treated as a completed model response.
    """
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_MODEL",
        "state": "STATE_DONE",
        "text": "Requesting permission to make tool call",
        "target": "TARGET_ENVIRONMENT",
    })
    self.assertFalse(step.is_complete_response)

  def test_step_type_tool_call_with_builtin(self):
    """Verifies that a step with a builtin tool proto field is typed TOOL_CALL and parses details."""
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_MODEL",
        "state": "STATE_ACTIVE",
        "view_file": {"file_path": "/foo"},
    })
    self.assertEqual(step.type, types.StepType.TOOL_CALL)

    self.assertLen(step.tool_calls, 1)
    self.assertEqual(step.tool_calls[0].name, "view_file")
    self.assertEqual(step.tool_calls[0].args, {"file_path": "/foo"})
    self.assertEqual(step.tool_calls[0].canonical_path, "/foo")

  def test_structured_output_extracted_from_finish(self):
    """Verifies that structured output is extracted when finish payload is present.

    Why: The connection layer is responsible for extracting and parsing
    the final structured output from the wire format so Layer 2 and E2E tests
    can access it natively.
    """
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_MODEL",
        "state": "STATE_DONE",
        "finish": {
            "output_string": (
                '{"total_revenue": 386.0, "top_selling_product": "Widget A"}'
            ),
        },
    })
    self.assertEqual(
        step.structured_output,
        {"total_revenue": 386.0, "top_selling_product": "Widget A"},
    )

  def test_structured_output_extracted_from_finish_handles_invalid_json(self):
    """Verifies that invalid JSON in finish payload defaults to None.

    Why: The connection layer should handle malformed JSON payloads gracefully
    by returning None instead of raising a fatal exception.
    """
    step = event_processor.LocalConnectionStep.from_dict({
        "source": "SOURCE_MODEL",
        "state": "STATE_DONE",
        "finish": {
            "output_string": (  # Invalid JSON
                '{"total_revenue": 386.0, "top_selling_product": }'
            ),
        },
    })
    self.assertIsNone(step.structured_output)

  def test_step_from_dict_normalizes_file_uri_arguments(self):
    """Verifies that LocalConnectionStep.from_dict normalizes file:// URIs."""
    step = event_processor.LocalConnectionStep.from_dict({
        "step_index": 1,
        "trajectory_id": "traj_1",
        "state": "STATE_WAITING_FOR_USER",
        "view_file": {"file_path": "file:///dev/shm/workspace/foo.py"},
    })
    self.assertLen(step.tool_calls, 1)
    self.assertEqual(
        step.tool_calls[0].args.get("file_path"), "/dev/shm/workspace/foo.py"
    )
    self.assertNotIn("canonical_path", step.tool_calls[0].args)
    self.assertEqual(
        step.tool_calls[0].canonical_path,
        "/dev/shm/workspace/foo.py",
    )

  def test_step_from_dict_normalizes_cns_uri_arguments(self):
    """Verifies that LocalConnectionStep.from_dict normalizes cns:// URIs.

    Why: The CNS-backed filesystem uses cns:// URIs as path representations.
    The workspace_only policy compares canonical_path against /cns/... paths
    provided by the user, so cns:// must be translated to /cns/... for
    policy matching to work correctly.
    """
    step = event_processor.LocalConnectionStep.from_dict({
        "step_index": 1,
        "trajectory_id": "traj_1",
        "state": "STATE_WAITING_FOR_USER",
        "create_file": {"path": "cns://el-d/home/user/workspace/kittens.md"},
    })
    self.assertLen(step.tool_calls, 1)
    self.assertEqual(
        step.tool_calls[0].args.get("path"),
        "/cns/el-d/home/user/workspace/kittens.md",
    )
    self.assertNotIn("canonical_path", step.tool_calls[0].args)
    self.assertEqual(
        step.tool_calls[0].canonical_path,
        "/cns/el-d/home/user/workspace/kittens.md",
    )


if __name__ == "__main__":
  absltest.main()
