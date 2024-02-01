from TileScheme.WorldCRS84Quad import WorldCRS84Quad

if __name__ == '__main__':
    # index_path = r"C:\temp\index_25_v2_copy.gpkg"
    # model_cutter = ModelWmtsCutter(index_path)
    # model_cutter.cut(1249531, 340376, 20)
    # model_cutter.cut(624765, 170188, 19)
    w = WorldCRS84Quad()
    e = w.tileXYToExtent(42, 11, 15)
    x, y = e.centroid()
    p = w.positionToTileXY(x, y, 14)
    print(p)
