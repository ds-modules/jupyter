import requests
import os
from shapely import geometry as sg, wkt
import pandas as pd
import random


def to_fahren(val):
    return (val - 273.15) * 9 / 5 + 32


def gen_hex_colour_code():
    return ''.join([random.choice('0123456789ABCDEF')
                    for x in range(6)])  # Make a random string with the letters
    # in the string '0123456789ABCDEF'.


def assign_colors(records_df, col_name):
    color_dict = {}
    for i, c in enumerate(list(set(records_df[col_name]))):
        # We map an institute to a different random color.
        color_dict[c] = "#" + gen_hex_colour_code()
    color_dict
    base_html = '''<tbody><tr>
    <th style="width:25%">Collection</th>
    <th style="width:15%">HEX</th>
    <th style="width:43%">Color</th>
    </tr>
    '''

    add_template = '''
    <tr>
    <td>COLLECTION&nbsp;</td>
    <td>HEX</td>
    <td style="background-color:HEX">&nbsp;</td>
    </tr>
    </tbody>
    '''

    to_render = base_html

    for k in color_dict.keys():
        if isinstance(k, str):
            to_render += add_template.replace(
                'COLLECTION', k).replace(
                'HEX', color_dict[k])

    to_render += '</tbody>'
    to_render = to_render.replace('Collection', col_name)

    return (color_dict, to_render)


class CalAdaptRequest(object):
    series_url = 'http://api.cal-adapt.org/api/series/'

    def __init__(self, slug=None):
        self.slug = slug or 'tasmax_year_CanESM2_rcp85'
        self.params = {'pagesize': 94}

    def concat_features(self, features, field='id'):
        lst = []
        for feat in features:
            json = self.series(geom=feat['geometry'])
            series = self.to_frame(json)['image']
            if series.any():
                series.name = feat[field]
                lst.append(series)
        return pd.concat(lst, axis=1)

    def list_series_slugs(self):
        json = requests.get(self.series_url, params=self.params).json()
        return [row['slug'] for row in json['results']]

    def series(self, geom=None):
        url = '%s%s/rasters/' % (self.series_url, self.slug)
        if geom:
            params = dict(self.params, g=geom.wkt)
            if isinstance(geom, (sg.Polygon, sg.MultiPolygon)):
                params['stat'] = 'mean'
        return requests.get(url, params=params).json()

    def series(self, geom=None, dates=None):
        if dates:
            url = os.path.join(self.series_url, self.slug, *dates)
        else:
            url = os.path.join(self.series_url, self.slug, 'rasters/')
        if geom:
            params = dict(self.params, g=geom.wkt)
            if isinstance(geom, (sg.Polygon, sg.MultiPolygon)):
                params['stat'] = 'mean'
        return requests.get(url, params=params).json()

    def to_frame(self, json):
        df = pd.DataFrame.from_records(json['results'])
        df['image'] = to_fahren(pd.to_numeric(df['image']))
        df['event'] = pd.to_datetime(df['event'], format='%Y-%m-%d')
        df.set_index('event', inplace=True)
        return df.dropna()


class GBIFRequest(object):
    """GBIF requests with pagination handling."""

    url = 'http://api.gbif.org/v1/occurrence/search'

    def fetch(self, params):
        resp = requests.get(self.url, params=params)
        return resp.json()

    def get_pages(self, params, thresh=500):
        params = dict({'limit': 100, 'offset': 0}, **params)
        data = {'endOfRecords': False}
        while not data['endOfRecords']:
            data = self.fetch(params)
            params['offset'] += params['limit']
            if params['offset'] > thresh:
                break
            yield data


class EcoEngineRequest(object):
    """EcoEngine requests with pagination handling."""

    url = 'https://ecoengine.berkeley.edu/api/checklists/?format=json'

    def fetch(self, params):
        resp = requests.get(self.url, params=params)
        return resp.json()

    def get_checklists(self, params, thresh=500):
        data = {"next": True}
        checklists = []
        while data["next"]:
            data = self.fetch(params)
            checklists.extend(data['results'])
        return checklists

    def get_scientific_names_from_checklists(self, params, checklists=False):

        checklists = self.get_checklists(params)
        urls = [
            r['url'] +
            "?format=json" for r in checklists if "sagehen" in r['footprint']]

        scientific_names = []

        for u in urls:
            res = requests.get(u).json()
            obs = [o['scientific_name'] for o in res['observations']]
            scientific_names.extend(obs)

        return scientific_names
