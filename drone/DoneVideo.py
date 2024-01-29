import socket
import threading
import cv2
import time


class VIDEO:
    def __init__(self):
        ip, port = '192.168.10.1', 8889
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'command', (ip, port))
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'streamon', (ip, port))
        self.void_frame = b''
        self.h264_frame = self.void_frame
        self.jpeg_frame = self.void_frame
        self.frame_event = threading.Event()  # tell transmitter that receiver has a new frame from tello ready
        self.stream_event = threading.Event()  # tell opencv that transmitter has the stream ready.
        threading.Thread(target=self.video_receiver, daemon=True).start()
        threading.Thread(target=self.video_transmitter, daemon=True).start()
        time.sleep(3)
        threading.Thread(target=self.opencv, daemon=True).start()
        time.sleep(3)

    def video_receiver(self):  # receive h264 stream from tello
        _receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # socket for receiving video stream (UDP)
        _receiver.bind(('', 11111))  # the udp port is fixed
        while True:
            frame = b''
            while True:
                byte_, _ = _receiver.recvfrom(2048)
                frame += byte_
                if len(byte_) != 1460:  # end of frame
                    self.h264_frame = frame
                    self.frame_event.set()  # let the reading frame event happen
                    self.frame_event.clear()  # prevent it happen until next set
                    break

    def video_transmitter(self):  # feed h264 stream to opencv
        _transmitter = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket for transmitting stream    (TCP)
        _transmitter.bind(('127.0.0.1', 12345))  # tcp port is up to us
        _transmitter.listen(0)
        while True:
            conn, address = _transmitter.accept()
            file_obj = conn.makefile('wb')
            stream_ready_flag = False
            while True:
                self.frame_event.wait()
                try:
                    file_obj.write(self.h264_frame)
                except BrokenPipeError:
                    print('[ Warning ] Tello returned nonsense!')
                    print('[ Warning ] Please refresh stream after a while~\n')
                    break
                file_obj.flush()

    def opencv(self):
        while True:
            cap = cv2.VideoCapture("tcp://127.0.0.1:12345")
            while (cap.isOpened()):
                ret, frame = cap.read()
                if not ret:
                    print('[ Error ] Please check if your tello is off~')
                    break
                ret, jpeg = cv2.imencode('.jpg', frame)
                self.jpeg_frame = jpeg.tobytes()
            cap.release()
            print('[ Warning ] OpenCV lost connection to transmitter!')
            print('[ Warning ] Try reconnection in 3 seconds~')
            time.sleep(3)