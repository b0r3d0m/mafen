# mafen

![logo](http://www.samsmartinc.com/assets/user/upload/images/muffin.png)

**mafen** is a web-based application that helps u with various [Hafen & Hearth](http://www.havenandhearth.com/portal/) tasks.
For example, you can check your character's inventory and study any items you want. Note that you can do it from any device you have at the moment. No need to launch a full desktop H&H client at all!

![main page](http://i.imgur.com/BFGu2yB.png)

**(click me)**

## Usage

* git clone
* Install [Python 2.x](https://www.python.org/)
* Install [Node.js](https://nodejs.org/en/)

### Start service
* cd service
* pip install -r requirements.txt
* vim config.ini (optional)
* python main.py &

### Start web backend
* cd web
* npm install
* vim server/config.json (optional)
* gulp bundle-js
* node server/index.js & # consider about using [forever](https://github.com/foreverjs/forever) though

## How can I help?
* ![star](http://github-svg-buttons.herokuapp.com/star.svg?user=b0r3d0m&repo=mafen) this project!
* ![fork](http://github-svg-buttons.herokuapp.com/fork.svg?user=b0r3d0m&repo=mafen) and create pull requests with any changes you want
* Feel free to send me an email with feature requests and your feedback

## License

Copyright © 2017 b0r3d0m <b0r3d0mness@gmail.com>

Distributed under the [MIT License](LICENSE.txt).

[Background image](web/client/bg.jpg) was made by [ragxar](http://havenandhearth.ru/viewtopic.php?f=67&t=2490#p23479).
