from TileScheme.ModelWmtsCutter import ModelWmtsCutter
from TileScheme.WmtsTile import WmtsTile

index_path = r"C:\temp\index_25_v2_copy.gpkg"
full_path = r'C:\temp\test_combine\tile_15.glb'
model_cutter = ModelWmtsCutter(index_path)
tile = WmtsTile(39051,10640,15)
model_cutter.cut(tile.x, tile.y, tile.z, full_path)
print('Done.')
