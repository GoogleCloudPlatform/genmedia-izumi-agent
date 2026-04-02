import os

LICENSE_JS = """/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

"""

LICENSE_PY = """# Copyright 2026 Google LLC
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

"""


def add_license(filepath, header):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "Copyright" in content[:200]:
        print(f"Skipping {filepath} (already or likely has license)")
        return

    # Check if file starts with shebang or encoding
    if content.startswith("#!"):
        lines = content.split("\n")
        # Insert after the first line (shebang)
        new_content = lines[0] + "\n" + header + "\n".join(lines[1:])
    else:
        new_content = header + content

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Added license to {filepath}")


def main():
    folders = ["mediagent_kit", "demos/backend", "demos/frontend/src"]
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            if ".venv" in root or "node_modules" in root or ".vite" in root:
                continue
            for file in files:
                filepath = os.path.join(root, file)
                if file.endswith(".py"):
                    add_license(filepath, LICENSE_PY)
                elif file.endswith((".js", ".ts", ".tsx", ".css")):
                    add_license(filepath, LICENSE_JS)


if __name__ == "__main__":
    main()
