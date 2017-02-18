import json
import threading
import time

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from authclient import AuthClient, AuthException
from config import Config
from gameclient import GameClient, GameException, MessageType, RelMessageType, ObjDataType, GameState
from messagebuf import MessageBuf
from simplelogger import SimpleLogger


class WSServer(WebSocket, SimpleLogger):
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
            self.error('Unknown message received: ' + action)

    def handleConnected(self):
        SimpleLogger.__init__(self)
        self.info('{} connected'.format(self.address))
        self.gs_lock = threading.Lock()
        self.set_gs(GameState.CONN)

    def handleClose(self):
        self.info('{} closed'.format(self.address))
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
                elif msg_type == MessageType.MSG_OBJDATA:
                    self.on_msg_objdata(data)
                elif msg_type == MessageType.MSG_CLOSE:
                    self.on_msg_close()

                if self.get_gs() == GameState.CLOSE:
                    return
            except GameException as e:
                self.error('Game session error: ' + str(e))

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
            self.rmsgs = [rmsg for rmsg in self.rmsgs if rmsg.seq > ack]

    def on_msg_objdata(self, msg):
        # NOTE: We don't really need to handle these messages,
        # we just want to get rid of them by sending the corresponding MSG_OBJACK messages
        while not msg.eom():
            fl = msg.get_uint8()
            id = msg.get_uint32()
            frame = msg.get_int32()

            while True:
                data_type = msg.get_uint8()
                if data_type == ObjDataType.OD_REM:
                    pass
                elif data_type == ObjDataType.OD_MOVE:
                    msg.get_int32()
                    msg.get_int32()
                    ia = msg.get_uint16()
                elif data_type == ObjDataType.OD_RES:
                    resid = msg.get_uint16()
                    if (resid & 0x8000) != 0:
                        resid &= ~0x8000
                        sdt_len = msg.get_uint8()
                        sdt = MessageBuf(msg.get_bytes(sdt_len))
                elif data_type == ObjDataType.OD_LINBEG:
                    msg.get_int32()
                    msg.get_int32()

                    msg.get_int32()
                    msg.get_int32()
                elif data_type == ObjDataType.OD_LINSTEP:
                    w = msg.get_int32()
                    if w == -1:
                        pass
                    elif (w & 0x80000000) == 0:
                        pass
                    else:
                        w = msg.get_int32()
                elif data_type == ObjDataType.OD_SPEECH:
                    zo = msg.get_int16() / 100.0
                    text = msg.get_string()
                elif data_type == ObjDataType.OD_COMPOSE:
                    resid = msg.get_uint16()
                elif data_type == ObjDataType.OD_CMPPOSE:
                    pfl = msg.get_uint8()
                    seq = msg.get_uint8()

                    if (pfl & 2) != 0:
                        while True:
                            resid = msg.get_uint16()
                            if resid == 65535:
                                break
                            if (resid & 0x8000) != 0:
                                resid &= ~0x8000
                                sdt_len = msg.get_uint8()
                                sdt = MessageBuf(msg.get_bytes(sdt_len))

                    if (pfl & 4) != 0:
                        while True:
                            resid = msg.get_uint16()
                            if resid == 65535:
                                break
                            if (resid & 0x8000) != 0:
                                resid &= ~0x8000
                                sdt_len = msg.get_uint8()
                                sdt = MessageBuf(msg.get_bytes(sdt_len))
                        ttime = msg.get_uint8() / 10.0
                elif data_type == ObjDataType.OD_CMPMOD:
                    while True:
                        modid = msg.get_uint16()
                        if modid == 65535:
                            break
                        while True:
                            resid = msg.get_uint16()
                            if resid == 65535:
                                break
                            if (resid & 0x8000) != 0:
                                resid &= ~0x8000
                                sdt_len = msg.get_uint8()
                                sdt = MessageBuf(msg.get_bytes(sdt_len))
                elif data_type == ObjDataType.OD_CMPEQU:
                    while True:
                        h = msg.get_uint8()
                        if h == 255:
                            break
                        ef = h & 0x80
                        et = h & 0x7f
                        at = msg.get_string()
                        resid = msg.get_uint16()
                        if (resid & 0x8000) != 0:
                            resid &= ~0x8000
                            sdt_len = msg.get_uint8()
                            sdt = MessageBuf(msg.get_bytes(sdt_len))
                        if (ef & 128) != 0:
                            x = msg.get_int16()
                            y = msg.get_int16()
                            z = msg.get_int16()
                elif data_type == ObjDataType.OD_ZOFF:
                    off = msg.get_int16() / 100.0
                elif data_type == ObjDataType.OD_LUMIN:
                    msg.get_int32()
                    msg.get_int32()

                    sz = msg.get_uint16()
                    sstr = msg.get_uint8()
                elif data_type == ObjDataType.OD_AVATAR:
                    while True:
                        layer = msg.get_uint16()
                        if layer == 65535:
                            break
                elif data_type == ObjDataType.OD_FOLLOW:
                    oid = msg.get_uint32()
                    if oid != 0xffffffffl:
                        xfres = msg.get_uint16()  # getres
                        xfname = msg.get_string()
                elif data_type == ObjDataType.OD_HOMING:
                    oid = msg.get_uint32()
                    if oid != 0xffffffffl:
                        pass
                    else:
                        msg.get_int32()
                        msg.get_int32()

                        msg.get_int32()  # double v = msg.int32() * 0x1p-10 * 11;
                elif data_type == ObjDataType.OD_OVERLAY:
                    oid = msg.get_int32()
                    resid = msg.get_uint16()
                    if resid == 65535:
                        pass
                    else:
                        if (resid & 0x8000) != 0:
                            resid &= ~0x8000
                            sdt_len = msg.get_uint8()
                            sdt = MessageBuf(msg.get_bytes(sdt_len))
                elif data_type == ObjDataType.OD_HEALTH:
                    hp = msg.get_uint8()
                elif data_type == ObjDataType.OD_BUDDY:
                    name = msg.get_string()
                    if len(name) > 0:
                        group = msg.get_uint8()
                        btype = msg.get_uint8()
                elif data_type == ObjDataType.OD_ICON:
                    resid = msg.get_uint16()
                    if resid == 65535:
                        pass
                    else:
                        ifl = msg.get_uint8()
                elif data_type == ObjDataType.OD_RESATTR:
                    resid = msg.get_uint16()
                    dat_len = msg.get_uint8()
                    if dat_len > 0:
                        dat = MessageBuf(msg.get_bytes(dat_len))
                elif data_type == ObjDataType.OD_END:
                    break

            msg = MessageBuf()
            msg.add_uint8(MessageType.MSG_OBJACK)
            msg.add_uint32(id)
            msg.add_int32(frame)
            self.gc.send_msg(msg)

    def on_msg_close(self):
        self.set_gs(GameState.CLOSE)