=====
FidusWriter-OJS
=====

FidusWriter-OJS is a Fidus writer plugin to connect a Fidus Writer instance 
with Open Journal Systems (OJS). 
This plugin has to be combined with the Fidus Writer plugin for OJS.



Quick start
-----------

1. Install Fidus Writer if you haven't done so already.

2. Within the virtual environment set up for your Fidus Writer instance,
   running `pip install fiduswriter-ojs`

3. Add "ojs" to your INSTALLED_APPS setting in the configuration.py file 
   like this::

    INSTALLED_APPS = [
        ...
        'ojs',
    ]


4. Run `python manage.py migrate` to create the polls models.

5. Run `python manage.py transpile` to create the needed JavaScript files.

6. (Re)start your Fidus Writer server

7. Following the install instructions of the Fidus Writer plugin to connect 
   the two plugins with each other.
