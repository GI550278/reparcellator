from pyproj import Transformer
import matplotlib.pyplot as plt
from shapely import Polygon, from_wkt

from TileScheme.WmtsTile import WmtsTile
from meshexchange.Surface.Extent import Extent


def plot_polygon(polygon, color='r'):
    x, y = polygon.exterior.xy
    plt.plot(x, y, color)


def plot_extent(extent, color='r'):
    polygon2 = Polygon(extent.asPolygon())
    plot_polygon(polygon2, color)


def plot_geo_extent(e, color):
    transformer = Transformer.from_crs(f"epsg:4326", f"epsg:32636")
    bottom_left = list(transformer.transform(e.y_min, e.x_min))
    top_right = list(transformer.transform(e.y_max, e.x_max))
    top_left = list(transformer.transform(e.y_max, e.x_min))
    bottom_right = list(transformer.transform(e.y_min, e.x_max))
    polygon = Polygon([bottom_left, top_left, top_right, bottom_right])
    x, y = polygon.exterior.xy
    plt.plot(x, y, color)


def average(a, b):
    return (a + b) / 2


def plot_special_geo_extent(e, color):
    transformer = Transformer.from_crs(f"epsg:4326", f"epsg:32636")

    bottom_left = list(transformer.transform(e.y_min, e.x_min))
    top_right = list(transformer.transform(e.y_max, e.x_max))
    top_left = list(transformer.transform(e.y_max, e.x_min))
    bottom_right = list(transformer.transform(e.y_min, e.x_max))

    k = 0
    xmin = average(top_left[k], bottom_left[k])
    xmax = average(top_right[k], bottom_right[k])
    k = 1
    ymin = average(bottom_right[k], bottom_left[k])
    ymax = average(top_right[k], top_left[k])

    plot_extent(Extent(xmin, ymin, xmax, ymax, '32636'), color)


def plot_special2_geo_extent(e, color):
    transformer = Transformer.from_crs(f"epsg:4326", f"epsg:32636")

    bottom_left = list(transformer.transform(e.y_min, e.x_min))
    top_right = list(transformer.transform(e.y_max, e.x_max))
    top_left = list(transformer.transform(e.y_max, e.x_min))
    bottom_right = list(transformer.transform(e.y_min, e.x_max))

    k = 0
    xmin = min(top_left[k], bottom_left[k])
    xmax = max(top_right[k], bottom_right[k])
    k = 1
    ymin = min(bottom_right[k], bottom_left[k])
    ymax = max(top_right[k], top_left[k])

    plot_extent(Extent(xmin, ymin, xmax, ymax, '32636'), color)


for x in range(156202, 156204):
    for y in range(42561, 42563):
        tile = WmtsTile(x, y, 17)
        e = tile.extent
        plot_geo_extent(e, 'g')
        # plot_special_geo_extent(e, 'r')
        plot_special2_geo_extent(e, 'b')
plt.show()
