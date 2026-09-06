"""
Synthetic Test Dataset Generator for Chandrayaan-2 and LROC Products.
Creates realistic mock ZIP archives with authentic PDS4 XML, PDS3 LBL, GeoTIFF, and ENVI headers.
"""
import io
import os
import zipfile
import numpy as np
from PIL import Image, TiffImagePlugin, TiffTags
from pathlib import Path


def generate_lunar_synthetic_surface(width: int = 512, height: int = 512, dtype=np.uint16) -> np.ndarray:
    """Generate realistic lunar surface texture with crater-like features."""
    np.random.seed(42)
    # Base regolith noise
    base = np.random.normal(loc=12000, scale=1500, size=(height, width)).astype(np.float64)

    # Add synthetic circular craters
    y, x = np.ogrid[:height, :width]
    for _ in range(12):
        cx = np.random.randint(50, width - 50)
        cy = np.random.randint(50, height - 50)
        r = np.random.randint(15, 60)
        dist_sq = (x - cx) ** 2 + (y - cy) ** 2
        crater_mask = dist_sq < (r ** 2)
        rim_mask = (dist_sq >= (r ** 2)) & (dist_sq < ((r + 8) ** 2))

        # Crater interior is darker / shadow on one side
        base[crater_mask] *= 0.6
        # Crater rim is brighter
        base[rim_mask] *= 1.35

    # Clip to dtype range
    if dtype == np.uint8:
        base_clipped = np.clip(base / 256.0, 10, 245).astype(np.uint8)
    else:
        base_clipped = np.clip(base, 100, 60000).astype(np.uint16)

    return base_clipped


def create_geotiff(
    output_path: Path,
    width: int = 512,
    height: int = 512,
    pixel_scale: float = 0.25,
    origin_x: float = 22.8,
    origin_y: float = -70.9,
    dtype=np.uint16
) -> None:
    """Save an image as a GeoTIFF with spatial resolution and tie point tags."""
    arr = generate_lunar_synthetic_surface(width, height, dtype=dtype)
    img = Image.fromarray(arr)

    # Create TIFF info tags
    ifd = Image.Exif() if hasattr(Image, "Exif") else None
    tiffinfo = TiffImagePlugin.ImageFileDirectory_v2()

    # 33550: ModelPixelScaleTag (scale_x, scale_y, scale_z)
    tiffinfo[33550] = (pixel_scale, pixel_scale, 0.0)
    # 33922: ModelTiepointTag (I, J, K, X, Y, Z)
    tiffinfo[33922] = (0.0, 0.0, 0.0, origin_x, origin_y, 0.0)
    # 34737: GeoAsciiParamsTag
    tiffinfo[34737] = "Moon_2000_Equirectangular|"

    img.save(output_path, format="TIFF", tiffinfo=tiffinfo)


