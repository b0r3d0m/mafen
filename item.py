import base64

from gameclient import GameClient
from resource import ResLoader


class Item(object):
    def __init__(self, wdg_id, coords, resid, study):
        self.wdg_id = wdg_id
        self.coords = coords
        self.resid = resid
        self.study = study
        self.info = None

    def add_info(self, info):
        self.info = info

    def build(self):
        if self.info is None:
            return None

        try:
            info = {
                'tooltip': None,
                'curio': False
            }

            res = ResLoader.get(self.resid)
            for layer in res.layers:
                if layer.ltype == 'tooltip':
                    info['tooltip'] = unicode(layer.ldata)
                elif layer.ltype == 'image':
                    img = layer.ldata[11:]  # Skip metadata
                    info['image'] = 'data:image/png;base64,' + base64.b64encode(img)
                else:
                    pass

            for e in self.info:
                if type(e) is not list:
                    continue

                if type(e[0]) is int:
                    resid = e[0]
                else:
                    continue

                res = ResLoader.get(resid)
                if res.resname == 'ui/tt/q/quality':
                    info['q'] = e[1]
                elif res.resname == 'ui/tt/curio':
                    info['curio'] = True
                    info['exp'] = e[1]
                    info['mw'] = e[2]
                    info['enc'] = e[3]
                    info['time'] = e[4] / GameClient.SERVER_TIME_RATIO / 60
                else:
                    pass

            if info['tooltip'] is None:
                return None

            return info
        except Exception:
            return None