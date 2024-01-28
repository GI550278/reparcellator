import json
import logging
import pathlib
from multiprocessing import Queue

import requests
from os import path
from urllib.parse import urlparse

from shapely import Polygon

from meshexchange.Surface.Extent import Extent


class FilterTileSet:
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
        self.on_remote = 'http' in self.src

        output_directory = pathlib.Path(self.dst)
        if not output_directory.exists():
            output_directory.mkdir(parents=True, exist_ok=True)

        self.tileset = None
        self.main_polygon = None
        self.tileQueue = Queue()
        self.tilesetQueue = Queue()

    def initTileSet(self, tilesetData):
        self.tileset = {}
        for key, value in tilesetData.items():
            if key == "root":
                self.tileset[key] = {}
            else:
                self.tileset[key] = tilesetData[key]

    def getLink(self, content):
        if 'uri' in content:
            return content['uri']
        elif 'url' in content:
            return content['url']
        else:
            raise Exception('missing url or uri')

    def getRegion(self, content):
        if "boundingVolume" in content:
            if "region" in content["boundingVolume"]:
                return content["boundingVolume"]["region"]
        return None

    def printContent(self, obj, root_dir, level):
        node = {}
        on_children = True
        for key in ['boundingVolume', 'geometricError', 'refine']:
            if key in obj:
                node[key] = obj[key]

        if 'content' not in obj:
            logging.info("no content in child, skipping")
        else:
            region = self.getRegion(obj['content'])
            if region is None:
                region = self.getRegion(obj)

            link = self.getLink(obj['content'])

            if link.endswith('.b3dm'):
                children_ = []
                if 'children' in obj:
                    for child in obj['children']:
                        if 'content' in child:
                            child_link = self.getLink(child['content'])

                            if child_link.endswith('.b3dm'):
                                children_.append(root_dir + '/' + child_link)
                            elif child_link.endswith('.json'):
                                cc = self.getRootInTileSet(root_dir, child_link)
                                if cc is not None:
                                    children_.append(root_dir + '/' + cc)

                p = None
                tile_uri = root_dir + '/' + link
                if self.on_remote:
                    if tile_uri[0] == '/':
                        uri = self.src + tile_uri
                    else:
                        uri = self.src + '/' + tile_uri

                    # assuming the link is valid for faster download
                    p = pathlib.Path(urlparse(uri).path)

                    # r = requests.head(uri)
                    # if r.status_code == 200:
                    #     p = pathlib.Path(urlparse(uri).path)
                else:
                    if not path.exists(self.src + '/' + tile_uri):
                        logging.warning(f"b3dm file not found: {tile_uri}")
                    else:
                        p = pathlib.Path(self.src + '/' + tile_uri)

                if p is not None:
                    q = pathlib.Path(self.dst + '/' + tile_uri)
                    output_directory = q.parents[0]
                    if not output_directory.exists():
                        output_directory.mkdir(parents=True, exist_ok=True)

                    ##########################################
                    tile_extent = Extent.fromRad(region).transform('32636')
                    tile_polygon = Polygon(tile_extent.asPolygon())

                    if self.main_polygon is None:
                        relation = 2
                    else:
                        relation = self.main_polygon.relation(tile_polygon)

                    if relation == 0:
                        result, on_children = False, False
                    else:
                        result, on_children = True, True
                    ###########################################
                    self.tileQueue.put(
                        {'src': p, 'data_directory': q, 'extent': region, 'level': level, 'relation': relation})
                    if result:
                        node['content'] = obj['content']
            elif link.endswith('.json'):
                tileset = root_dir + '/' + link
                n = tileset.rfind('/')
                self.processTileSet(tileset[:n], tileset[n + 1:].strip(), level + 1)
                node['content'] = obj['content']
                return node

        if 'children' in obj and on_children:
            node['children'] = []
            for child in obj['children']:
                filtered_content = self.printContent(child, root_dir, level + 1)
                if filtered_content is not None:
                    node['children'].append(filtered_content)
        return node

    def processTileSet(self, root_dir, tileset_name, level=0):

        if len(root_dir) > 0:
            if root_dir[0] == '/':
                tileset_path = self.src + root_dir + '/' + tileset_name
            else:
                tileset_path = self.src + '/' + root_dir + '/' + tileset_name
        else:
            if tileset_name[0] == '/':
                tileset_path = self.src + tileset_name
            else:
                tileset_path = self.src + '/' + tileset_name

        if self.on_remote:
            r = requests.get(tileset_path)
            if r.status_code == 200:
                tilesetData = json.loads(r.content.decode('utf-8'))
            else:
                return None
        else:
            if not path.exists(tileset_path):
                logging.warning(f"tileset file not found: {tileset_path}")
                return None

            try:
                with open(tileset_path, 'r') as f:
                    tilesetData = json.load(f)
            except:
                return None

        filteredContent = self.printContent(tilesetData['root'], root_dir, level)

        tileset = {}
        for key, value in tilesetData.items():
            if key == "root":
                tileset[key] = filteredContent
            else:
                tileset[key] = tilesetData[key]

        if len(root_dir) > 0:
            if root_dir[0] == '/':
                output_tileset = self.dst + root_dir + '/' + tileset_name
            else:
                output_tileset = self.dst + '/' + root_dir + '/' + tileset_name
        else:
            output_tileset = self.dst + '/' + tileset_name

        self.tilesetQueue.put({'tileset': tileset, 'path': output_tileset})

    def getRootInTileSet(self, root_dir, tileset):
        p = self.src
        if len(root_dir) > 0:
            if root_dir[0] == '/':
                p += root_dir
            else:
                p += '/' + root_dir
        tileset_file = pathlib.Path(tileset)
        if tileset[0] == '/':
            tileset_path = p + tileset
        else:
            tileset_path = p + "/" + tileset
        if self.on_remote:
            r = requests.get(tileset_path)
            if r.status_code == 200:
                tilesetData = json.loads(r.content.decode('utf-8'))
            else:
                return None
        else:
            if not path.exists(tileset_path):
                logging.warning(f"tileset file not found: {tileset_path}")
                return None

            try:
                with open(tileset_path, 'r') as f:
                    tilesetData = json.load(f)
            except:
                return ""

        obj = tilesetData['root']
        if 'content' not in obj:
            logging.info("No content in tileset root, skipping")
            return ""
        else:
            link = self.getLink(obj['content'])
            if link.endswith('.b3dm'):
                try:
                    root = str(tileset_file.with_name(link))
                except Exception as e:
                    logging.error('Failed to find b3dm(%s): %s', link, e)
                    return ""
                return root
            elif link.endswith('.json'):
                return self.getRootInTileSet(root_dir, link)
