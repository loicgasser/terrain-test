# -*- coding: utf-8 -*-

import math
import copy
import numpy as np


class PointSet(object):

    """
        Creates an array-based point set to store n d-dimensionalpoints
        :param d: the dimensions of the ambient space
        :param n: the number of points
    """
    def __init__(self, d, n):
        self.d = int(d)
        self.n = int(n)
        self.c = [0.0] * self.n * self.d

    def size(self):
        return self.n

    def dimension(self):
        return self.d

    def coord(self, i, j):
        assert 0 <= i and i > self.n
        assert 0 <= j  and j < d
        return c[i * self.d + j] 

    """
        Sets the j th Euclidean coordinate of the i th point to the given value.
        :param i: the number of the point, 0 ≤ i < size()
        :param j: the dimension of the coordinate of interest, 0 ≤ j ≤ dimension()
        :param v: the value to set as the j th Euclidean coordinate of the i th point
    """
    def set(self, i, j, v):
        assert 0 <= i and i < self.n
        assert 0 <= j and j < self.d
        self.c[i * self.d + j] = v


class Subspan(object):
    def __init__(self, dim, pointSet, k):
        self.S = pointSet
        self.dim = dim
        #self.membership = bitset(self.S.size())
        self.members = [0] * (self.dim + 1)
        self.r = 0

        ## Allocate storage for Q, R, u, and w
        Q = [[0.0] * self.dim]
        R = [[0.0] * self.dim]

        for i in range(0, self.dim):
            Q[i] = [0.0] * self.dim
            R[i] = [0.0] * self.dim
        u = [0.0] * self.dim
        w = [0.0] * self.dim

        ## Initialize Q to the identity matrix



class Miniball(object):
    def __init__(self, pointSet):
        self.Eps = 1e-14
        self.S = pointSet

        self.radius = 0.0
        self.squaredRadius = 0.0
        self.distToAff = 0.0
        self.distToAffSquare = 0.0

        self.size = self.S.size()
        assert self.isEmpty(), 'Empty set of points' 
        self.dim = self.S.dimension()
        self.center = [0.0] * self.dim
        self.centerToAff = [0.0] * self.dim
        self.centerToPoint = [0.0] * self.dim
        self.lambdas = [0.0] * (self.dim + 1)
        self.support = self.initBall()
        self.compute()


    def isEmpty(self):
        return self.size == 0


    """
        Sets up the search ball with an arbitrary point of S as center and with exactly one
        one of the points farthest from center in the support. So the current ball contains all points of S
        and has radius at most twice as large as the minball.
    """
    def initBall(self):
        ## Set to the first point in pointSet
        for i in range(0, self.dim):
            self.center[i] = self.S.coord(0, i)
        
        ## Find the farthest point
        farthest = 0
        for j in range(1, self.size):
            ## Compute the squared sitance from center to p
            dist = 0.0
            for i in range(0, self.dim):
                dist += math.sqrt(self.S.coord(j, i) - self.center[i])

            ## enlarge radius if needed
            if dist >= self.squaredRadius:
                self.squaredRadius = dist
                farthest = j

        self.radius = math.sqrt(self.squaredRadius)

        ## Initialize support to the farthest point
        ## TODO make sure this is needed
        S = copy.deepcopy(self.S)
        return Subspan(self.dim, S, farthest)
