from resource import ResLoader


class Gob(object):
    def __init__(self, gob_id):
        self.gob_id = gob_id
        self.composeid = None
        self.resid = None
        self.c = None
        self.sent = False

    def compose(self, resid):
        self.composeid = resid

    def res(self, resid):
        self.resid = resid

    def move(self, c):
        self.c = c

    def buddy(self, name):
        self.name = name

    def is_player(self):
        if self.composeid is None:
            return False

        resinfo = ResLoader.get_map(self.composeid)
        if resinfo is None:
            return False

        return resinfo['resname'] == 'gfx/borka/body'

    def is_table(self):
        if self.resid is None:
            return False

        resinfo = ResLoader.get_map(self.resid)
        if resinfo is None:
            return False

        return 'table' in resinfo['resname']