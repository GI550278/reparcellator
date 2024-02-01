import sys
from osgeo import ogr
from osgeo import osr

import math
import os

from b3dmlib.FilterTileSet import FilterTileSet


# from b3dmlib.WalkOnTileSet import WalkOnTileSet

# from bin.FilterTileSet import FilterTileSet
# from bin.ReadTileSet import ReadTileSet

os.environ['GDAL_DATA'] = r'C:\Users\sguya\PycharmProjects\reparcellator\venv\Lib\site-packages\osgeo\data\gdal'


class IndexShapeWriter:
    def __init__(self):
        # Set up the shapefile driver
        self.driver = ogr.GetDriverByName("ESRI Shapefile")

    def closeDataSource(self):
        # Save and close DataSource
        self.ds = None

    def createDataSource(self, name):
        # create the data source
        self.ds = self.driver.CreateDataSource(name + ".shp")

        # create the spatial reference system, WGS84
        self.srs = osr.SpatialReference()
        self.srs.ImportFromEPSG(4326)

        # create one layer
        self.layer = self.ds.CreateLayer("index", self.srs, ogr.wkbPolygon)

        # Add an ID field
        idField = ogr.FieldDefn("id", ogr.OFTInteger)
        self.layer.CreateField(idField)
        nameField = ogr.FieldDefn("name", ogr.OFTString)
        self.layer.CreateField(nameField)
        self.counter = 0

    def write(self, extent_deg, name):
        # Create ring
        ring = ogr.Geometry(ogr.wkbLinearRing)
        ring.AddPoint(extent_deg[0], extent_deg[1])
        ring.AddPoint(extent_deg[0], extent_deg[3])
        ring.AddPoint(extent_deg[2], extent_deg[3])
        ring.AddPoint(extent_deg[2], extent_deg[1])

        # Create polygon
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)

        # Create the feature and set values
        featureDefn = self.layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        feature.SetGeometry(poly)
        feature.SetField("id", self.counter)
        self.counter += 1
        feature.SetField("name", name)
        self.layer.CreateFeature(feature)

        feature = None


i = IndexShapeWriter()
i.createDataSource(r'c:\temp\index_shp.shp')

cnt = 0


def foo(data):
    global cnt
    extent = data['extent']
    if extent is None:
        return False, False
    name = data['src']

    extent_deg = list(map(lambda x: x * 180 / math.pi, extent[0:4]))
    i.write(extent_deg, str(name))
    print(cnt, name)
    cnt += 1

    if cnt > 100:
        return False, False
    return True, True


src = r"C:\Users\sguya\Downloads\cesium-starter-app-master\public\wmts_test_v1\flip_yz_v5"
# src = r"C:\temp\copy_1_v8"
# src = r"O:\Data\Vricon\Vricon_Lebanon_2023\Lebanon_1\vricon_3d_surface_model_3dtiles_1\data\unzip"
# src = r"C:\temp\vricon_small_sample"
tileset = r"tileset.json"

# src = r"C:\Users\sguya\Downloads\cesium-starter-app-master\public\exp003\2710_1_draco"
# tileset = r"DataSource_2710_1_draco_best_real.json"

# src = r"C:\Users\sguya\Downloads\cesium-starter-app-master\public\create_dtm\Example 004 - Trees\trees_2610_without"
# tileset = r"DataSource_trees_2610_without_best_real.json"

# src = r"C:\Users\sguya\Downloads\cesium-starter-app-master\public\3DTiles\guy27102023_1"
# tileset = "DataSource_guy27102023_1_best_real.json"
#
# src = r'C:\Users\sguya\Downloads\cesium-starter-app-master\public\Example\3DTiles'
# tileset = "DataSource_toGuyNew_best_real.json"


# src = r"C:\Users\sguya\Downloads\cesium-starter-app-master\public\Example_10"
# tileset = "tileset.json"

dst = r"c:\temp\delme"
w = FilterTileSet(src, dst)
w.processTileSet('', tileset, foo)

i.closeDataSource()
print('done')
