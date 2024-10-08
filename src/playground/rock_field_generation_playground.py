#!/usr/bin/env python3
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

# Usage:
# (from lunasynth root folder)
# [inside an environment with all dependencies]
# $ panel serve src/playground/rock_field_generation_playground.py --show

import lunasynth.terrain_enhancement as terrain_enhancement
import matplotlib.pyplot as plt
import panel as pn
import param

pn.extension()


class RockFieldParams(param.Parameterized):
    k = param.Number(default=0.06, bounds=(0.0, 1.0), step=0.01, doc="The overall rock abundance")
    size_x = param.Number(
        default=100,
        bounds=(0, 1000),
        step=10,
        doc="The size of the rock field in the x direction",
    )
    size_y = param.Number(
        default=100,
        bounds=(0, 1000),
        step=10,
        doc="The size of the rock field in the y direction",
    )
    h_min = param.Number(default=0.1, bounds=(0, 3), step=0.1, doc="The minimum height of the rocks")
    h_max = param.Number(default=6.0, bounds=(4, 30), step=1, doc="The maximum height of the rocks")

    def __init__(self, **params):
        super().__init__(**params)
        self.rock_field = terrain_enhancement.RockField()

    @param.depends(
        "k",
        "size_x",
        "size_y",
        "h_min",
        "h_max",
    )
    def update_plot(self) -> pn.Row:
        self.rock_field.generate_rock_field(self.k, self.size_x, self.size_y, self.h_min, self.h_max)
        self.rock_field.plot()
        self.rock_field.cfa_model.plot_cum_rock_size()
        self.rock_field.cfa_model.plot_creation()
        if self.rock_field.rock_field_fig is not None:
            plt.close(self.rock_field.rock_field_fig)
        if self.rock_field.cfa_model.cfa_fig is not None:
            plt.close(self.rock_field.cfa_model.cfa_fig)
        if self.rock_field.cfa_model.creation_fig is not None:
            plt.close(self.rock_field.cfa_model.creation_fig)
        return pn.Row(
            pn.pane.Matplotlib(self.rock_field.rock_field_fig, sizing_mode="stretch_both"),
            pn.pane.Matplotlib(self.rock_field.cfa_model.cfa_fig, sizing_mode="stretch_both"),
            pn.pane.Matplotlib(self.rock_field.cfa_model.creation_fig, sizing_mode="stretch_both"),
        )


rock_field_param = RockFieldParams()
template = pn.template.MaterialTemplate(
    title="LunaSynth Rock Field Playground",
    sidebar=[rock_field_param.param],
    main=[rock_field_param.update_plot],
).servable()
