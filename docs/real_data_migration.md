# Real Lunar Data Migration Guide (SIH26166)

## 1. Unified Interface: `ImagePair`

The entire registration pipeline is designed around the generic `ImagePair` abstraction (`prototype/data_interface.py`):

```python
@dataclass
class ImagePair:
    reference: np.ndarray          # 2D float32 or uint8 array
    source: np.ndarray             # 2D float32 or uint8 array
    metadata: Optional[Dict[str, Any]] = None
    ground_truth_transform: Optional[np.ndarray] = None
    name: str = "lunar_pair"
```

## 2. Plugging in Real Multi-Sensor Datasets

When real Chandrayaan-2 (OHRC, TMC-2, IIRS) or LROC products are ingested through the Phase 8 Ingestion/Metadata parsers:

1. **Extract rasters**: Load GeoTIFF or ENVI array using `metadata_extractor` and `tifffile`/`rasterio`/`Pillow`.
2. **Harmonize GSD (Optional)**: Use `MultiscaleRepresentation.resample_to_gsd(src, src_gsd, ref_gsd)` to bring rasters to comparable pixel scales.
3. **Instantiate `ImagePair`**:
   ```python
   pair = ImagePair(
       reference=ref_raster,
       source=src_raster,
       metadata={
           "ref_sensor": "LROC",
           "src_sensor": "OHRC",
           "ref_gsd_m": 0.50,
           "src_gsd_m": 0.25,
           "region_code": "R01"
       },
       name="R01_OHRC_to_LROC"
   )
   ```
4. **Execute Pipeline**:
   ```python
   orchestrator = PrototypeRegistrationOrchestrator()
   report = orchestrator.run(input_pair=pair)
   ```

No changes to feature detection, matching, spatial selection, RANSAC, subpixel refinement, warping, or evaluation are required.
