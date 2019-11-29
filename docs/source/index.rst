Welcome to LineUsPythonModule's documentation!
==============================================

Line-us is an internet connected robot drawing arm. It's small, portable and draws with a nice
wobbly line using a real pen on paper. The free app lets you draw, send messages, share
sketchbooks or enjoy collecting artworks from others!

Line-us was created in London by Durrell Bishop and Robert Poll. There is a lot more
information on our website: https://www.line-us.com

If you have any questions please drop us an email: help@line-us.com of post on our forum:
https://forum.line-us.com

Quickstart
^^^^^^^^^^

It's easy to get started with the Line-us module in Python, but first make sure you are running
Python3 and have the module installed::

   $ python --version
   Python 3.7.5

   $ pip install lineus

We would recommend using a virtual environment. Pipenv is my preference but there are plenty
of options.

Begin by importing the LineUs class and creating a LineUs object::

   >>> from lineus import LineUs
   >>> my_line_us = LineUs()

The LineUs object will then immediately start listening for Line-us machines on your local
network. If you only have one you can connect to it with::

   >>> my_line_us.connect()

Which will return ``True`` if the connection was successful. Once you're connected you can
start to send commands. If you want to draw you'll be sending ``G01`` so can do something like::

   >>> my_line_us.g01(900, 300, 0)
   >>> my_line_us.g01(900, -300, 0)
   >>> my_line_us.g01(900, -300, 1000)

   >>> my_line_us.g01(1200, 300, 0)
   >>> my_line_us.g01(1200, -300, 0)
   >>> my_line_us.g01(1200, -300, 1000)

   >>> my_line_us.g01(900, 0, 0)
   >>> my_line_us.g01(1200, 0, 0)
   >>> my_line_us.g01(1200, 0, 1000)

   >>> my_line_us.g01(1500, 150, 0)
   >>> my_line_us.g01(1500, -300, 0)
   >>> my_line_us.g01(1500, -300, 1000)

   >>> my_line_us.g01(1500, 250, 0)
   >>> my_line_us.g01(1500, 300, 0)
   >>> my_line_us.g01(1500, 300, 1000)


It's a good idea to disconnect cleanly from your Line-us::

   >>> my_line_us.disconnect()

That should cover the vast majority of what you need for most uses, but there's more information
on the full API below.

Have fun!!

.. toctree::
   :maxdepth: 3
   :caption: Contents:

The LineUs class in detail
^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: lineus
    :members:
    :exclude-members: SlowSearchThread

Index and search
================

* :ref:`genindex`
* :ref:`search`
