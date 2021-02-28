#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""очень похож на сервер, но вместо того, чтобы прослушивать соединения, он начинает инициировать соединения через start_connections():
"""

import sys
import socket
import selectors
import types

sel = selectors.DefaultSelector()
messages = [b"Message 1 from client.", b"Message 2 from client."]


def start_connections(host, port, num_conns):
    """num_conns считывается из командной строки, которая
    представляет собой количество соединений, создаваемых с сервером.
    Как и сервер, каждый сокет настроен на неблокирующий режим.
    """

    server_addr = (host, port)
    for i in range(0, num_conns):
        connid = i + 1
        print("Создаём соединение", connid, "к", server_addr)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)

        # connect_ex() используется вместо connect (), так как connect()
        # немедленно вызовет исключение BlockingIOError.
        # connect_ex() изначально возвращает индикатор ошибки errno.EINPROGRESS,
        # вместо того чтобы вызывать исключение во время выполнения соединения.
        # Как только соединение завершено, сокет готов к чтению и записи и
        # возвращается как таковой select().
        sock.connect_ex(server_addr)

        events = selectors.EVENT_READ | selectors.EVENT_WRITE

        # После настройки сокета данные, которые мы хотим сохранить
        # вместе с сокетом, создаются с использованием types.SimpleNamespace.
        # Сообщения, которые клиент будет отправлять на сервер,
        # копируются с помощью list(messages), так как каждое соединение будет
        # вызывать socket.send() и изменять список. Все необходимое для отслеживания
        # того, что клиент ДОЛЖЕН ОТПРАВИТЬ, УЖЕ ОТПРАВЛЕНО и ПОЛУЧЕНО, а
        # общее количество байтов в сообщениях хранится в объекте data.
        data = types.SimpleNamespace(
            connid=connid,
            # суммарная длина сообщения (messages глобальный)
            msg_total=sum(len(m) for m in messages),
            recv_total=0,
            messages=list(messages),
            outb=b"",
        )
        sel.register(sock, events, data=data)


def service_connection(key, mask):
    """Обрабатывается соединение, когда оно готово.
    По сути, это то же самое, что и сервер:

    key - это именованный кортеж, возвращаемый функцией select(), который
          содержит объект сокета (fileobj) и объект данных.
    mask - содержит уже готовые события.
    """
    # Есть одно важное отличие от сервера. Он отслеживает количество байтов,
    # полученных от сервера, поэтому может закрыть свою сторону соединения.
    # Когда сервер обнаруживает это, он также закрывает свою сторону соединения.
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            print("получил", repr(recv_data),
                  "от соединения", data.connid)
            data.recv_total += len(recv_data)
        if not recv_data or data.recv_total == data.msg_total:
            print("закрываем соединения", data.connid)
            # Это означает, что клиент закрывает свой сокет,
            # Но не забудьте сначала вызвать sel.unregister (), чтобы он больше не контролировался select().
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        if data.outb:
            print("отправка", repr(data.outb), "к подключению", data.connid)
            sent = sock.send(data.outb)  # Должен быть готов к ззаписи
            data.outb = data.outb[sent:]


if len(sys.argv) != 4:
    print("usage:", sys.argv[0], "<host> <port> <num_connections>")
    sys.exit(1)


host, port, num_conns = sys.argv[1:4]
start_connections(host, int(port), int(num_conns))

try:
    while True:
        events = sel.select(timeout=1)
        if events:
            for key, mask in events:
                service_connection(key, mask)
        # Чтобы продолжить, проверьте, отслеживается ли сокет.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("поймал прерывание клавиатуры, выход")
finally:
    sel.close()
