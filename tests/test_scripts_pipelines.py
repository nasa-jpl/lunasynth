#!/usr/bin/env python
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


import os
import subprocess
from pathlib import Path

import pytest

# test all pipelines. parametrize the test with the pipeline name

pipelines_path = Path(__file__).parent.parent / "scripts" / "pipelines"

# find all .sh in the pipelines directory
pipeline_files = pipelines_path.glob("*.sh")


@pytest.mark.parametrize("pipeline_file", pipeline_files)
def test_pipelines(pipeline_file):
    # run the pipeline
    print(f"Running pipeline {str(pipeline_file)}")
    # Ensure the script is executable
    # if not pipeline_file.is_executable():
    #     pytest.skip(f"Script {pipeline_file} is not executable.")
    try:
        # Run the script
        ret = subprocess.run(
            [str(pipeline_file)],  # command to run
            check=True,  # check=True raises an exception if the return code is not 0
            capture_output=True,  # capture_output returns bytes, convert to string
            text=True,  # capture_output returns bytes, convert to string
            env=os.environ,  # pass the environment variables
            cwd=str(
                pipeline_file.parent.parent.parent
            ),  # set the working directory to the parent of the pipeline folde
        )  # set the working directory to the parent of the pipeline folde
    except subprocess.CalledProcessError as e:
        pytest.fail(
            f"Error running {pipeline_file}: \n" f"stdout: {e.stdout.decode()}\n" f"stderr: {e.stderr.decode()}"
        )
    ret = subprocess.run(["bash", "-c", str(pipeline_file)], shell=True, check=True, capture_output=True)
    # print the output
    print(ret.stdout)
    # check the output returncode
    assert ret.returncode == 0
