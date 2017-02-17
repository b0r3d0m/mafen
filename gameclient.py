import socket

from messagebuf import MessageBuf


class MessageType:
    MSG_SESS = 0
    MSG_REL = 1
    MSC_ACK = 2


class RelMessageType:
    RMSG_NEWWDG = 0
    RMSG_WDGMSG = 1


class GameException(Exception):
    pass


class GameClient:
    def __init__(self, host, port):
        try:
            self.host = host
            self.port = port
            self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        self.__send_msg(msg)

    def recv_msg(self):
        data, addr = self.s.recvfrom(65535)
        # TODO: if (!p.getSocketAddress().equals(server)) continue;
        msg = MessageBuf(data)
        print '<', str(msg)
        return msg

    def ack(self, seq):
        msg = MessageBuf()
        msg.add_uint8(MessageType.MSC_ACK)
        msg.add_uint16(seq)
        self.__send_msg(msg)

    def __send_msg(self, msg):
        print '>', str(msg)
        self.s.sendto(msg.buf, (self.host, self.port))