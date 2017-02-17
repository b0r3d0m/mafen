import json

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from authclient import AuthClient, AuthException
from config import Config


class WSServer(WebSocket):
    config = Config()

    @staticmethod
    def serve(config_path):
        WSServer.config.load(config_path)
        server = SimpleWebSocketServer(
            WSServer.config.mafen_host,
            WSServer.config.mafen_port,
            WSServer
        )
        server.serveforever()

    def handleMessage(self):
        msg = json.loads(self.data)
        action = msg['action']
        data = msg['data']
        if action == 'connect':
            self.handleConnectMessage(data)
        else:
            print('Unknown message received: ' + action)

    def handleConnectMessage(self, data):
        try:
            ac = AuthClient()
            ac.connect(
                WSServer.config.auth_host,
                WSServer.config.auth_port,
                WSServer.config.cert_path
            )
            ac.login(data['username'], data['password'])
            cookie = ac.get_cookie()
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'connect',
                    'success': True
                }))
            )
        except AuthException as e:
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'connect',
                    'success': False,
                    'reason': str(e)
                }))
            )

    def handleConnected(self):
        print self.address, 'connected'

    def handleClose(self):
        print self.address, 'closed'