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
import numpy as np
import streamlit as st

# Usage:
# $ streamlit run src/playground/rock_field_models_playground.py


def app():
    st.title("Moon Rock Field Playground")

    st.write("This is an interactive app for generating rock fields.")
    st.write("Use the sliders below to adjust the parameters of the rock field.")

    st.write("The rock field is generated using the following formula:")
    st.latex(
        r"""
        F(D) = k \cdot \exp(-q \cdot D)
    """
    )
    st.write("Where:")
    st.write(" - $F(D)$ is the frequency of rocks with diameter D")
    st.write(" - $k$ is the overall rock abundance")
    st.write(" - $q$ is a coefficient that controls the distribution of rock sizes")
    st.write(" - $D$ is the diameter of the rock")

    st.write("An empirical formula for $q(k)$ in the Moon is given by:")
    st.latex(
        r"""
        q = 0.5648 + 0.01285/k
    """
    )

    k = st.slider("k", 0.0, 1.0, 0.06)
    q_slider = st.slider("q", 0.0, 2.0, 1.0)
    q_k = 0.5648 + 0.01285 / k

    d_min = 0.01
    d_max = 10
    n_d = 100
    D = np.logspace(np.log10(d_min), np.log10(d_max), n_d)

    F_slider_q = [k * np.exp(-q_slider * d) for d in D]
    F_q_k = [k * np.exp(-q_k * d) for d in D]

    import matplotlib.pyplot as plt

    plt.plot(D, F_q_k, label=f"$F_k(D) = k*exp(-{q_k:.2f}*D)$, empirical $q$", color="green")
    plt.plot(
        D,
        F_slider_q,
        label=f"$F_k(D) = k*exp(-{q_slider:.2f}*D)$, $q$ from slider",
        color="blue",
    )
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Rock Diameter D, m")
    plt.ylabel("Areal fraction $F_k(D)$")
    plt.plot([d_min, d_max], [k, k], "r--", label="k")
    plt.legend()
    st.pyplot(plt)


if __name__ == "__main__":
    app()
