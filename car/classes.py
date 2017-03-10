from __future__ import print_function, absolute_import, division

# STDLIB imports
import os
import time
import socket
import warnings
import threading as thr

# 3rd party imports
import cv2

# Project imports
from FIPER.generic import *

print("OpenCV version:", cv2.__version__)

DUMMY_VIDEOFILE = ""
DUMMY_FRAMESIZE = (640, 480, 3)  # = 921,600 B in uint8


class CaptureDeviceMockerWhite(object):
    """Mocks the interface of cv2.VideoCapture"""

    @staticmethod
    def read():
        """
        Mocks the functionality of VideoCapture().read():

        returns success code and a white noise frame
        """
        return True, white_noise(DUMMY_FRAMESIZE)


class CaptureDeviceMockerFile(object):
    """Mocks the interface of cv2.VideoCapture"""

    myreader = cv2.VideoCapture(DUMMY_VIDEOFILE)

    @staticmethod
    def read():
        """
        Mocks the functionality of VideoCapture().read():

        reads a file frame-by-frame
        """
        return CaptureDeviceMockerFile.myreader.read()


class Car(object):

    """
    A video stream server, located somewhere on the local network.
    It has a mounted video capture device, read by openCV.
    Video frames are forwarded to a central server for further processing
    """

    def __init__(self, ID, address):
        self.ID = ID

        if not DUMMY_VIDEOFILE:
            self.eye = cv2.VideoCapture(0)
        elif not os.path.exists(DUMMY_VIDEOFILE):
            self.eye = CaptureDeviceMockerWhite
        else:
            self.eye = CaptureDeviceMockerFile

        self.messenger = None  # message channel wrapper
        self.send_message = None
        self.get_message = None
        self.server_ip = None  # this will be the UDP stream's target
        self.server_port = None

        self.address = address

        self.dsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.live = True
        self.streaming = False

        self.stream_worker = None

    def connect(self, server_ip):
        """Establishes connections with the server"""

        self.server_ip = server_ip

        # Read a single frame to infer the frame shape
        success, frame = self.eye.read()
        if not success:
            self.eye = CaptureDeviceMockerWhite
            frame = self.eye.read()[1]
            msg = "Capture device unreachable!\n"
            msg += "Falling back to white noise stream!"
            warnings.warn(msg)

        # Initiate connection by setting up the message-passing
        # socket, then send ID and video frame shape to the server
        msocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        msocket.connect((server_ip, MESSAGE_SERVER_PORT))
        self.out("MSOCKET connected to {}:{}".format(server_ip, MESSAGE_SERVER_PORT))
        self.messenger = Messaging(msocket)
        self.messenger.send(str(self.ID).encode())
        self.messenger.send(str(frame.shape)[1:-1].replace(", ", "x").encode())
        self.server_port = int(self.messenger.recv())
        self.out("Streaming to {}".format(self.server_port))

    def launch_stream(self):
        """
        Launches the worker thread which streams video to the server
        Thread creation is done here too, because threads cannot be
        restarted.
        (Turning streaming off, then on again wouldn't be possible)
        """
        self.streaming = True
        self.stream_worker = thr.Thread(target=self.see)
        self.stream_worker.start()

    def terminate_stream(self):
        """Tears down the streaming thread"""
        self.streaming = False
        time.sleep(3)  # Wait for loop termination

    def see(self):
        """
        Obtain frames from the capture device via OpenCV.
        Send the frames to the UDP client (the main server)
        """
        pushed = 0
        self.streaming = True
        while self.streaming:
            success, frame = self.eye.read()
            ##########################################
            # Data preprocessing has to be done here #
            serial = frame.astype(DTYPE).tostring()  #
            ##########################################
            for slc in (serial[i:i+1024] for i in range(0, len(serial), 1024)):
                self.dsocket.sendto(slc, (self.server_ip, STREAM_SERVER_PORT))
            pushed += 1
            print("\rPushed {:>3} frames".format(pushed), end="")
        self.out("Stream terminated!")

    def out(self, *args, **kw):
        """Wrapper for print(). Appends car's ID to every output line"""
        sep, end = kw.get("sep", " "), kw.get("end", "\n")
        print("CAR {}: ".format(self.ID), *args, sep=sep, end=end)

    def shutdown(self):
        if self.streaming:
            self.terminate_stream()
        self.live = False

        self.dsocket.close()
        Messaging.send(self.msocket, "{} offline".format(self.ID))
        self.msocket.close()

    def mainloop(self):
        """
        This loop wathces the messaging system and receives
        control commands from the server.
        """
        while self.live:
            msg = Messaging.recv(self.msocket, timeout=1).lower()
            if msg is None:
                continue
            self.out("Received message:", msg)
            if msg == "shutdown":
                self.shutdown()
                break
            elif msg == "stream on":
                if self.streaming:
                    self.out("Received <stream on>, when already streaming!")
                else:
                    self.launch_stream()
            elif msg == "stream off":
                self.terminate_stream()
            else:
                self.out("Received unknown command:", msg)
        self.out("Shutting down...")


def readargs():
    pleading = "Please supply "
    question = ["the local IP address of this Car",
                "the remote IP address for the server",
                "a unique ID for this Car"]
    return [raw_input(pleading + q + " > ") for q in question]


def main():
    import sys

    if len(sys.argv) == 4:
        localIP, serverIP, carID = sys.argv[1:4]
    else:
        localIP, serverIP, carID = readargs()

    lightning_mcqueen = Car(ID=carID, address=localIP)
    lightning_mcqueen.connect(serverIP)
    lightning_mcqueen.mainloop()

    print("OUTSIDE: Car was shut down nicely.")


if __name__ == '__main__':
    main()
