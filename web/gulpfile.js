'use strict';

var watchify = require('watchify');
var browserify = require('browserify');
var gulp = require('gulp');
var source = require('vinyl-source-stream');
var gutil = require('gulp-util');
var ngAnnotate = require('browserify-ngannotate');

function bundleScript(watch) {
  var b = browserify({
    entries: ['./client/scripts/app.js'],
    debug: true,
    cache: {},
    packageCache: {}
  });
  b.transform(ngAnnotate);
  b.transform('browserify-css', { global: true });
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
