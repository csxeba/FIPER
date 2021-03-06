from __future__ import unicode_literals, print_function, absolute_import

import time
import socket

import numpy as np
import cv2


# Ports
MESSAGE_SERVER_PORT = 1234
STREAM_SERVER_PORT = 1235


def getsrv(ip, port, timeout=0):
    s = socket.socket()
    while 1:
        try:
            s.bind((ip, port))
            break
        except socket.error as E:
            if E.errno == 98:
                print("Socket not available yet... Waiting...")
                time.sleep(1)
            else:
                raise
    s.listen(1)
    if timeout:
        s.settimeout(timeout)
    return s


def listen(myaddr="127.0.0.1"):
    print("Awaiting connection...")
    mserver = getsrv(myaddr, MESSAGE_SERVER_PORT, timeout=1)
    dserver = getsrv(myaddr, STREAM_SERVER_PORT)

    while 1:
        try:
            mconn, addr = mserver.accept()
            print("Connection from", addr)
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            print("Exiting...")
            return
        except Exception as E:
            print("Caught exception:", str(E))
            return
        else:
            dconn, addr = dserver.accept()
            break
    return mconn, dconn


def framestream(dconn, frameshape):
    datalen = np.prod(frameshape)
    data = b""
    while 1:
        while len(data) < datalen:
            data += dconn.recv(1024)
        yield np.fromstring(data[:datalen], dtype="uint8").reshape(frameshape)
        data = data[datalen:]


def display(mconn, dconn):
    print("Displaying framestream...")
    for frame in framestream(dconn, (480, 640, 3)):
        cv2.imshow("OpenCV", frame)
        key = cv2.waitKey(30)
        if key >= 0:
            mconn.send(str(key))
        if key == 27:
            cv2.destroyAllWindows()
            break


if __name__ == '__main__':
    mc, dc = listen()
    display(mc, dc)
