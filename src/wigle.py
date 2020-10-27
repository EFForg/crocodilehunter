#!/usr/bin/python3
"""
Interface to the wigle.net API
put the username and access key in the following environment variables: WIGLE_NAME, WIGLE_KEY
author: cooperq@eff.org
licence: GPL3
"""
import json
import os
import urllib
import requests

class Wigle():

    base_url = "https://api.wigle.net/api"

    def __init__(self, wigle_name=None, wigle_key=None):
        if wigle_name is None:
            self.api_name = os.environ["WIGLE_NAME"]
            self.api_key = os.environ["WIGLE_KEY"]
        else:
            self.api_name = wigle_name
            self.api_key = wigle_key

    def _api_request(self, api_stub, qs_params, method="GET"):
        query = urllib.parse.urlencode(qs_params)
        v3_url = f"{self.base_url}/v3/{api_stub}?{query}"
        resp = requests.request(method, v3_url,
                                auth=(self.api_name, self.api_key,))
        print(v3_url)

        if resp.status_code >= 400:
            print(resp.content)
            return resp

        return json.loads(resp.text)


    def _old_api_request(self, api_stub, qs_params, method="GET"):
        """
        make a request to the wigle.net API
        @param string api_stub The last part of the path to the API endpoint after /api/v2/
        @param dictionary qs_params A dictionary containing key,value pairs to append to the querystring
        @param string method what HTTP method to use, defaults to "GET"
        @return dictionary returns the decoded json response from wigle as a dict
        """
        # TODO raise a useful error if either env variable is missing
        query = urllib.parse.urlencode(qs_params)
        v2_url = f"{self.base_url}/v2/{api_stub}?{query}"
        # print(v2_url)
        resp = requests.request(method, v2_url,
                                auth=(self.api_name, self.api_key,))
        if resp.status_code >= 400:
            return resp

        resp = json.loads(resp.text)
        prev_resp = resp
        while prev_resp['searchAfter'] is not None:
            qs_params['searchAfter'] = prev_resp['searchAfter']
            query = urllib.parse.urlencode(qs_params)
            v2_url = f"https://api.wigle.net/api/v2/{api_stub}?{query}"
            #print(full_url)
            prev_resp = json.loads(requests.request(method, v2_url,
                                    auth=(self.api_name, self.api_key,)).text)
            resp['results'] += prev_resp['results']

        return resp

    def get_cell_detail(self, operator, lac, cid):
        """ Get detail for a specific CID/LAC combo """
        # TODO: this never seems to actually return any search results?
        qs_params = {
            "operator": operator,
            "lac": lac, # TODO: why is it lac here, but cell_net below?
            "cid": cid,
        }
        return self._old_api_request("network/detail", qs_params)

    def channel_search(self, lat, lon, gps_offset):
        """ gps_offset is so that we can specify the search radius around the GPS coords."""
        # TODO: this doesn't return results as often as it should, meaning we end up marking things are more suspicious than they actually are.
        params = {
            "latitude1": lat + gps_offset,
            "latitude2": lat - gps_offset,
            "longitude1": lon + gps_offset,
            "longitude2": lon - gps_offset
        }
        res = self._api_request("cellChannel/LTE", params)
        def _noneorzero(element):
            return element is not None and element != 0

        return set(filter(_noneorzero, [x['channel'] for x in res['results']] ))

    def cell_search(self, lat, lon, gps_offset, cell_id = None, tac = None):
        """ gps_offset is so that we can specify the search radius around the GPS coords."""
        # TODO: this doesn't return results as often as it should, meaning we end up marking things are more suspicious than they actually are.
        params = {
            "latrange1": lat + gps_offset,
            "latrange2": lat - gps_offset,
            "longrange1": lon + gps_offset,
            "longrange2": lon - gps_offset,
            "showGsm": False,
            "showCdma": False,
            "showWcdma": False,
            "showLte": True
        }
        if cell_id is not None:
            params["cell_id"] = cell_id
        if tac is not None:
            params["cell_net"] = tac
        return self._old_api_request("cell/search", params)

    def earfcn_search(self, lat, lon, offset):
        qs_params = {
            "latrange1": lat + offset,
            "latrange2": lat - offset,
            "longrange1": lon + offset,
            "longrange2": lon - offset,
            "showGsm": False,
            "showCdma": False,
            "showWcdma": False,
            "showLte": True
        }
        res = self._old_api_request("cell/search", qs_params)

        def _noneorzero(element):
            return element is not None and element != 0

        return set(filter(_noneorzero, [x['channel'] for x in res['results']] ))



    def run_test(self):
        """ Run some basic tests """
        """
        print(f"{resp['user']}'s rank this month: {resp['statistics']['monthRank']}")
        resp = get_cell_detail("310260", "14450", "25541899")
        print(f"\n=============\n{resp}\n============")
        resp = get_cell_detail("310260", "14450", "666")
        print(f"\n=============\n{resp}\n============")
        """

        resp = self.cell_search(37.72, -122.156, 0.05, 8410908)
        print(f"\n=============\n{resp}\n============")

        resp = self.earfcn_search(37.72, -122.156, 0.05)
        print(f"\n=============\nLocal EARFCN\n{resp}\n============")

        resp = self.channel_search(37.72, -122.156, 0.05)
        print(f"\n=============\nChannel Search\n{resp}\n============")


if __name__ == "__main__":
    w = Wigle()
    w.run_test()

