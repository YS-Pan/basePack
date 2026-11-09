"""Exercise the public client against a real local HTTP server."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from basepack.embedding.client import EmbeddingClient


@pytest.fixture
def service():
    state = SimpleNamespace(requests=[], entered=threading.Event(),
                            release=threading.Event(), completed=threading.Event())

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state.requests.append((self.path, self.headers['Content-Type'], payload))
            inputs = payload['inputs']
            if inputs == ['slow']:
                state.entered.set()
                assert state.release.wait(5)
                state.completed.set()
            status = 503 if inputs == ['error'] else 200
            body = {'detail': 'native upstream failure'} if status == 503 else {
                'pid': 123, 'embedding_identity': 'fixture', 'vectors': [[0.6, 0.8]]}
            encoded = json.dumps(body).encode('utf-8')
            try:
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # The timeout test deliberately disconnects while work is still running.
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    machine = SimpleNamespace(raw={'embedding': {
        'endpoint': f'http://127.0.0.1:{server.server_port}/'}})
    state.client = EmbeddingClient(machine)
    try:
        yield state
    finally:
        state.release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def test_client_sends_inputs_and_returns_service_result(service):
    inputs = [{'text': '项目资料', 'image': 'D:/资料/图像.png'}]
    assert service.client.embed(inputs, timeout=2) == {
        'pid': 123, 'embedding_identity': 'fixture', 'vectors': [[0.6, 0.8]]}
    assert service.requests == [('/predict', 'application/json', {'inputs': inputs})]


def test_native_http_error_preserves_status_and_body(service):
    with pytest.raises(HTTPError) as error:
        service.client.embed(['error'], timeout=2)
    assert error.value.code == 503
    assert json.load(error.value) == {'detail': 'native upstream failure'}
    assert len(service.requests) == 1


def test_timeout_does_not_retry_or_interrupt_another_request(service):
    try:
        with pytest.raises(TimeoutError):
            service.client.embed(['slow'], timeout=0.05)
        assert service.entered.wait(2)
        assert not service.completed.is_set()
        assert service.client.embed(['healthy'], timeout=2)['pid'] == 123
        assert [item[2]['inputs'] for item in service.requests] == [['slow'], ['healthy']]
    finally:
        service.release.set()
    assert service.completed.wait(2)
