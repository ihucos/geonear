geonear
=======

Geonear makes fast geo queries on Redis possible.
Consider it pre-Beta, no unit tests yet.

>>> from redis import StrictRedis
>>> from geonear import Globe
>>> globe = Globe(StrictRedis(), geohash_precision=8)
>>> import random; random.seed('')

Populate database
>>> globe.pin('max', location='Sophienstr. 9, 10178 Berlin')
>>> globe.pin('peter', location='Sophienstr. 10, 10178 Berlin', data=['my', 'data'])
>>> globe.pin('anna', location='Sophienstr. 11, 10178 Berlin')
>>> globe.pin('mr bean', location='Sophienstr. 20, 10178 Berlin')

Simple query
>>> area = globe.near(location='Sophienstr. 10, 10178 Berlin')
>>> area
<Area containing 3 pins (e.g. 'peter'), size 9 >
>>> list(area)
['anna', 'max', 'peter']

Delete entry
>>> globe.delete('max')

>>> not 'max' in globe and not 'max' in area
True

Fetch data
>>> globe.map_with_data(area)
{'peter': [u'my', u'data'], 'anna': None}

List used geohashes
>>> area.geohashes
set(['u33dbcze', 'u33dbczm', 'u33dbczj', 'u33dbczk', 'u33dbczh', 'u33dbcz7', 'u33dbczt', 'u33dbcz5', 'u33dbczs'])

>>> globe.debug(area, 'mr bean')
image: http://maps.googleapis.com/maps/api/staticmap?size=800x600&maptype=hybrid&sensor=false&scale=2&markers=label:1|color:blue|52.52529,13.40298&path=enc:azq_ImuxpA?cAb@??bAc@?&path=enc:}xq_ImuxpA?cA`@??bAa@?&path=enc:azq_IisxpA?cAb@??bAc@?&path=enc:}xq_IisxpA?cA`@??bAa@?&path=enc:azq_IcqxpA?eAb@??dAc@?&path=enc:}xq_IcqxpA?eA`@??dAa@?&path=enc:{wq_ImuxpA?cA`@??bAa@?&path=enc:{wq_IisxpA?cA`@??bAa@?&path=enc:{wq_IcqxpA?eA`@??dAa@?&markers=label:A|52.52572,13.40075&path=fillcolor:red|weight:0|enc:g}q_IqhxpA?cA`@??bAa@? (516 chars, 2048 allowed)
<BLANKLINE>
image legend
------------
 1 | <Area containing 2 pins (e.g. 'peter'), size 9 >
 A | mr bean
------------
