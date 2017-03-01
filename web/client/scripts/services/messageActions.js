'use strict';

var messageActions = {
  init: function($rootScope) {
    this.findFirstWithProp = $rootScope.findFirstWithProp;
  }
};

messageActions.attr = function(ms, msg) {
  ms.attrs = msg.attrs;
};

messageActions.buddy = function(ms, msg) {
  ms.buddies[msg.id] = msg.name;
};

messageActions.connect = function(ms, msg) {
  if (msg.success) {
    ms.loggedIn = true;
    ms.loginDeferred.resolve();
  } else {
    ms.loginDeferred.reject();
  }
};

messageActions.character = function(ms, msg) {
  ms.characters.push(msg.name);
};

messageActions.destroy = function(ms, msg) {
  ms.items = ms.items.filter(function(item) {
    return item.id !== msg.id;
  });
  delete ms.meters[msg.id];
};

messageActions.enc = function(ms, msg) {
  ms.enc = msg.enc;
};

messageActions.exp = function(ms, msg) {
  ms.exp = msg.exp;
};

messageActions.item = function(ms, msg) {
    if (ms.meters[msg.id] !== undefined) {
      msg.meter = ms.meters[msg.id];
      delete ms.meters[msg.id];
    }
    ms.items.push(msg);
};

messageActions.gobrem = function(ms, msg) {
  ms.players = ms.players.filter(function(playerId) {
    return playerId !== msg.id;
  });
  delete ms.buddies[msg.id];
};

messageActions.kinadd = messageActions.kinupd = function(ms, msg) {
  ms.kins[msg.id] = {
    name: msg.name,
    online: msg.online
  };
};

messageActions.kinchst = function(ms, msg) {
  if (msg.id in ms.kins) {
    ms.kins[msg.id].online = msg.online;
  }
};

messageActions.kinrm = function(ms, msg) {
  delete ms.kins[msg.id];
};

messageActions.mchat = function(ms, msg) {
  ms.chats.push({
    id: msg.id,
    name: msg.name,
    closable: false
  });
};

messageActions.meter = function(ms, msg) {
  var item = this.findFirstWithProp(ms.items, 'id', msg.id);
  if (item !== undefined) {
    item.meter = msg.meter;
  } else {
    ms.meters[msg.id] = msg.meter;
  }
};

messageActions.msg = function(ms, msg) {
  (ms.msgs[msg.chat] = ms.msgs[msg.chat] || []).push({
    from: msg.from,
    text: msg.text
  });
};

messageActions.party = function(ms, msg) {
  ms.pmembers = msg.members;
};

messageActions.pchat = function(ms, msg) {
  ms.chats.push({
    id: msg.id,
    name: 'Party',
    closable: false
  });
};

messageActions.pchatrm = function(ms, msg) {
  ms.chats = ms.chats.filter(function(chat) {
    return chat.id !== msg.id;
  });
};

messageActions.pgob = function(ms, msg) {
  ms.pgob = msg.id;
};

messageActions.player = function(ms, msg) {
  ms.players.push(msg.id);
};

messageActions.pmchat = function(ms, msg) {
  ms.chats.push({
    id: msg.id,
    name: msg.other,
    closable: true
  });
};

messageActions.time = function(ms, msg) {
  ms.tm = msg.time;
  ms.epoch = msg.epoch;
  if (!msg.inc) {
    ms.lastrep = 0;
  }
};

module.exports = messageActions;
