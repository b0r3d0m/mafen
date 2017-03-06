var path = require('path');
var bodyParser = require('body-parser');
var jwt = require('jsonwebtoken');

// Read config
var nconf = require('nconf');
nconf.file({ file: path.join(__dirname, 'config.json') });

// Initialize Express
var express = require('express');
var app = express();

// Configure views
var pug = require('pug');
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'pug');

// Serve static files
app.use(express.static('client'));

// Configure middlewares
var favicon = require('serve-favicon');
app.use(favicon('./client/assets/icons/favicon.ico'));
app.use(bodyParser.json());

// Define routes
app.get('/', function(req, res) {
  res.render('index');
});

app.post('/auth', function (req, res) {
  if (req.body.type === 'requestToken') {
    var data = jwt.sign(req.body, nconf.get('general').secret);
  } else {
    var data = jwt.verify(req.body.token, nconf.get('general').secret);
  }
  
  res.send(data);
});

// Start server
var port = nconf.get('general').port;
var http = require('http');
var server = http.createServer(app).listen(port, function() {
  console.log('App is started at PORT ' + port);
});

// Export some stuff for tests
var cleanup = function() {
  server.close();
}
module.exports = server;
module.exports.cleanup = cleanup;
