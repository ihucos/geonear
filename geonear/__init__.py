# The MIT License (MIT)
#
# Copyright (c) 2014 Irae Hueck Costa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#
#  TODO: merge globe.data and globe.filter_data to take_data or something?
#  TODO: of course implement the "shake"
#  TODO: add namespace support, call it label?
#  TODO: find nicer method names, especially for almost_near and friends.

import hashlib
import json
import webbrowser
from random import choice

import gpolyencode
import requests

import geohash  # install with `pip install python-geohash`
from colornames import colornames

PROJECT_URL = 'http://github.com/ihuecos/geonear'


def hash_iter(args):
    '''
    >>> hash_iter(('cake', 'cheese'))
    'b69691f4abf463d3f6efe74e9a178cc491a1b1ad'
    >>> hash_iter(('ca', 'kecheese'))
    'dea7019737074c692531be734b32116808e712fd'
    '''
    master_hash = hashlib.new('ripemd160')
    for arg in args:
        h = hashlib.new('sha256')
        h.update(arg)
        arg_hash = h.hexdigest()
        master_hash.update(arg_hash)
    return master_hash.hexdigest()


def geohash_and_neighbors(gh, neighbors_deepth=1):
    '''
    >>> geohash_and_neighbors('bg4r', neighbors_deepth=0)
    set(['bg4r'])
    >>> sorted(geohash_and_neighbors('bg4r'))
    ['bg4n', 'bg4p', 'bg4q', 'bg4r', 'bg4w', 'bg4x', 'bg60', 'bg62', 'bg68']
    >>> sorted(geohash_and_neighbors('bg4r', neighbors_deepth=2))
    ['bg1v', 'bg1y', 'bg1z', 'bg3b', 'bg3c', 'bg4j', 'bg4m', 'bg4n', 'bg4p', 'bg4q', 'bg4r', 'bg4t', 'bg4v', 'bg4w', 'bg4x', 'bg4y', 'bg4z', 'bg60', 'bg61', 'bg62', 'bg63', 'bg68', 'bg69', 'bg6b', 'bg6c']

    '''

    # some neighbors are calculated repeatedly, that's ok for performance
    ghs = set([gh])
    for i in range(neighbors_deepth):
        for gh in tuple(ghs):  # tuple because we want to copy ghs
            ghs.update(geohash.expand(gh))
    return ghs


def hscan(redis, *args, **kw):
    cursor = 0
    while True:
        cursor, results = redis.hscan(*args, cursor=cursor, **kw)
        for key, val in results.items():
            yield key, val
        if not int(cursor):  # int because cursor is returned as string
            break


class NominatimGeocode(object):
    def __init__(self,
                 search_endpoint=None,
                 reverse_endpoint=None,
                 mail=None):
        self._search_endpoint = (search_endpoint or
                                 'http://nominatim.openstreetmap.org/search')
        self._reverse_endpoint = (reverse_endpoint or
                                  'http://nominatim.openstreetmap.org/reverse')
        self._mail = mail or ''
        self._headers = {'User-Agent':
                         'Geonear pre-Beta ({})'.format(PROJECT_URL)}

    def geocode(self, query):
        result = requests.get(self._search_endpoint,
                              params={
                                  'q': query, 'email': self._mail,
                                  'limit': 1, 'format': 'json'},
                              headers=self._headers
                              ).json()
        if not result:
            raise ValueError('no geocode result found for {}'.format(query))
        return (float(result[0]['lat']), float(result[0]['lon']))

    def reverse_geocode(self, (lat, lon)):
        result = requests.get(self._reverse_endpoint,
                              params={
                                  'lat': lat, 'lon': lon, 'email': self._mail,
                                  'addressdetails': 0, 'format': 'json'},
                              headers=self._headers).json()
        if result.get(u'error') == u'Unable to geocode':
            raise ValueError('cannot geocode {}'.format((lat, lon)))
        return result['display_name']


