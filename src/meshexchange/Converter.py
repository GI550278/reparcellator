import os
import sys
import time

from meshexchange.Surface.Extent import Extent
from meshexchange.OSGBModule import OSGBModule
from meshexchange.B3DMModule import B3DMModule
from os import path
import pathlib
import json
from multiprocessing import Queue, Process


def getRegion(content):
    if "boundingVolume" in content:
        if "region" in content["boundingVolume"]:
            return content["boundingVolume"]["region"]
    return None


def getLink(content):
    if 'uri' in content:
        return content['uri']
    elif 'url' in content:
        return content['url']
    else:
        raise Exception('missing url or uri')


def renameTile(child):
    if int(child.replace('\\', '/').split('/')[1]) < 12:
        return child.replace('../', '/').lstrip('/').replace('\\', '_').replace('/', '_')
    return child


class Converter:
    """
    This class can be used to convert b3dm file to osgb, or to convert a complete set of tiles
        that is defined by the given tileset json file
    USAGE:

        # first create a Converter object and specify from and to directories
        c = Converter('path/to/input/b3dmdir','path/to/output/osgbdir')
        c.convert('f1234.b3dm')
        # the output will be f1234.osgb in the output directory

        queue data fields:
            b3dm_file: a full path to b3dm file
            children: a list of full path to the children b3dm file
            children_extent: a list (same size as children) with geo extent four numbers in rad

    """

    def __init__(self, src, dst, **kwargs):
        self.src = src
        self.data_directory = dst + "/Data"
        self.destination_directory_root = dst

        self.add_white_for_missing_textures = kwargs['add_white_for_missing_textures'] \
            if 'add_white_for_missing_textures' in kwargs else True
        self.on_split = kwargs['on_split'] if 'on_split' in kwargs else True
        self.on_remove_meshes_with_no_texture = kwargs['on_remove_meshes_with_no_texture'] \
            if 'on_remove_meshes_with_no_texture' in kwargs else True
        self.first_job = kwargs['first_job'] if 'first_job' in kwargs else False
        self.main_extent = kwargs['main_extent'] if 'main_extent' in kwargs else None
        self.writeHint = kwargs['writeHint'] if 'writeHint' in kwargs else 1
        self.osgb_version = kwargs['version'] if 'version' in kwargs else 80
        self.Y_UP = kwargs['Y_UP'] if 'Y_UP' in kwargs else False
        self.jpegQuality = kwargs['jpegQuality'] if 'jpegQuality' in kwargs else None
        self.reduce = kwargs['reduce'] if 'reduce' in kwargs else None
        name = kwargs['renameCallback'] if 'renameCallback' in kwargs else None
        if name is not None:
            self.renameCallback = globals()[name]
        else:
            self.renameCallback = None
        self.validation()
        self.q = B3DMModule()
        self.o = OSGBModule(self.osgb_version,
                            destination_directory_root=self.destination_directory_root,
                            data_directory=self.data_directory,
                            main_extent=self.main_extent,
                            range=100)
        self.convertQueue = Queue()

    def validation(self):
        # validate main_extent if given
        if self.main_extent is not None:
            if not isinstance(self.main_extent, Extent):
                raise Exception("wrong type od main_extent, Extent expected")
            if not self.main_extent.epsg == "32636":
                raise Exception(f"wrong projection of the main_extent[{self.main_extent.epsg}], 32636 expected")

        # check existence of the source directory
        if not os.path.exists(self.src):
            raise Exception('source directory not found')

    def addConvertJob(self, b3dm_file, **kwargs):
        if self.convertQueue.qsize() > 120:
            print('\r',
                  'Queue is full. Waiting...',
                  end='')
            while self.convertQueue.qsize() > 10:
                print('\r',
                      f'Queue is full. Waiting... queue size {self.convertQueue.qsize()}...',
                      end='')

                time.sleep(1)

        children = kwargs['children'] if 'children' in kwargs else []
        children_extent = kwargs['children_extent'] if 'children_extent' in kwargs else []

        self.convertQueue.put({'b3dm_file': b3dm_file, 'children': children, 'children_extent': children_extent})

    def performConvert(self, data):
        self.convert_b3dm_to_osgb(data['b3dm_file'], children=data['children'], children_extent=data['children_extent'])

    def reader_proc(self):
        while True:
            msg = self.convertQueue.get()
            if msg == "DONE":
                break
            self.performConvert(msg)

    def startConverters(self, num_of_reader_procs):
        all_reader_procs = list()
        for ii in range(0, num_of_reader_procs):
            reader_p = Process(target=self.reader_proc)
            reader_p.daemon = True
            reader_p.start()  # Launch reader_p() as another proc

            all_reader_procs.append(reader_p)

        return all_reader_procs

    def stopConverters(self, num_of_reader_procs):
        for ii in range(0, num_of_reader_procs):
            self.convertQueue.put("DONE")

        print('\r', f'No more new tiles. Converting tiles in queue... {self.convertQueue.qsize()} tiles left', end='')
        while not self.convertQueue.empty():
            print('\r', f'No more new tiles. Converting tiles in queue... {self.convertQueue.qsize()} tiles left',
                  end='')
            time.sleep(1)
        print()

    def convert_b3dm_to_osgb(self, b3dm_file, **kwargs):
        """
        convert a single b3dm file to osgb file
        :param b3dm_file: the path to b3dm file relative to convert input directory
        :param kwargs:
        :return:
        """
        try:

            osgb_dir, osgb_file = self.osgbFilePath(b3dm_file)
            image_file, image_path = self.imageRelativePath(b3dm_file, osgb_dir)
            e = self.q.b3dmToExtendedExchange(self.src + '/' + b3dm_file,
                                              image_path,
                                              image_file,
                                              self.writeHint,
                                              self.Y_UP)

            # no parts empty mesh
            if len(e.parts) == 0:
                return

            children = kwargs['children'] if 'children' in kwargs else []
            children_extent = kwargs['children_extent'] if 'children_extent' in kwargs else []
            e.parts[0]['children'], e.parts[0]['children_extent'] = self.childrenPrepare(children, children_extent,
                                                                                         osgb_dir)

            if self.on_remove_meshes_with_no_texture:
                if len(e.parts[0]['children']) == 0:
                    subpart = e.parts[0]['subparts'][0]
                    if subpart['imageIndex'] is None or subpart['texCoords'] is None:
                        return

            if self.on_split:
                grp = self.o.extendedExchangeToGroupSplit(e, jpegQuality=self.jpegQuality, reduce=self.reduce)
            else:
                grp = self.o.extendedExchangeToGroup(e, jpegQuality=self.jpegQuality, reduce=self.reduce)

            if grp is None:
                return

            if self.add_white_for_missing_textures:
                grp2 = self.o.replaceMissingTextures(grp)
            else:
                grp2 = grp

            if not osgb_dir.exists():
                osgb_dir.mkdir(parents=True, exist_ok=True)
            self.o.groupToFile(grp2, osgb_file)
        except Exception as ex:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print('\nError while converting b3dm', ex)
            print(exc_type, fname, exc_tb.tb_lineno)
            print('\n end of error message')

    def childrenPrepare(self, children, children_extent, osgb_dir):
        children2 = []
        children_extent2 = []
        for child_index, child in enumerate(children):
            try:
                child_relpath, child_path = self.childRelativePath(child, osgb_dir)
            except Exception as e:
                print("Error while creating relative path", e)
                continue
            children2.append(child_relpath)
            children_extent2.append(children_extent[child_index])
        return children2, children_extent2

    def childRelativePath(self, child, osgb_dir):
        """
        :return:
        child_relpath :string - the child osgb file path relative to the given osgb_dir directory
        child_file :string - the absolute path to the child osgb file
        """

        if self.renameCallback is not None:
            child = self.renameCallback(child)

        child_path = pathlib.Path(child)
        child_file = pathlib.Path(self.data_directory + '/' + str(child_path.with_suffix('.osgb')))
        windows_path = str(os.path.relpath(child_file, osgb_dir))
        child_relpath = str(pathlib.PurePosixPath(pathlib.Path(windows_path)))
        return child_relpath, str(child_file)

    def osgbFilePath(self, b3dm_file):
        """
        :return:
        osgb_dir - the destination directory of the osgb
        osgb_file - the absolute path to the destination osgb
        """

        if self.renameCallback is not None:
            b3dm_file = self.renameCallback(b3dm_file)

        osgb_file = self.data_directory + '/' + b3dm_file.replace(".b3dm", '.osgb')

        osgb_dir = pathlib.Path(osgb_file).parent
        return osgb_dir, osgb_file

    def imageRelativePath(self, b3dm_file, osgb_dir):
        """
        :return:
        imageFile - the image path relative to the given osgb_dir directory
        imagePath - the absolute image path
        """

        try:
            if self.renameCallback is not None:
                b3dm_file = self.renameCallback(b3dm_file)

            image_path = self.data_directory + '/' + b3dm_file.replace(".b3dm", '.jpg')
            dst_image_windows_path = str(os.path.relpath(image_path, osgb_dir))
            image_file = str(pathlib.PurePosixPath(pathlib.Path(dst_image_windows_path)))
            return image_file, image_path
        except Exception as e:
            print("Error while creating relative path", e)
            return '', ''

    def processContent(self, obj, root_dir):
        if 'content' not in obj:
            print('\r',
                  f'no content',
                  end='')
        else:
            region = getRegion(obj['content'])
            if region is None:
                region = getRegion(obj)
            region_extent = Extent.fromRad(region).transform('32636')

            if self.main_extent is not None:
                if not self.main_extent.intersect(region_extent):
                    return

            link = getLink(obj['content'])
            if link.endswith('.b3dm'):
                children_ = []
                children_extent = []
                if 'children' in obj:
                    for child in obj['children']:
                        if 'content' in child:
                            child_link = getLink(child['content'])

                            if child_link.endswith('.b3dm'):
                                children_.append(root_dir + '/' + child_link)
                                child_extent = getRegion(child)[:4]
                                children_extent.append(child_extent)
                            elif child_link.endswith('.json'):
                                cc, child_extent = self.getRootInTileSet(root_dir, child_link)
                                if cc is not None:
                                    children_.append(root_dir + '/' + cc)
                                    children_extent.append(child_extent)
                tile_uri = root_dir + '/' + link
                if not path.exists(self.src + '/' + tile_uri):
                    print("WARNING: b3dm file not found:", tile_uri)
                    return
                else:
                    print('\r',
                          f'adding tile to queue {tile_uri}',
                          end='')
                    # print(children_)
                    # if '7\\' in tile_uri or '7/' in tile_uri:
                    #     return

                    self.addConvertJob(tile_uri, children=children_, children_extent=children_extent)
                    if self.first_job:
                        while not self.o.isReferenceExist():
                            print('\r',
                                  f'Waiting for reference point...',
                                  end='')
                            time.sleep(1)

                        self.first_job = False

            elif link.endswith('.json'):
                print('\r',
                      link,
                      end='')
                tileset = root_dir + '/' + link
                n = tileset.rfind('/')
                self.printTileSet(tileset[:n], tileset[n + 1:].strip())
                return

        if 'children' in obj:
            for child in obj['children']:
                self.processContent(child, root_dir)

    def getRootInTileSet(self, root_dir, tileset):
        p = self.src
        if len(root_dir) > 0:
            p += '/' + root_dir
        tileset_file = pathlib.Path(tileset)

        tileset_path = p + "/" + tileset
        if not path.exists(tileset_path):
            print("WARNING: tileset file not found:", tileset_path)
            return None, None

        try:
            with open(tileset_path, 'r') as f:
                tileset_data = json.load(f)
        except Exception as e:
            print("error reading tileset file", e)
            return "", None

        obj = tileset_data['root']
        if 'content' not in obj:
            return "", None
        else:
            link = getLink(obj['content'])
            if link.endswith('.b3dm'):
                try:
                    root = str(tileset_file.parent.joinpath(link))
                    extent = obj['boundingVolume']['region'][:4]
                    # root = str(tileset_file.with_name(link))
                except Exception as e:
                    print('Error could not find :' + link, e)
                    return "", None
                return root, extent
            elif link.endswith('.json'):
                return self.getRootInTileSet(root_dir, link)

    def printTileSet(self, root_dir, tileset):

        if len(root_dir) > 0:
            tileset_path = self.src + '/' + root_dir + '/' + tileset
        else:
            tileset_path = self.src + '/' + tileset

        if not path.exists(tileset_path):
            print("WARNING: tileset file not found:", tileset_path)
            return None

        try:
            with open(tileset_path, 'r') as f:
                tileset_data = json.load(f)
        except Exception as e:
            print("Error reading tileset ", e)
            return None

        self.processContent(tileset_data['root'], root_dir)

    def convertTileSet(self, tileset):
        self.first_job = False
        self.printTileSet("", tileset)
