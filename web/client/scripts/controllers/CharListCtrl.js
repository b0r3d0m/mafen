'use strict';

angular.module('app').controller('CharListCtrl', function($scope, $location, $uibModalInstance, mafenSession) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.chooseCharacter = function(character) {
    $scope.mafenSession.send({
      action: 'play',
      data: {
        char_name: character
      }
    });
    $scope.close();
    $location.url('/');
  };

  $scope.close = function() {
    $uibModalInstance.dismiss('cancel');
  };
});
