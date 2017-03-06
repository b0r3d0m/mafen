'use strict';

angular.module('app').service('serverConnector', function($http, $q) {
  'ngInject';

  this.auth = function(data) {
    var deferred = $q.defer();

    $http({
      method: 'POST',
      url: '/auth',
      data: data
    }).then(function successCallback(res) {
      deferred.resolve(res);
    }, function errorCallback(err) {
      deferred.reject(err);
    });

    return deferred.promise
  }
});