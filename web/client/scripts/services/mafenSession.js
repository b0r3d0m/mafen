'use strict';

var jsSHA256 = require('js-sha256/build/sha256.min.js');
var v = require('voca');

var messageActions = require('./messageActions');

angular.module('app').service('mafenSession', function($rootScope, $timeout, $q, CODES) {
  'ngInject';

  var that = this;
  messageActions.init($rootScope);

  this.reset = function() {
    that.loginDeferred = $q.defer();
    that.loggedIn = false;
    that.characters = [];
    that.items = [];
    that.meters = {};
    that.attrs = {};
    that.chats = [];
    that.msgs = {};
    that.players = [];
    that.buddies = {};
    that.callbacks = {};
    that.lastrep = 0;
    that.kins = {};
    that.pmembers = [];
    that.lores = {};
    that.pwaiting = false;
    that.activeChatId = undefined;

    return that;
  };

  var onmessage = function(message) {
    console.log(message.data);

    var msg = JSON.parse(message.data);

    if (messageActions[msg.action] === undefined) {
      console.error("Unknown action received: " + msg.action);
      return;
    }

    messageActions[msg.action](that, msg);

    var cb = that.callbacks[msg.action];
    if (cb) {
      cb(msg);
    }

    $rootScope.$apply();
  };

  this.waitForConnection = function(callback, interval) {
    if (that.ws.readyState === 1) { // OPEN
      callback();
    } else {
      $timeout(function() {
        that.waitForConnection(callback, interval);
      }, interval);
    }
  };

  this.connect = function(addr) {
    that.ws = new WebSocket(addr);
    that.ws.onmessage = onmessage;
    return that;
  };

  this.wsOnClose = function(onclose) {
    if (that.ws !== undefined && typeof(onclose) === "function") {
      that.ws.onclose = onclose;
    }
    return that;
  };

  this.login = function(username, password) {
    that.send({
      action: 'connect',
      data: {
        username: username,
        password: jsSHA256.sha256(password)
      }
    });
    return that.loginDeferred.promise;
  };

  this.send = function(data) {
    // To avoid "Error: Failed to execute 'send' on 'WebSocket': Still in CONNECTING state"
    that.waitForConnection(function() {
      that.ws.send(JSON.stringify(data));
    }, 1000);
  };

  this.close = function() {
    that.ws.close(CODES.wsClosedByUser);
  };

  this.getTotalMW = function() {
    var total = 0;
    for (var i = 0; i < that.items.length; ++i) {
      var item = that.items[i];
      if (item.info.curio && item.study) {
        total += item.info.mw;
      }
    }
    return total;
  };

  this.getTotalExpCost = function() {
    var total = 0;
    for (var i = 0; i < that.items.length; ++i) {
      var item = that.items[i];
      if (item.info.curio && item.study) {
        total += item.info.enc;
      }
    }
    return total;
  };

  this.getTotalLPHour = function() {
    var total = 0;
    for (var i = 0; i < that.items.length; ++i) {
      var item = that.items[i];
      if (item.info.curio && item.study) {
        total += item.info.exp / (item.info.time / 60);
      }
    }
    return total;
  };

  this.getTotalLP = function() {
    var total = 0;
    for (var i = 0; i < that.items.length; ++i) {
      var item = that.items[i];
      if (item.info.curio && item.study) {
        total += item.info.exp;
      }
    }
    return total;
  };

  this.getProgress = function(id) {
    var progress = '';
    var item = $rootScope.findFirstWithProp(that.items, 'id', id);
    if (item !== undefined && item.meter !== undefined) {
      var minsLeft = item.info.time * (100 - item.meter) / 100;
      progress = v.sprintf(
        '%d%% (~%s left)',
        item.meter,
        $rootScope.minutesToHoursMinutes(minsLeft)
      );
    }
    return progress;
  };

  this.getPlayerName = function(playerId) {
    if (playerId === that.pgob) {
      return 'You';
    }
    return that.buddies[playerId] || '???';
  };

  this.parseTotalSecs = function(totalSecs) {
    var secsInDay = 60 * 60 * 24;
    var secsInHour = 60 * 60;

    var day = totalSecs / secsInDay;
    var secsToday = totalSecs % secsInDay;
    var hours = secsToday / secsInHour;
    var mins = (secsToday % secsInHour) / 60;

    return {
      day: day,
      secsToday: secsToday,
      hours: hours,
      mins: mins
    };
  };

  this.humanSecs = function(secs) {
    var times = that.parseTotalSecs(secs);
    return v.sprintf('Day %d, %02d:%02d', times.day, times.hours, times.mins);
  };

  this.getServerTime = function() {
    if (that.tm === undefined || that.epoch === undefined) {
      return '';
    }

    var now = (new Date).getTime();
    var raw = ((now - that.epoch) * 3) + (that.tm * 1000);
    if (that.lastrep === 0) {
      that.rgtime = raw;
    } else {
      var gd = (now - that.lastrep) * 3;
      that.rgtime += gd;
      if (Math.abs(that.rgtime + gd - raw) > 1000) {
        that.rgtime += ((raw - that.rgtime) * (1.0 - Math.pow(10.0, -(now - that.lastrep) / 1000.0)));
      }
    }
    that.lastrep = now;

    var totalSecs = that.rgtime / 1000;
    return that.humanSecs(totalSecs);
  };

  this.isDewyLadysMantleTime = function() {
    var totalSecs = that.rgtime / 1000;
    var times = that.parseTotalSecs(totalSecs);

    var dewyLadysMantleTimeStart = 4 * 60 * 60 + 45 * 60;
    var dewyLadysMantleTimeEnd = 7 * 60 * 60 + 15 * 60;

    return times.secsToday >= dewyLadysMantleTimeStart && times.secsToday <= dewyLadysMantleTimeEnd;
  };

  this.on = function(msgType, callback) {
    that.callbacks[msgType] = callback;
  };
})
