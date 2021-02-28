#!/usr/bin/env python3

import sys
import socket
import selectors
import types

sel = selectors.DefaultSelector()


def accept_wrapper(sock):
    """�������-��������� ���  accept(), ����� �������� ����� ������ ������ �
    ���������������� ��� � ������� ���������."""
    # ��������� ��������� ����� ��� ��������������� ���
    # ���������� ������� EVENT_READ, �� ������ ���� ����� � ������.
    # �� �������� sock.accept ()
    conn, addr = sock.accept()  # ������ ���� ����� � ������

    print("�������� ���������� ��", addr)

    conn.setblocking(False)  # ����� ��������� ����� � ������������� �����.

    # ������ ��� �������� ������, ������� �� ����� �������� ������ � �������
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")

    # ��������� �� ����� �����, ����� ���������� ���������� ������ � ������ � ������, ��� ���� ������� ��������������� � ������� ����������:
    events = selectors.EVENT_READ | selectors.EVENT_WRITE

    # ����� �������, ����� � ������� ������ ���������� � sel.register().
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    """�������������� ���������� ����������, ����� ��� ������.

    ������ �������� ������� � ����������� �������������.
    key - ��� ����������� ������, ������������ �������� select(), �������
          �������� ������ ������ (fileobj) � ������ ������.
    mask - �������� ��� ������� �������.

    !!!�������� ��������, ��� ��� ���� ������ ������� ��
    �������� ��������� �������: ������ �������, ��� ������
    ������� ���� ������� ����������, ����� �� ��������
    ���������� ���������. ���� ������ �� �����������, ������
    ������� ���������� ��������. � �������� ���������� ��
    ������ �������� ���� ������ �� ����� � �������������
    ���������� ���������� �����������, ���� ��� �� ��������
    ������ �� ���������� ������������� �������.
    """
    sock = key.fileobj
    data = key.data

    # ���� ����� ����� � ������, �� mask & selectors.EVENT_READ �������
    if mask & selectors.EVENT_READ:
        # ���������� sock.recv().
        recv_data = sock.recv(1024)  # ������ ���� ����� � ������
        if recv_data:
            # ����� ��������� ������ ����������� � data.outb,
            # ����� �� ����� ���� ��������� �����.
            data.outb += recv_data
        else:
            # �������� �������� �� ���� else:, ���� ������ �� ��������
            print("�������� ���������� �", data.addr)

            # ��� ��������, ��� ������ ������ ���� �����,
            # ������� ������ ���� ������ ��� �������.
            # �� �� �������� ������� ������� sel.unregister (), ����� �� ������ �� ��������������� select().
            sel.unregister(sock)
            sock.close()

    if mask & selectors.EVENT_WRITE:
        # ����� ����� ����� � ������, ��� ������ ������ ����� ����� ���
        # ��������� ������,
        if data.outb:
            print("���", repr(data.outb), "���", data.addr)

            # ����� ���������� ������, ���������� � data.outb,
            # ���� ���������� ������� � ������� sock.send().
            sent = sock.send(data.outb)  # ������ ���� ����� � ������

            # ����� ������������ ����� ��������� �� ������ ��������:
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

#  ���� �������
try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                # ���� key.data ����� �������� None, ������ �� �������
                # �� ��������������� ������, � ��� �����  accept() (�������)����������
                accept_wrapper(key.fileobj)
            else:
                # ���� key.data �� ����� None, ������, ��� ���������� �����,
                # ������� ��� ��� ������, � ��� ���������� ��� �����������.
                # ���������� service_connection () � ���������� ���� � �����,
                # ������� �������� ��, ��� ��� ����� ��� ������ � �������.
                service_connection(key, mask)
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()
