import copy
import json
import threading
import time

from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from authclient import AuthClient, AuthException
from config import Config
from gameclient import GameClient, GameException, MessageType, RelMessageType, ObjDataType, PartyDataType, GameState
from gob import Gob
from item import Item
from lore import Lore
from messagebuf import MessageBuf, Coord, Coords
from resource import ResLoader
from simplelogger import SimpleLogger
from wound import Wound


class WSServer(WebSocket, SimpleLogger):
    config = Config()
    clients = {}
    clients_lock = threading.Lock()

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
    def remove_client(key):
        with WSServer.clients_lock:
            return WSServer.clients.pop(key, None)

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
        elif action == 'inv':
            self.handle_inv_message(data)
        elif action == 'cancelinv':
            self.handle_cancelinv_message(data)
        elif action == 'pmchat':
            self.handle_pmchat_message(data)
        elif action == 'closepmchat':
            self.handle_closepmchat_message(data)
        elif action == 'clicknearest':
            self.handle_clicknearest_message(data)
        elif action == 'wiact':
            self.handle_wiact_message(data)
        elif action == 'cl':
            self.handle_cl_message(data)
        elif action == 'drop':
            self.handle_drop_message(data)
        else:
            self.error('Unknown message received: ' + action)

    def handleConnected(self):
        SimpleLogger.__init__(self)
        self.info('{} connected'.format(self.address))
        self.gs_lock = threading.Lock()
        self.set_gs(GameState.CONN)
        WSServer.set_client_status(self.address, True)

    def handleClose(self):
        if WSServer.remove_client(self.address) is None:
            return
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
            self.mapview_wdg_id = -1
            self.chr_wdg_id = -1
            self.epry_wdg_id = -1
            self.inv_wdg_id = -1
            self.study_wdg_id = -1
            self.buddy_wdg_id = -1
            self.waiting_wdg_id = -1
            self.flowermenu_wdg_id = -1
            self.rseq = 0
            self.wseq = 0
            self.rmsgs = []
            self.rmsgs_lock = threading.Lock()
            self.items = []
            self.items_lock = threading.Lock()
            self.buddies = {}
            self.gobs = {}
            self.gobs_lock = threading.Lock()
            self.mchats = {}
            self.pchat_wdg_id = -1
            self.pmchats = {}
            self.lores = []
            self.lores_lock = threading.Lock()
            self.wounds = {}
            self.wounds_lock = threading.Lock()
            self.pgob_id = -1

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

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(item_id)
        msg.add_string('transfer')
        msg.add_list([Coords.Z])  # Ignored
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

    def handle_inv_message(self, data):
        if self.get_gs() != GameState.PLAY or self.buddy_wdg_id == -1:
            # TODO: Send response back to the client
            return

        kin_id = data['id']

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(self.buddy_wdg_id)
        msg.add_string('inv')
        msg.add_list([kin_id])
        self.queue_rmsg(msg)

    def handle_cancelinv_message(self, data):
        if self.get_gs() != GameState.PLAY or self.waiting_wdg_id == -1:
            # TODO: Send response back to the client
            return

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(self.waiting_wdg_id)
        msg.add_string('close')
        self.queue_rmsg(msg)
        self.waiting_wdg_id = -1

    def handle_pmchat_message(self, data):
        if self.get_gs() != GameState.PLAY or self.buddy_wdg_id == -1:
            # TODO: Send response back to the client
            return

        kin_id = data['id']

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(self.buddy_wdg_id)
        msg.add_string('chat')
        msg.add_list([kin_id])
        self.queue_rmsg(msg)

    def handle_closepmchat_message(self, data):
        if self.get_gs() != GameState.PLAY:
            # TODO: Send response back to the client
            return

        chat_id = data['id']

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(chat_id)
        msg.add_string('close')
        self.queue_rmsg(msg)

    def handle_clicknearest_message(self, data):
        if self.get_gs() != GameState.PLAY:
            # TODO: Send response back to the client
            return

        if self.mapview_wdg_id == -1:
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'clicknearest',
                    'success': False,
                    'reason': 'Map has not been constructed yet'
                }))
            )
            return

        obj_name = data['name']
        if obj_name != 'table':
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'clicknearest',
                    'success': False,
                    'reason': 'Unsupported object name'
                }))
            )
            return

        with self.gobs_lock:
            tables = []
            pl = None
            for gob_id, gob in self.gobs.iteritems():
                if gob.c is None:
                    continue
                if gob.is_table():
                    tables.append(gob)
                elif gob_id == self.pgob_id:
                    pl = gob
            if len(tables) == 0:
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'clicknearest',
                        'success': False,
                        'reason': 'No tables found (try again later)'
                    }))
                )
                return
            if pl is None:
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'clicknearest',
                        'success': False,
                        'reason': 'Player object has not been received yet'
                    }))
                )
                return

            nearest = None
            nearestc = None
            for table in tables:
                d = Coord.diff(pl.c, table.c)
                if nearest is None or d.x + d.y < nearestc:
                    nearest = table
                    nearestc = d.x + d.y

            msg = MessageBuf()
            msg.add_uint8(RelMessageType.RMSG_WDGMSG)
            msg.add_uint16(self.mapview_wdg_id)
            msg.add_string('click')
            msg.add_list([
                Coords.Z,  # pc (not used)
                Coords.Z,  # mc (not used)
                3,  # RMB
                0,  # modflags (no Alt / Ctrl / etc)
                0,  # no overlay
                nearest.gob_id,
                Coord.floor(nearest.c, Coords.POSRES),
                0,  # overlay ID
                -1  # click ID
            ])
            self.queue_rmsg(msg)

            self.sendMessage(
                unicode(json.dumps({
                    'action': 'clicknearest',
                    'success': True
                }))
            )

    def handle_wiact_message(self, data):
        if self.get_gs() != GameState.PLAY:
            # TODO: Send response back to the client
            return

        item_id = data['iid']

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(item_id)
        msg.add_string('take')
        msg.add_list([
            Coords.Z,
            Coords.Z
        ])
        self.queue_rmsg(msg)

        wound_id = int(data['wid'])

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(self.chr_wdg_id)
        msg.add_string('wiact')
        msg.add_list([
            wound_id,
            0  # modflags
        ])
        self.queue_rmsg(msg)

    def handle_cl_message(self, data):
        if self.get_gs() != GameState.PLAY or self.flowermenu_wdg_id == -1:
            # TODO: Send response back to the client
            return

        option = data['option']

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(self.flowermenu_wdg_id)
        msg.add_string('cl')
        if option == -1:
            msg.add_list([
                option
            ])
        else:
            msg.add_list([
                option,
                0  # modflags
            ])
        self.queue_rmsg(msg)

        self.flowermenu_wdg_id = -1  # TODO: Handle it on DSTWDG message or smth like that

    def handle_drop_message(self, data):
        if self.get_gs() != GameState.PLAY:
            # TODO: Send response back to the client
            return

        coords = data['coords']

        msg = MessageBuf()
        msg.add_uint8(RelMessageType.RMSG_WDGMSG)
        msg.add_uint16(self.inv_wdg_id)
        msg.add_string('drop')
        msg.add_list([
            Coord(coords['x'], coords['y'])
        ])
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
                                'place': item.place,
                                'coords': None if item.place == 'equip' else {
                                    'x': item.coords.x,
                                    'y': item.coords.y
                                },
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

                # TODO: Make copy
                with self.lores_lock:
                    for lore in self.lores:
                        if lore.sent:
                            continue
                        info = lore.build()
                        if info is None:
                            continue
                        self.sendMessage(
                            unicode(json.dumps({
                                'action': 'lore',
                                'resid': lore.resid,
                                'info': info
                            }))
                        )
                        lore.sent = True

                # TODO: Make copy
                with self.wounds_lock:
                    for wid, wound in self.wounds.iteritems():
                        if wound.sent:
                            continue
                        info = wound.build()
                        if info is None:
                            continue
                        self.sendMessage(
                            unicode(json.dumps({
                                'action': 'woundadd',
                                'wid': wid,
                                'info': info
                            }))
                        )
                        self.wounds[wid].sent = True

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
                elif rel_type == RelMessageType.RMSG_PARTY:
                    self.on_rmsg_party(rmsg)
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
        elif wdg_type == 'epry':
            self.epry_wdg_id = wdg_id
        elif wdg_type == 'item':
            if wdg_parent == self.inv_wdg_id:
                wdg = 'inv'
            elif wdg_parent == self.study_wdg_id:
                wdg = 'study'
            elif wdg_parent == self.epry_wdg_id:
                wdg = 'equip'
            else:
                return
            coords = wdg_pargs[0]
            resid = wdg_cargs[0]
            with self.items_lock:
                item = Item(wdg_id, coords, resid, place=wdg)
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
            self.mchats[wdg_id] = chat_name
        elif wdg_type == 'pchat':
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'pchat',
                    'id': wdg_id
                }))
            )
            self.pchat_wdg_id = wdg_id
        elif wdg_type == 'pmchat':
            other = wdg_cargs[0]
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'pmchat',
                    'id': wdg_id,
                    'other': self.buddies.get(other, '???')
                }))
            )
            self.pmchats[wdg_id] = other
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
            self.mapview_wdg_id = wdg_id  # TODO: Add synchronization
            with self.gobs_lock:
                self.pgob_id = pgob
        elif wdg_type == 'wnd':
            if len(wdg_cargs) > 1:
                if wdg_cargs[1] == "Invitation":
                    self.waiting_wdg_id = wdg_id
        elif wdg_type == 'sm':
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'flowermenu',
                    'options': wdg_cargs
                }))
            )
            self.flowermenu_wdg_id = wdg_id  # TODO: Add synchronization
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
                online = wdg_args[2]
                # group, seen etc
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'kinadd',
                        'id': buddy_id,
                        'name': buddy_name,
                        'online': online
                    }))
                )
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
            if wdg_id in self.mchats:
                sender_id = wdg_args[0]
                sender_msg = wdg_args[1]
            elif wdg_id in self.pmchats:
                t = wdg_args[0]  # in / out
                sender_msg = wdg_args[1]
                sender_id = 0 if t == 'out' else self.pmchats[wdg_id]
            elif wdg_id == self.pchat_wdg_id:
                sender_id = wdg_args[0]
                # gobid = wdg_args[1]  # Not used
                sender_msg = wdg_args[2]
            else:
                return
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'msg',
                    'chat': wdg_id,
                    'from': 'You' if sender_id == 0 else self.buddies.get(sender_id, '???'),
                    'text': sender_msg
                }))
            )
        elif wdg_msg == 'err':
            if wdg_id in self.pmchats:
                err = wdg_args[0]
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'msg',
                        'chat': wdg_id,
                        'from': 'System',
                        'text': err
                    }))
                )
            else:
                pass
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
        elif wdg_msg == 'rm':
            if wdg_id == self.buddy_wdg_id:
                buddy_id = wdg_args[0]
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'kinrm',
                        'id': buddy_id
                    }))
                )
                del self.buddies[buddy_id]
        elif wdg_msg == 'chst':
            if wdg_id == self.buddy_wdg_id:
                buddy_id = wdg_args[0]
                online = wdg_args[1]
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'kinchst',
                        'id': buddy_id,
                        'online': online
                    }))
                )
        elif wdg_msg == 'upd':
            if wdg_id == self.buddy_wdg_id:
                buddy_id = wdg_args[0]
                buddy_name = wdg_args[1]
                online = wdg_args[2]
                # group, seen etc
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'kinupd',
                        'id': buddy_id,
                        'name': buddy_name,
                        'online': online
                    }))
                )
                self.buddies[buddy_id] = buddy_name
        elif wdg_msg == 'exps':
            rst = wdg_args[0]
            lores = []
            i = 1
            while i < len(wdg_args):
                resid = wdg_args[i]
                i += 1
                mtime = wdg_args[i]
                i += 1
                score = wdg_args[i]
                i += 1
                lore = Lore(resid, mtime, score)
                lore.sent = False
                lores.append(lore)
            with self.lores_lock:
                self.lores = lores
        elif wdg_msg == 'wounds':
            i = 0
            while i < len(wdg_args):
                wid = wdg_args[i]
                resid = wdg_args[i + 1]
                qdata = wdg_args[i + 2]
                with self.wounds_lock:
                    if resid == 0:
                        self.sendMessage(
                            unicode(json.dumps({
                                'action': 'woundrm',
                                'wid': wid
                            }))
                        )
                        self.wounds.pop(resid, None)
                    else:
                        wound = Wound(wid, resid, qdata)
                        wound.sent = False
                        self.wounds[wid] = wound
                i += 3
        else:
            pass

    def on_rmsg_dstwdg(self, msg):
        wdg_id = msg.get_uint16()
        if wdg_id == self.waiting_wdg_id:
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'waitrm'
                }))
            )
            self.waiting_wdg_id = -1
        elif wdg_id == self.pchat_wdg_id:
            self.sendMessage(
                unicode(json.dumps({
                    'action': 'pchatrm',
                    'id': wdg_id
                }))
            )
        else:
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

    def on_rmsg_party(self, msg):
        while not msg.eom():
            t = msg.get_uint8()
            if t == PartyDataType.PD_LIST:
                mids = []
                while True:
                    mid = msg.get_int32()
                    if mid < 0:
                        break
                    mids.append(mid)
                self.sendMessage(
                    unicode(json.dumps({
                        'action': 'party',
                        'members': mids
                    }))
                )
            elif t == PartyDataType.PD_LEADER:
                mid = msg.get_int32()
            elif t == PartyDataType.PD_MEMBER:
                mid = msg.get_int32()
                vis = msg.get_uint8() == 1
                if vis:
                    c = msg.get_coords()
                col = msg.get_color()

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
                        self.gobs.pop(id, None)
                    self.sendMessage(
                        unicode(json.dumps({
                            'action': 'gobrem',
                            'id': id
                        }))
                    )
                elif data_type == ObjDataType.OD_MOVE:
                    c = Coord.mul(msg.get_coords(), Coords.POSRES)
                    ia = msg.get_uint16()
                    with self.gobs_lock:
                        gob = self.gobs.get(id, Gob(id))
                        gob.move(c)
                        self.gobs[id] = gob
                elif data_type == ObjDataType.OD_RES:
                    resid = msg.get_uint16()
                    if (resid & 0x8000) != 0:
                        resid &= ~0x8000
                        sdt_len = msg.get_uint8()
                        sdt = MessageBuf(msg.get_bytes(sdt_len))
                    with self.gobs_lock:
                        gob = self.gobs.get(id, Gob(id))
                        gob.res(resid)
                        self.gobs[id] = gob
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