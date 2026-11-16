# LuNaSynth Documentation

LuNaSynth generates synthetic images of lunar terrain for navigation testing. It enhances a Moon
Digital Elevation Model with rocks and craters and renders it with Blender.

- New to LuNaSynth? Start with the [User Guide](docs/sections/user_guide.md).
- Looking for a class or function? See the [API Reference](docs/api/index).
- Want a full walkthrough? Follow the [dataset generation tutorial](src/tutorials/render_dataset_tutorial.ipynb).

Data summaries:
<a href="docs/rock_table.html">Apollo rocks</a> and
<a href="docs/moon_dem_table.html">Moon DEMs</a>.

<!--
Pages are added to the navigation automatically, see the section pages in docs/sections/:
markdown files in docs/ go to Notes, notebooks in src/tutorials/ to Tutorials, and markdown files
at the repository root and READMEs under src/ to Project.
-->

```{toctree}
:maxdepth: 2
:hidden:

User Guide <docs/sections/user_guide>
Tutorials <docs/sections/tutorials>
API Reference <docs/api/index>
Notes <docs/sections/notes>
Project <docs/sections/project>
```
