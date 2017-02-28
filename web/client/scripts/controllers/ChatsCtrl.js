'use strict';

angular.module('app').controller('ChatsCtrl', function($rootScope, $scope, mafenSession) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.inputMsgs = {};

  $scope.sendMsg = function(chatId) {
    $scope.mafenSession.send({
      action: 'msg',
      data: {
        id: chatId,
        msg: $scope.inputMsgs[chatId]
      }
    });
    $scope.inputMsgs[chatId] = '';
  };

  $scope.getChat = function(chatId) {
    return $rootScope.findFirstWithProp($scope.mafenSession.chats, 'id', chatId);
  };

  $scope.mafenSession.on('msg', function(msg) {
    if (msg.from !== 'You') {
      ion.sound.play('button_tiny');
    }

    var activeChat = $scope.getChat($scope.activeChatId);
    if (activeChat.id !== msg.chat) {
      var chat = $scope.getChat(msg.chat);
      chat.unread = true;
    }
  });

  $scope.onChatSelect = function(chatId) {
    $scope.activeChatId = chatId;
    var chat = $scope.getChat(chatId);
    chat.unread = false;
  };

  $scope.inviteKin = function(kinId) {
    $scope.mafenSession.send({
      action: 'inv',
      data: {
        id: parseInt(kinId, 10)
      }
    });
  };

  $scope.chatKin = function(kinId) {
    $scope.mafenSession.send({
      action: 'pmchat',
      data: {
        id: parseInt(kinId, 10)
      }
    });
  };
});
