'use strict';

angular.module('app').controller('LoginCtrl', function($rootScope, $scope, $uibModal, mafenSession, alertify, PATHS, CODES, $cookies) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.user = {};

  var onclose = function(e) {
    if (e.code !== CODES.wsClosedByUser) {
      alertify.alert(
        "Lost connection to the server. Maybe you logged in to the game client.",
        $rootScope.logout);
    }
  };

  $scope.login = function() {
    var loginPromise = createLoginConnect($scope.user.username, $scope.user.password);
    loginPromise.then(function(e) {
      if ($scope.rememberMe) setCookies();

      $uibModal.open({
        ariaLabelledBy: 'charlist-modal-title',
        ariaDescribedBy: 'charlist-modal-body',
        templateUrl: PATHS.views + 'charlist.html',
        controller: 'CharListCtrl'
      });
    }, function() {
      alertify.error('Authentication failed');
    });
  };

  function setCookies() {
    var user = {
      username: $scope.user.username,
      password: $scope.user.password
    }

    var expireDate = new Date();
    expireDate.setFullYear(expireDate.getFullYear() + 1);

    $cookies.putObject('user', user, {'expires': expireDate});
  }

  //attempt to auto login the user
  function autoLogin() {
    var currentUser = $cookies.getObject('user');

    if (currentUser && currentUser != "") {
      var loginPromise = createLoginConnect(currentUser.username, currentUser.password)

      loginPromise.then(function() {
        $uibModal.open({
          ariaLabelledBy: 'charlist-modal-title',
          ariaDescribedBy: 'charlist-modal-body',
          templateUrl: PATHS.views + 'charlist.html',
          controller: 'CharListCtrl'
        });
      }, function() {
        alertify.error('Oops! Something went wrong');
      })
    }
  };

  function createLoginConnect(username, password) {
    $scope.mafenSession
      .reset()
      .connect('ws://mafen.club:8000')
      .wsOnClose(onclose);

    $scope.loginPromise = $scope.mafenSession.login(username, password);

    return $scope.loginPromise;
  };

  autoLogin();
});
