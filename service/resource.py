import errno
import os

import requests

from messagebuf import MessageBuf


class ResException(Exception):
    pass


class ResLayer(object):
    def __init__(self, ltype, ldata):
        self.ltype = ltype
        self.ldata = ldata


class Resource(object):
    def __init__(self, resname, resver, rawinfo):
        self.resname = resname
        self.resver = resver

        buf = MessageBuf(rawinfo)

        canon_sig = 'Haven Resource 1'
        sig = buf.get_bytes(len(canon_sig))
        if sig != canon_sig:
            raise ResException('Wrong signature')

        ver = buf.get_uint16()
        if ver != self.resver:
            raise ResException('Wrong version')

        self.layers = []
        while not buf.eom():
            layer_type = buf.get_string()
            layer_len = buf.get_int32()
            layer_data = buf.get_bytes(layer_len)
            self.layers.append(ResLayer(layer_type, layer_data))


class ResLoader(object):
    res_map = {}

    @staticmethod
    def get(resid):
        resinfo = ResLoader.get_map(resid)
        if resinfo is None:
            raise ResException('No mapping found')

        resname = resinfo['resname']
        resver = resinfo['resver']

        try:
            with open(ResLoader.__get_res_path(resname, resver), 'rb') as f:
                return Resource(resname, resver, f.read())
        except Exception:
            pass

        r = requests.get('http://game.havenandhearth.com/hres/' + resname + '.res')
        if r.status_code != requests.codes.ok:
            raise ResException('Unable to fetch resource')
        res = Resource(resname, resver, r.content)
        try:
            os.makedirs(resname[:resname.rfind('/') + 1])
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise ResException('Unable to create directories')
            pass
        with open(ResLoader.__get_res_path(resname, resver), 'wb') as f:
            f.write(r.content)
        return res

    @staticmethod
    def add_map(resid, resname, resver):
        ResLoader.res_map[resid] = {
            'resname': resname,
            'resver': resver
        }

    @staticmethod
    def get_map(resid):
        return ResLoader.res_map.get(resid)

    @staticmethod
    def __get_res_path(resname, resver):
        program_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(program_path, '{}_{}.res'.format(resname, resver))