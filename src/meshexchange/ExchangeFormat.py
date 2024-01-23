class ExchangeFormat:

    def __init__(self, **kwargs):
        self.indices = kwargs['indices'] if 'indices' in kwargs else []
        self.vertices = kwargs['vertices'] if 'vertices' in kwargs else []
        self.texCoords = kwargs['texCoords'] if 'texCoords' in kwargs else []
        self.imageBlob = kwargs['imageBlob'] if 'imageBlob' in kwargs else bytearray()
        self.imageFile = kwargs['imageFile'] if 'imageFile' in kwargs else ""
        self.subTileName = "unknown.osgb"
