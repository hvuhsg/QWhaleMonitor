from requests import Response
from hashlib import sha256


class SiteStatus:
    def __init__(self, response: Response = None):
        if response is not None:
            self.status_code = response.status_code
            self.content_hash = sha256(response.content).hexdigest()
            self.url = response.url
            self.headers = {k: v for k, v in response.headers.items()}
            self.links = response.links
            self.is_redirect = response.is_redirect
            self.is_permanent_redirect = response.is_permanent_redirect
            self.reason = response.reason
            self.history = [response.url for response in response.history]
            self.elapsed = response.elapsed.total_seconds()

    def to_dict(self):
        return {
            "status_code": self.status_code,
            "content_hash": self.content_hash,
            "url": self.url,
            "headers": self.headers,
            "links": self.links,
            "is_redirect": self.is_redirect,
            "is_permanent_redirect": self.is_permanent_redirect,
            "reason": self.reason,
            "history": self.history,
            "elapsed": self.elapsed
        }
