import logging
from TileScheme.ModelPrinter import ModelPrinter
from src.meshexchange.Surface.Extent import Extent

"""
Create sqlite index for given 3dtiles set 
"""

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    mc = ModelPrinter(src="http://localhost:8000/3dtiles/4",
                      dst=r"c:\temp\copy_4",
                      output_file=r"O:\Data\3DBest\Data_3DTiles\Index\test_index_4_v00.gpkg")
    e = Extent.fromRad([0.6025426069863078,
                        0.5509374200611408,
                        0.6025520557542373,
                        0.5509516260878613])
    extent_utm = e.transform('32636').buffer(10)
    polygon = extent_utm.asPolygon()
    mc.startConverters(2, 1)
    mc.process_tileset('', 'tileset.json', None)
    mc.stopConverters(2, 1)

    print('Done')
