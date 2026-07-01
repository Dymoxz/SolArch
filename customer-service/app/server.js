const { createServer } = require('node:http');
const { handleRoutes } = require('./routes');

const hostname = '0.0.0.0';
const port = 3000;

const server = createServer((req, res) => {
    // Forward all application traffic into our main router
    handleRoutes(req, res);
});

server.listen(port, hostname, () => {
    console.log(`Customer Service microserver listening at http://localhost:${port}/`);
});