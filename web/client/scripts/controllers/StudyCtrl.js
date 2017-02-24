'use strict';

angular.module('app').controller('StudyCtrl', function($rootScope, $scope, mafenSession) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.transferItem = function(id) {
    $scope.mafenSession.send({
      action: 'transfer',
      data: {
        id: id
      }
    });
  };
});
