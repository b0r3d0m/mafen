import socket

from messagebuf import MessageBuf
from simplelogger import SimpleLogger


class MessageType(object):
    MSG_SESS = 0
    MSG_REL = 1
    MSG_ACK = 2
    MSG_BEAT = 3
    MSG_OBJDATA = 6
    MSG_OBJACK = 7
    MSG_CLOSE = 8


class RelMessageType(object):
    RMSG_NEWWDG = 0
    RMSG_WDGMSG = 1
    RMSG_DSTWDG = 2
    RMSG_GLOBLOB = 4
    RMSG_RESID = 6
    RMSG_CATTR = 9


class ObjDataType(object):
    OD_REM = 0
    OD_MOVE = 1
    OD_RES = 2
    OD_LINBEG = 3
    OD_LINSTEP = 4
    OD_SPEECH = 5
    OD_COMPOSE = 6
    OD_ZOFF = 7
    OD_LUMIN = 8
    OD_AVATAR = 9
    OD_FOLLOW = 10
    OD_HOMING = 11
    OD_OVERLAY = 12
    OD_AUTH = 13
    OD_HEALTH = 14
    OD_BUDDY = 15
    OD_CMPPOSE = 16
    OD_CMPMOD = 17
    OD_CMPEQU = 18
    OD_ICON = 19
    OD_RESATTR = 20
    OD_END = 255


class GameState(object):
    CONN = 0
    PLAY = 1
    CLOSE = 2

class GameException(Exception):
    pass


class GameClient(SimpleLogger):
    SERVER_TIME_RATIO = 3.29

    def __init__(self, host, port, verbose=False):
        SimpleLogger.__init__(self)
        self.verbose = verbose
        try:
            self.host = host
            self.port = port
            self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.s.connect((self.host, self.port))
        except Exception as e:
            raise GameException(e)

    def start_session(self, username, cookie):
        msg = MessageBuf()
        msg.add_uint8(MessageType.MSG_SESS)
        msg.add_uint16(2)  # Magic number
        msg.add_string('Hafen')
        msg.add_uint16(9)  # Protocol version
        msg.add_string(username)
        msg.add_uint16(len(cookie))
        msg.add_bytes(cookie)
        self.send_msg(msg)

    def recv_msg(self):
        data, addr = self.s.recvfrom(65535)
        msg = MessageBuf(data)
        if self.verbose:
            self.info('< ' + str(msg))
        return msg

    def ack(self, seq):
        msg = MessageBuf()
        msg.add_uint8(MessageType.MSG_ACK)
        msg.add_uint16(seq)
        self.send_msg(msg)

    def beat(self):
        msg = MessageBuf()
        msg.add_uint8(MessageType.MSG_BEAT)
        self.send_msg(msg)

    def send_msg(self, msg):
        if self.verbose:
            self.info('> ' + str(msg))
        self.s.sendto(msg.buf, (self.host, self.port))