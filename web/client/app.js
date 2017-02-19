'use strict';

require('bootstrap/dist/css/bootstrap.min.css');
require('./ribbons.css');
require('./hue.css');
require('./app.css');

require('angular');
require('angular-route');
require('angular-ui-bootstrap/dist/ui-bootstrap-tpls.js');

// TODO
var loggedIn = false;

var app = angular.module('app', ['ngRoute', 'ui.bootstrap'])
.config(function($routeProvider, $locationProvider) {
  'ngInject';

  var checkLoggedin = function($q, $location) {
    'ngInject';

    // TODO: remove defer
    var deferred = $q.defer();

    if (loggedIn) {
      deferred.resolve();
    } else {
      deferred.reject();
      $location.url('/login');
    }

    return deferred.promise;
  };

  $routeProvider
    .when('/', {
      templateUrl: 'main.html',
      controller: 'MainCtrl',
      resolve: {
        loggedin: checkLoggedin
      }
    })
    .when('/login', {
      templateUrl: 'login.html',
      controller: 'LoginCtrl'
    })
    .otherwise({
      redirectTo: '/'
    });
})
.run(function($rootScope, $location, $uibModal) {
  'ngInject';

  $rootScope.logout = function() {
    // TODO: Close WebSocket
    $location.url('/login');
  };

  // TODO: Move the following code to the service

  $rootScope.characters = [];
  $rootScope.items = [];
  $rootScope.attrs = {};

  $rootScope.ws = new WebSocket('ws://127.0.0.1:8000');

  $rootScope.ws.onmessage = function(message) {
    console.log(message.data); // TODO: rm

    var msg = JSON.parse(message.data);

    if (msg.action === 'connect') {
      if (msg.success) {
        $uibModal.open({
          ariaLabelledBy: 'charlist-modal-title',
          ariaDescribedBy: 'charlist-modal-body',
          templateUrl: 'CharacterListModalContent.html',
          controller: 'CharacterListModalCtrl',
          controllerAs: '$ctrl',
          size: 'lg'
        });
        loggedIn = true;
      } else {
        // TODO: Show alert
      }
    } else if (msg.action === 'character') {
      $rootScope.characters.push(msg.name);
    } else if (msg.action === 'item') {
      $rootScope.items.push(msg);
    } else if (msg.action === 'destroy') {
      $rootScope.items = $rootScope.items.filter(function(item) {
        return item.id !== msg.id;
      });
    } else if (msg.action === 'attr') {
      $rootScope.attrs = msg.attrs;
    } else {
      // TODO
    }
    $rootScope.$apply();
  };

  $rootScope.getTotalMW = function() {
    var total = 0;
    for (var i = 0; i < $rootScope.items.length; ++i) {
      var item = $rootScope.items[i];
      if (item.info.curio && item.study) {
        total += item.info.mw;
      }
    }
    return total;
  };
});

app.controller('LoginCtrl', function($rootScope, $scope, $location) {
  'ngInject';

  $scope.user = {};

  $scope.login = function() {
    $rootScope.ws.send(JSON.stringify({
      action: 'connect',
      data: {
        username: $scope.user.username,
        password: $scope.user.password // TODO: SHA-256
      }
    }));
  };
});

app.controller('MainCtrl', function($rootScope, $scope) {
  'ngInject';

  $scope.transferItem = function(id) {
    $rootScope.ws.send(JSON.stringify({
      action: 'transfer',
      data: {
        id: id
      }
    }));
  };
});

app.controller('CharacterListModalCtrl', function($rootScope, $location, $uibModalInstance) {
  'ngInject';

  var $ctrl = this;

  $ctrl.chooseCharacter = function(character) {
    $rootScope.ws.send(JSON.stringify({
      action: 'play',
      data: {
        char_name: character
      }
    }));
    $ctrl.close();
    $location.url('/');
  };

  $ctrl.close = function() {
    $uibModalInstance.dismiss('cancel');
  };
});
