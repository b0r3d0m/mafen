import json
import threading
import time

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from authclient import AuthClient, AuthException
from config import Config
from gameclient import GameClient, GameException, MessageType, RelMessageType, GameState
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
        elif action == 'play':
            self.handle_play_message(data)
        else:
            print('Unknown message received: ' + action)

    def handleConnected(self):
        print self.address, 'connected'
        self.gs_lock = threading.Lock()
        self.set_gs(GameState.CONN)

    def handleClose(self):
        print self.address, 'closed'
        self.set_gs(GameState.CLOSE)

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

            self.charlist_wdg_id = -1
            self.rseq = 0
            self.wseq = 0
            self.rmsgs = []
            self.rmsgs_lock = threading.Lock()

            self.gc = GameClient(WSServer.config.game_host, WSServer.config.game_port)

            self.rworker_th = threading.Thread(target=self.rworker)
            self.rworker_th.daemon = True
            self.rworker_th.start()

            self.sworker_th = threading.Thread(target=self.sworker)
            self.sworker_th.daemon = True
            self.sworker_th.start()
        except AuthException as e:
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'connect',
                    'success': False,
                    'reason': str(e)
                }))
            )

    def set_gs(self, gs):
        with self.gs_lock:
            self.gs = gs

    def get_gs(self):
        with self.gs_lock:
            return self.gs

    def handle_play_message(self, data):
        if self.charlist_wdg_id == -1:
            return

        char_name = data['char_name']

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(self.charlist_wdg_id)
        msg.add_string('play')
        msg.add_list([char_name])
        self.queue_rmsg(msg)

    def queue_rmsg(self, rmsg):
        msg = MessageBuf()
        msg.add_uint8(MessageType.MSG_REL)
        msg.add_uint16(self.wseq)
        msg.add_bytes(rmsg.buf)

        msg.seq = self.wseq
        with self.rmsgs_lock:
            self.rmsgs.append(msg)
        self.wseq += 1

    def sworker(self):
        last = 0
        conn_retries = 0
        while True:
            now = int(time.time())
            gs = self.get_gs()
            if gs == GameState.CONN:
                if now - last > 2:
                    if conn_retries > 5:
                        self.sendMessage(
                            unicode(json.dumps({
                                'action': 'close',
                                'reason': 'Unable to initiate the game session'
                            }))
                        )
                        self.set_gs(GameState.CLOSE)
                        return
                    self.gc.start_session(self.username, self.cookie)
                    last = now
                    conn_retries += 1
                time.sleep(0.1)
            elif gs == GameState.PLAY:
                with self.rmsgs_lock:
                    for rmsg in self.rmsgs:
                        self.gc.send_msg(rmsg)
                        last = now
                if now - last > 5:
                    self.gc.beat()
                    last = now
                time.sleep(0.3)
            elif gs == GameState.CLOSE:
                return

    def rworker(self):
        while True:
            try:
                msg = self.gc.recv_msg()  # TODO: Make it non-blocking to check the game state
                msg_type = msg.get_uint8()
                data = MessageBuf(msg.get_remaining())
                if msg_type == MessageType.MSG_SESS:
                    self.on_msg_sess(data)
                elif msg_type == MessageType.MSG_REL:
                    self.on_msg_rel(data)
                elif msg_type == MessageType.MSG_ACK:
                    self.on_msg_ack(data)
                elif msg_type == MessageType.MSG_CLOSE:
                    self.on_msg_close()

                if self.get_gs() == GameState.CLOSE:
                    return
            except GameException as e:
                print('Error: ' + str(e))

    def on_msg_sess(self, msg):
        err = msg.get_uint8()
        if err == 0:
            self.set_gs(GameState.PLAY)
        else:
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'close',
                    'reason': 'Unable to initiate the game session'
                }))
            )
            self.set_gs(GameState.CLOSE)

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

    def on_msg_ack(self, msg):
        ack = msg.get_uint16()
        with self.rmsgs_lock:
            rmsgs = [rmsg for rmsg in self.rmsgs if rmsg.seq > ack]

    def on_msg_close(self):
        self.set_gs(GameState.CLOSE)