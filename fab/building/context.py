from aiohttp import ClientSession

from ..caching import Cache, HashAlgo
from .sandboxes import SandboxFactory


class Context:
    cache: Cache
    hash_algo: HashAlgo
    http_session: ClientSession
    sandbox_factory: SandboxFactory

    def __init__(
        self,
        cache: Cache,
        hash_algo: HashAlgo,
        http_session: ClientSession,
        sandbox_factory: SandboxFactory,
    ) -> None:
        self.cache = cache
        self.hash_algo = hash_algo
        self.http_session = http_session
        self.sandbox_factory = sandbox_factory
