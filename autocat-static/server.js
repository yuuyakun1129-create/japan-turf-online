const http = require('http');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const dir = __dirname;
const parts = ['00','01','02','03','04']
  .map(n => fs.readFileSync(path.join(dir, `sitepart_${n}.txt`), 'utf8'))
  .join('');
const html = zlib.gunzipSync(Buffer.from(parts, 'base64'));
const port = Number(process.env.PORT || 3000);

http.createServer((req, res) => {
  if (req.url === '/' || req.url === '/index.html' || req.url.startsWith('/?')) {
    res.writeHead(200, {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store'
    });
    res.end(html);
    return;
  }
  res.writeHead(404, {'Content-Type':'text/plain; charset=utf-8'});
  res.end('Not Found');
}).listen(port, '0.0.0.0', () => console.log(`AUTOCAT static listening on ${port}`));
