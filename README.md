# mafen

![logo](http://www.samsmartinc.com/assets/user/upload/images/muffin.png)

mafen is a web-based application that helps u with various [Hafen & Hearth](http://www.havenandhearth.com/portal/) tasks.
For example, you can check your character's inventory and study any items you want. Note that you can do it from any device you have at the moment. No need to launch a full desktop H&H client at all!

![main page](http://i.imgur.com/BFGu2yB.png)

## Usage

* git clone
* Install [Python 2.x](https://www.python.org/)
* Install [Node.js](https://nodejs.org/en/)

### Start service
* cd service
* vim config.ini (optional)
* python main.py &

### Start web backend
* cd web
* npm install
* vim server/config.json (optional)
* gulp bundle-js
* node server/index.js

## License

Copyright © 2017 b0r3d0m <b0r3d0mness@gmail.com>