class Globe(object):
    '''
    >>> import redis
    >>> r = redis.StrictRedis()
    >>> r.flushdb() # FIXME: WILL ERASE WHOLE DATABASE (OMG!!)
    True
    >>> globe = Globe(r, geohash_precision=8)
    >>> globe.pin('user1', location='Sophienstr. 9, 10178 Berlin')
    >>> globe.pin('user2', location='Sophienstr. 11, 10178 Berlin')
    >>> globe.near(location='Sophienstr. 10, 10178 Berlin')
    set(['user2', 'user1'])
    >>> 'user1' in globe
    True
    >>> globe.delete('user1')
    >>> globe.near(who='user2')
    set(['user2'])
    >>> globe.distance(who='user1')(location='New York')
    1234
    '''

    def __init__(self, redis, geohash_precision,
                 cache_geocoding=20,  # FIXME: XXX seems not to be working!!!
                 nominatim_search_endpoint=None,
                 nominatim_reverse_endpoint=None,
                 nominatim_mail=None,
                 namespace='',
                 data_serialize=json.dumps,
                 data_deserialize=json.loads):

        self._redis = redis
        self._geohash_precision = geohash_precision
        self._cache_geocoding = cache_geocoding
        self._nominatim = NominatimGeocode(
            mail=nominatim_mail,
            search_endpoint=nominatim_search_endpoint,
            reverse_endpoint=nominatim_reverse_endpoint)
        self._key_prefix = 'globe:{}:'.format(namespace)
        self._data_serialize = data_serialize
        self._data_deserialize = data_deserialize

        self._add_or_move_pin_script = redis.register_script('''
            local key_prefix = ARGV[1]   -- prepend this to all keys
            local pin_id = ARGV[2]       -- the pin that will be added or moved
            local new_pin_gh = ARGV[3]   -- where this pin should be pinned
            local pin_data = ARGV[4] -- which data should be saved for this pin

            -- get the current pin location
            local pin_gh = redis.call('hget', key_prefix..'pins', pin_id)

            -- set pin data if requested
            if pin_data then
                redis.call('hset', key_prefix..'data', pin_id, pin_data)
            end

            -- if this pin has an location in our redis database
            if pin_gh then
                redis.call(
                    'smove', -- move this pin
                    key_prefix..'gh:'..pin_gh,     -- from his current geohash
                    key_prefix..'gh:'..new_pin_gh, -- to the requested geohash
                    pin_id)
            else
                -- or if it is not known yet add it to the database
                redis.call('sadd', key_prefix.."gh:"..new_pin_gh, pin_id)
            end
            -- update this pin location at the central index
            redis.call('hset', key_prefix..'pins', pin_id, new_pin_gh)''')

        self._delete_pin_script = redis.register_script('''
            local key_prefix = ARGV[1] -- prepend this to all keys
            local pin_id = ARGV[2]

            local pin_gh = redis.call('hget', key_prefix..'pins', pin_id)
            if pin_gh then
                redis.call('hdel', key_prefix..'pins', pin_id)
                redis.call('hdel', key_prefix..'data', pin_id) -- delete data if any
                redis.call('srem', key_prefix..'gh:'..pin_gh, pin_id)
            end
            return pin_gh''')

    def pin(self, pin_id, **kws):
        # TODO: also allow setting data
        gh = self._kws2geohash(kws)
        pin_data = kws.get('data')
        if pin_data:
            args = [self._key_prefix, pin_id, gh,
                    self._data_serialize(pin_data)]
        else:
            args = [self._key_prefix, pin_id, gh]
        self._add_or_move_pin_script(args=args)

    def make_area(self, geohashes):
        return Area(self._redis, geohashes, key_prefix=self._key_prefix)

    def near(self, size=1, **kws):
        gh = self._kws2geohash(kws)
        geohashes = geohash_and_neighbors(gh, size)
        return self.make_area(geohashes)

    def almost_near(self, **kws):
        return self.near(2, **kws)

    def almost_almost_near(self, **kws):
        return self.near(3, **kws)

    def almost_almost_almost_near(self, **kws):
        return self.near(4, **kws)

    def filter_data(self, pin_ids):
        pin_ids = tuple(pin_ids)
        if not pin_ids:
            return ()
        return (self._data_deserialize(data) for data in
                self._redis.hmget(self._key_prefix + 'data', *pin_ids)
                if data is not None)

    def map_with_data(self, pin_ids):
        pin_ids = tuple(pin_ids)
        if not pin_ids:
            return ()
        pin_datas = self._redis.hmget(self._key_prefix + 'data', *pin_ids)
        return dict(zip(pin_ids,
                        ((self._data_deserialize(data)
                          if data is not None else None)
                         for data in pin_datas)))

    def delete(self, pin_id):
        # TODO: can also delete a Area object and a list of pin ids
        success = self._delete_pin_script(args=[self._key_prefix, pin_id])
        if not success:
            raise ValueError('pin {} not found'.format(pin_id))

    def __contains__(self, pin_id):
        return bool(self._redis.hexists(self._key_prefix + "pins", pin_id))

    def __len__(self):
        return self._redis.hlen(self._key_prefix + 'pins')

    def geohash_scan(self, buffer=50):
        return hscan(self._redis, self._key_prefix + 'pins', count=buffer)

    def latlon_scan(self, buffer=50):
        return ((pin, geohash.decode(gh))
                for pin, gh in self.geohash_scan(buffer))

    def bbox_scan(self, buffer=50):
        return ((pin, geohash.bbox(gh))
                for pin, gh in self.geohash_scan(buffer))

    def data_scan(self, buffer=50):
        return ((pin_id, self._deserialize_data(data)) for pin_id, data
                in hscan(self._redis, self._key_prefix + 'data', count=buffer))

    def scan(self, buffer=50):
        return (pin for pin, gh in self.geohash_scan(buffer))

    def latlon(self, pin_id):
        gh = self.geohash(pin_id)
        return geohash.decode(gh)

    def geohash(self, pin_id):
        gh = self._redis.hget(self._key_prefix + 'pins', pin_id)
        if not gh:
            raise ValueError('no such pin_id')
        return gh

    def bbox(self, pin_id):
        # is this method a good idea?
        gh = self.geohash(pin_id)
        return geohash.bbox(gh)

    def data(self, pin_id):
        # check if pin_id exists?
        return self._redis.hget(self._key_prefix + 'data', pin_id)

    def distance(self, **kws):
        # def calculate_distance(**other_kws):
        #     from geopy.distance import great_circle
        raise NotImplementedError()
        # return calculate_distance

    def _kws2geohash(self, kws):

        if 'latlon' in kws:
            return geohash.encode(kws['latlon'],
                                  precision=self._geohash_precision)

        elif 'location' in kws:

            cache_geocoding = (
                kws['cache_geocoding'] if 'cache_geocoding' in kws
                else self._cache_geocoding)

            # take geohash from cache if geocoding caching is enabled
            if cache_geocoding:
                cache_key = hash_iter(('geocoding',
                                       'google',
                                       str(self._geohash_precision),
                                       kws['location']))
                gh = self._redis.get(cache_key)
                if gh:
                    return gh

            # geocode the location to a geohash
            lat, lon = self._nominatim.geocode(kws['location'])
            gh = geohash.encode(lat, lon,
                                precision=self._geohash_precision)

            # if cache the geolocated location
            if cache_geocoding:
                self._redis.setex(cache_key, self._cache_geocoding, gh)

            return gh

        elif 'geohash' in kws:
            return geohash.encode(*geohash.decode(kws['geohash']),
                                  precision=self._geohash_precision)

        elif 'who' in kws:
            return self.geohash(kws['who'])

        else:
            raise ValueError('needs one location specificaton')

    def debug(self, items,
              size=(800, 600), return_only=False, maptype="hybrid"):

            if maptype not in ('roadmap', 'satellite', 'hybrid', 'terrain'):
                raise TypeError('maptype not supported')

            polyenc = gpolyencode.GPolyEncoder()
            url = 'http://maps.googleapis.com/maps/api/staticmap?'
            url += 'size={}x{}&maptype={}&sensor=false&scale=2'.format(
                size[0], size[1], maptype)

            for (color_name, color_hex), item in zip(colornames, items):


                if isinstance(item, Area):
                    polygons = item.get_polygons()
                    for points in polygons:
                        p = polyenc.encode([(p[1], p[0]) for p in points])
                        polyline_encoded = p['points']
                        url += '&path=fillcolor:0x{}|weight:0|enc:{}'.format(
                            color_hex[1:], polyline_encoded)
                    print "{}: {}".format(item, color_name)

                elif isinstance(item, basestring):
                    gh = self.geohash(item)
                    if gh:
                        bbox = geohash.bbox(gh)
                        points = [(bbox['n'], bbox['w']),
                                  (bbox['n'], bbox['e']),
                                  (bbox['s'], bbox['e']),
                                  (bbox['s'], bbox['w']),
                                  (bbox['n'], bbox['w'])]
                        p = polyenc.encode([(p[1], p[0]) for p in points])
                        polyline_encoded = p['points']
                        url += '&path=color:0x{}|enc:{}'.format(
                            color_hex[1:], polyline_encoded)
                    print "{}: {}".format(item, color_name)

                else:
                    raise TypeError()

            webbrowser.open_new_tab(url)

    def __repr__(self):
        return '<Globe with {} pins at {}>'.format(len(self), hex(id(self)))


