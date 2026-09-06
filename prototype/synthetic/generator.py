"""
Procedural Lunar Terrain Generator for SIH26166.
Generates synthetic terrain patterns resembling:
- Large craters with rims and central peaks
- Small crater swarms and micro-craters
- Radial ejecta rays
- Lunar rilles, sinuous valleys, and wrinkle ridges
- Realistic sun-angle Lambertian shading and shadow effects
"""
import numpy as np
from scipy.ndimage import gaussian_filter


class SyntheticTerrainGenerator:
    """
    Generates synthetic 2D lunar terrain rasters with realistic geomorphological features.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def set_seed(self, seed: int):
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def _generate_multiscale_noise(self, width: int, height: int, octaves: int = 5) -> np.ndarray:
        """Generate fractal Brownian motion elevation noise."""
        elevation = np.zeros((height, width), dtype=np.float64)
        for i in range(octaves):
            scale = 2 ** i
            sigma = max(width, height) / (4.0 * scale)
            raw_noise = self.rng.randn(height, width)
            smoothed = gaussian_filter(raw_noise, sigma=sigma)
            # Normalize octave
            if smoothed.std() > 1e-6:
                smoothed = (smoothed - smoothed.mean()) / smoothed.std()
            elevation += (1.0 / (i + 1)) * smoothed
        return elevation

    def _add_craters(
        self,
        elevation: np.ndarray,
        albedo: np.ndarray,
        num_large: int = 6,
        num_medium: int = 15,
        num_small: int = 35
    ) -> None:
        """Add multi-scale impact craters, rims, central peaks, and ejecta blankets."""
        height, width = elevation.shape
        y_grid, x_grid = np.ogrid[:height, :width]

        # 1. Large Craters
        for _ in range(num_large):
            cx = self.rng.uniform(0.15 * width, 0.85 * width)
            cy = self.rng.uniform(0.15 * height, 0.85 * height)
            radius = self.rng.uniform(width * 0.08, width * 0.20)
            depth = self.rng.uniform(1.5, 3.0)
            has_peak = radius > (width * 0.12)

            dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
            norm_dist = dist / radius

            # Parabolic depression with elevated rim
            crater_mask = norm_dist <= 1.0
            rim_mask = (norm_dist > 0.9) & (norm_dist < 1.4)

            # Bowl depression
            elevation[crater_mask] -= depth * (1.0 - norm_dist[crater_mask] ** 2)

            # Raised rim
            rim_height = depth * 0.35 * (1.0 - np.abs(norm_dist[rim_mask] - 1.1) / 0.3)
            elevation[rim_mask] += np.maximum(0, rim_height)

            # Central peak
            if has_peak:
                peak_mask = norm_dist < 0.25
                peak_h = depth * 0.45 * (1.0 - norm_dist[peak_mask] / 0.25)
                elevation[peak_mask] += peak_h

            # Ejecta rays (high albedo streaks)
            num_rays = self.rng.randint(6, 14)
            angles = self.rng.uniform(0, 2 * np.pi, num_rays)
            dx = x_grid - cx
            dy = y_grid - cy
            pt_angles = np.arctan2(dy, dx)
            for ray_ang in angles:
                ang_diff = np.abs(np.arctan2(np.sin(pt_angles - ray_ang), np.cos(pt_angles - ray_ang)))
                ray_mask = (ang_diff < 0.08) & (dist < (radius * 4.0)) & (dist > (radius * 0.8))
                albedo[ray_mask] += self.rng.uniform(0.15, 0.35) * np.exp(-dist[ray_mask] / (radius * 2.0))

        # 2. Medium Craters
        for _ in range(num_medium):
            cx = self.rng.uniform(0.05 * width, 0.95 * width)
            cy = self.rng.uniform(0.05 * height, 0.95 * height)
            radius = self.rng.uniform(width * 0.03, width * 0.08)
            depth = self.rng.uniform(0.8, 1.8)

            dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
            norm_dist = dist / radius

            crater_mask = norm_dist <= 1.0
            rim_mask = (norm_dist > 0.85) & (norm_dist < 1.3)

            elevation[crater_mask] -= depth * (1.0 - norm_dist[crater_mask] ** 2)
            rim_h = depth * 0.3 * (1.0 - np.abs(norm_dist[rim_mask] - 1.05) / 0.25)
            elevation[rim_mask] += np.maximum(0, rim_h)

        # 3. Small crater swarms
        for _ in range(num_small):
            cx = self.rng.uniform(0.02 * width, 0.98 * width)
            cy = self.rng.uniform(0.02 * height, 0.98 * height)
            radius = self.rng.uniform(3.0, width * 0.03)
            depth = self.rng.uniform(0.3, 0.8)

            dist = np.sqrt((x_grid - cx) ** 2 + (y_grid - cy) ** 2)
            norm_dist = dist / radius
            crater_mask = norm_dist <= 1.0
            elevation[crater_mask] -= depth * (1.0 - norm_dist[crater_mask] ** 2)

    def _add_rilles_and_ridges(self, elevation: np.ndarray, num_features: int = 3) -> None:
        """Add sinuous valleys (rilles) and wrinkle ridges."""
        height, width = elevation.shape
        y_grid, x_grid = np.ogrid[:height, :width]

        for _ in range(num_features):
            is_ridge = self.rng.choice([True, False])
            # Random parametric curve
            p0 = np.array([self.rng.uniform(0, width), self.rng.uniform(0, height)])
            angle = self.rng.uniform(0, np.pi)
            length = self.rng.uniform(width * 0.4, width * 0.9)
            curve_amp = self.rng.uniform(15, 45)
            freq = self.rng.uniform(1.5, 3.5)

            # Sample points along curve
            t_vals = np.linspace(0, 1, 100)
            cx_pts = p0[0] + length * np.cos(angle) * t_vals + curve_amp * np.sin(freq * np.pi * t_vals) * np.sin(angle)
            cy_pts = p0[1] + length * np.sin(angle) * t_vals - curve_amp * np.sin(freq * np.pi * t_vals) * np.cos(angle)

            # Apply Gaussian stamp along trajectory
            for px, py in zip(cx_pts[::3], cy_pts[::3]):
                if 0 <= px < width and 0 <= py < height:
                    dist_sq = (x_grid - px) ** 2 + (y_grid - py) ** 2
                    width_sigma = 8.0 if is_ridge else 6.0
                    stamp = np.exp(-dist_sq / (2.0 * width_sigma ** 2))
                    if is_ridge:
                        elevation += 0.4 * stamp
                    else:
                        elevation -= 0.5 * stamp

    def _render_sun_illumination(
        self,
        elevation: np.ndarray,
        albedo: np.ndarray,
        sun_azimuth_deg: float = 45.0,
        sun_elevation_deg: float = 25.0
    ) -> np.ndarray:
        """
        Render realistic lunar surface radiance using digital elevation gradient and Lambertian reflection.
        """
        # Gradients (slopes)
        gy, gx = np.gradient(elevation)

        # Surface normal vector: N = [-gx, -gy, 1] / sqrt(gx^2 + gy^2 + 1)
        norm = np.sqrt(gx ** 2 + gy ** 2 + 1.0)
        nx = -gx / norm
        ny = -gy / norm
        nz = 1.0 / norm

        # Sun illumination vector
        az_rad = np.radians(sun_azimuth_deg)
        el_rad = np.radians(sun_elevation_deg)
        sx = np.cos(el_rad) * np.cos(az_rad)
        sy = np.cos(el_rad) * np.sin(az_rad)
        sz = np.sin(el_rad)

        # Lambertian cosine factor (cos i = N . S)
        cos_i = nx * sx + ny * sy + nz * sz
        # Clip negative illumination (shadows)
        cos_i = np.clip(cos_i, 0.0, 1.0)

        # Combine with surface albedo
        radiance = albedo * (0.05 + 0.95 * cos_i)

        # Apply smooth non-linear lunar photometric curve
        radiance = np.power(np.clip(radiance, 0.0, 1.0), 0.85)
        return radiance

    def generate(
        self,
        width: int = 512,
        height: int = 512,
        sun_azimuth_deg: float = 45.0,
        sun_elevation_deg: float = 25.0,
        dtype=np.float32
    ) -> np.ndarray:
        """
        Generate complete synthetic lunar terrain image.
        """
        # Base elevation and albedo
        elevation = self._generate_multiscale_noise(width, height, octaves=5)
        albedo = np.full((height, width), 0.65, dtype=np.float64)
        albedo += 0.05 * self.rng.randn(height, width)

        # Geomorphological structures
        self._add_craters(elevation, albedo)
        self._add_rilles_and_ridges(elevation)

        # Smooth elevation slightly for realistic slope gradients
        elevation = gaussian_filter(elevation, sigma=1.2)
        albedo = np.clip(albedo, 0.1, 1.0)

        # Physical shading
        radiance = self._render_sun_illumination(
            elevation, albedo, sun_azimuth_deg=sun_azimuth_deg, sun_elevation_deg=sun_elevation_deg
        )

        if dtype == np.uint8:
            return (np.clip(radiance, 0.0, 1.0) * 255.0).astype(np.uint8)
        else:
            return np.clip(radiance, 0.0, 1.0).astype(np.float32)
