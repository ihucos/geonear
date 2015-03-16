.. geonear documentation master file, created by
   sphinx-quickstart on Tue Mar  3 15:07:00 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to geonear's documentation!
===================================

Contents:


Initiate our globe
   >>> r = redis.StrictRedis()
   >>> globe = geonear.Globe(r, geohash_precision=8)

Add some Pins
   >>> globe.pin('u1', location="Franzoesische Strasse 14, Berlin")
   >>> globe.pin('u2', location="Franzoesische Strasse 53, Berlin")
   >>> globe.pin('u3', location="Franzoesische Strasse 18, Berlin")

   >>> globe.debug(['u1', 'u2', 'u3'])
.. image:: http://maps.googleapis.com/maps/api/staticmap?size=800x600&maptype=hybrid&sensor=false&scale=2&markers=label:A|52.51456,13.3877&path=fillcolor:red|weight:0|enc:owo_I_wupA?eA%60@??dAa@?&markers=label:B|52.51473,13.38804&path=fillcolor:red|weight:0|enc:sxo_IeyupA?cAb@??bAc@?&markers=label:C|52.51456,13.38907&path=fillcolor:red|weight:0|enc:owo_Is_vpA?cA%60@??bAa@?
   :width: 50%

Make a geoquery.
   >>> area = globe.almost_near(location="Franzoesische Strasse 12, Berlin")
   >>> print area
   <Area containing 2 pins (e.g. 'u2'), size 25 >
   >>> list(area) #  lazy evaluation
   ['u1', 'u2']
   >>> globe.debug(['u1', 'u2', 'u3', area])
.. image:: http://maps.googleapis.com/maps/api/staticmap?size=800x600&maptype=hybrid&sensor=false&scale=2&markers=label:1|color:blue|52.51499,13.38821&path=enc:uyo_IeyupA?cA%60@??bAa@?&path=enc:sxo_IeyupA?cAb@??bAc@?&path=enc:uyo_I_wupA?eA%60@??dAa@?&path=enc:sxo_I_wupA?eAb@??dAc@?&path=enc:uyo_I{tupA?cA%60@??bAa@?&path=enc:sxo_I{tupA?cAb@??bAc@?&path=enc:uyo_IwrupA?cA%60@??bAa@?&path=enc:sxo_IwrupA?cAb@??bAc@?&path=enc:uyo_IqpupA?eA%60@??dAa@?&path=enc:sxo_IqpupA?eAb@??dAc@?&path=enc:owo_IeyupA?cA%60@??bAa@?&path=enc:mvo_IeyupA?cA%60@??bAa@?&path=enc:owo_I_wupA?eA%60@??dAa@?&path=enc:mvo_I_wupA?eA%60@??dAa@?&path=enc:kuo_IeyupA?cA%60@??bAa@?&path=enc:kuo_I_wupA?eA%60@??dAa@?&path=enc:owo_I{tupA?cA%60@??bAa@?&path=enc:mvo_I{tupA?cA%60@??bAa@?&path=enc:owo_IwrupA?cA%60@??bAa@?&path=enc:mvo_IwrupA?cA%60@??bAa@?&path=enc:kuo_I{tupA?cA%60@??bAa@?&path=enc:kuo_IwrupA?cA%60@??bAa@?&path=enc:owo_IqpupA?eA%60@??dAa@?&path=enc:mvo_IqpupA?eA%60@??dAa@?&path=enc:kuo_IqpupA?eA%60@??dAa@?&markers=label:A|52.51456,13.3877&path=fillcolor:red|weight:0|enc:owo_I_wupA?eA%60@??dAa@?&markers=label:B|52.51473,13.38804&path=fillcolor:red|weight:0|enc:sxo_IeyupA?cAb@??bAc@?&markers=label:C|52.51456,13.38907&path=fillcolor:red|weight:0|enc:owo_Is_vpA?cA%60@??bAa@?
   :width: 50% 


.. toctree::
   :maxdepth: 2

.. automodule:: geonear
   :members: Globe, Area
    


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

