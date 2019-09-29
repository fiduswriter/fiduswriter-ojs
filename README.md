FidusWriter-OJS
=====

FidusWriter-OJS is a Fidus writer plugin to connect a Fidus Writer instance
with Open Journal Systems (OJS).
This plugin has to be combined with the `OJS-FidusWriter plugin <https://github.com/fiduswriter/ojs-fiduswriter>`_ for OJS.


NOTE
----

Installation
------------

1. Within a Python virtual environment, install Fidus Writer with the plugin like this:

    pip install fiduswriter[ojs]

2. Create a Fidus Writer project in the current folder by running:

    fiduswriter startproject

3. There will now be a configuration.py file in the current folder. Add "ojs" to your INSTALLED_APPS setting in the configuration.py file
   like this::

    INSTALLED_APPS += (
        ...
        'ojs',
    )


4. Run Fidus Writer::

    fiduswriter runserver

5. Following the install instructions of the `OJS-FidusWriter plugin <https://github.com/fiduswriter/ojs-fiduswriter>`_ to connect
   the two plugins with each other.


Credits
-----------

This plugin has been developed by the `Opening Scholarly Communications in the Social Sciences (OSCOSS) <http://www.gesis.org/?id=10714>`_ project, financed by the German Research Foundation (DFG) and executed by the University of Bonn and GESIS – Leibniz Institute for the Social Sciences.

Original Developers: `Fakhri Momeni <https://github.com/momenifi>`_ and `Johannes Wilm <https://github.com/johanneswilm>`_
