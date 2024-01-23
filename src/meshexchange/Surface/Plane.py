from numpy import array, dot


class Plane:
    def __init__(self, n=array([0, 0, 1]), d=0):
        self.n = n
        self.D = d

    def distance(self, pnt):
        return abs((dot(self.n, pnt) + self.D))

    def spot(self, x, y):
        if abs(self.n[2]) < 1e-8:
            raise Exception("the plane is orthogonal")
        return -(self.n[0] * x + self.n[1] * y + self.D) / self.n[2]
