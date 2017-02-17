import hashlib
import socket
import ssl

from messagebuf import MessageBuf


class AuthException(Exception):
    pass


class AuthClient:
    def connect(self, host, port, cert_path):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.ws = ssl.wrap_socket(s, ca_certs=cert_path)
            self.ws.connect((host, port))
        except Exception as e:
            raise AuthException(e)

    def login(self, username, password):
        msg = MessageBuf()
        msg.add_string('pw')
        msg.add_string(username)
        msg.add_bytes(hashlib.sha256(password).digest())  # TODO: Let a client to hash its password
        self.__send_msg(msg)

        rpl = self.__recv_msg()
        status = rpl.get_string()
        if status == 'ok':
            acc = rpl.get_string()  # This is normally the same thing as `username`
            return
        elif status == 'no':
            err = rpl.get_string()
            raise AuthException(err)
        else:
            raise AuthException('Unexpected reply: "' + status + '"')

    def get_cookie(self):
        msg = MessageBuf()
        msg.add_string('cookie')
        self.__send_msg(msg)

        rpl = self.__recv_msg()
        status = rpl.get_string()
        if status == 'ok':
            cookie = rpl.get_bytes(32)
            return cookie
        else:
            raise AuthException('Unexpected reply: "' + status + '"')

    def __prepend_header(self, msg):
        tmp = MessageBuf()
        tmp.add_uint16(len(msg.buf), be=True)
        tmp.add_bytes(msg.buf)
        return tmp

    def __send_msg(self, msg):
        msg = self.__prepend_header(msg)
        print '>', str(msg)
        self.ws.sendall(msg.buf)

    def __recv_msg(self):
        header = MessageBuf(self.__recv_bytes(2))
        data_len = header.get_uint16(be=True)
        msg = MessageBuf(self.__recv_bytes(data_len))
        print '<', str(msg)
        return msg

    def __recv_bytes(self, l):
        res = ''
        while True:
            bytes_to_read = l - len(res)
            if bytes_to_read < 1:
                break

            data = self.ws.recv(bytes_to_read)
            if not data:
                break

            res += data
        return res