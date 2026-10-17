// Copy only round 35's new upper-right pigment onto the inherited wall.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decode, encode, thumbnail} = require('./finish-wall.cjs');

const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const oldBytes = fs.readFileSync('artifacts/line-1/wall.png');
if (hash(oldBytes) !== '5d924d234c8f677d2223f0809174718248dcfdd6e22f52524e1aea0e19a35146') {
  throw Error('inherited wall does not match round 34');
}
const newBytes = fs.readFileSync('artifacts/line-1/wall-v16.png');
const old = decode(oldBytes);
const edited = decode(newBytes);
if (old.width !== 1254 || old.height !== 1254 ||
    old.width !== edited.width || old.height !== edited.height) {
  throw Error('wall dimensions changed');
}
const result = {...old, pixels: Buffer.from(old.pixels)};
const bounds = {left: 934, top: 258, right: 1060, bottom: 357};
const feather = 7;
let changed = 0, protectedPixels = 0, outsideMaskChanged = 0;
for (let y = 0; y < old.height; y++) for (let x = 0; x < old.width; x++) {
  const alpha = Math.max(0, Math.min(1,
    (x-bounds.left)/feather, (bounds.right-x)/feather,
    (y-bounds.top)/feather, (bounds.bottom-y)/feather));
  if (!alpha) protectedPixels++;
  const at = (y*old.width+x)*3;
  let differs = false;
  for (let c = 0; c < 3; c++) {
    result.pixels[at+c] = Math.round(old.pixels[at+c]*(1-alpha) + edited.pixels[at+c]*alpha);
    differs ||= result.pixels[at+c] !== old.pixels[at+c];
  }
  if (!alpha && differs) outsideMaskChanged++;
  if (differs) changed++;
}
if (outsideMaskChanged !== 0 || changed < 1000) throw Error('addition mask failed');
const png = encode(result), jpeg = thumbnail(result);
if (!decode(png).pixels.equals(result.pixels)) throw Error('PNG round trip failed');
if (jpeg.length > 100000) throw Error('JPEG exceeds 100 KB');
fs.writeFileSync('artifacts/line-1/wall-v16.png', png);
fs.writeFileSync('artifacts/line-1/wall.png', png);
fs.writeFileSync('dist/line-1/35.jpg', jpeg);
const report = {previous_sha256: hash(oldBytes), sha256: hash(png),
  format: 'PNG', width: old.width, height: old.height, png_bytes: png.length,
  preview_format: 'JPEG', preview_width: 512, preview_height: 512,
  preview_bytes: jpeg.length, bounds, feather_pixels: feather,
  changed_pixels: changed, protected_pixels: protectedPixels,
  total_pixels: old.width*old.height,
  outside_mask_changed_pixels: outsideMaskChanged,
  png_roundtrip_passed: true};
fs.writeFileSync('line-1/media-check-35.json', JSON.stringify(report, null, 2)+'\n');
console.log(JSON.stringify(report, null, 2));
