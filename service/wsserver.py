import copy
import json
import threading
import time

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from authclient import AuthClient, AuthException
from config import Config
from gameclient import GameClient, GameException, MessageType, RelMessageType, ObjDataType, GameState, ClientState
from gob import Gob
from item import Item
from messagebuf import MessageBuf
from resource import ResLoader
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

    @staticmethod
    def set_client_status(key, status):
        with WSServer.clients_lock:
            WSServer.clients[key] = status

    @staticmethod
    def get_client_status(key):
        with WSServer.clients_lock:
            res = WSServer.clients.get(key)
            return res

    @staticmethod
    def remove_client(key):
        with WSServer.clients_lock:
            WSServer.clients.pop(key, None)

    def get_address_key(self):
        return '{}:{}'.format(*self.address)

    def handleMessage(self):
        msg = json.loads(self.data)
        action = msg['action']
        data = msg['data']
        if action == 'connect':
            self.handle_connect_message(data)
        elif action == 'play':
            self.handle_play_message(data)
        elif action == 'transfer':
            self.handle_transfer_message(data)
        elif action == 'msg':
            self.handle_msg_message(data)
        else:
            self.error('Unknown message received: ' + action)

    def handleConnected(self):
        SimpleLogger.__init__(self)
        self.info('{} connected'.format(self.address))
        self.gs_lock = threading.Lock()
        self.set_gs(GameState.CONN)
        key = self.get_address_key()
        WSServer.set_client_status(key, ClientState.CONN)

    def handleClose(self):
        key = self.get_address_key()
        client_status = WSServer.get_client_status(key)
        if client_status is None or client_status == ClientState.CLOSE:
            return
        WSServer.set_client_status(key, ClientState.CLOSE)
        # or mb WSServer.remove_client(key)
        self.info('{} closed'.format(self.address))
        self.set_gs(GameState.CLOSE)

    def handle_connect_message(self, data):
        self.username = data['username']
        self.password = data['password']
        try:
            ac = AuthClient(WSServer.config.verbose)
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
            self.gameui_wdg_id = -1
            self.chr_wdg_id = -1
            self.inv_wdg_id = -1
            self.study_wdg_id = -1
            self.buddy_wdg_id = -1
            self.rseq = 0
            self.wseq = 0
            self.rmsgs = []
            self.rmsgs_lock = threading.Lock()
            self.items = []
            self.items_lock = threading.Lock()
            self.buddies = {}
            self.gobs = {}
            self.gobs_lock = threading.Lock()

            self.gc = GameClient(
                WSServer.config.game_host,
                WSServer.config.game_port,
                WSServer.config.verbose
            )

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
            if self.gs == GameState.CLOSE:
                self.close()  # TODO: Add reason

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

    def handle_transfer_message(self, data):
        if self.get_gs() != GameState.PLAY:
            # TODO: Send response back to the client
            return

        item_id = data['id']

        coords = None
        with self.items_lock:
            for item in self.items:
                if item.wdg_id == item_id:
                    coords = copy.copy(item.coords)
        if coords is None:
            # TODO: Send response back to the client
            return

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(item_id)
        msg.add_string('transfer')
        msg.add_list([coords])
        self.queue_rmsg(msg)

    def handle_msg_message(self, data):
        if self.get_gs() != GameState.PLAY:
            # TODO: Send response back to the client
            return

        chat_id = data['id']
        chat_msg = data['msg']

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(chat_id)
        msg.add_string('msg')
        msg.add_list([chat_msg])
        self.queue_rmsg(msg)

    def queue_rmsg(self, rmsg):
        msg = MessageBuf()
        msg.add_uint8(MessageType.MSG_REL)
        msg.add_uint16(self.wseq)
        msg.add_bytes(rmsg.buf)

        msg.seq = self.wseq
        with self.rmsgs_lock:
            self.rmsgs.append(msg)
        self.wseq = (self.wseq + 1) % 65536

    def sworker(self):
        last = 0
        conn_retries = 0
        while True:
            now = int(time.time())
            gs = self.get_gs()
            if gs == GameState.CONN:
                if now - last > 2:
                    if conn_retries > 5:
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

                # TODO: Make copy
                with self.items_lock:
                    for item in self.items:
                        if item.sent:
                            continue
                        info = item.build()
                        if info is None:
                            continue
                        self.sendMessage(
                            unicode(json.dumps({
                                'action': 'item',
                                'id': item.wdg_id,
                                'study': item.study,
                                'info': info
                            }))
                        )
                        item.sent = True

                # TODO: Make copy
                with self.gobs_lock:
                    for gob_id, gob in self.gobs.iteritems():
                        if gob.sent:
                            continue
                        if gob.is_player():
                            self.sendMessage(
                                unicode(json.dumps({
                                    'action': 'player',
                                    'id': gob.gob_id
                                }))
                            )
                            self.gobs[gob_id].sent = True

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
                else:
                    pass

                if self.get_gs() == GameState.CLOSE:
                    return
            except GameException as e:
                self.error('Game session error: ' + str(e))

    def on_msg_sess(self, msg):
        err = msg.get_uint8()
        if err == 0:
            self.set_gs(GameState.PLAY)
        else:
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
                elif rel_type == RelMessageType.RMSG_DSTWDG:
                    self.on_rmsg_dstwdg(rmsg)
                elif rel_type == RelMessageType.RMSG_GLOBLOB:
                    self.on_rmsg_globlob(rmsg)
                elif rel_type == RelMessageType.RMSG_RESID:
                    self.on_rmsg_resid(rmsg)
                elif rel_type == RelMessageType.RMSG_CATTR:
                    self.on_rmsg_cattr(rmsg)
                else:
                    pass
                self.gc.ack(seq)
                self.rseq = (self.rseq + 1) % 65536
            seq += 1

    def on_rmsg_newwdg(self, msg):
        wdg_id = msg.get_uint16()
        wdg_type = msg.get_string()
        wdg_parent = msg.get_uint16()
        wdg_pargs = msg.get_list()
        wdg_cargs = msg.get_list()

        if wdg_type == 'charlist':
            self.charlist_wdg_id = wdg_id
        elif wdg_type == 'gameui':
            self.gameui_wdg_id = wdg_id
        elif wdg_type == 'inv':
            if wdg_parent == self.gameui_wdg_id:
                self.inv_wdg_id = wdg_id
            elif wdg_parent == self.chr_wdg_id:
                self.study_wdg_id = wdg_id
            else:
                pass
        elif wdg_type == 'chr':
            self.chr_wdg_id = wdg_id
        elif wdg_type == 'item':
            if wdg_parent == self.inv_wdg_id:
                wdg = 'inv'
            elif wdg_parent == self.study_wdg_id:
                wdg = 'study'
            else:
                return
            coords = wdg_pargs[0]
            resid = wdg_cargs[0]
            with self.items_lock:
                item = Item(wdg_id, coords, resid, study=(wdg == 'study'))
                item.sent = False
                self.items.append(item)
        elif wdg_type == 'buddy':
            self.buddy_wdg_id = wdg_id
        elif wdg_type == 'mchat':
            chat_name = wdg_cargs[0]
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'mchat',
                    'id': wdg_id,
                    'name': chat_name
                }))
            )
        elif wdg_type == 'mapview':
            pgob = -1
            if len(wdg_cargs) > 2:
                pgob = wdg_cargs[2]
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'pgob',
                    'id': pgob
                }))
            )
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
            elif wdg_id == self.buddy_wdg_id:
                buddy_id = wdg_args[0]
                buddy_name = wdg_args[1]
                # online, group, seen etc
                self.buddies[buddy_id] = buddy_name
        elif wdg_msg == 'tt':
            with self.items_lock:
                for item in self.items:
                    if item.wdg_id == wdg_id:
                        item.add_info(wdg_args)
        elif wdg_msg == 'meter':
            meter = wdg_args[0]
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'meter',
                    'id': wdg_id,
                    'meter': meter
                }))
            )
        elif wdg_msg == 'msg':
            sender_id = wdg_args[0]
            sender_msg = wdg_args[1]

            self.sendMessage(
                unicode(json.dumps({
                    'action': 'msg',
                    'chat': wdg_id,
                    'from': 'You' if sender_id == 0 else self.buddies.get(sender_id, '???'),
                    'text': sender_msg
                }))
            )
        elif wdg_msg == 'exp':
            exp = wdg_args[0]
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'exp',
                    'exp': exp
                }))
            )
        elif wdg_msg == 'enc':
            enc = wdg_args[0]
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'enc',
                    'enc': enc
                }))
            )
        else:
            pass

    def on_rmsg_dstwdg(self, msg):
        wdg_id = msg.get_uint16()
        with self.items_lock:
            for item in self.items[:]:
                if item.wdg_id == wdg_id:
                    self.sendMessage(
                        unicode(json.dumps({
                            'action': 'destroy',
                            'id': wdg_id
                        }))
                    )
                    self.items.remove(item)
                    break

    def on_rmsg_globlob(self, msg):
        inc = msg.get_uint8() != 0
        while not msg.eom():
            t = msg.get_string()
            a = msg.get_list()
            if t == 'tm':
                tm = a[0]
                epoch = time.time() * 1000
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'time',
                        'time': tm,
                        'epoch': epoch,
                        'inc': inc
                    }))
                )
            else:
                pass

    def on_rmsg_resid(self, msg):
        resid = msg.get_uint16()
        resname = msg.get_string()
        resver = msg.get_uint16()
        ResLoader.add_map(resid, resname, resver)

    def on_rmsg_cattr(self, msg):
        attrs = {}
        while not msg.eom():
            name = msg.get_string()
            base = msg.get_int32()
            comp = msg.get_int32()
            attrs[name] = {
                'base': base,
                'comp': comp
            }
        self.sendMessage(
            unicode(json.dumps({
                'action': 'attr',
                'attrs': attrs
            }))
        )

    def on_msg_ack(self, msg):
        ack = msg.get_uint16()
        with self.rmsgs_lock:
            self.rmsgs = [rmsg for rmsg in self.rmsgs if rmsg.seq > ack]

    def on_msg_objdata(self, msg):
        # NOTE: We don't really need to handle all of these messages,
        # we just want to get rid of most of them by sending the corresponding MSG_OBJACK messages
        while not msg.eom():
            fl = msg.get_uint8()
            id = msg.get_uint32()
            frame = msg.get_int32()

            while True:
                data_type = msg.get_uint8()
                if data_type == ObjDataType.OD_REM:
                    with self.gobs_lock:
                        del self.gobs[id]
                    self.sendMessage(
                        unicode(json.dumps({
                            'action': 'gobrem',
                            'id': id
                        }))
                    )
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
                    with self.gobs_lock:
                        gob = self.gobs.get(id, Gob(id))
                        gob.compose(resid)
                        self.gobs[id] = gob
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
                    with self.gobs_lock:
                        gob = self.gobs.get(id, Gob(id))
                        gob.buddy(name)
                        self.gobs[id] = gob
                    self.sendMessage(
                        unicode(json.dumps({
                            'action': 'buddy',
                            'id': id,
                            'name': name
                        }))
                    )
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