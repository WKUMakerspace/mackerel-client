#!/usr/bin/env python

import Node


class KioskNode(Node):
    def __init__(self, name):
        super().__init__(name, 'kiosk')

        self.users = set()


