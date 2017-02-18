import ConfigParser


class Config(object):
    def load(self, filename):
        config = ConfigParser.SafeConfigParser()
        config.read(filename)

        self.mafen_host = config.get('mafen', 'host')
        self.mafen_port = int(config.get('mafen', 'port'))

        self.auth_host = config.get('auth', 'host')
        self.auth_port = int(config.get('auth', 'port'))
        self.cert_path = config.get('auth', 'cert_path')

        self.game_host = config.get('game', 'host')
        self.game_port = int(config.get('game', 'port'))