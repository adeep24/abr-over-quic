import os
import asyncio
import logging
import pickle
from urllib.parse import urlparse
import argparse
from typing import Deque, Dict, List, Optional, Union, cast
import ssl
import time
from collections import deque

import aioquic
from aioquic.h0.connection import H0_ALPN, H0Connection
from aioquic.h3.connection import H3_ALPN, H3Connection

from aioquic.h3.events import (
    DataReceived,
    H3Event,
    HeadersReceived,
    PushPromiseReceived,
)
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent

from protocol.client import connect
from protocol.socketFactory import QuicFactorySocket

try:
    import uvloop
except ImportError:
    uvloop = None

import logger
logger = logger.logger("h3 client")
# logger = logging.getLogger("h3 client")

HttpConnection = Union[H0Connection, H3Connection]

USER_AGENT = "aioquic/" + aioquic.__version__


class URL:
    def __init__(self, url: str) -> None:
        parsed = urlparse(url)

        self.authority = parsed.netloc
        self.full_path = parsed.path
        if parsed.query:
            self.full_path += "?" + parsed.query
        self.scheme = parsed.scheme


class HttpRequest:
    def __init__(
        self, method: str, url: URL, content: bytes = b"", headers: Dict = {}
    ) -> None:
        self.content = content
        self.headers = headers
        self.method = method
        self.url = url


class HttpClient(QuicFactorySocket):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.pushes: Dict[int, Deque[H3Event]] = {}
        self._http: Optional[HttpConnection] = None
        self._request_events: Dict[int, Deque[H3Event]] = {}
        self._request_waiter: Dict[int, asyncio.Future[Deque[H3Event]]] = {}

        if self._quic.configuration.alpn_protocols[0].startswith("hq-"):
            self._http = H0Connection(self._quic)
        else:
            self._http = H3Connection(self._quic)

    async def get(self, url: str, headers: Dict = {}) -> Deque[H3Event]:
        """
        Perform a GET request.
        """
        return await self._request(
            HttpRequest(method="GET", url=URL(url), headers=headers)
        )

    async def post(self, url: str, data: bytes, headers: Dict = {}) -> Deque[H3Event]:
        """
        Perform a POST request.
        """
        return await self._request(
            HttpRequest(method="POST", url=URL(url), content=data, headers=headers)
        )

    def http_event_received(self, event: H3Event) -> None:
        if isinstance(event, (HeadersReceived, DataReceived)):
            stream_id = event.stream_id
            if stream_id in self._request_events:
                # http
                self._request_events[event.stream_id].append(event)
                if event.stream_ended:
                    request_waiter = self._request_waiter.pop(stream_id)
                    request_waiter.set_result(self._request_events.pop(stream_id))

            elif event.push_id in self.pushes:
                # push
                self.pushes[event.push_id].append(event)

        elif isinstance(event, PushPromiseReceived):
            self.pushes[event.push_id] = deque()
            self.pushes[event.push_id].append(event)

    def quic_event_received(self, event: QuicEvent) -> None:
        #  pass event to the HTTP layer
        if self._http is not None:
            for http_event in self._http.handle_event(event):
                self.http_event_received(http_event)

    async def _request(self, request: HttpRequest):
        stream_id = self._quic.get_next_available_stream_id()
        self._http.send_headers(
            stream_id=stream_id,
            headers=[
                (b":method", request.method.encode()),
                (b":scheme", request.url.scheme.encode()),
                (b":authority", request.url.authority.encode()),
                (b":path", request.url.full_path.encode()),
                (b"user-agent", USER_AGENT.encode()),
            ]
            + [(k.encode(), v.encode()) for (k, v) in request.headers.items()],
        )
        self._http.send_data(stream_id=stream_id, data=request.content, end_stream=True)

        waiter = self._loop.create_future()
        self._request_events[stream_id] = deque()
        self._request_waiter[stream_id] = waiter
        self.transmit()

        return await asyncio.shield(waiter)


async def perform_http_request(
    client: HttpClient, url: str, data: str, include: bool, output_dir: Optional[str],
) -> None:
    # perform request
    start = time.time()
    logger.info('here 2')
    if data is not None:
        http_events = await client.post(
            url,
            data=data.encode(),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    else:
        http_events = await client.get(url)
    elapsed = time.time() - start

    logger.info('here 3')
    # print speed
    octets = 0
    for http_event in http_events:
        if isinstance(http_event, DataReceived):
            octets += len(http_event.data)
    logger.info(
        "Received %d bytes in %.3f s (%.3f Mbps)"
        % (octets, elapsed, octets * 8 / elapsed / 1000000)
    )

    tput = octets * 8 / elapsed / 1000000

    # stiching downloaded data
    downloaded_data = b''
    for http_event in http_events:
        if isinstance(http_event, DataReceived):
            downloaded_data += http_event.data
    
    # downloaded_data = ''.join(downloaded_data)
    # logger.info(downloaded_data)



    # output response
    # if output_dir is not None:
    #     output_path = os.path.join(
    #         output_dir, os.path.basename(urlparse(url).path) or "index.html"
    #     )
    #     with open(output_path, "wb") as output_file:
    #         for http_event in http_events:
    #             # if isinstance(http_event, HeadersReceived) and include:
    #             #     headers = b""
    #             #     for k, v in http_event.headers:
    #             #         headers += k + b": " + v + b"\r\n"
    #             #     if headers:
    #             #         output_file.write(headers + b"\r\n")
    #             # elif isinstance(http_event, DataReceived):
    #             #     output_file.write(http_event.data)
    #             if isinstance(http_event, DataReceived):
    #                 logger.info(http_event.data)
    #                 output_file.write(http_event.data)

    return (octets, tput, elapsed, downloaded_data)