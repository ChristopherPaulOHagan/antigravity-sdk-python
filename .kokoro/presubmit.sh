#!/bin/bash
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

# Kokoro presubmit script for antigravity-sdk-py.
# Runs unit tests on every GoB change.

set -eo pipefail

cd "${KOKORO_ARTIFACTS_DIR}/git/antigravity-sdk-py"

echo "--- Setting up Python environment ---"
# The ubuntu2004 Docker image ships Python 3.8; install 3.13 via pyenv
# (pre-installed on Kokoro images). Pattern matches google-genai SDK.
pyenv install 3.13
pyenv global 3.13

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel

echo "--- Installing package and test dependencies ---"
pip install -e ".[dev]"

echo "--- Running tests ---"
python -m pytest -v --tb=short

echo "--- Building wheel ---"
pip install build
python -m build --wheel --outdir dist/

echo "--- Verifying wheel installs and imports correctly ---"
pip install --force-reinstall --no-deps dist/*.whl
python -c "from google.antigravity.agent import Agent; print('Import OK: Agent')"
python -c "from google.antigravity.connections.local_connection import LocalConnection; print('Import OK: LocalConnection')"

echo "--- Presubmit passed ---"
