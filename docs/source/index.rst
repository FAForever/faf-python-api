.. Forged Alliance API Project documentation master file, created by
   sphinx-quickstart on Mon Feb 22 20:44:46 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Forged Alliance API Project's documentation!
=======================================================

The Forged Alliance Forever API exposes some of the internal resources that are being used in the system. Some examples are player
statistics, overall rankings, games, achievements, and etc... Those are just a few of the many things that are accessible
when using the API. All of these resources can be accessed through the normal PHP channels of GET, POST, PUT, and DELETE.
The API is organized around REST. We have attempted to make the API easy to use while maintaining modern practices. JSON is
returned on every response and attempts to follow the standards as documented on http://jsonapi.org.

Accessing the resources in the API follow a similar trend. A list of resources can be typically found by /resource-name and
an individual resource can be typically found by /resource-name/{id}.

The API endpoint can be found here:

   http://api.faforever.com

Accessing public resources can be as easy as

   curl http://api.faforever.com/ranked1v1

Although, some endpoints do require that you are logged in.

..
   .. toctree::
   :maxdepth: 2

.. toctree::
   :maxdepth: 2

   api
   models
   modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

