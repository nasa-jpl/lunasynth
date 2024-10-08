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
import matplotlib.pyplot as plt
import numpy as np

zref = 550.0
x = np.array([-300.0, 0.0, zref])

n_steps = 250

# Generate a trajectory that starts at x and ends at the origin.
# Integrate is a parabola in the x-z plane.

# The trajectory is defined by the following equations:
v = np.array([0.0, 0, 4.0])
x_list = []
dt = 1
t = 0
camera_pitch = -np.pi / 2
camera_yaw = 0
for i in range(n_steps):
    az = 0.1
    ax = 0.4
    t = t + dt
    # v[0] = v[0] + ax * dt
    # v[1] = v[1]
    # v[2] = v[2] + az * dt
    x[0] = 0.004 * (x[2] - zref) * (x[2] - zref)  # some parabolic trajectory that looks like a landing
    x[1] = x[1] + v[1] * dt
    x[2] = x[2] + v[2] * dt
    x_list.append([t, *x.copy(), camera_pitch, camera_yaw])

x_array = np.array(x_list)

# plot trajectory

plt.plot(x_array[:, 1], x_array[:, 3])
plt.xlabel("x")
plt.ylabel("z")
plt.axis("equal")
plt.grid()
plt.savefig("trajectory.png", dpi=600)

# Save trajectory to file
np.savetxt(
    "trajectory.csv",
    x_array,
    delimiter=",",
    header="t,camera_x,camera_y,camera_z,camera_pitch,camera_yaw",
    comments="",
)
