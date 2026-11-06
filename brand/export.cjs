/* Export the shared SVG master into platform-sized PNG files. No network calls. */
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const { Resvg } = require(process.argv[2]
  ? path.resolve(process.argv[2]) : path.join(root, '.brand-tools/node_modules/@resvg/resvg-js'));
const { PNG } = require(require.resolve('pngjs', { paths: [process.argv[2]
  ? path.resolve(process.argv[2]) : path.join(root, '.brand-tools/node_modules')] }));
const bg = '#0B1016', lime = '#C9F84A';
const master = fs.readFileSync(path.join(__dirname, 'mark.svg'), 'utf8');
const markPath = master.match(/d="(M140[^"]+)"/)[1];
const fontOptions = { loadSystemFonts: true, defaultFontFamily: 'Arial' };
function svg(width, height, content, background = false) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">${background ? `<rect width="100%" height="100%" fill="${bg}"/>` : ''}${content}</svg>`;
}
function mark(x, y, scale, color = lime) {
  return `<path fill="${color}" transform="translate(${x} ${y}) scale(${scale})" d="${markPath}"/>`;
}
function write(file, content) {
  const target = path.join(root, file); fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content);
}
function png(file, content, width) {
  write(file, new Resvg(content, { font: fontOptions, ...(width ? { fitTo: { mode: 'width', value: width } } : {}) }).render().asPng());
}
function lockup(file) {
  const source = fs.readFileSync(path.join(__dirname, file), 'utf8')
    .replace(/d="M140[^"]+"/, `d="${markPath}"`);
  write('brand/' + file, source);
  return source;
}
const stacked = lockup('logo-stacked.svg');
const horizontal = lockup('logo-horizontal.svg');
png('brand/logo-stacked.png', stacked, 1000);
png('brand/logo-horizontal.png', horizontal, 1600);
png('brand/mark.png', master, 600);
png('brand/logo-on-charcoal.png', stacked.replace(/(<svg[^>]*>)/, '$1<rect width="100%" height="100%" fill="#0B1016"/>'), 1000);
const icon = svg(1024, 1024, mark(227, 189, .95), true);
png('mobile/assets/icon.png', icon);
png('brand/store/google-play-icon.png', icon, 512);
// Entire symbol fits within the central 66/108 circle, including its extreme corners.
const adaptive = svg(1080, 1080, mark(330, 302, .7));
png('mobile/assets/adaptive-foreground.png', adaptive);
png('mobile/assets/adaptive-monochrome.png', svg(1080, 1080, mark(330, 302, .7, '#FFFFFF')));
png('mobile/assets/splash-mark.png', svg(1080, 1080, mark(330, 302, .7)));
png('mobile/assets/favicon.png', icon, 64);
png('mobile/assets/logo-horizontal.png', horizontal, 1200);
const banner = svg(1280, 400, mark(110, 81, .35) + '<text x="390" y="242" fill="#C9F84A" font-family="Arial, sans-serif" font-size="142" font-weight="700" letter-spacing="-4">SlipSavvy</text>', true);
write('docs/assets/banner.svg', banner);
png('brand/banner.png', banner);
const feature = svg(1024, 500, mark(105, 131, .35) + '<text x="385" y="289" fill="#C9F84A" font-family="Arial, sans-serif" font-size="108" font-weight="700" letter-spacing="-3">SlipSavvy</text>', true);
png('brand/store/google-play-feature.png', feature);
// Play feature graphics use RGB PNG, while app/listing icons retain RGBA PNG.
const featureFile = path.join(root, 'brand/store/google-play-feature.png');
fs.writeFileSync(featureFile, PNG.sync.write(PNG.sync.read(fs.readFileSync(featureFile)), { colorType: 2 }));
png('brand/social-preview.png', svg(1200, 630, mark(125, 179, .4) + '<text x="425" y="357" fill="#C9F84A" font-family="Arial, sans-serif" font-size="132" font-weight="700" letter-spacing="-4">SlipSavvy</text>', true));
write('site/assets/banner.svg', banner);
write('site/assets/mark.svg', master);
write('site/assets/logo-horizontal.svg', horizontal);
write('site/assets/favicon.png', fs.readFileSync(path.join(root, 'mobile/assets/favicon.png')));
console.log('Exported SlipSavvy brand assets.');
