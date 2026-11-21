"""Direct HTTP access to a registered loopback endpoint."""

from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener


class _RefuseRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, stream, code, message, headers, new_url):
        return None


def managed_opener():
    return build_opener(ProxyHandler({}), _RefuseRedirect())
