'use strict';

angular.module('app').controller('LoginCtrl', function($rootScope, $scope, $uibModal, mafenSession, alertify, PATHS, CODES, $cookies, serverConnector) {
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
      if ($scope.rememberMe) requestToken();

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

  function requestToken() {
    var expireDate = new Date();
    expireDate.setFullYear(expireDate.getFullYear() + 1);

    var data = {
      username: $scope.user.username,
      password: $scope.user.password,
      type: 'requestToken'
    }

    var tryToRequestToken = serverConnector.auth(data);

    tryToRequestToken.then(function(res) {
      $cookies.putObject('token', res.data, {'expires': expireDate});
    }, function(err) {
      console.log(err);
    });
  }

  function checkToken(token) {
    var data = {
      token: token,
      type: 'checkToken'
    }

    var tryToCheckToken = serverConnector.auth(data);

    tryToCheckToken.then(function(res) {
      var loginPromise = createLoginConnect(res.data.username, res.data.password)

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
    }, function(err) {
      console.log(err);
    });
  }

  //attempt to auto login the user
  function autoLogin() {
    var token = $cookies.getObject('token');

    if (token && token != "") {
      checkToken(token);
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
