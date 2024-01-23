class Triangle:
    def __init__(self, points):
        self.p = points

    def cartesian(self, lam):
        return [lam[0] * self.p[0][0] + lam[1] * self.p[1][0] + lam[2] * self.p[2][0],
                lam[0] * self.p[0][1] + lam[1] * self.p[1][1] + lam[2] * self.p[2][1]]

    def barycentric(self, p):
        det_t = (self.p[1][1] - self.p[2][1]) * (self.p[0][0] - self.p[2][0]) + (self.p[2][0] - self.p[1][0]) * (
                self.p[0][1] - self.p[2][1])
        lam1_top = (self.p[1][1] - self.p[2][1]) * (p[0] - self.p[2][0]) + (self.p[2][0] - self.p[1][0]) * (
                p[1] - self.p[2][1])

        lam2_top = (self.p[2][1] - self.p[0][1]) * (p[0] - self.p[2][0]) + (self.p[0][0] - self.p[2][0]) * (
                p[1] - self.p[2][1])

        lam1 = lam1_top / det_t
        lam2 = lam2_top / det_t
        lam3 = 1 - lam1 - lam2

        return [lam1, lam2, lam3]
