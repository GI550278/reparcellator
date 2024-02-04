import logging

from shapely import Polygon

from src.TileScheme.ModelPrinter import ModelPrinter
from src.meshexchange.Surface.Extent import Extent

"""
Create sqlite index for given 3dtiles set 
"""

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    for n in [0, 1, 2, 3]:
        mc = ModelPrinter(src=f"http://localhost:8000/3dtiles/{n}",
                          dst=rf"c:\temp\copy_{n}",
                          output_file=rf"V:\Data\3DBest\Data_3DTiles\Index\index_{n}_v1.gpkg")
        # e = Extent.fromRad([0.6025426069863078,
        #                     0.5509374200611408,
        #                     0.6025520557542373,
        #                     0.5509516260878613])
        # extent_utm = e.transform('32636').buffer(10)
        # polygon = extent_utm.asPolygon()
        # x, y = 643308.852, 3491610.160
        # temp_extent = Extent.fromUtm36Dimensions(x, y, 100, 100)
        # model_polygon = Polygon(temp_extent.asPolygon())

        mc.startConverters(2, 1)
        mc.process_tileset('', 'tileset.json', None)
        mc.stopConverters(2, 1)

        print(f'Done {n}')
