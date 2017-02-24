#!/usr/bin/env python

import os

from wsserver import WSServer


PROGRAM_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_NAME = os.path.join(PROGRAM_PATH, 'config.ini')


def main():
    WSServer.serve(CONFIG_FILE_NAME)


if __name__ == '__main__':
    main()