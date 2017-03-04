'use strict';

angular.module('app').controller('MiscCtrl', function($scope, mafenSession, alertify) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.mafenSession.on('clicknearest', function(msg) {
    if (!msg.success) {
      alertify.error(msg.reason);
    } else {
      alertify.success('Success!');
    }
  });

  $scope.clickNearest = function(objName) {
    $scope.mafenSession.send({
      action: 'clicknearest',
      data: {
        name: objName
      }
    });
  };
});
