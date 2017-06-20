=====
FidusWriter-OJS
=====

FidusWriter-OJS is a Fidus writer plugin to connect a Fidus Writer instance
with Open Journal Systems (OJS).
This plugin has to be combined with the `OJS-FidusWriter plugin <https://github.com/fiduswriter/ojs-fiduswriter>`_ for OJS.



Installation
-----------

1. Install Fidus Writer if you haven't done so already.

2. Within the virtual environment set up for your Fidus Writer instance,
   running::

    pip install fiduswriter-ojs

3. Add "ojs" to your INSTALLED_APPS setting in the configuration.py file
   like this::

    INSTALLED_APPS += (
        ...
        'ojs',
    )


4. Run this to create the models::

    python manage.py migrate

5. Create the needed JavaScript files by running this::

    python manage.py transpile

6. (Re)start your Fidus Writer server.

7. Following the install instructions of the `OJS-FidusWriter plugin <https://github.com/fiduswriter/ojs-fiduswriter>`_ to connect
   the two plugins with each other.


Credits
-----------

This plugin has been developed by the `Opening Scholarly Communications in the Social Sciences (OSCOSS) <http://www.gesis.org/?id=10714>`_ project, financed by the German Research Foundation (DFG) and executed by the University of Bonn and GESIS – Leibniz Institute for the Social Sciences. 

Lead Developers: `Fakhri Momeni <https://github.com/momenifi>`_ and `Johannes Wilm <https://github.com/johanneswilm>`_
