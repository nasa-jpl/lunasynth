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


import pytest


@pytest.fixture(scope="session", autouse=True)
def lunasynth_log_dir(tmp_path_factory):
    # write log files to a temporary directory instead of the current directory
    with pytest.MonkeyPatch.context() as mp:
        log_dir = tmp_path_factory.mktemp("logs")
        mp.setenv("LUNASYNTH_LOG_DIR", str(log_dir))
        yield log_dir
