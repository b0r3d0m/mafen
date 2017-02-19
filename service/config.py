import ConfigParser


class Config(object):
    def load(self, filename):
        config = ConfigParser.SafeConfigParser()
        config.read(filename)

        self.mafen_host = config.get('mafen', 'host')
        self.mafen_port = config.getint('mafen', 'port')
        self.verbose = config.getboolean('mafen', 'verbose')

        self.auth_host = config.get('auth', 'host')
        self.auth_port = config.getint('auth', 'port')
        self.cert_path = config.get('auth', 'cert_path')

        self.game_host = config.get('game', 'host')
        self.game_port = config.getint('game', 'port')