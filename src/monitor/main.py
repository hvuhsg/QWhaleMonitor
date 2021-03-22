from typing import Union
from time import sleep, time
import traceback
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

import requests
from requests import ConnectTimeout, ConnectionError
from notifiers import get_notifier

from db import DB
from .config import SCAN_INTERVAL
from .status import SiteStatus

Status = Union[str, SiteStatus]


class Scanner(Thread):
    def __init__(self, db: DB):
        super().__init__(name="Scanner", daemon=False)
        self.__time_interval = SCAN_INTERVAL
        self.__db = db
        self.__stop = False
        self.__thread_pool = ThreadPoolExecutor(thread_name_prefix="ScannerWorker", max_workers=10)

    def _get_sites_for_scan(self):
        sites = self.__db.get_unscanned_sites()
        return sites

    def _scan_site(self, site: dict) -> Status:
        site_url = site["url"]

        try:
            response = requests.get(site_url, timeout=site["timeout"])
        except ConnectTimeout:
            status = "TimeoutError"
        except ConnectionError:
            status = "ConnectionError"
        else:
            status = SiteStatus(response)
        return status

    def _update_site_status(self, site, status: Status):
        self.__db.update_site_status(site.doc_id, status.to_dict())

    def _need_to_notify(self, site, status) -> Union[dict, None]:
        old_status = site["status"]
        current_status = status.to_dict()

        notify_fields = site["notify_on"]
        connection_error_to_connected = False
        connection_error_to_connection_error = False
        success_to_success = False

        need_notify = False
        diff = {"from": old_status, "to": current_status}

        if old_status is None:
            diff = None
        elif type(old_status) == str:  # Old status was error
            if type(current_status) == str:  # Current status is error
                if current_status != old_status:
                    connection_error_to_connection_error = True
                else:
                    connection_error_to_connected = True
            else:  # Current status is ok
                connection_error_to_connected = True
        else:  # Old status was ok
            if type(current_status) == str:  # Current status is error
                connection_error_to_connected = True
            else:
                diff = {}
                for k, v in old_status.items():
                    if current_status[k] != v and k in notify_fields:
                        diff[k] = {"from": v, "to": current_status[k]}
                success_to_success = True

        if connection_error_to_connected and "connection_error_to_connected" in notify_fields:
            need_notify = True

        if connection_error_to_connection_error and "connection_error_to_connection_error" in notify_fields:
            need_notify = True

        if diff is None:
            return None

        if success_to_success:
            for k, v in diff.items():
                if k in notify_fields:
                    need_notify = True
                    break

        return diff if need_notify else None

    def _send_notification(self, site, notification):
        p = get_notifier('pushover')
        p.notify(
            user="ufg86adtpmq93zk9ue8d956rd7fjvc",
            token="a3domhu4ph84tnezcpka5umx7jvfy2",
            message=f"{notification}",
            url=site["url"],
            priority=1
        )

    def _handle_site_scanning(self, site):
        try:
            status = self._scan_site(site)
            notification = self._need_to_notify(site, status)
            print("Need notification", notification is not None)
            if notification is not None:
                print("Send notification")
                self._send_notification(site, notification)
            self._update_site_status(site, status)
        except Exception:
            traceback.print_exc()

    def round(self):
        print("Start round")
        unscanned_sites = self._get_sites_for_scan()
        for site in unscanned_sites:
            print(f"Scanning site {site['url']}")
            self.__thread_pool.submit(self._handle_site_scanning, site)

    def _loop(self):
        while not self.__stop:
            start_time = time()
            self.round()
            end_time = time()
            run_time = end_time - start_time
            sleep(self.__time_interval.total_seconds() - run_time)

    def run(self):
        self._loop()

    def stop(self):
        self.__stop = True