def create_synthetic_datasets(output_dir: Path = Path("./tests/sample_data")) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created_zips = {}

    # =========================================================================
    # 1. Chandrayaan-2 OHRC ZIP
    # =========================================================================
    ohrc_zip_path = output_dir / "ch2_ohrc_orbital_product.zip"
    with zipfile.ZipFile(ohrc_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # GeoTIFF
        buf_tif = io.BytesIO()
        arr = generate_lunar_synthetic_surface(512, 512, np.uint16)
        img = Image.fromarray(arr)
        tiffinfo = TiffImagePlugin.ImageFileDirectory_v2()
        tiffinfo[33550] = (0.25, 0.25, 0.0)
        tiffinfo[33922] = (0.0, 0.0, 0.0, 22.80, -70.90, 0.0)
        img.save(buf_tif, format="TIFF", tiffinfo=tiffinfo)
        zf.writestr("data/ch2_ohrc_20230815_sc23.tif", buf_tif.getvalue())

        # PDS4 XML Label
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1">
    <Identification_Area>
        <logical_identifier>urn:isro:ch2:ohrc:data:ch2_ohrc_20230815_sc23</logical_identifier>
        <version_id>1.0</version_id>
        <title>Chandrayaan-2 OHRC Calibrated Lunar Surface Swath</title>
        <product_class>Product_Observational</product_class>
        <processing_level>Calibrated</processing_level>
    </Identification_Area>
    <Observation_Area>
        <Time_Coordinates>
            <start_date_time>2023-08-15T06:12:45.120Z</start_date_time>
            <stop_date_time>2023-08-15T06:14:15.840Z</stop_date_time>
        </Time_Coordinates>
        <Investigation_Area>
            <name>Chandrayaan-2</name>
            <type>Mission</type>
        </Investigation_Area>
        <Observing_System>
            <Observing_System_Component>
                <name>Orbital High Resolution Camera</name>
                <type>Instrument</type>
            </Observing_System_Component>
        </Observing_System>
        <Discipline_Area>
            <Geometry>
                <Surface_Geometry>
                    <center_latitude>-70.9250</center_latitude>
                    <center_longitude>22.8450</center_longitude>
                    <Bounding_Coordinates>
                        <west_bounding_coordinate>22.7500</west_bounding_coordinate>
                        <east_bounding_coordinate>22.9400</east_bounding_coordinate>
                        <north_bounding_coordinate>-70.8500</north_bounding_coordinate>
                        <south_bounding_coordinate>-71.0000</south_bounding_coordinate>
                    </Bounding_Coordinates>
                </Surface_Geometry>
                <Sun_Angles>
                    <incidence_angle>42.500</incidence_angle>
                    <emission_angle>3.200</emission_angle>
                    <phase_angle>40.100</phase_angle>
                    <solar_azimuth>112.450</solar_azimuth>
                    <solar_elevation>47.500</solar_elevation>
                    <look_angle>2.100</look_angle>
                </Sun_Angles>
            </Geometry>
            <Cartography>
                <map_projection_name>Equirectangular</map_projection_name>
                <coordinate_system_id>Moon_2000</coordinate_system_id>
                <pixel_resolution unit="m/pixel">0.25</pixel_resolution>
            </Cartography>
        </Discipline_Area>
    </Observation_Area>
    <File_Area_Observational>
        <File>
            <file_name>ch2_ohrc_20230815_sc23.tif</file_name>
        </File>
        <Array_2D_Image>
            <axes>2</axes>
            <axis_index_order>Last_Index_Fastest</axis_index_order>
            <Element_Array>
                <data_type>UnsignedLSB2</data_type>
            </Element_Array>
            <Axis_Array>
                <axis_name>Line</axis_name>
                <elements>512</elements>
                <sequence_number>1</sequence_number>
            </Axis_Array>
            <Axis_Array>
                <axis_name>Sample</axis_name>
                <elements>512</elements>
                <sequence_number>2</sequence_number>
            </Axis_Array>
        </Array_2D_Image>
    </File_Area_Observational>
</Product_Observational>"""
        zf.writestr("metadata/ch2_ohrc_20230815_sc23.xml", xml_content)

        # Browse image
        buf_jpg = io.BytesIO()
        arr_8 = (arr / 256.0).astype(np.uint8)
        Image.fromarray(arr_8).save(buf_jpg, format="JPEG")
        zf.writestr("browse/ch2_ohrc_20230815_sc23_browse.jpg", buf_jpg.getvalue())

        # Auxiliary ephemeris table
        zf.writestr("auxiliary/orbit_geometry_ephem.tab", "# TIME, ORBIT_RADIUS_KM, ALTITUDE_KM\n2023-08-15T06:12:45, 1837.4, 100.2\n")

    created_zips["OHRC"] = ohrc_zip_path

    # =========================================================================
    # 2. Chandrayaan-2 TMC-2 ZIP
    # =========================================================================
    tmc2_zip_path = output_dir / "ch2_tmc2_orbital_product.zip"
    with zipfile.ZipFile(tmc2_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        buf_tif = io.BytesIO()
        arr = generate_lunar_synthetic_surface(512, 512, np.uint16)
        img = Image.fromarray(arr)
        tiffinfo = TiffImagePlugin.ImageFileDirectory_v2()
        tiffinfo[33550] = (5.0, 5.0, 0.0)
        tiffinfo[33922] = (0.0, 0.0, 0.0, 22.75, -70.85, 0.0)
        img.save(buf_tif, format="TIFF", tiffinfo=tiffinfo)
        zf.writestr("data/ch2_tmc2_triplet_nadir.tif", buf_tif.getvalue())

        # PDS4 XML
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1">
    <Identification_Area>
        <logical_identifier>urn:isro:ch2:tmc2:data:ch2_tmc2_triplet_nadir</logical_identifier>
        <version_id>1.0</version_id>
        <title>Chandrayaan-2 TMC-2 Stereo Triplet Nadir Strip</title>
        <product_class>Product_Observational</product_class>
        <processing_level>L2_Derived_DEM</processing_level>
    </Identification_Area>
    <Observation_Area>
        <Time_Coordinates>
            <start_date_time>2023-08-15T06:11:30.000Z</start_date_time>
            <stop_date_time>2023-08-15T06:15:30.000Z</stop_date_time>
        </Time_Coordinates>
        <Investigation_Area>
            <name>Chandrayaan-2</name>
            <type>Mission</type>
        </Investigation_Area>
        <Observing_System>
            <Observing_System_Component>
                <name>Terrain Mapping Camera-2 (TMC-2)</name>
                <type>Instrument</type>
            </Observing_System_Component>
        </Observing_System>
        <Discipline_Area>
            <Geometry>
                <Surface_Geometry>
                    <center_latitude>-70.9200</center_latitude>
                    <center_longitude>22.8400</center_longitude>
                    <Bounding_Coordinates>
                        <west_bounding_coordinate>22.7000</west_bounding_coordinate>
                        <east_bounding_coordinate>22.9800</east_bounding_coordinate>
                        <north_bounding_coordinate>-70.8000</north_bounding_coordinate>
                        <south_bounding_coordinate>-71.0400</south_bounding_coordinate>
                    </Bounding_Coordinates>
                </Surface_Geometry>
                <Sun_Angles>
                    <incidence_angle>38.200</incidence_angle>
                    <emission_angle>12.000</emission_angle>
                    <phase_angle>36.500</phase_angle>
                    <solar_azimuth>110.100</solar_azimuth>
                    <solar_elevation>51.800</solar_elevation>
                </Sun_Angles>
            </Geometry>
            <Cartography>
                <map_projection_name>Equirectangular</map_projection_name>
                <coordinate_system_id>Moon_2000</coordinate_system_id>
                <pixel_resolution unit="m/pixel">5.0</pixel_resolution>
            </Cartography>
        </Discipline_Area>
    </Observation_Area>
    <File_Area_Observational>
        <File>
            <file_name>ch2_tmc2_triplet_nadir.tif</file_name>
        </File>
    </File_Area_Observational>
</Product_Observational>"""
        zf.writestr("metadata/ch2_tmc2_triplet_nadir.xml", xml_content)
        # Browse
        buf_png = io.BytesIO()
        Image.fromarray(arr_8).save(buf_png, format="PNG")
        zf.writestr("browse/ch2_tmc2_triplet_thumb.png", buf_png.getvalue())

    created_zips["TMC-2"] = tmc2_zip_path

    # =========================================================================
    # 3. Chandrayaan-2 IIRS ZIP
    # =========================================================================
    iirs_zip_path = output_dir / "ch2_iirs_orbital_product.zip"
    with zipfile.ZipFile(iirs_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Binary cube data (64 samples, 64 lines, 16 bands)
        cube_arr = np.random.randint(500, 30000, size=(64, 64, 16), dtype=np.uint16)
        zf.writestr("data/ch2_iirs_hyperspectral_cube.dat", cube_arr.tobytes())

        # ENVI header
        hdr_content = """ENVI
description = {Chandrayaan-2 IIRS Calibrated Hyperspectral Radiance Cube}
samples = 64
lines = 64
bands = 16
header offset = 0
file type = ENVI Standard
data type = 12
interleave = bsq
byte order = 0
map info = {Equirectangular, 1.0, 1.0, 22.80, -70.90, 80.0, 80.0, Moon_2000, units=Meters}
coordinate system string = {Moon_2000_Equirectangular}
wavelength = {800.0, 850.0, 900.0, 950.0, 1000.0, 1100.0, 1200.0, 1300.0, 1400.0, 1500.0, 1600.0, 1700.0, 1800.0, 1900.0, 2000.0, 2100.0}
"""
        zf.writestr("data/ch2_iirs_hyperspectral_cube.hdr", hdr_content)

        # PDS4 XML
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Product_Observational xmlns="http://pds.nasa.gov/pds4/pds/v1">
    <Identification_Area>
        <logical_identifier>urn:isro:ch2:iirs:data:ch2_iirs_hyperspectral_cube</logical_identifier>
        <version_id>1.0</version_id>
        <title>Chandrayaan-2 IIRS Hyperspectral Mineral Cube</title>
        <product_class>Product_Observational</product_class>
        <processing_level>Calibrated_Spectra</processing_level>
    </Identification_Area>
    <Observation_Area>
        <Time_Coordinates>
            <start_date_time>2023-08-15T06:10:00.000Z</start_date_time>
            <stop_date_time>2023-08-15T06:16:00.000Z</stop_date_time>
        </Time_Coordinates>
        <Investigation_Area>
            <name>Chandrayaan-2</name>
            <type>Mission</type>
        </Investigation_Area>
        <Observing_System>
            <Observing_System_Component>
                <name>Imaging Infrared Spectrometer (IIRS)</name>
                <type>Instrument</type>
            </Observing_System_Component>
        </Observing_System>
        <Discipline_Area>
            <Geometry>
                <Surface_Geometry>
                    <center_latitude>-70.9000</center_latitude>
                    <center_longitude>22.8000</center_longitude>
                    <Bounding_Coordinates>
                        <west_bounding_coordinate>22.6000</west_bounding_coordinate>
                        <east_bounding_coordinate>23.0000</east_bounding_coordinate>
                        <north_bounding_coordinate>-70.7500</north_bounding_coordinate>
                        <south_bounding_coordinate>-71.0500</south_bounding_coordinate>
                    </Bounding_Coordinates>
                </Surface_Geometry>
                <Sun_Angles>
                    <incidence_angle>45.000</incidence_angle>
                    <emission_angle>0.500</emission_angle>
                    <phase_angle>44.800</phase_angle>
                    <solar_azimuth>115.000</solar_azimuth>
                    <solar_elevation>45.000</solar_elevation>
                </Sun_Angles>
            </Geometry>
            <Cartography>
                <map_projection_name>Equirectangular</map_projection_name>
                <coordinate_system_id>Moon_2000</coordinate_system_id>
                <pixel_resolution unit="m/pixel">80.0</pixel_resolution>
            </Cartography>
        </Discipline_Area>
    </Observation_Area>
    <File_Area_Observational>
        <File>
            <file_name>ch2_iirs_hyperspectral_cube.dat</file_name>
        </File>
    </File_Area_Observational>
</Product_Observational>"""
        zf.writestr("metadata/ch2_iirs_hyperspectral_cube.xml", xml_content)
        # Browse
        buf_png = io.BytesIO()
        Image.fromarray(arr_8).save(buf_png, format="PNG")
        zf.writestr("browse/ch2_iirs_band_preview.png", buf_png.getvalue())

    created_zips["IIRS"] = iirs_zip_path

    # =========================================================================
    # 4. NASA LROC Reference ZIP
    # =========================================================================
    lroc_zip_path = output_dir / "lroc_nac_reference_product.zip"
    with zipfile.ZipFile(lroc_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        buf_tif = io.BytesIO()
        arr = generate_lunar_synthetic_surface(512, 512, np.uint8)
        img = Image.fromarray(arr)
        tiffinfo = TiffImagePlugin.ImageFileDirectory_v2()
        tiffinfo[33550] = (0.5, 0.5, 0.0)
        tiffinfo[33922] = (0.0, 0.0, 0.0, 22.82, -70.92, 0.0)
        img.save(buf_tif, format="TIFF", tiffinfo=tiffinfo)
        zf.writestr("data/m1142442434re_lroc_nac.tif", buf_tif.getvalue())

        # PDS3 ODL Label
        lbl_content = """PDS_VERSION_ID                     = PDS3
RECORD_TYPE                        = FIXED_LENGTH
RECORD_BYTES                       = 512
FILE_RECORDS                       = 512

/* Identification Parameters */
PRODUCT_ID                         = "M1142442434RE"
DATA_SET_ID                        = "LRO-L-LROC-2-EDR-V1.0"
INSTRUMENT_HOST_NAME               = "LUNAR RECONNAISSANCE ORBITER"
INSTRUMENT_NAME                    = "LUNAR RECONNAISSANCE ORBITER CAMERA"
INSTRUMENT_ID                      = "LROC"
SPACECRAFT_NAME                    = "LRO"
PRODUCT_TYPE                       = "CDR"

/* Time Parameters */
START_TIME                         = 2023-08-15T06:12:00.000Z
STOP_TIME                          = 2023-08-15T06:13:30.000Z

/* Spatial and Resolution Parameters */
CENTER_LATITUDE                    = -70.9200 <DEGREE>
CENTER_LONGITUDE                   = 22.8200 <DEGREE>
MINIMUM_LATITUDE                   = -71.0200 <DEGREE>
MAXIMUM_LATITUDE                   = -70.8200 <DEGREE>
WESTERNMOST_LONGITUDE              = 22.7200 <DEGREE>
EASTERNMOST_LONGITUDE              = 22.9200 <DEGREE>
RESOLUTION                         = 0.500 <METER/PIXEL>
MAP_SCALE                          = 0.500 <METER/PIXEL>

/* Photometric and Solar Geometry */
INCIDENCE_ANGLE                    = 45.300 <DEGREE>
EMISSION_ANGLE                     = 4.100 <DEGREE>
PHASE_ANGLE                        = 42.100 <DEGREE>
SOLAR_AZIMUTH_ANGLE                = 114.200 <DEGREE>
SOLAR_ELEVATION                    = 44.700 <DEGREE>
LOOK_ANGLE                         = 3.800 <DEGREE>

/* Georeferencing */
MAP_PROJECTION_TYPE                = "EQUIRECTANGULAR"
COORDINATE_SYSTEM_NAME             = "MOON_2000"
TARGET_NAME                        = "MOON"

/* Image Object Pointers and Dimensions */
^IMAGE                             = "m1142442434re_lroc_nac.tif"

OBJECT                             = IMAGE
  LINES                            = 512
  LINE_SAMPLES                     = 512
  SAMPLE_BITS                      = 8
  BANDS                            = 1
END_OBJECT                         = IMAGE

END
"""
        zf.writestr("metadata/m1142442434re_lroc_nac.lbl", lbl_content)

        # Browse
        buf_jpg = io.BytesIO()
        Image.fromarray(arr).save(buf_jpg, format="JPEG")
        zf.writestr("browse/m1142442434re_browse.jpg", buf_jpg.getvalue())

    created_zips["LROC"] = lroc_zip_path

    print(f"Synthetic test products generated in: {output_dir}")
    for k, v in created_zips.items():
        print(f"  - {k}: {v}")

    return created_zips


if __name__ == "__main__":
    create_synthetic_datasets()
