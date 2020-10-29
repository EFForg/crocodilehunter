import base64
import configparser
import datetime
from functools import lru_cache
import hashlib
import json
from pprint import pprint
import requests

from access_points import get_scanner
from database import OcidCellCache

config_fp = 'config.ini'
config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
config.read(config_fp)
expire_offset = int(config['general']['ocid_cache_len'])

def ocid_get_location(api_key):
    url = "https://us1.unwiredlabs.com/v2/process.php"
    wifi_scanner = get_scanner()
    aps = wifi_scanner.get_access_points()
    aps = [{'bssid': ap.bssid, 'signal': ap.quality*-1} for ap in aps]

    payload = {
        'token': api_key,
        'address': 0,
        'wifi': aps
    }
    response = requests.request("POST", url, json=payload)

    return response.json()

def ocid_check_cell_search_cache(db_session, mcc, mnc, lac, cid):
    hit = None
    hasher = hashlib.sha256()
    hash_key = f'{mcc}-{mnc}-{lac}-{cid}'
    hasher.update(hash_key.encode("utf-8"))
    cell_hash = hasher.hexdigest()
    # I guess this is how we get SQL Alchemy to give us entries as dictionaries?
    hits = db_session.query(OcidCellCache).filter(OcidCellCache.cell_hash == cell_hash).all()
    if hits:
        hit = hits[0].to_dict()
        if int(datetime.datetime.utcnow().timestamp()) >= int(hit['expires']):
            hit = None
            db_session.query(OcidCellCache).filter(OcidCellCache.cell_hash==cell_hash).delete()
            db_session.commit()
    return hit

def ocid_clean_cell_search_cache(db_session):
    # I guess this is how we get SQL Alchemy to give us entries as dictionaries?
    cache_entries = db_session.query(OcidCellCache).all()

    if cache_entries:
        for entry in cache_entries:
            entry_dict = entry.to_dict()
            if int(datetime.datetime.utcnow().timestamp()) >= int(entry_dict['expires']):
                db_session.query(OcidCellCache).filter(
                    OcidCellCache.cell_hash==entry_dict['cell_hash']).delete()
                db_session.commit()

def ocid_search_cell(db_session, api_key, mcc, mnc, lac, cid):
    response_text = None
    cache_check = ocid_check_cell_search_cache(db_session, mcc, mnc, lac, cid)
    if cache_check is None:
        url = "http://opencellid.org/cell/get"
        payload = {
            "key": api_key,
            "mcc": mcc,
            "mnc": mnc,
            "lac": lac,
            "cellid": cid,
            "radio": "LTE",
            "format": "json"
        }
        response = requests.request("GET", url, params=payload)
        expires = datetime.datetime.utcnow() + datetime.timedelta(0, expire_offset)
        expires = expires.timestamp()
        response_json = response.json()
        ocid_update_cell_search_cache(db_session, mcc, mnc, lac, cid, response.text, expires)
    else:
        response_json = json.loads(cache_check['response'])
    return response_json

def ocid_update_cell_search_cache(db_session, mcc, mnc, lac, cid, response, expires):
    hasher = hashlib.sha256()
    hash_key = f'{mcc}-{mnc}-{lac}-{cid}'
    hasher.update(hash_key.encode("utf-8"))
    cell_hash = hasher.hexdigest()
    cache_entry = OcidCellCache(
        cell_hash = cell_hash,
        expires = expires,
        response = response.encode("utf-8")
    )
    db_session.add(cache_entry)
    db_session.commit()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("ocid.py <api_key>")
        sys.exit(1)
    api_key = sys.argv[1]
    mcc = 310
    mnc = 410
    lac = 35634
    cid = 170003605
    print(ocid_get_location(api_key))
    print(ocid_search_cell(api_key,mcc,mnc,lac,cid))
