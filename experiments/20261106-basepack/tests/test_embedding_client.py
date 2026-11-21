"""Exercise the public client against a real local HTTP server."""
from concurrent.futures import ThreadPoolExecutor
from errno import ECONNREFUSED
from io import BytesIO
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from basepack.embedding import client
from basepack.embedding.client import EmbeddingClient
from basepack.runtime import control
from basepack.runtime.recovery import EMBEDDING_DRAINING_HEADER, RuntimeStartRequired


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
            status = 503 if inputs in (['error'], ['draining']) else 200
            body = {'detail': 'native upstream failure'} if status == 503 else {
                'pid': 123, 'embedding_identity': 'fixture', 'vectors': [[0.6, 0.8]]}
            encoded = json.dumps(body).encode('utf-8')
            try:
                self.send_response(status)
                if inputs == ['draining']:
                    self.send_header(EMBEDDING_DRAINING_HEADER, '1')
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
    service.client.machine.raw['embedding']['windows_task'] = True
    with pytest.raises(HTTPError) as error:
        service.client.embed(['error'], timeout=2)
    assert error.value.code == 503
    assert 'native upstream failure' in ' '.join(error.value.__notes__)
    assert json.load(error.value) == {'detail': 'native upstream failure'}
    assert len(service.requests) == 1


def test_timeout_does_not_retry_or_interrupt_another_request(service):
    service.client.machine.raw['embedding']['windows_task'] = True
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


def test_long_lived_managed_client_reports_each_confirmed_connection_refusal(monkeypatch):
    machine = SimpleNamespace(raw={'embedding': {'endpoint': 'http://127.0.0.1:18288', 'windows_task': True}})
    embedder = EmbeddingClient(machine)
    refused = URLError(ConnectionRefusedError(ECONNREFUSED, 'fixture connection refused'))
    opens = []

    def request(payload, *, timeout):
        opens.append(json.loads(payload.data)['inputs'])
        if opens[-1] == ['available']:
            return BytesIO(b'{"vectors":[[1.0]]}')
        raise refused

    commands = []

    def start_command(config, component):
        commands.append((config, component))
        return {'argv': ['host', 'runtime', 'start', 'embedding']}

    monkeypatch.setattr(client, 'managed_opener', lambda: SimpleNamespace(open=request))
    monkeypatch.setattr(control, 'start_command', start_command)
    assert embedder.embed(['available'])['vectors'] == [[1.0]]
    for _ in range(2):
        with pytest.raises(RuntimeStartRequired) as error:
            embedder.embed(['unavailable'])
        assert error.value.result['status'] == 'runtime_start_required'
        assert error.value.__cause__ is refused
    assert commands == [(machine, 'embedding')] * 2
    assert opens == [['available'], ['unavailable'], ['unavailable']]


def test_managed_client_preserves_an_ambiguous_disconnect(monkeypatch):
    machine = SimpleNamespace(raw={'embedding': {'endpoint': 'http://127.0.0.1:18288', 'windows_task': True}})
    disconnected = ConnectionResetError('connection reset while waiting for response')
    requests = []

    def request(payload, *, timeout):
        requests.append(payload.full_url)
        raise disconnected

    monkeypatch.setattr(client, 'managed_opener', lambda: SimpleNamespace(open=request))
    monkeypatch.setattr(control, 'start_command', lambda *_: pytest.fail('disconnect offered recovery'))
    with pytest.raises(ConnectionResetError) as error:
        EmbeddingClient(machine).embed(['probe'])
    assert error.value is disconnected
    assert requests == ['http://127.0.0.1:18288/predict']


def test_managed_concurrent_callers_receive_draining_recovery(service, monkeypatch):
    managed_client = service.client
    managed_client.machine.raw['embedding']['windows_task'] = True
    command = {'argv': ['host', 'runtime', 'start', 'embedding']}
    monkeypatch.setattr(control, 'start_command', lambda *_: command)
    assert managed_client.embed(['available'], timeout=2)['pid'] == 123

    def embed_during_drain(_):
        with pytest.raises(RuntimeStartRequired) as error:
            managed_client.embed(['draining'], timeout=2)
        return error.value.result

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(embed_during_drain, range(4)))
    assert all(result['status'] == 'runtime_start_required' and result['argv'] == command['argv']
               for result in results)
    assert [request[2]['inputs'] for request in service.requests] == [['available'], *([['draining']] * 4)]


def test_unmanaged_draining_response_is_native(service):
    with pytest.raises(HTTPError) as error:
        service.client.embed(['draining'], timeout=2)
    assert error.value.headers[EMBEDDING_DRAINING_HEADER] == '1'
