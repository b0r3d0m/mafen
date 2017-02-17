import socket

from messagebuf import MessageBuf


class MessageType:
    MSG_SESS = 0
    MSG_REL = 1
    MSG_ACK = 2
    MSG_BEAT = 3
    MSG_CLOSE = 8


class RelMessageType:
    RMSG_NEWWDG = 0
    RMSG_WDGMSG = 1


class GameState:
    CONN = 0
    PLAY = 1
    CLOSE = 2


class GameException(Exception):
    pass


class GameClient:
    def __init__(self, host, port):
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
        print '<', str(msg)
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
        print '>', str(msg)
        self.s.sendto(msg.buf, (self.host, self.port))