'use strict';

angular.module('app').controller('WoundsCtrl', function($scope, $uibModal, mafenSession, PATHS) {
  'ngInject';

  $scope.mafenSession = mafenSession;

  $scope.healWound = function(wid) {
    $uibModal.open({
      ariaLabelledBy: 'charlist-modal-title',
      ariaDescribedBy: 'charlist-modal-body',
      templateUrl: PATHS.views + 'heal.html',
      controller: 'HealCtrl',
      resolve: {
        wid: function() {
          return wid;
        }
      }
    });
  };
});
