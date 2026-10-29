# Unity demo frontend source

This folder contains the HTML, CSS, JavaScript, thumbnails and provenance/check records for the v0.2.0 demo. Large render PNGs, embedded textures, Three.js vendor bundle and terrain/rock data are shipped in the checked Release archive, not Git history.

For a complete working page, download [Lunar_Unity_Demo.zip](https://github.com/moonspace123/moon-terrain/releases/download/v0.2.0/Lunar_Unity_Demo.zip), extract it, and open `Lunar_Unity_Demo/index.html` in Edge or Chrome. No server is required. Alternatively run `python tools/download_unity_demo.py` from the repository root.

To edit the interface, copy these source files over the matching files in the extracted demo, preserving its generated assets. The complete offline archive retains its own local Three.js license. Unity renders are static; the interactive companion is Three.js, not a Unity WebGL build.
