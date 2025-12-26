import numpy as np

class Tr2D:
    def __init__(self, anchor_positions):
        self.anchors = np.array(anchor_positions)

    def solve_once(self, distances):
        A = []
        b = []

        x1, y1 = self.anchors[0]
        d1 = distances[0]

        for i in range(1, 3):
            xi, yi = self.anchors[i]
            di = distances[i]

            A_row = [2 * (xi - x1), 2 * (yi - y1)]
            b_val = (d1**2 - di**2) - (x1**2 - xi**2) - (y1**2 - yi**2)

            A.append(A_row)
            b.append(b_val)

        A = np.array(A)
        b = np.array(b)

        position = np.linalg.solve(A, b)
        return position[0], position[1]

    def compute_distances_from_position(self, tag_position):
        tag = np.array(tag_position)
        distances = [np.linalg.norm(tag - anchor) for anchor in self.anchors]
        return distances
    