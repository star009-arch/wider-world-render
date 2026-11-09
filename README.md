# wider-world-render

Render workflow for 3D reconstruction shots used in documentaries on The Wider World (YouTube).
`blender_cables.py` builds each scene procedurally in Blender 4.2 (no external assets); the `render-3d` workflow splits
each shot into frame chunks across parallel runners and publishes the frames as release assets.
