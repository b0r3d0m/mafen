'use strict';

var watchify = require('watchify');
var browserify = require('browserify');
var gulp = require('gulp');
var source = require('vinyl-source-stream');
var gutil = require('gulp-util');
var ngAnnotate = require('browserify-ngannotate');

var path = require('path');
var fse = require('fs-extra');

function bundleScript(watch) {
  var b = browserify({
    entries: ['./client/scripts/app.js'],
    debug: true,
    cache: {},
    packageCache: {}
  });
  b.transform(ngAnnotate);
  b.transform('browserify-css', {
        global: true,
        processRelativeUrl: function(relativeUrl) {
          // 'browserify-css' docs: https://github.com/cheton/browserify-css#2-how-do-i-load-font-and-image-files-from-node_modules
          var stripQueryStringAndHashFromPath = function(url) {
              return url.split('?')[0].split('#')[0];
          };
          var relativePath = stripQueryStringAndHashFromPath(relativeUrl);
          var queryStringAndHash = relativeUrl.substring(relativePath.length);
          var rootDir = path.resolve(process.cwd());

          var prefix = 'node_modules';
          var indexOfPrefix = relativePath.indexOf(prefix); // 'relativePath' like '../../../node_modules/bootstrap..'
          if (indexOfPrefix >= 0) {
            relativePath = relativePath.substring(indexOfPrefix); // 'relativePath' now 'node_modules/bootstrap..'
            var vendorPath = path.join('vendor', relativePath.substring(prefix.length)); // 'vendorPath' now 'vendor/bootstrap..'
            var source = path.join(rootDir, relativePath);
            var target = path.join(rootDir, 'client', vendorPath); // put 'vendor/bootstrap..' in 'client' folder

            fse.copySync(source, target);

            return vendorPath + queryStringAndHash;
          }
          return relativeUrl;
        }
    })

  b.plugin('minifyify', { map: 'bundle.js.map', output: './client/bundle.js.map' });
  if (watch) {
    b.plugin(watchify);
  }

  function bundle() {
    return b.bundle()
      .on('error', gutil.log.bind(gutil, 'Browserify Error'))
      .pipe(source('bundle.js'))
      .pipe(gulp.dest('./client'));
  }

  b.on('update', bundle);
  b.on('log', gutil.log);

  return bundle();
}

gulp.task('bundle-js', function() {
  return bundleScript(false);
});

gulp.task('default', ['bundle-js'], function() {
  return bundleScript(true);
});
