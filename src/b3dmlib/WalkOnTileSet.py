import json
import pathlib
from os import path
from urllib.parse import urlparse

import requests


class WalkOnTileSet:
    def __init__(self, src):
        self.src = src
        self.on_remote = 'http' in self.src

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
        raise Exception('missing region')

    def printContent(self, obj, root_dir, callback):
        if 'content' not in obj:
            print("no content")
        else:
            region = self.getRegion(obj['content'])
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
                if self.on_remote:
                    tile_uri = root_dir + '/' + link

                    if tile_uri[0] == '/':
                        uri = self.src + tile_uri
                    else:
                        uri = self.src + '/' + tile_uri
                    r = requests.head(uri)
                    if r.status_code == 200:
                        p = pathlib.Path(urlparse(uri).path)
                        callback({'src': str(p.parents[0]), 'b3dm_file': str(p.name), 'extent': region})
                    else:
                        return None
                else:
                    tile_uri = root_dir + '/' + link
                    if not path.exists(self.src + '/' + tile_uri):
                        print("WARNING: b3dm file not found:", tile_uri)
                        # return
                    else:
                        p = pathlib.Path(self.src + '/' + tile_uri)

                        callback({'src': str(p.parents[0]), 'b3dm_file': str(p.name), 'extent': region})

            elif link.endswith('.json'):
                print(link + " JSON")
                tileset = root_dir + '/' + link
                n = tileset.rfind('/')
                self.printTileSet(tileset[:n], tileset[n + 1:].strip(), callback)
                return

        if 'children' in obj:
            for child in obj['children']:
                self.printContent(child, root_dir, callback)

    def printTileSet(self, root_dir, tileset, callback):
        p = self.src
        if len(root_dir) > 0:
            if root_dir[0] == '/':
                p += root_dir
            else:
                p += '/' + root_dir
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
                return None

        self.printContent(tilesetData['root'], root_dir, callback)

    def getRootInTileSet(self, root_dir, tileset):
        p = self.src
        if len(root_dir) > 0:
            p += '/' + root_dir
        tileset_file = pathlib.Path(tileset)

        tileset_path = p + "/" + tileset
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
