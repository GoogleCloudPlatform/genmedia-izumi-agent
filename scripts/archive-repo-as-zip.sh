#!/bin/bash
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# This script archives the git repository into a single zip file.

set -e

# The root of the repository
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# The name of the output file
OUTPUT_FILE="mediagent_demos.zip"

# A temporary directory to stage the files
STAGE_DIR=$(mktemp -d)

# Cleanup the temporary directory on exit
trap 'rm -rf "$STAGE_DIR"' EXIT

# Remove the existing zip file if it exists
rm -f "$REPO_ROOT/$OUTPUT_FILE"

export STAGE_DIR

export FINAL_STAGE_DIR="$STAGE_DIR/mediagent_demos"
mkdir -p "$FINAL_STAGE_DIR"

echo "Archiving main repository..."
git archive HEAD | tar -x -C "$FINAL_STAGE_DIR"



echo "Creating zip file: $OUTPUT_FILE..."
(cd "$STAGE_DIR" && zip -r "$REPO_ROOT/$OUTPUT_FILE" mediagent_demos)

echo "Successfully created $OUTPUT_FILE"