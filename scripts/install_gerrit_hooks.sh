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

# Installs/Overwrites the Gerrit commit-msg hook in the repository.

# Function to install/overwrite the Gerrit commit-msg hook
force_install_gerrit_hook() {
  local git_dir
  git_dir=$(git rev-parse --git-dir 2>/dev/null)
  if [ ! -d "$git_dir" ]; then
    echo "Skipping non-git directory: $(pwd)"
    return 0
  fi

  # Determine the absolute path for more reliable echo messages
  local abs_path
  abs_path=$(pwd)
  echo "----------------------------------------------------"
  echo "Processing repository at: $abs_path"

  local hook_path="$git_dir/hooks/commit-msg"
  local hook_url="https://gerrit-review.googlesource.com/tools/hooks/commit-msg"

  echo "Installing/overwriting Gerrit commit-msg hook at: $hook_path"
  mkdir -p "$(dirname "$hook_path")"
  if curl -s -Lo "$hook_path" "$hook_url"; then
    chmod +x "$hook_path"
    # Basic check to see if the downloaded file seems okay
    if [ -s "$hook_path" ]; then
      echo "Hook downloaded and installed successfully."
    else
      echo "ERROR: Hook download seems to have resulted in an empty file."
      return 1
    fi
  else
    echo "ERROR: Hook download failed from $hook_url"
    return 1
  fi
}



# Install in the main repository
echo "=== Main Repository ==="
force_install_gerrit_hook



# Clean up the exported function from the shell environment
unset -f force_install_gerrit_hook

echo "----------------------------------------------------"
echo "Gerrit hooks installed."
