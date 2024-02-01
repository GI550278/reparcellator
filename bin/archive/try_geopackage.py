from src.reparcellator.TileIndex import TileIndex

ti = TileIndex()
coordinate = [[-77.05, 38.9],
              [-78.05, 38.9],
              [-78.00, 40.0]]
ti.append('path1', coordinate)
ti.append('path2', coordinate)
output_file = r"c:\temp\geopackage_1.gpkg"
ti.export_to_geopackage(output_file)
