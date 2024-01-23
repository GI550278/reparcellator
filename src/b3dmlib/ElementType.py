class ElementType:

    def __init__(self, element_type):
        self.type = element_type
        self.element_size = {
            "SCALAR": 1,
            "VEC2": 2, "VEC3": 3, "VEC4": 4,
            "MAT2": 4, "MAT3": 9, "MAT4": 16
        }

    def getSize(self):
        if self.type in self.element_size:
            return self.element_size.get(self.type)
        return 0