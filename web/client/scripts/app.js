'use strict';

require('@cgross/angular-busy/dist/angular-busy.min.css');
require('angular-tablesort/tablesort.css');
require('bootstrap/dist/css/bootstrap.min.css');

require('angular');
require('@cgross/angular-busy/dist/angular-busy.min.js');
require('angularjs-scroll-glue/src/scrollglue.js');
require('angular-css');
require('angular-route');
require('angular-tablesort');
require('angular-toarrayfilter/toArrayFilter.js');
require('angular-ui-bootstrap/dist/ui-bootstrap-tpls.js');
require('alertify.js/dist/js/ngAlertify.js');
require('ion-sound/js/ion.sound.min.js');

var app = angular.module('app', ['ngAlertify', 'ngRoute', 'ui.bootstrap', 'cgBusy', 'tableSort', 'angularCSS', 'luegg.directives', 'angular-toArrayFilter'])
.constant('PATHS', {
  views: '/views/',
  styles: '/styles/',
  assets: '/assets/'
})
.constant('CODES', {
  wsClosedByUser: 4000  // code for CloseEvent object (4000–4999 available for use by applications)
})
.config(function($routeProvider, $locationProvider, PATHS) {
  'ngInject';

  var checkLoggedIn = function($q, $location, mafenSession) {
    'ngInject';

    var deferred = $q.defer();

    if (mafenSession.loggedIn) {
      deferred.resolve();
    } else {
      deferred.reject();
      $location.url('/login');
    }

    return deferred.promise;
  };

  $routeProvider
    .when('/study', {
      templateUrl: PATHS.views + 'study.html',
      controller: 'StudyCtrl',
      css: [
        PATHS.styles + 'header.css',
        PATHS.styles + 'footer.css',
        PATHS.styles + 'study.css',
        PATHS.styles + 'common.css'
      ],
      resolve: {
        loggedin: checkLoggedIn
      }
    })
    .when('/chats', {
      templateUrl: PATHS.views + 'chats.html',
      controller: 'ChatsCtrl',
      css: [
        PATHS.styles + 'header.css',
        PATHS.styles + 'footer.css',
        PATHS.styles + 'chats.css',
        PATHS.styles + 'common.css'
      ],
      resolve: {
        loggedin: checkLoggedIn
      }
    })
    .when('/attrs', {
      templateUrl: PATHS.views + 'attrs.html',
      controller: 'AttrsCtrl',
      css: [
        PATHS.styles + 'header.css',
        PATHS.styles + 'footer.css',
        PATHS.styles + 'attrs.css',
        PATHS.styles + 'common.css'
      ],
      resolve: {
        loggedin: checkLoggedIn
      }
    })
    .when('/lores', {
      templateUrl: PATHS.views + 'lores.html',
      controller: 'LoresCtrl',
      css: [
        PATHS.styles + 'header.css',
        PATHS.styles + 'footer.css',
        PATHS.styles + 'lores.css',
        PATHS.styles + 'common.css'
      ],
      resolve: {
        loggedin: checkLoggedIn
      }
    })
    .when('/wounds', {
      templateUrl: PATHS.views + 'wounds.html',
      controller: 'WoundsCtrl',
      css: [
        PATHS.styles + 'header.css',
        PATHS.styles + 'footer.css',
        PATHS.styles + 'wounds.css',
        PATHS.styles + 'common.css'
      ],
      resolve: {
        loggedin: checkLoggedIn
      }
    })
    .when('/misc', {
      templateUrl: PATHS.views + 'misc.html',
      controller: 'MiscCtrl',
      css: [
        PATHS.styles + 'header.css',
        PATHS.styles + 'footer.css',
        PATHS.styles + 'misc.css'
      ],
      resolve: {
        loggedin: checkLoggedIn
      }
    })
    .when('/login', {
      templateUrl: PATHS.views + 'login.html',
      controller: 'LoginCtrl',
      css: [
        PATHS.styles + 'login.css',
        PATHS.styles + 'ribbons.css',
        PATHS.styles + 'hue.css',
        PATHS.styles + 'common.css'
      ]
    })
    .otherwise({
      redirectTo: '/study'
    });

  ion.sound({
    sounds: [{
      name: 'button_tiny'
    }],
    path: PATHS.assets + 'sounds/'
  });
})
.run(function($rootScope, $location, $interval, mafenSession) {
  'ngInject';

  $rootScope.minutesToHoursMinutes = function(totalMins) {
    var hours = Math.floor(totalMins / 60);
    var minutes = totalMins % 60;
    return hours + ':' + parseInt(minutes, 10);
  };

  $rootScope.findFirstWithProp = function(arr, prop, val) {
    return arr.filter(function(obj) {
      return obj[prop] === val;
    })[0];
  };

  $rootScope.isCurrentPage = function(path) {
    return path === $location.path();
  };

  $rootScope.logout = function() {
    mafenSession.close();
    mafenSession.loggedIn = false;
    $location.url('/login');
  };

  $interval(function() {
    $rootScope.serverTime = mafenSession.getServerTime();
    $rootScope.isDewyLadysMantleTime = mafenSession.isDewyLadysMantleTime();
  }, 1000);
});

require('./controllers/AttrsCtrl.js');
require('./controllers/CharListCtrl.js');
require('./controllers/ChatsCtrl.js');
require('./controllers/LoginCtrl.js');
require('./controllers/LoresCtrl.js');
require('./controllers/MiscCtrl.js');
require('./controllers/StudyCtrl.js');
require('./controllers/WoundsCtrl.js');
require('./services/mafenSession.js');
