#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import argparse
import os
import subprocess


def parse_help_output(output):
    lines = output.split("\n")
    markdown = []
    description = ""

    # Extract the description
    last_line = 1
    if "positional arguments:" in lines:
        description_index = lines.index("positional arguments:")
        description += "\n".join(lines[last_line:description_index]).strip()
        last_line = description_index + 1

    if "options:" in lines:
        description_index = lines.index("options:")
        description += "\n".join(lines[last_line:description_index]).strip()
        last_line = description_index + 1

    markdown.append("# Help Section\n")
    markdown.append("## Description")
    # markdown.append(description)
    # markdown.append("\n## Usage")
    markdown.append("```sh\n")
    markdown.append(output)
    markdown.append("\n```\n")
    return "\n".join(markdown)


def generate_markdown(script_path) -> str:
    result = subprocess.run(["python", script_path, "-h"], capture_output=True)
    output = result.stdout.decode("utf-8")
    if result.returncode != 0:
        error_output = result.stderr.decode("utf-8")
        print(f"Error generating help for {script_path}:\n{error_output}")
        return None
    markdown = parse_help_output(output)
    return markdown


def process_scripts(script_paths) -> None:
    if not os.path.exists("docs"):
        os.makedirs("docs")
    if not os.path.exists("docs/cli"):
        os.makedirs("docs/cli")

    cli_md_content = ["# CLI Documentation\n\n"]
    cli_md_content.append("This document contains links to the CLI help documentation for various scripts.\n\n")

    for script_path in script_paths:
        if not os.path.isfile(script_path):
            print(f"File not found: {script_path}")
            continue
        markdown = generate_markdown(script_path)
        if markdown:
            local_output = os.path.join("cli", os.path.splitext(os.path.basename(script_path))[0] + "_HELP.md")
            output_file = os.path.join("docs", local_output)
            with open(output_file, "w") as f:
                f.write(markdown)
            print(f"Markdown documentation generated and saved to {output_file}")
            cli_md_content.append(f"- [{os.path.basename(script_path)}]({local_output})\n")

    cli_md_file = os.path.join("docs", "CLI.md")
    with open(cli_md_file, "w") as f:
        f.write("\n".join(cli_md_content))
    print(f"CLI index documentation generated and saved to {cli_md_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Markdown help documentation for Python scripts.")
    parser.add_argument("scripts", nargs="+", help="List of script paths to process.")

    args = parser.parse_args()
    process_scripts(args.scripts)
