# SIH26166 Synthetic Dataset Engine

## 1. Motivation

Downloading and storing full orbital datasets (such as 40+ large multi-gigabyte Chandrayaan-2 OHRC and TMC-2 products) during rapid algorithm prototyping is constrained by network bandwidth, storage limits, and lack of sub-pixel dense manual ground-truth tie points.

The **Synthetic Dataset Engine** solves this by:
1. Procedurally generating realistic lunar terrain features on demand.
2. Applying analytical transformations while retaining the exact ground-truth matrix $H_{gt}$.
3. Allowing deterministic, reproducible testing with fixed random seeds.

## 2. Terrain Generation Elements

The procedural generator (`prototype/synthetic/generator.py`) simulates:
- **Regolith Elevation & Noise**: Multi-octave fractional Brownian motion noise.
- **Impact Craters**: Parabolic depressions with raised rim walls, central peaks, and interior shadow casting.
- **Secondary Crater Swarms**: Clustered micro-craters across the landscape.
- **Radial Ejecta Rays**: High-albedo streaks emanating radially from craters.
- **Sinuous Rilles & Wrinkle Ridges**: Non-linear elevation channels and ridges.
- **Lambertian Shading**: Surface normal calculation from elevation gradient dotted with solar incidence vector.

## 3. The 8 Benchmark Scenarios

1. `illumination`: Solar azimuth and elevation angle shift, gradient shading, gamma variations.
2. `scale`: Moderate scale difference (1.25x) simulating GSD variation with ground track shift.
3. `rotation_translation`: Orbital spacecraft track rotation (25 deg) and translation.
4. `viewpoint`: Off-nadir perspective tilt / projective homography distortion.
5. `scale_illumination`: Multi-scale difference (1.20x) combined with low sun-angle lighting.
6. `viewpoint_illumination`: Perspective homography combined with steep shadow variations.
7. `strong_scale`: High scale differential (1.45x) simulating high-to-medium resolution sensors.
8. `combined`: Full challenge (rotation, scale, shear, perspective tilt, illumination gradient, sensor noise, mild blur).
