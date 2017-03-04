'use strict';

angular.module('app').controller('MiscCtrl', function($scope, mafenSession) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.clickNearest = function(objName) {
    $scope.mafenSession.send({
      action: 'clicknearest',
      data: {
        name: objName
      }
    });
  };
});
