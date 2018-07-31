#!/usr/bin/env python

from datetime import datetime


class SaltShaker:
    def __init__(self, seed):
        self.seed = seed
        self.seed = (seed ^ 0x5deece66d) & ((1 << 48) - 1)

    # Identical to java.Random.next(bits)
    # next() is taken by generators
    def nextRand(self, bits):
        self.seed = (self.seed * 0x5deece66d + 0xb) & ((1 << 48) - 1)

        return (self.seed >> (48 - bits))

    def nextLong(self):
        return (self.nextRand(32) << 32) + self.nextRand(32)