class Area(object):
    def __init__(self, redis, geohashes, key_prefix):
        self._geohashes = geohashes
        self._redis = redis
        self._key_prefix = key_prefix

    def __iter__(self):
        pin_ids = self._redis.sunion(
            *(self._key_prefix + "gh:" + gh for gh in self.geohashes))
        return iter(sorted(pin_ids))  # sorted makes the results more consistent

    def __len__(self):
        pipe = self._redis.pipeline()
        for gh in self.geohashes:
            pipe.scard(self._key_prefix + 'gh:' + gh)
        return sum(pipe.execute())

    def __include__(self, pin_id):
        pipe = self._redis.pipeline()
        for gh in self.geohashes:
            pipe.sismember(self._key_prefix + 'gh:' + gh, pin_id)
        return any(pipe.execute())

    def __and__(self, other):
        if not isinstance(other, Area):
            raise TypeError('other must also be a Area')
        return Area(self._redis,
                    self.geohashes.intersection(other.geohashes),
                    key_prefix=self._key_prefix)

    def __or__(self, other):
        if not isinstance(other, Area):
            raise TypeError('other must also be a Area')
        return Area(self._redis,
                    self.geohashes.union(other.geohashes),
                    key_prefix=self._key_prefix)

    def __eq__(self, other):
        if not isinstance(other, Area):
            return False
        return self.geohashes == other.geohashes

    def __repr__(self):
        pins = tuple(self)
        if pins:
            more = ' (e.g. {})'.format(repr(choice(pins)))
        else:
            more = ''
        return '<Area containing {} pins{}, size {} >'.format(
            len(self), more, len(self.geohashes))

    @property
    def geohashes(self):
        return self._geohashes

    @property
    def bboxes(self):
        return tuple(geohash.bbox(gh) for gh in self.geohashes)

    def _get_named_neighbors(self, gh):
        ghs = {}
        gh_bbox = geohash.bbox(gh)
        for g in geohash.expand(gh):
            if gh == g:
                continue
            b = geohash.bbox(g)

            if gh_bbox['n'] == b['n'] and gh_bbox['w'] == b["e"]:
                ghs['L'] = g
            elif gh_bbox['n'] == b['n'] and gh_bbox['e'] == b["w"]:
                ghs['R'] = g

            elif gh_bbox['e'] == b['e'] and gh_bbox['n'] == b["s"]:
                ghs['U'] = g
            elif gh_bbox['e'] == b['e'] and gh_bbox['s'] == b["n"]:
                ghs['D'] = g

            elif gh_bbox['n'] == b['s'] and gh_bbox['w'] == b['e']:
                ghs['LU'] = g
            elif gh_bbox['n'] == b['s'] and gh_bbox['e'] == b['w']:
                ghs['RU'] = g

            elif gh_bbox['s'] == b['n'] and gh_bbox['w'] == b['e']:
                ghs['LD'] = g
            elif gh_bbox['s'] == b['n'] and gh_bbox['e'] == b['w']:
                ghs['RD'] = g

        return ghs

    def get_edge_points(self):

        # search for edges
        edge_points = []
        edge_detection = [
            dict(empty='LU', notempty='', edge=('n', 'w')),
            dict(empty='RU', notempty='', edge=('n', 'e')),
            dict(empty='LD', notempty='', edge=('s', 'w')),
            dict(empty='RD', notempty='', edge=('s', 'e')),
            dict(empty=('LU',), notempty='LU', edge=('n', 'w')),
            dict(empty=('RU',), notempty='RU', edge=('n', 'e')),
            dict(empty=('LD',), notempty='LD', edge=('s', 'w')),
            dict(empty=('RD',), notempty='RD', edge=('s', 'e')),
        ]

        for gh in self.geohashes:
            neighbors = self._get_named_neighbors(gh)

            for detect in edge_detection:
                empty_passes = all(neighbors[direction] not in self.geohashes
                                   for direction in detect['empty'])
                notempty_passes = all(neighbors[direction] in self.geohashes
                                      for direction in detect['notempty'])

                if empty_passes and notempty_passes:
                    x_name, y_name = detect['edge']
                    b = geohash.bbox(gh)
                    edge_points.append((b[x_name], b[y_name]))

        return edge_points

    def get_polygons(self):

        # search for edges
        edge_lines = []
        edge_detection = [
            ('U', (('n', 'w'), ('n', 'e'))),
            ('D', (('s', 'w'), ('s', 'e'))),
            ('L', (('n', 'w'), ('s', 'w'))),
            ('R', (('n', 'e'), ('s', 'e'))),
        ]

        for gh in self.geohashes:
            neighbors = self._get_named_neighbors(gh)

            for empty, ((x1_name, y1_name),
                        (x2_name, y2_name)) in edge_detection:
                if neighbors[empty] not in self.geohashes:
                    b = geohash.bbox(gh)
                    edge_lines.append(((b[x1_name], b[y1_name]),
                                       (b[x2_name], b[y2_name])))

        # merge all the lines to one path
        lines = list(edge_lines)
        while True:
            break_ = False
            found = False
            for (from_point1, to_point1) in lines:
                if break_:
                    break
                for (from_point2, to_point2) in lines:
                    if break_:
                        break
                    if (from_point1, to_point1) == (from_point2, to_point2):
                        continue
                    if to_point1 == from_point2 and (
                            from_point1[0] == to_point2[0]
                            or from_point1[1] == to_point2[1]):
                        new = (from_point1, to_point2)
                        remove1 = (from_point1, to_point1)
                        remove2 = (from_point2, to_point2)
                        break_ = True
                        found = True
            if not found:
                break
            lines.remove(remove1)
            lines.remove(remove2)
            lines.append(new)

        def get_next_line(all_lines, p):
            for (p1, p2) in all_lines:
                if p == p1:
                    all_lines.remove((p1, p2))
                    return p2
                if p == p2:
                    all_lines.remove((p1, p2))
                    return p1
            raise ValueError('no next line found')

        polygons = []
        while True:
            polygon_points = []
            try:
                # choose any point to begin with
                next_point = lines[0][0]
            except IndexError:
                break

            # aggregate all polygons
            while True:

                # find next point
                found = False
                for (p1, p2) in lines:
                    if next_point == p1:
                        lines.remove((p1, p2))
                        next_point = p2
                        found = True
                        break
                    if next_point == p2:
                        lines.remove((p1, p2))
                        next_point = p1
                        found = True
                        break
                if not found:
                    break

                polygon_points.append(next_point)

            # "close the circle"
            polygon_points.append(polygon_points[0])

            polygons.append(polygon_points)

        return polygons
