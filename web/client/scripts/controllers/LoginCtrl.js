'use strict';

angular.module('app').controller('LoginCtrl', function($scope, $uibModal, mafenSession, alertify, PATHS) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.user = {};

  $scope.login = function() {
    $scope.mafenSession.reset();
    $scope.mafenSession.connect('ws://127.0.0.1:8000');
    $scope.loginPromise = $scope.mafenSession.login($scope.user.username, $scope.user.password);
    $scope.loginPromise.then(function() {
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
});
