"""
ComponentType values used in buffers inside glb/gltf files
"""


class ComponentType:
    """
    ComponentType values used in buffers inside glb/gltf files
    """
    BYTE = 5120
    UNSIGNED_BYTE = 5121
    SHORT = 5122
    UNSIGNED_SHORT = 5123
    UNSIGNED_INT = 5125
    FLOAT = 5126

    def __init__(self, component_type):
        self.type = component_type
        self.code_letter = {
            self.BYTE: 'b',
            self.UNSIGNED_BYTE: 'B',
            self.SHORT: 'h',
            self.UNSIGNED_SHORT: 'H',
            self.UNSIGNED_INT: 'I',
            self.FLOAT: 'f'
        }

    def codeLetter(self):
        if self.type in self.code_letter:
            return self.code_letter.get(self.type)
        return ''

    def getSize(self):
        if self.type in [5120, 5121]:
            return 1
        if self.type in [5122, 5123]:
            return 2
        if self.type in [5125, 5126]:
            return 4
        return 0
