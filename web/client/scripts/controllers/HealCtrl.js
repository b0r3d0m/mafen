'use strict';

angular.module('app').controller('HealCtrl', function($scope, $q, $timeout, $uibModalInstance, mafenSession, alertify, wid) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.mafenSession.on('flowermenu', function(msg) {
    alertify.confirm('Do you want to apply this item?', function() {
      // user clicked "ok"
      $scope.mafenSession.send({
        action: 'cl',
        data: {
          option: 0 // Select "Apply" -- this should be the only option in our case
        }
      });
      $scope.healDeferred.resolve();
    }, function() {
      // user clicked "cancel"
      $scope.mafenSession.send({
        action: 'cl',
        data: {
          option: -1
        }
      });
      $scope.healDeferred.reject('cancelled');
    });
  });

  $scope.applyToWound = function(item) {
    $scope.healDeferred = $q.defer();
    $scope.healDeferred.promise.then(function() {
      alertify.success('Success');
    }, function(reason) {
      $scope.mafenSession.send({
        action: 'drop',
        data: {
          coords: {
            x: item.coords.x,
            y: item.coords.y
          }
        }
      });
      if (reason !== 'cancelled') {
        alertify.error('Failed');
      }
    });

    $timeout(function() {
      $scope.healDeferred.reject();
    }, 5000);

    $scope.mafenSession.send({
      action: 'wiact',
      data: {
        iid: item.id,
        wid: wid
      }
    });
  };

  $scope.close = function() {
    if ($scope.healDeferred) {
      $scope.healDeferred.reject('cancelled');
    }
    $uibModalInstance.dismiss('cancel');
  };
});
