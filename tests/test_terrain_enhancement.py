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


from lunasynth.terrain_enhancement import RockField


def test_generate_rock_field():
    # render it
    rock_field = RockField()
    rock_field.generate_rock_field(
        k=0.06,
        size_x=10,
        size_y=10,
        h_min=0.4,
        h_max=6.0,
    )

    # check rock field
    assert rock_field.rocks is not None
    for rock in rock_field.rocks:
        assert rock.x >= 0
        assert rock.x < 10
        assert rock.y >= 0
        assert rock.y < 10
        assert rock.diameter >= 0.39
        assert rock.diameter <= 6.01
