import base64

from resource import ResLoader


class Wound(object):
    def __init__(self, wid, resid, qdata):
        self.wid = wid
        self.resid = resid
        self.qdata = qdata

    def build(self):
        try:
            info = {
                'tooltip': None,
                'hhp': self.qdata
            }

            res = ResLoader.get(self.resid)
            for layer in res.layers:
                if layer.ltype == 'tooltip':
                    info['tooltip'] = unicode(layer.ldata)
                elif layer.ltype == 'image':
                    img = layer.ldata[11:]  # Skip metadata
                    info['image'] = 'data:image/png;base64,' + base64.b64encode(img)
                elif layer.ltype == 'pagina':
                    info['desc'] = unicode(layer.ldata)
                else:
                    pass

            if info['tooltip'] is None:
                return None

            return info
        except Exception as ex:
            return None