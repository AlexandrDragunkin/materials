#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import socket
import selectors
import traceback

import libserver

sel = selectors.DefaultSelector()


def accept_wrapper(sock):
    """функция-декоратор для  accept(), чтобы получить новый объект сокета и
    зарегистрировать его с помощью селектора."""
    # Поскольку слушающий сокет был зарегистрирован для
    # селекторов событий EVENT_READ, он должен быть готов к чтению.
    # Мы вызываем sock.accept ()
    conn, addr = sock.accept()  # Должен быть готов к чтению

    print("Принятое соединение от", addr)

    conn.setblocking(False)  # чтобы перевести сокет в неблокирующий режим.

    message = libserver.Message(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=message)


if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Избегайте исключения bind (): OSError: [Errno 48] Адрес уже используется
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print("listening on", (host, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

#  цикл событий
try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                # Если key.data имеет значение None, значит он получен
                # из прослушивающего сокета, и нам нужно принять accept() соединение
                accept_wrapper(key.fileobj)
            else:
                # Если key.data не равно None, значит, это клиентский сокет,
                # который уже был принят, и нам необходимо его обслуживать.
                # Вызывается service_connection () и передается ключ и маска,
                # которые содержат всё, что нам нужно для работы с сокетом.
                message = key.data
                try:
                    message.process_events(mask)
                except Exception:
                    print(
                        "main: error: exception for",
                        f"{message.addr}:\n{traceback.format_exc()}",
                    )
                    message.close()
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()
