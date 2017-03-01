'use strict';

angular.module('app').controller('LoresCtrl', function($rootScope, $scope, mafenSession) {
  'ngInject';

  $scope.mafenSession = mafenSession;
});
