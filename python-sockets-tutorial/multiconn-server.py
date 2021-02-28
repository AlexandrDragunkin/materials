#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import socket
import selectors
import types

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

    # объект для хранения данных, которые мы хотим включить вместе с сокетом
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    
    # Поскольку мы хотим знать, когда клиентское соединение готово к чтению и записи, оба этих события устанавливаются с помощью следующего:
    events = selectors.EVENT_READ | selectors.EVENT_WRITE

    # Маска событий, сокет и объекты данных передаются в sel.register().
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    """Обрабатывается клиентское соединение, когда оно готово.
    
    Сердце простого сервера с несколькими подключениями.
    key - это именованный кортеж, возвращаемый функцией select (), который 
          содержит объект сокета (fileobj) и объект данных.
    mask - содержит уже готовые события.
    """
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Должен быть готов к чтению
        if recv_data:
            data.outb += recv_data
        else:
            print("Закрытие соединения с", data.addr)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print("Эхо", repr(data.outb), "для", data.addr)
            sent = sock.send(data.outb)  # Должен быть готов к записи
            data.outb = data.outb[sent:]


if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<host> <port>")
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print("listening on", (host, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                # Если key.data имеет значение None, значит он получен
                # из прослушивающего сокета, и нам нужно  accept() (принять)соединение
                accept_wrapper(key.fileobj)
            else:
                # Если key.data не равно None, значит, это клиентский сокет,
                # который уже был принят, и нам необходимо его обслуживать.
                # Вызывается service_connection () и передается ключ и маска,
                # которые содержат всё, что нам нужно для работы с сокетом.
                service_connection(key, mask)
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()
