import time, queue, socket, sqlite3, datetime, threading


class Tello:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', 8889))
        self.db_queue = queue.Queue()  # cache flight data
        self.cmd_queue = queue.Queue()
        self.cmd_event = threading.Event()
        self.MAX_TIME_OUT = 15  # It must be longer than 10 sec, give time to "take off" command.
        self.MAX_RETRY = 2
        self.state = {}
        threading.Thread(target=self.flight_logger, daemon=True).start()
        threading.Thread(target=self.receiver, daemon=True).start()
        threading.Thread(target=self.sender, daemon=True).start()
        threading.Thread(target=self.update_state, daemon=True).start()

    def command(self, cmd):
        self.cmd_queue.put(cmd)

    def flight_logger(self):
        con = sqlite3.connect(
            f'Tello_flight_log_{datetime.datetime.fromtimestamp(time.time()).strftime("%Y%m%d_%H%M%S")}.db')
        cur = con.cursor()
        cur.execute('CREATE TABLE commands(timestamp REAL, command TEXT, who TEXT);')
        cur.execute('CREATE TABLE   states(timestamp REAL, log     TEXT          );')
        print('Flight Data Recording Begins ~')
        while 1:
            operation = self.db_queue.get()
            if operation == 'commit':
                con.commit()
                print('Flight Data Saved ~')
            elif operation == 'close':
                con.close()
                print('Flight Data Recording Ends ~')
                break
            else:
                cur.execute(operation)

    def receiver(self):
        while True:
            bytes_, address = self.socket.recvfrom(1024)
            if bytes_ == b'ok':
                self.cmd_event.set()  # one command has been successfully executed. Begin new execution.
            else:
                print('[ Station ]:', bytes_)
            try:
                self.db_queue.put(
                    'INSERT INTO commands(timestamp, command, who) VALUES({}, "{}", "{}");'.format(time.time(),
                                                                                                   bytes_.decode(),
                                                                                                   "Tello"))
            except UnicodeDecodeError as e:
                print('Decoding Error that could be ignored~')

    def sender(self, debug=True):
        tello_address = ('192.168.10.1', 8889)
        self.cmd_event.set()  # allow the first wait to proceed
        while True:
            self.cmd_event.wait()  # block second get until an event is set from receiver or failure set
            self.cmd_event.clear()  # block a timeout-enabled waiting
            cmd = self.cmd_queue.get()
            self.db_queue.put(
                f'INSERT INTO commands(timestamp, command, who) VALUES({time.time()}, "{cmd}", "Station");')
            self.socket.sendto(cmd.encode('utf-8'), tello_address)
            cmd_ok = False
            for i in range(self.MAX_RETRY):
                if self.cmd_event.wait(timeout=self.MAX_TIME_OUT):
                    cmd_ok = True
                    break
                else:
                    if debug: print(f'Failed command: "{cmd}", Failure sequence: {i + 1}.')
                    self.socket.sendto(cmd.encode('utf-8'), tello_address)
            if cmd_ok:
                print(f'Success with "{cmd}".')
                if cmd == 'land':
                    self.db_queue.put('commit')
                    self.db_queue.put('close')
            else:
                self.cmd_event.set()  # The failure set
                if debug: print(f'Stop retry: "{cmd}", Maximum re-tries: {self.MAX_RETRY}.')

    def update_state(self):
        UDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        UDP.bind(('', 8890))
        while True:
            bytes_, address = UDP.recvfrom(1024)
            str_ = bytes_.decode()
            self.db_queue.put('INSERT INTO states(timestamp, log) VALUES({},"{}");'.format(time.time(), str_))
            state = str_.split(';')
            state.pop()
            self.state.update(dict([s.split(':') for s in state]))


