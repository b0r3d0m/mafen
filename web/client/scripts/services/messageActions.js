'use strict';

var messageActions = {
  init: function($rootScope) {
    this.findFirstWithProp = $rootScope.findFirstWithProp;
  }
};

messageActions.connect = function(that, msg) {
  if (msg.success) {
    that.loggedIn = true;
    that.loginDeferred.resolve();
  } else {
    that.loginDeferred.reject();
  }
};

messageActions.character = function(that, msg) {
  that.characters.push(msg.name);
};

messageActions.item = function(that, msg) {
  that.items.push(msg);
};

messageActions.destroy = function(that, msg) {
  that.items = that.items.filter(function(item) {
    return item.id !== msg.id;
  });
  delete that.meters[msg.id];
};

messageActions.attr = function(that, msg) {
  that.attrs = msg.attrs;
};

messageActions.meter = function(that, msg) {
  that.meters[msg.id] = msg.meter;
};

messageActions.mchat = function(that, msg) {
  that.chats.push({
    id: msg.id,
    name: msg.name
  });
};

messageActions.pchat = function(that, msg) {
  that.chats.push({
    id: msg.id,
    name: 'Party'
  });
};

messageActions.pmchat = function(that, msg) {
  that.chats.push({
    id: msg.id,
    name: msg.other
  });
};

messageActions.pchatrm = function(that, msg) {
  that.chats = that.chats.filter(function(chat) {
    return chat.id !== msg.id;
  });
};

messageActions.msg = function(that, msg) {
  (that.msgs[msg.chat] = that.msgs[msg.chat] || []).push({
    from: msg.from,
    text: msg.text
  });
};

messageActions.player = function(that, msg) {
  that.players.push(msg.id);
};

messageActions.buddy = function(that, msg) {
  that.buddies[msg.id] = msg.name;
};

messageActions.pgob = function(that, msg) {
  that.pgob = msg.id;
};

messageActions.gobrem = function(that, msg) {
  that.players = that.players.filter(function(playerId) {
    return playerId !== msg.id;
  });
  delete that.buddies[msg.id];
};

messageActions.enc = function(that, msg) {
  that.enc = msg.enc;
};

messageActions.exp = function(that, msg) {
  that.exp = msg.exp;
};

messageActions.time = function(that, msg) {
  that.tm = msg.time;
  that.epoch = msg.epoch;
  if (!msg.inc) {
    that.lastrep = 0;
  }
};

messageActions.kinadd = messageActions.kinupd = function(that, msg) {
  that.kins[msg.id] = {
    name: msg.name,
    online: msg.online
  };
};

messageActions.kinchst = function(that, msg) {
  if (msg.id in that.kins) {
    that.kins[msg.id].online = msg.online;
  }
};

messageActions.kinrm = function(that, msg) {
  delete that.kins[msg.id];
};

module.exports = messageActions;
