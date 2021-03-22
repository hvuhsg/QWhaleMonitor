from typing import List
from datetime import datetime, timedelta

from tinydb import TinyDB, Query, where
from tinydb.table import Document

from config import SITE_SCAN_TIMEOUT


class DB:
    _instance = None

    @classmethod
    def get_instance(cls):
        return cls._instance

    def __init__(self, file_name: str):
        if DB._instance is not None:
            raise TypeError("DB is singleton use DB.get_instance()")

        self.__db_file = file_name
        self.__db = TinyDB(self.__db_file)
        self.__sites = self.__db.table("sites")
        self.__site_token_links = self.__db.table("site_token_links")

        DB._instance = self

    def add_site(self, site_name, site_url, timeout, filters, **kwargs) -> int:
        """
        Add site to db

        :param filters: The changes on the site that will trigger notification
        :param timeout: timeout of the http request
        :param site_name: The website name for notifications
        :param site_url: Url for monitoring
        :param kwargs: extra in the future
        :return: site id
        """
        if timeout is None:
            timeout = SITE_SCAN_TIMEOUT
        if filters is None:
            filters = ["connection_error_to_connected", "status_code"]

        private_site_args = {
            "registration_date": datetime.utcnow().isoformat(),
            "enable_scan": True,
            "last_scan_date": None,
            "timeout": timeout,
            "status": None,
            "interval": timedelta(minutes=1).total_seconds(),
            "notify_on": filters,

            # Notify on option values
            # "connection_error_to_connected"
            # "connection_error_to_connection_error"
            # "status_code"
            # "content_hash"
            # "url"
            # "headers"
            # "links"
            # "is_redirect"
            # "is_permanent_redirect"
            # "reason"
            # "history"
            # "elapsed"
        }

        return self.__sites.insert(
            {"name": site_name, "url": site_url, **private_site_args, **kwargs}
        )

    def disable_site(self, site_id) -> bool:
        """
        Stop site from bean scanned

        :param site_id: db site id
        :return: True for success and False for error
        """

        return bool(self.__sites.update({"enable_scan": False}, doc_ids=[site_id]))

    def connect_site_to_token(self, site_id: int, token: str) -> bool:
        try:
            self.__site_token_links.insert({"site_id": site_id, "token": token})
        except (ValueError, RuntimeError):
            return False
        else:
            return True

    def connected_token(self, site_id: int):
        document = self.__site_token_links.search(where("site_id") == site_id)
        if not document:
            return None
        return document["token"]

    def get_unscanned_sites(self) -> List[Document]:
        all_sites = self.__sites.all()
        unscanned_sites = []
        for site in all_sites:
            if site["last_scan_date"] is None and site["enable_scan"]:
                unscanned_sites.append(site)
                continue
            if datetime.utcnow() - datetime.fromisoformat(site["last_scan_date"]) \
                    > timedelta(seconds=site["interval"]) and site["enable_scan"]:
                unscanned_sites.append(site)
        return unscanned_sites

    def update_site_status(self, site_id: int, status: dict) -> bool:
        self.__sites.update({"status": status, "last_scan_date": datetime.utcnow().isoformat()}, doc_ids=[site_id])
