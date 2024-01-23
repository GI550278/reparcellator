import json
import pathlib
import shutil
from os import path
from urllib.parse import urlparse

import requests


class FilterTileSet:
    def __init__(self, src, dst):
        self.src = src
        self.dst = dst
        self.on_remote = 'http' in self.src

        output_directory = pathlib.Path(self.dst)
        if not output_directory.exists():
            output_directory.mkdir(parents=True, exist_ok=True)

        self.tileset = None

    def initTileSet(self, tilesetData):
        self.tileset = {}
        for key, value in tilesetData.items():
            if key == "root":
                self.tileset[key] = {}
                # rootData = tilesetData[key]
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
        # raise Exception('missing region')

    def printContent(self, obj, root_dir, callback):
        node = {}
        on_children = True
        for key in ['boundingVolume', 'geometricError', 'refine']:
            if key in obj:
                node[key] = obj[key]

        if 'content' not in obj:
            print("no content")
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
                    r = requests.head(uri)
                    if r.status_code == 200:
                        p = pathlib.Path(urlparse(uri).path)
                else:
                    if not path.exists(self.src + '/' + tile_uri):
                        print("WARNING: b3dm file not found:", tile_uri)
                        # return
                    else:
                        p = pathlib.Path(self.src + '/' + tile_uri)

                if p is not None:
                    q = pathlib.Path(self.dst + '/' + tile_uri)
                    output_directory = q.parents[0]
                    if not output_directory.exists():
                        output_directory.mkdir(parents=True, exist_ok=True)

                    # shutil.copy(p, q)
                    result, on_children = callback({'src': p, 'data_directory': q, 'extent': region})
                    if result:
                        node['content'] = obj['content']
            elif link.endswith('.json'):
                print(link + " JSON")
                tileset = root_dir + '/' + link
                n = tileset.rfind('/')
                self.processTileSet(tileset[:n], tileset[n + 1:].strip(), callback)
                node['content'] = obj['content']
                return node

        if 'children' in obj and on_children:
            node['children'] = []
            for child in obj['children']:
                filtered_content = self.printContent(child, root_dir, callback)
                if filtered_content is not None:
                    node['children'].append(filtered_content)
        return node

    def processTileSet(self, root_dir, tileset_name, callback):

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
                print("WARNING: tileset file not found:", tileset_path)
                return None

            try:
                with open(tileset_path, 'r') as f:
                    tilesetData = json.load(f)
            except:
                return None

        filteredContent = self.printContent(tilesetData['root'], root_dir, callback)

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

        with open(output_tileset, 'w') as f:
            json.dump(tileset, f)

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
                print("WARNING: tileset file not found:", tileset_path)
                return None

            try:
                with open(tileset_path, 'r') as f:
                    tilesetData = json.load(f)
            except:
                return ""

        obj = tilesetData['root']
        if 'content' not in obj:
            return ""
        else:
            link = self.getLink(obj['content'])
            if link.endswith('.b3dm'):
                try:
                    root = str(tileset_file.with_name(link))
                except:
                    print('Error could not find :' + link)
                    return ""
                return root
            elif link.endswith('.json'):
                return self.getRootInTileSet(root_dir, link)
