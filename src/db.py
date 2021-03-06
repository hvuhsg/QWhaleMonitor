from typing import List
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson.objectid import ObjectId

from config import SITE_SCAN_TIMEOUT, SCAN_INTERVAL


class DB:
    _instance = None

    @classmethod
    def get_instance(cls):
        return cls._instance

    def __init__(self, file_name: str):
        if DB._instance is not None:
            raise TypeError("DB is singleton use DB.get_instance()")

        self.__db_file = file_name
        self.__db = MongoClient("mongodb://monitor:monitorpass@127.0.0.1:27017/Monitoring").get_database("Monitoring")
        self.__users = self.__db.get_collection("users")
        self.__sites = self.__db.get_collection("sites")
        self.__site_token_links = self.__db.get_collection("site_token_links")

        DB._instance = self

    def add_user(self, token: str, user_data: dict = None):
        if user_data is None:
            user_data = dict()
        return self.__users.insert_one({"token": token, "user_data": user_data})

    def user_exist(self, token: str):
        return self.__users.find_one({"token": token}) is not None

    def add_site(self, site_name, site_url, timeout, filters, scan_interval, **kwargs) -> str:
        """
        Add site to db

        :param scan_interval: Every scan interval time the site will be scanned
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
            filters = ["connection_error_to_connected", "status_code", "connection_error_to_connection_error"]
        if scan_interval is None:
            scan_interval = SCAN_INTERVAL
        else:
            scan_interval = max(SCAN_INTERVAL, timedelta(minutes=scan_interval)).total_seconds()

        private_site_args = {
            "registration_date": datetime.utcnow().isoformat(),
            "enable_scan": True,
            "last_scan_date": None,
            "timeout": timeout,
            "status": None,
            "interval": scan_interval,
            "notify_on": filters,
        }

        object_id = self.__sites.insert_one(
            {"name": site_name, "url": site_url, **private_site_args, **kwargs}
        ).inserted_id
        return str(object_id)

    def disable_site(self, site_id) -> bool:
        """
        Stop site from bean scanned

        :param site_id: db site id
        :return: True for success and False for error
        """

        return bool(self.__sites.update_one({"_id": site_id}, {"$set": {"enable_scan": False}}))

    def connect_site_to_token(self, site_id: str, token: str) -> bool:
        try:
            self.__site_token_links.insert_one({"site_id": ObjectId(site_id), "token": token})
        except (ValueError, RuntimeError):
            return False
        else:
            return True

    def connected_token(self, site_id: str):
        document = self.__site_token_links.find({"site_id": ObjectId(site_id)})
        if not document:
            return None
        return document["token"]

    def get_unscanned_sites(self) -> List[dict]:
        # TODO: find query
        all_sites = self.__sites.find({"enable_scan": True})
        unscanned_sites = []
        for site in all_sites:
            if site["last_scan_date"] is None:
                unscanned_sites.append(site)
                continue
            if datetime.utcnow() - datetime.fromisoformat(site["last_scan_date"]) \
                    > timedelta(seconds=site["interval"]):
                unscanned_sites.append(site)
        return unscanned_sites

    def update_site_status(self, site_id: ObjectId, status: dict) -> bool:
        self.__sites.update_one(
            {"_id": ObjectId(site_id)}, {"$set": {"status": status, "last_scan_date": datetime.utcnow().isoformat()}}
        )

    def get_sites_by_token(self, token: str):
        token_site_links = self.__site_token_links.find({"token": token}, {"site_id": 1})
        site_ids = [site["site_id"] for site in token_site_links]

        def obj_id_to_str(site):
            site["_id"] = str(site["_id"])
            return site
        return [obj_id_to_str(site) for site in self.__sites.find({"_id": {"$in": site_ids}})]
