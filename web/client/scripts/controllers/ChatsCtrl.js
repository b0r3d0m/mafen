'use strict';

angular.module('app').controller('ChatsCtrl', function($rootScope, $scope, $timeout, mafenSession) {
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

    var activeChat = $scope.getChat($scope.mafenSession.activeChatId);
    if (activeChat.id !== msg.chat) {
      var chat = $scope.getChat(msg.chat);
      chat.unread = true;
    }
  });

  $scope.onChatSelect = function(chatId) {
    var chat = $scope.getChat(chatId);
    chat.unread = false;

    if ($scope.mafenSession.activeChatId === undefined) {
      $scope.mafenSession.activeChatId = mafenSession.chats[0].id;
    }

    $timeout(function() {
      $scope.mafenSession.activeChatId = chatId;
    });
  };

  $scope.closeChat = function(chatId) {
    $scope.mafenSession.send({
      action: 'closepmchat',
      data: {
        id: chatId
      }
    });
    $scope.mafenSession.chats = $scope.mafenSession.chats.filter(function(chat) {
      return chat.id !== chatId;
    });
  };

  $scope.inviteKin = function(kinId) {
    $scope.mafenSession.send({
      action: 'inv',
      data: {
        id: parseInt(kinId, 10)
      }
    });
    $scope.mafenSession.pwaiting = true;
    $scope.mafenSession.invitedKinId = kinId;
  };

  $scope.cancelInvitation = function(kinId) {
    $scope.mafenSession.send({
      action: 'cancelinv',
      data: {}
    });
    $scope.mafenSession.pwaiting = false;
    $scope.mafenSession.invitedKinId = undefined;
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
