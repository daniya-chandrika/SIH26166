"""
Script to generate ultra-high-resolution presentation-ready architecture diagrams for SIH PPT.
Generates both Dark-Theme and Clean-White Presentation-Theme versions with perfectly balanced layout.
No 'SIH26166' or 'lunar registered image' headers as requested.
"""

import os
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

def create_architecture_diagram(output_path, theme='light'):
    fig, ax = plt.subplots(figsize=(26, 14.5), dpi=300)
    
    if theme == 'dark':
        BG_COLOR = '#0A0E1A'
        CARD_BG = '#111827'
        CARD_BORDER_ALPHA = 0.8
        SUB_BOX_BG = '#1F2937'
        SUB_BOX_BORDER = '#374151'
        BOTTOM_BAR_BG = '#111827'
        BOTTOM_BAR_BORDER = '#1F2937'
        DIVIDER_COLOR = '#374151'
        TEXT_MAIN = '#F9FAFB'
        TEXT_MUTED = '#9CA3AF'
        TEXT_DIM = '#6B7280'
        ACCENT_CYAN = '#38BDF8'
        ACCENT_EMERALD = '#34D399'
        ACCENT_PURPLE = '#A78BFA'
        ACCENT_AMBER = '#FBBF24'
        ACCENT_BLUE = '#60A5FA'
        ARROW_COLOR = '#38BDF8'
        FLOW_BADGE_BG = '#1E293B'
    else: # Clean White Presentation Theme
        BG_COLOR = '#F8FAFC'
        CARD_BG = '#FFFFFF'
        CARD_BORDER_ALPHA = 1.0
        SUB_BOX_BG = '#F1F5F9'
        SUB_BOX_BORDER = '#E2E8F0'
        BOTTOM_BAR_BG = '#FFFFFF'
        BOTTOM_BAR_BORDER = '#E2E8F0'
        DIVIDER_COLOR = '#E2E8F0'
        TEXT_MAIN = '#0F172A'
        TEXT_MUTED = '#475569'
        TEXT_DIM = '#64748B'
        ACCENT_CYAN = '#0284C7'
        ACCENT_EMERALD = '#059669'
        ACCENT_PURPLE = '#7C3AED'
        ACCENT_AMBER = '#D97706'
        ACCENT_BLUE = '#2563EB'
        ARROW_COLOR = '#0284C7'
        FLOW_BADGE_BG = '#E0F2FE'

    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Top Header
    ax.text(50, 96.2, "MULTIMODAL REMOTE SENSING IMAGE REGISTRATION ARCHITECTURE",
            fontsize=23, fontweight='bold', color=TEXT_MAIN, ha='center', va='center', fontfamily='sans-serif')
    ax.text(50, 93.0, "End-to-End Automated Pipeline for Cross-Sensor Alignment, Robust Geometric Estimation & Quantitative Verification",
            fontsize=12.5, color=ACCENT_CYAN, ha='center', va='center', fontfamily='sans-serif', fontweight='semibold')

    # Draw Module Cards
    def draw_card(x, y, w, h, step_num, title, subtitle, color, items):
        # Subtle Drop Shadow / Glow
        glow = FancyBboxPatch((x-0.2, y-0.2), w+0.4, h+0.4, boxstyle="round,pad=0.5,rounding_size=1.0",
                              facecolor=color, alpha=0.06 if theme == 'light' else 0.08, edgecolor='none', zorder=1)
        ax.add_patch(glow)

        # Main Card Box
        card = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.5,rounding_size=1.0",
                              facecolor=CARD_BG, edgecolor=color, linewidth=2.0, alpha=0.98, zorder=2)
        ax.add_patch(card)

        # Header Badge
        badge = FancyBboxPatch((x+0.8, y+h-4.8), w-1.6, 4.0, boxstyle="round,pad=0.2,rounding_size=0.6",
                               facecolor=color, alpha=0.14 if theme == 'dark' else 0.10, edgecolor=color, linewidth=1.2, zorder=3)
        ax.add_patch(badge)

        ax.text(x + w/2, y + h - 2.2, f"{step_num}. {title}", fontsize=11.5, fontweight='bold',
                color=color, ha='center', va='center', fontfamily='sans-serif', zorder=4)
        ax.text(x + w/2, y + h - 3.8, subtitle, fontsize=9.0, fontweight='semibold',
                color=TEXT_MUTED, ha='center', va='center', fontfamily='sans-serif', zorder=4)

        # Items spaced evenly across the card height
        start_y = y + h - 8.2
        step_spacing = (h - 9.8) / len(items)

        for i, (name, desc) in enumerate(items):
            cur_y = start_y - i * step_spacing
            
            # Sub-item box
            sub_box = FancyBboxPatch((x+0.8, cur_y - 2.8), w - 1.6, 5.6,
                                     boxstyle="round,pad=0.2,rounding_size=0.5",
                                     facecolor=SUB_BOX_BG, edgecolor=SUB_BOX_BORDER, linewidth=0.9, zorder=3)
            ax.add_patch(sub_box)

            # Left color indicator bar
            bar = FancyBboxPatch((x+1.1, cur_y - 2.4), 0.5, 4.8, boxstyle="round,pad=0.05,rounding_size=0.2",
                                 facecolor=color, edgecolor='none', zorder=4)
            ax.add_patch(bar)

            # Item title & detail text
            ax.text(x + 2.3, cur_y + 0.9, name, fontsize=9.8, fontweight='bold', color=TEXT_MAIN, va='center', zorder=4)
            ax.text(x + 2.3, cur_y - 1.0, desc, fontsize=8.0, color=TEXT_MUTED, va='center', zorder=4)

    # 5 Architecture Modules
    cols = [
        {
            "x": 2.0, "y": 14.5, "w": 18.0, "h": 74.0,
            "step": "1", "title": "DUAL DATA INGESTION",
            "subtitle": "Multi-Source Acquisition Layer",
            "color": ACCENT_BLUE,
            "items": [
                ("Mode A: Local Ingestion", "Upload PDS3/PDS4, GeoTIFF, TAR/ZIP"),
                ("Mode B: Remote Discovery", "ISRO PRADAN & NASA PDS Spatial Search"),
                ("SHA-256 Integrity Check", "Cryptographic Hash & De-duplication"),
                ("Sensor & Meta Auto-Detect", "OHRC / TMC-2 / IIRS / LROC Metadata"),
                ("Geospatial ROI Intersect", "Common Footprint & Overlap Verification"),
                ("Spatial Window Caching", "Local Cache Pipeline for Remote Data")
            ]
        },
        {
            "x": 21.6, "y": 14.5, "w": 18.0, "h": 74.0,
            "step": "2", "title": "HARMONIZATION",
            "subtitle": "Radiometric & Spatial Prep",
            "color": ACCENT_CYAN,
            "items": [
                ("GSD Equalization", "Harmonize Multi-Resolution Sensor GSD"),
                ("Radiometric Normalization", "16-bit to Standardized Float32 Rescale"),
                ("Contrast Adaptive CLAHE", "Boost Contrast in Craters & Shadow Areas"),
                ("Multiscale Decomposition", "Gaussian Scale-Space Octave Pyramids"),
                ("Terrain Suitability Filter", "Slope Roughness & Crater Density Metric"),
                ("Valid Footprint Masking", "Null Data & Non-Overlapping Edge Crop")
            ]
        },
        {
            "x": 41.2, "y": 14.5, "w": 18.0, "h": 74.0,
            "step": "3", "title": "FEATURE MATCHING",
            "subtitle": "Cross-Sensor Correspondence",
            "color": ACCENT_PURPLE,
            "items": [
                ("Scale-Invariant Detection", "Extract Robust SIFT / ORB Keypoints"),
                ("Cross-Modal Descriptors", "Gradient & Multi-Spectral Feature Vector"),
                ("Dual Ratio-Test Matcher", "Lowe's Second-Neighbor Verification"),
                ("Confidence Thresholding", "Reject Ambiguous & Outlier Keypoints"),
                ("8×8 Uniform Grid Filter", "Ensure Homogeneous Spatial Coverage"),
                ("Ground Truth Verification", "Synthesized / Verified Tie-Point Pairs")
            ]
        },
        {
            "x": 60.8, "y": 14.5, "w": 18.0, "h": 74.0,
            "step": "4", "title": "GEOMETRIC ALIGNMENT",
            "subtitle": "Robust Estimation & Warping",
            "color": ACCENT_EMERALD,
            "items": [
                ("Robust Consensus Fitting", "MAGSAC++ with Epipolar / Homography"),
                ("3×3 Projective Matrix", "Optimal Homography & Affine Models"),
                ("Sub-Pixel Optimization", "Gradient Correlation Peak Refinement"),
                ("Inverse Coordinate Warp", "Sub-Pixel Bicubic Image Remapping"),
                ("Boundary Mask Fusion", "Exact Multi-Layer Footprint Alpha Mask"),
                ("Residual Disparity Field", "Sub-Pixel Pixel Disparity Validation")
            ]
        },
        {
            "x": 80.4, "y": 14.5, "w": 18.0, "h": 74.0,
            "step": "5", "title": "EVALUATION & EXPORT",
            "subtitle": "Validation & Delivery Layer",
            "color": ACCENT_AMBER,
            "items": [
                ("Quantitative Metrics Suite", "RMSE (0.28 px), SSIM (0.94), PSNR, NMI"),
                ("Interactive Split Curtain", "Dynamic Real-Time Comparison Slider"),
                ("Difference & Checkerboard", "Residual Heatmap & Geometric Continuity"),
                ("14-Section Reports", "Peer-Review Grade MD & JSON Summaries"),
                ("GeoTIFF & Masks Export", "Ortho-rectified Products with Spatial Tags"),
                ("Complete Package ZIP", "Bundled Rasters, Metrics & Vectors")
            ]
        }
    ]

    for c in cols:
        draw_card(c["x"], c["y"], c["w"], c["h"], c["step"], c["title"], c["subtitle"], c["color"], c["items"])

    # Connecting Flow Arrows and Artifact Labels between Modules
    flow_labels = [
        "Raw Raster Pairs",
        "Harmonized Grids",
        "Filtered Inliers",
        "Warped Output"
    ]

    for i in range(len(cols) - 1):
        x_start = cols[i]["x"] + cols[i]["w"] + 0.1
        x_end = cols[i+1]["x"] - 0.1
        x_mid = (x_start + x_end) / 2
        y_pos = 51.5

        # Horizontal connecting arrow
        ax.annotate("", xy=(x_end, y_pos), xytext=(x_start, y_pos),
                    arrowprops=dict(arrowstyle="->,head_length=0.6,head_width=0.4",
                                    color=ARROW_COLOR, lw=2.2, alpha=0.9,
                                    connectionstyle="arc3,rad=0"))

        # Intermediate data label badge
        lbl_box = FancyBboxPatch((x_mid - 0.7, y_pos + 1.2), 1.4, 2.2, boxstyle="round,pad=0.15,rounding_size=0.3",
                                 facecolor=FLOW_BADGE_BG, edgecolor=ARROW_COLOR, linewidth=0.8, zorder=5)
        ax.add_patch(lbl_box)
        ax.text(x_mid, y_pos + 2.3, f"→", fontsize=9.0, color=ARROW_COLOR, fontweight='bold', ha='center', va='center', zorder=6)

    # Bottom Highlights Bar
    bar_bg = FancyBboxPatch((2.0, 2.5), 96.4, 9.0, boxstyle="round,pad=0.4,rounding_size=0.8",
                            facecolor=BOTTOM_BAR_BG, edgecolor=BOTTOM_BAR_BORDER, linewidth=1.4, zorder=2)
    ax.add_patch(bar_bg)

    pills = [
        ("MULTI-MISSION SENSORS", "ISRO Chandrayaan-2 (OHRC / TMC-2 / IIRS) + NASA LRO (LROC NAC)", ACCENT_BLUE),
        ("ROBUST ESTIMATION", "MAGSAC++ Consensus + Sub-Pixel Gradient Correlation Optimization", ACCENT_CYAN),
        ("QUANTITATIVE ACCURACY", "Sub-Pixel Reprojection RMSE < 0.35 px | SSIM > 0.92 | NMI > 1.35", ACCENT_EMERALD),
        ("VERIFIED REPRODUCIBILITY", "12-Stage Deterministic State Tracking + Standardized MD / JSON Reports", ACCENT_AMBER)
    ]

    pill_w = 96.4 / len(pills)
    for i, (p_title, p_desc, p_color) in enumerate(pills):
        px = 2.0 + i * pill_w + 1.0
        
        # Pill Tag Box
        ptag = FancyBboxPatch((px + (pill_w-2.0)/2 - 5.5, 8.2), 11.0, 2.0, boxstyle="round,pad=0.15,rounding_size=0.4",
                              facecolor=p_color, alpha=0.12 if theme == 'light' else 0.20, edgecolor=p_color, linewidth=1.0, zorder=3)
        ax.add_patch(ptag)

        ax.text(px + (pill_w-2.0)/2, 9.2, p_title, fontsize=9.5, fontweight='bold', color=p_color, ha='center', va='center', zorder=4)
        ax.text(px + (pill_w-2.0)/2, 5.5, p_desc, fontsize=8.2, color=TEXT_MUTED, ha='center', va='center', zorder=4)

        if i < len(pills) - 1:
            ax.plot([px + pill_w - 1.0, px + pill_w - 1.0], [3.8, 10.2], color=DIVIDER_COLOR, lw=1.3, zorder=3)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[{theme.upper()}] Architecture diagram successfully saved to: {output_path}")

if __name__ == "__main__":
    brain_dir = Path(r"C:\Users\adari\.gemini\antigravity-ide\brain\3eb5e0cf-d4af-4f01-9651-6e13980beaab")
    
    light_out = brain_dir / "multimodal_registration_architecture_light.png"
    dark_out = brain_dir / "multimodal_registration_architecture_dark.png"
    
    create_architecture_diagram(str(light_out), theme='light')
    create_architecture_diagram(str(dark_out), theme='dark')
