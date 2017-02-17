import json
import threading

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from authclient import AuthClient, AuthException
from config import Config
from gameclient import GameClient, GameException, MessageType, RelMessageType
from messagebuf import MessageBuf


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
            self.handle_connect_message(data)
        else:
            print('Unknown message received: ' + action)

    def handleConnected(self):
        print self.address, 'connected'

    def handleClose(self):
        print self.address, 'closed'

    def handle_connect_message(self, data):
        self.username = data['username']
        self.password = data['password']
        try:
            ac = AuthClient()
            ac.connect(
                WSServer.config.auth_host,
                WSServer.config.auth_port,
                WSServer.config.cert_path
            )
            ac.login(self.username, self.password)
            self.cookie = ac.get_cookie()
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'connect',
                    'success': True
                }))
            )
            self.game_session_th = threading.Thread(target=self.game_loop)
            self.game_session_th.daemon = True
            self.game_session_th.start()
        except AuthException as e:
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'connect',
                    'success': False,
                    'reason': str(e)
                }))
            )

    def game_loop(self):
        self.charlist_wdg_id = -1
        self.rseq = 0

        self.gc = GameClient(WSServer.config.game_host, WSServer.config.game_port)
        self.gc.start_session(self.username, self.cookie)
        while True:
            try:
                msg = self.gc.recv_msg()
                msg_type = msg.get_uint8()
                if msg_type == MessageType.MSG_SESS:
                    self.on_msg_sess(MessageBuf(msg.get_remaining()))
                elif msg_type == MessageType.MSG_REL:
                    self.on_msg_rel(MessageBuf(msg.get_remaining()))
            except GameException as e:
                print('Error: ' + str(e))

    def on_msg_sess(self, msg):
        err = msg.get_uint8()
        if err != 0:
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'close',
                    'reason': 'Unable to initiate the game session'
                }))
            )
            # TODO: Interrupt

    def on_msg_rel(self, msg):
        seq = msg.get_uint16()
        while not msg.eom():
            rel_type = msg.get_uint8()
            if (rel_type & 0x80) != 0:
                rel_type &= 0x7F
                rel_len = msg.get_uint16()
                rmsg = MessageBuf(msg.get_bytes(rel_len))
            else:
                rmsg = MessageBuf(msg.get_remaining())
            if seq == self.rseq:
                if rel_type == RelMessageType.RMSG_NEWWDG:
                    self.on_rmsg_newwdg(rmsg)
                elif rel_type == RelMessageType.RMSG_WDGMSG:
                    self.on_rmsg_wdgmsg(rmsg)
                else:
                    pass
                self.gc.ack(seq)
                self.rseq += 1  # TODO: Handle overflow
            seq += 1

    def on_rmsg_newwdg(self, msg):
        wdg_id = msg.get_uint16()
        wdg_type = msg.get_string()
        wdg_parent = msg.get_uint16()

        if wdg_type == 'charlist':
            self.charlist_wdg_id = wdg_id
        elif wdg_type == 'gameui':
            pass
        elif wdg_type == 'inv':
            pass
        elif wdg_type == 'item':
            pass
        else:
            pass

    def on_rmsg_wdgmsg(self, msg):
        wdg_id = msg.get_uint16()
        wdg_msg = msg.get_string()
        wdg_args = msg.get_list()

        if wdg_msg == 'add':
            if wdg_id == self.charlist_wdg_id:
                char_name = wdg_args[0]
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'character',
                        'name': char_name
                    }))
                )
        elif wdg_msg == 'tt':
            pass
        elif wdg_msg == 'err':
            pass
        else:
            pass