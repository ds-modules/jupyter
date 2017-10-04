import requests
import os
from shapely import geometry as sg, wkt
import pandas as pd


def to_fahren(val):
    return (val - 273.15) * 9 / 5 + 32


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
